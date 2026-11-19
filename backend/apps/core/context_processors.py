"""Context processors disponíveis em todos os templates."""
from django.conf import settings
from django.templatetags.static import static


def map_settings(request):
    """Configuração do mapa base usada pelo Leaflet (frontend/static/js/app.js)."""
    return {
        'map_config': {
            'tileUrl': settings.MAP_TILE_URL,
            'attribution': settings.MAP_TILE_ATTRIBUTION,
            'maxZoom': settings.MAP_TILE_MAX_ZOOM,
            # URLs explícitas: com o manifest do WhiteNoise o CSS referencia
            # imagens com hash e o Leaflet não consegue deduzir o caminho.
            'markerIcon': static('vendor/leaflet/images/marker-icon.png'),
            'markerIcon2x': static('vendor/leaflet/images/marker-icon-2x.png'),
            'markerShadow': static('vendor/leaflet/images/marker-shadow.png'),
        }
    }


def site_settings(request):
    """Opções globais de interface (acessibilidade e privacidade)."""
    return {
        'vlibras_enabled': settings.VLIBRAS_ENABLED,
    }
