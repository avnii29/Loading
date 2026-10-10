from app.config import get_settings
from app.services.location.mappls import MapplsService
from app.services.location.osm import OsmService
from app.services.location.service_area import service_area_from_settings
from app.services.location.token import MapplsTokenManager

_settings = get_settings()
token_manager = MapplsTokenManager(_settings)
_provider = _settings.map_provider
if _provider in {"osm", "leaflet", "openstreetmap"}:
    geo_service = OsmService(_settings)
else:
    geo_service = MapplsService(_settings, token_manager)
# Existing call sites still import this name. It is the active provider, which defaults to OpenStreetMap.
mappls_service = geo_service
service_area = service_area_from_settings(_settings)
