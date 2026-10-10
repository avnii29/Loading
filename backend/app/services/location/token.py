from __future__ import annotations

import logging
import threading
import time

import httpx

from app.config import Settings
from app.services.location.errors import MAP_PROVIDER_AUTH_FAILED, LocationError

logger = logging.getLogger("anuvarthan.location")


class MapplsTokenManager:
    """Caches Mappls OAuth tokens using the documented expires_in value."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.Lock()
        self._token: str | None = None
        self._token_type = "bearer"
        self._expires_at = 0.0

    def configured(self) -> bool:
        return bool(self._settings.mappls_client_id and self._settings.mappls_client_secret)

    def get_access_token(self) -> tuple[str, str]:
        if self._settings.mappls_access_token:
            return self._settings.mappls_access_token, "static"
        if not self.configured():
            raise LocationError(
                MAP_PROVIDER_AUTH_FAILED,
                "Mappls credentials are not configured.",
                503,
            )
        now = time.monotonic()
        with self._lock:
            if self._token and now < self._expires_at:
                return self._token, self._token_type
            token, token_type, expires_in = self._request_token()
            # Use the lifetime Mappls returned; refresh one minute early.
            lifetime = max(30.0, float(expires_in) - 60.0)
            self._token = token
            self._token_type = token_type
            self._expires_at = now + lifetime
            return token, token_type

    def invalidate(self) -> None:
        with self._lock:
            self._token = None
            self._expires_at = 0.0

    def _request_token(self) -> tuple[str, str, int]:
        started = time.perf_counter()
        try:
            response = httpx.post(
                self._settings.mappls_oauth_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._settings.mappls_client_id,
                    "client_secret": self._settings.mappls_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self._settings.mappls_timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise LocationError(MAP_PROVIDER_AUTH_FAILED, "Mappls authentication timed out.", 503) from exc
        except httpx.HTTPError as exc:
            raise LocationError(MAP_PROVIDER_AUTH_FAILED, "Mappls authentication is unavailable.", 503) from exc
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "mappls_oauth status=%s duration_ms=%s",
            response.status_code,
            duration_ms,
        )
        if response.status_code >= 400:
            self.invalidate()
            raise LocationError(MAP_PROVIDER_AUTH_FAILED, "Mappls authentication failed.", 503)
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise LocationError(MAP_PROVIDER_AUTH_FAILED, "Mappls authentication failed.", 503)
        return (
            str(token),
            str(payload.get("token_type") or "bearer"),
            int(payload.get("expires_in") or 3600),
        )
