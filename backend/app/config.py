import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env before any Settings() read (main imports config before database).
# Existing process environment wins, so a host's production variables are not replaced by a local file.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def _csv(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _optional_float(name: str) -> float | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    return float(raw)


class Settings:
    app_name: str
    environment: str
    frontend_origins: list[str]
    jwt_secret: str
    jwt_algorithm: str
    access_token_minutes: int
    cookie_name: str
    cookie_secure: bool
    upload_dir: str
    max_upload_bytes: int
    allowed_upload_types: set[str]

    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "Anuvarthan API")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.frontend_origins = _csv(
            "FRONTEND_ORIGIN",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
        )
        self.jwt_secret = os.getenv("JWT_SECRET", "")
        if self.environment == "production" and (
            len(self.jwt_secret) < 32 or self.jwt_secret.startswith("change-me")
        ):
            raise RuntimeError(
                "Set a unique JWT_SECRET of at least 32 characters before starting in production."
            )
        self.jwt_algorithm = "HS256"
        self.access_token_minutes = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
        self.cookie_name = os.getenv("AUTH_COOKIE_NAME", "ds_access_token")
        self.cookie_secure = self.environment == "production"
        self.upload_dir = os.getenv(
            "UPLOAD_DIR",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "var", "uploads"),
        )
        self.max_upload_bytes = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
        self.allowed_upload_types = {
            "image/jpeg",
            "image/png",
            "image/webp",
        }
        self.map_provider = os.getenv("MAP_PROVIDER", "osm").strip().lower()
        self.mappls_access_token = os.getenv("MAPPLS_ACCESS_TOKEN", "").strip()
        self.mappls_client_id = os.getenv("MAPPLS_CLIENT_ID", "").strip()
        self.mappls_client_secret = os.getenv("MAPPLS_CLIENT_SECRET", "").strip()
        self.mappls_region = os.getenv("MAPPLS_REGION", "IND").strip() or "IND"
        self.mappls_timeout_seconds = float(os.getenv("MAPPLS_TIMEOUT_SECONDS", "8"))
        self.mappls_search_base_url = os.getenv(
            "MAPPLS_SEARCH_BASE_URL",
            "https://search.mappls.com",
        ).rstrip("/")
        self.mappls_route_base_url = os.getenv(
            "MAPPLS_ROUTE_BASE_URL",
            "https://route.mappls.com",
        ).rstrip("/")
        self.mappls_place_base_url = os.getenv(
            "MAPPLS_PLACE_BASE_URL",
            "https://place.mappls.com",
        ).rstrip("/")
        self.mappls_oauth_url = os.getenv(
            "MAPPLS_OAUTH_URL",
            "https://outpost.mappls.com/api/security/oauth/token",
        )
        self.mappls_route_resource = os.getenv("MAPPLS_ROUTE_RESOURCE", "route_adv").strip() or "route_adv"
        self.mappls_matrix_resource = os.getenv("MAPPLS_MATRIX_RESOURCE", "distance_matrix").strip() or "distance_matrix"
        self.mappls_route_optimization_enabled = os.getenv(
            "MAPPLS_ROUTE_OPTIMIZATION_ENABLED",
            "false",
        ).strip().lower() in {"1", "true", "yes"}
        self.service_area_name = os.getenv("SERVICE_AREA_NAME", "").strip()
        self.service_area_center_lat = _optional_float("SERVICE_AREA_CENTER_LAT")
        self.service_area_center_lng = _optional_float("SERVICE_AREA_CENTER_LNG")
        self.service_area_radius_km = _optional_float("SERVICE_AREA_RADIUS_KM")
        self.location_live_min_interval_seconds = int(os.getenv("LOCATION_LIVE_MIN_INTERVAL_SECONDS", "15"))
        self.location_live_min_distance_m = int(os.getenv("LOCATION_LIVE_MIN_DISTANCE_M", "40"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
