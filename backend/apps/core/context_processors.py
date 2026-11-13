"""Context processors disponíveis em todos os templates."""
from django.conf import settings


def map_settings(request):
    """Configuração do mapa base usada pelo Leaflet (frontend/static/js/app.js)."""
    return {
        'map_config': {
            'tileUrl': settings.MAP_TILE_URL,
            'attribution': settings.MAP_TILE_ATTRIBUTION,
            'maxZoom': settings.MAP_TILE_MAX_ZOOM,
        }
    }
