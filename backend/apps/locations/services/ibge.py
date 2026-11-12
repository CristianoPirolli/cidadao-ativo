"""
Serviço de integração com API do IBGE
Busca e cacheia lista de municípios brasileiros
"""
import json
from pathlib import Path

import requests
from django.conf import settings


class IBGEService:
    """Serviço para buscar municípios via API do IBGE"""

    # URL da API do IBGE
    API_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

    CACHE_FILENAME = "municipios_cache.json"

    @staticmethod
    def cache_file() -> Path:
        """Arquivo de cache em ``settings.DATA_DIR`` (gravável em runtime)."""
        return Path(settings.DATA_DIR) / IBGEService.CACHE_FILENAME

    @staticmethod
    def _ensure_cache_dir():
        """Garante que o diretório de cache existe"""
        cache_dir = IBGEService.cache_file().parent
        cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def fetch_municipios(force_refresh: bool = False) -> list[dict]:
        """
        Busca todos os municípios brasileiros

        Args:
            force_refresh: Se True, força busca na API mesmo com cache válido

        Returns:
            Lista de dicionários com municípios
            Formato: [{id, nome, uf, nome_completo}, ...]
        """
        # Verificar cache
        if not force_refresh and IBGEService.cache_file().exists():
            try:
                with open(IBGEService.cache_file(), encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Erro ao ler cache: {e}")

        # Buscar da API
        try:
            response = requests.get(IBGEService.API_URL, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Processar dados
            municipios = []
            for item in data:
                try:
                    # Try microrregiao path first (standard structure)
                    if item.get("microrregiao") and item["microrregiao"].get("mesorregiao"):
                        uf_sigla = item["microrregiao"]["mesorregiao"]["UF"]["sigla"]
                        uf_nome = item["microrregiao"]["mesorregiao"]["UF"]["nome"]
                    # Fallback to regiao-imediata (alternative structure)
                    elif item.get("regiao-imediata") and item["regiao-imediata"].get("regiao-intermediaria"):
                        uf_sigla = item["regiao-imediata"]["regiao-intermediaria"]["UF"]["sigla"]
                        uf_nome = item["regiao-imediata"]["regiao-intermediaria"]["UF"]["nome"]
                    else:
                        # Skip if we can't get UF info
                        print(f"Skipping {item.get('nome')}: no UF info")
                        continue

                    municipio = {
                        "id": item["id"],
                        "nome": item["nome"],
                        "uf": uf_sigla,
                        "uf_nome": uf_nome,
                        "nome_completo": f"{item['nome']}/{uf_sigla}"
                    }
                    municipios.append(municipio)
                except (KeyError, TypeError) as e:
                    print(f"Error processing municipality {item.get('nome', 'unknown')}: {e}")
                    continue

            # Ordenar por nome
            municipios.sort(key=lambda x: x["nome"])

            # Salvar cache
            IBGEService._ensure_cache_dir()
            with open(IBGEService.cache_file(), 'w', encoding='utf-8') as f:
                json.dump(municipios, f, ensure_ascii=False, indent=2)

            return municipios

        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar municípios do IBGE: {e}")
            # Se falhar e não tem cache, retornar lista vazia
            return []

    @staticmethod
    def search_municipios(query: str, uf: str | None = None) -> list[dict]:
        """
        Busca municípios por nome

        Args:
            query: Termo de busca (parte do nome do município)
            uf: Filtrar por UF (opcional)

        Returns:
            Lista de municípios que correspondem à busca
        """
        municipios = IBGEService.fetch_municipios()

        # Normalizar query
        query_lower = query.lower().strip()

        # Filtrar
        results = []
        for m in municipios:
            nome_match = query_lower in m["nome"].lower()
            uf_match = (uf is None) or (m["uf"].lower() == uf.lower())

            if nome_match and uf_match:
                results.append(m)

        return results[:50]  # Limitar a 50 resultados

    @staticmethod
    def get_municipio_by_id(municipio_id: int) -> dict | None:
        """
        Busca município por ID do IBGE

        Args:
            municipio_id: ID do município no IBGE

        Returns:
            Dicionário com dados do município ou None
        """
        municipios = IBGEService.fetch_municipios()

        for m in municipios:
            if m["id"] == municipio_id:
                return m

        return None

    @staticmethod
    def get_municipio_by_nome(nome: str, uf: str) -> dict | None:
        """
        Busca município por nome e UF

        Args:
            nome: Nome do município
            uf: Sigla da UF

        Returns:
            Dicionário com dados do município ou None
        """
        municipios = IBGEService.fetch_municipios()

        nome_lower = nome.lower().strip()
        uf_lower = uf.lower().strip()

        for m in municipios:
            if m["nome"].lower() == nome_lower and m["uf"].lower() == uf_lower:
                return m

        return None

    @staticmethod
    def get_municipios_by_uf(uf: str) -> list[dict]:
        """
        Busca todos os municípios de uma UF

        Args:
            uf: Sigla da UF

        Returns:
            Lista de municípios da UF
        """
        municipios = IBGEService.fetch_municipios()
        uf_lower = uf.lower().strip()

        return [m for m in municipios if m["uf"].lower() == uf_lower]


# Funções de conveniência
def get_all_municipios() -> list[dict]:
    """Retorna todos os municípios brasileiros"""
    return IBGEService.fetch_municipios()


def search_municipios(query: str, uf: str | None = None) -> list[dict]:
    """Busca municípios por nome"""
    return IBGEService.search_municipios(query, uf)


def get_municipio(municipio_id: int) -> dict | None:
    """Busca município por ID"""
    return IBGEService.get_municipio_by_id(municipio_id)


def find_municipio(nome: str, uf: str) -> dict | None:
    """Busca município por nome e UF"""
    return IBGEService.get_municipio_by_nome(nome, uf)
