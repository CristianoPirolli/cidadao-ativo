"""
Serviço de geocoding
Converte coordenadas (lat/lng) em endereço usando Nominatim (OpenStreetMap)
"""
import re
import unicodedata

import requests

from apps.locations.services.ibge import find_municipio, get_all_municipios


class GeocodingService:
    """Serviço para geocoding reverso usando Nominatim"""

    # URL do Nominatim (OpenStreetMap)
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

    # User-Agent obrigatório para Nominatim
    USER_AGENT = "CidadaoAtivo/1.0 (contato@cidadaoativo.com)"

    @staticmethod
    def reverse_geocode(lat: float, lng: float) -> dict | None:
        """
        Converte coordenadas em endereço

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            Dict com informações do local ou None
        """
        try:
            params = {
                "lat": lat,
                "lon": lng,
                "format": "json",
                "addressdetails": 1,
                "accept-language": "pt-BR,pt",
            }

            headers = {
                "User-Agent": GeocodingService.USER_AGENT
            }

            response = requests.get(
                GeocodingService.NOMINATIM_URL,
                params=params,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"Erro Nominatim: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Erro ao fazer geocoding: {e}")
            return None

    @staticmethod
    def get_city_from_coords(lat: float, lng: float) -> dict | None:
        """
        Extrai município e UF das coordenadas

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            Dict com {municipio, uf, municipio_ibge_id} ou None
        """
        data = GeocodingService.reverse_geocode(lat, lng)

        if not data or "address" not in data:
            return None

        address = data["address"]

        # Tentar extrair cidade de vários campos possíveis
        # Ordem de prioridade: city > town > village > municipality > county
        # Note: "municipality" às vezes retorna "Região Geográfica" ao invés do nome real do município
        city = None
        field_priority = ["city", "town", "village", "municipality", "county"]

        for field in field_priority:
            if field in address and address[field]:
                potential_city = address[field]

                # Filtrar nomes que claramente não são municípios
                if 'região geográfica' in potential_city.lower():
                    print(f"[Geocoding] Ignorando '{field}': {potential_city} (parece ser uma região, não um município)")
                    continue

                city = potential_city
                print(f"[Geocoding] Município extraído do campo '{field}': {city}")
                break

        # Se ainda não achou, tentar city_district como último recurso
        if not city and "city_district" in address:
            city = address["city_district"]
            print(f"[Geocoding] Município extraído de 'city_district': {city}")

        # Extrair estado
        state = address.get("state", None)

        if not city or not state:
            print(f"[Geocoding] Não foi possível extrair município ou estado. City: {city}, State: {state}")
            return None

        # Tentar encontrar UF (sigla do estado)
        uf = GeocodingService._get_uf_from_state_name(state)

        if not uf:
            print(f"[Geocoding] UF não encontrada para estado: {state}")
            return {
                "municipio": city,
                "uf": None,
                "uf_nome": state,
                "municipio_ibge_id": None,
                "raw_address": address
            }

        # Estratégia de busca em cascata:
        # 1. Buscar correspondência exata primeiro
        municipio_ibge = find_municipio(city, uf)

        # 2. Se não encontrou, tentar fuzzy matching
        if not municipio_ibge:
            print(f"[Geocoding] Match exato não encontrado para '{city}/{uf}', tentando fuzzy matching...")
            municipio_ibge = GeocodingService.fuzzy_search_municipio(city, uf)

        if municipio_ibge:
            print(f"[Geocoding] Município encontrado no IBGE: {municipio_ibge['nome']}/{municipio_ibge['uf']} (ID: {municipio_ibge['id']})")
            return {
                "municipio": municipio_ibge["nome"],  # Usar nome oficial do IBGE
                "uf": municipio_ibge["uf"],
                "uf_nome": state,
                "municipio_ibge_id": municipio_ibge["id"],
                "municipio_completo": municipio_ibge["nome_completo"],
                "raw_address": address,
                "original_name": city  # Nome original retornado pelo Nominatim
            }
        else:
            print(f"[Geocoding] Município '{city}/{uf}' não encontrado na base do IBGE")
            return {
                "municipio": city,
                "uf": uf,
                "uf_nome": state,
                "municipio_ibge_id": None,
                "municipio_completo": f"{city}/{uf}",
                "raw_address": address
            }

    @staticmethod
    def _get_uf_from_state_name(state_name: str) -> str | None:
        """
        Converte nome do estado em sigla UF

        Args:
            state_name: Nome do estado (ex: "São Paulo")

        Returns:
            Sigla da UF (ex: "SP") ou None
        """
        estados = {
            "Acre": "AC",
            "Alagoas": "AL",
            "Amapá": "AP",
            "Amazonas": "AM",
            "Bahia": "BA",
            "Ceará": "CE",
            "Distrito Federal": "DF",
            "Espírito Santo": "ES",
            "Goiás": "GO",
            "Maranhão": "MA",
            "Mato Grosso": "MT",
            "Mato Grosso do Sul": "MS",
            "Minas Gerais": "MG",
            "Pará": "PA",
            "Paraíba": "PB",
            "Paraná": "PR",
            "Pernambuco": "PE",
            "Piauí": "PI",
            "Rio de Janeiro": "RJ",
            "Rio Grande do Norte": "RN",
            "Rio Grande do Sul": "RS",
            "Rondônia": "RO",
            "Roraima": "RR",
            "Santa Catarina": "SC",
            "São Paulo": "SP",
            "Sergipe": "SE",
            "Tocantins": "TO"
        }

        # Buscar case-insensitive
        state_lower = state_name.lower().strip()
        for nome, sigla in estados.items():
            if nome.lower() == state_lower:
                return sigla

        return None

    @staticmethod
    def validate_coords(lat: float, lng: float) -> bool:
        """
        Valida se coordenadas estão dentro do Brasil (aproximadamente)

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            True se coordenadas parecem estar no Brasil
        """
        # Brasil aproximadamente: lat -33 a 5, lng -74 a -34
        if lat < -35 or lat > 6:
            return False
        if lng < -75 or lng > -30:
            return False
        return True

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normaliza texto removendo acentos, convertendo para minúsculas
        e removendo caracteres especiais

        Args:
            text: Texto para normalizar

        Returns:
            Texto normalizado
        """
        if not text:
            return ""

        # Converter para minúsculas
        text = text.lower().strip()

        # Remover acentos/diacríticos
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ASCII', 'ignore').decode('ASCII')

        # Remover caracteres especiais extras, manter apenas letras, números e espaços
        text = re.sub(r'[^a-z0-9\s]', '', text)

        # Normalizar espaços múltiplos
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    @staticmethod
    def fuzzy_search_municipio(municipio_name: str, uf: str) -> dict | None:
        """
        Busca município com correspondência aproximada (fuzzy matching)

        Estratégia de busca em ordem:
        1. Correspondência exata (já tentada antes de chamar esta função)
        2. Correspondência normalizada (sem acentos, minúsculas)
        3. Correspondência parcial (começa com o nome buscado)
        4. Correspondência por palavras-chave principais

        Args:
            municipio_name: Nome do município para buscar
            uf: Sigla da UF

        Returns:
            Dict com dados do município ou None
        """
        if not municipio_name or not uf:
            return None

        # Normalizar os termos de busca
        search_normalized = GeocodingService.normalize_text(municipio_name)
        uf_normalized = uf.upper().strip()

        # Buscar todos os municípios do estado
        all_municipios = get_all_municipios()
        municipios_uf = [m for m in all_municipios if m.get('uf', '').upper() == uf_normalized]

        if not municipios_uf:
            return None

        # 1. Tentar correspondência normalizada exata
        for m in municipios_uf:
            nome_norm = GeocodingService.normalize_text(m.get('nome', ''))
            if nome_norm == search_normalized:
                print(f"[Geocoding] Match normalizado: '{municipio_name}' -> '{m['nome']}'")
                return m

        # 2. Tentar correspondência que comece com o termo
        for m in municipios_uf:
            nome_norm = GeocodingService.normalize_text(m.get('nome', ''))
            if nome_norm.startswith(search_normalized) or search_normalized.startswith(nome_norm):
                print(f"[Geocoding] Match parcial: '{municipio_name}' -> '{m['nome']}'")
                return m

        # 3. Tentar correspondência por palavras-chave (para casos como "Município de X")
        search_words = set(search_normalized.split())
        search_words.discard('de')
        search_words.discard('do')
        search_words.discard('da')
        search_words.discard('dos')
        search_words.discard('das')

        best_match = None
        best_score = 0

        for m in municipios_uf:
            nome_norm = GeocodingService.normalize_text(m.get('nome', ''))
            nome_words = set(nome_norm.split())

            # Calcular palavras em comum
            common_words = search_words & nome_words
            if common_words:
                score = len(common_words) / max(len(search_words), len(nome_words))
                if score > best_score:
                    best_score = score
                    best_match = m

        # Só aceitar se tiver pelo menos 50% de correspondência
        if best_match and best_score >= 0.5:
            print(f"[Geocoding] Match por palavras-chave: '{municipio_name}' -> '{best_match['nome']}' (score: {best_score:.2f})")
            return best_match

        return None


# Funções de conveniência
def get_city_from_location(lat: float, lng: float) -> dict | None:
    """
    Obtém município a partir de coordenadas

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        Dict com informações do município ou None
    """
    print(f"[Geocoding] Iniciando busca para coordenadas: lat={lat}, lng={lng}")

    if not GeocodingService.validate_coords(lat, lng):
        print("[Geocoding] Coordenadas fora dos limites do Brasil")
        return {
            "error": "Coordenadas fora do Brasil. Verifique se a localização está correta.",
            "valid": False
        }

    result = GeocodingService.get_city_from_coords(lat, lng)

    if not result:
        print("[Geocoding] Nenhum resultado retornado do Nominatim")
        return {
            "error": "Não foi possível determinar o município. O serviço de localização pode estar temporariamente indisponível.",
            "valid": False
        }

    # Só marca como válido se encontrou o município NA BASE DO IBGE
    if result.get('municipio_ibge_id'):
        result["valid"] = True
        print(f"[Geocoding] Sucesso! Município: {result.get('municipio_completo')}")
        return result
    else:
        # Município encontrado pelo Nominatim mas não está na base do IBGE
        municipio_nome = result.get('municipio', 'desconhecido')
        uf = result.get('uf', '')
        original_name = result.get('original_name', municipio_nome)

        error_msg = f"Localização detectada: {municipio_nome}/{uf}"

        if original_name != municipio_nome:
            error_msg += f" (detectado como '{original_name}')"

        error_msg += "\n\nEste município não foi encontrado na base do IBGE ou pode estar com nome diferente. Por favor, selecione manualmente da lista abaixo."

        print(f"[Geocoding] Município não encontrado no IBGE: {municipio_nome}/{uf}")

        return {
            "error": error_msg,
            "valid": False,
            "municipio": municipio_nome,
            "uf": uf,
            "municipio_completo": f"{municipio_nome}/{uf}",
            "partial_data": result
        }


def reverse_geocode(lat: float, lng: float) -> dict | None:
    """Geocoding reverso - converte lat/lng em endereço completo"""
    return GeocodingService.reverse_geocode(lat, lng)
