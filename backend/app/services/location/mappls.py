from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import Settings
from app.services.location.coords import LatLng, decode_polyline, encode_lng_lat, is_indian_pincode, validate_lat_lng
from app.services.location.errors import (
    LOCATION_NOT_CONFIGURED,
    LOCATION_SEARCH_UNAVAILABLE,
    MAP_PROVIDER_AUTH_FAILED,
    MAP_PROVIDER_RATE_LIMITED,
    MAP_PROVIDER_TIMEOUT,
    MAP_PROVIDER_UPSTREAM,
    NO_LOCATION_RESULTS,
    ROUTING_UNAVAILABLE,
    LocationError,
)
from app.services.location.token import MapplsTokenManager
from app.services.location.types import DistanceResult, LocationResult, RouteResult

logger = logging.getLogger("anuvarthan.location")

TRAVEL_PROFILES = {
    "CAR": "driving",
    "DRIVER": "driving",
    "DRIVING": "driving",
    "TWO_WHEELER": "biking",
    "BIKING": "biking",
    "WALKING": "walking",
    "VOLUNTEER": "walking",
}


class MapplsService:
    def __init__(self, settings: Settings, tokens: MapplsTokenManager) -> None:
        self._settings = settings
        self._tokens = tokens

    def configured(self) -> bool:
        return bool(self._settings.mappls_access_token or self._tokens.configured())

    def search_places(
        self,
        query: str,
        *,
        bias: LatLng | None = None,
    ) -> list[LocationResult]:
        if not query.strip():
            return []
        if len(query.strip()) > 45:
            raise LocationError("INVALID_QUERY", "Search text is too long.", 400)
        params: dict[str, Any] = {
            "query": query.strip(),
            "region": self._settings.mappls_region,
            "tokenizeAddress": "",
        }
        if bias:
            params["location"] = f"{bias.latitude},{bias.longitude}"
        if is_indian_pincode(query):
            params["filter"] = f"pin:{query.strip()}"
        payload = self._get(
            f"{self._settings.mappls_search_base_url}/search/places/autosuggest/json",
            params,
            operation="autosuggest",
            empty_code=NO_LOCATION_RESULTS,
        )
        rows = payload.get("suggestedLocations") or []
        results = [self._from_suggest(row, approximate=is_indian_pincode(query)) for row in rows]
        return [row for row in results if row]

    def geocode(self, address: str) -> list[LocationResult]:
        if not address.strip():
            return []
        payload = self._get(
            f"{self._settings.mappls_search_base_url}/search/address/geocode",
            {
                "address": address.strip(),
                "itemCount": 5,
                "region": self._settings.mappls_region,
            },
            operation="geocode",
            empty_code=NO_LOCATION_RESULTS,
        )
        raw = payload.get("copResults")
        items = raw if isinstance(raw, list) else [raw] if raw else []
        results = [self._from_geocode(item) for item in items]
        return [row for row in results if row]

    def reverse_geocode(self, point: LatLng) -> LocationResult:
        validate_lat_lng(point.latitude, point.longitude)
        payload = self._get(
            f"{self._settings.mappls_search_base_url}/search/address/rev-geocode",
            {
                "lat": point.latitude,
                "lng": point.longitude,
                "region": self._settings.mappls_region,
            },
            operation="reverse_geocode",
            empty_code=NO_LOCATION_RESULTS,
        )
        rows = payload.get("results") or []
        if not rows:
            raise LocationError(NO_LOCATION_RESULTS, "No address was found for that point.", 404)
        return self._from_reverse(rows[0], point)

    def get_place_details(self, mappls_pin: str) -> LocationResult:
        pin = mappls_pin.strip()
        if not pin:
            raise LocationError(NO_LOCATION_RESULTS, "A Mappls Pin is required.", 400)
        payload = self._get(
            f"{self._settings.mappls_place_base_url}/O2O/entity/place-details/{pin}",
            {},
            operation="place_details",
            empty_code=NO_LOCATION_RESULTS,
        )
        return self._from_place(payload, pin)

    def resolve_place(self, result: LocationResult) -> LocationResult:
        if result.latitude is not None and result.longitude is not None:
            return result
        if not result.mappls_pin:
            return result
        try:
            detailed = self.get_place_details(result.mappls_pin)
        except LocationError:
            return result
        if detailed.latitude is None:
            return LocationResult(
                provider="mappls",
                formatted_address=detailed.formatted_address or result.formatted_address,
                name=detailed.name or result.name,
                locality=detailed.locality or result.locality,
                city=detailed.city or result.city,
                state=detailed.state or result.state,
                pincode=detailed.pincode or result.pincode,
                landmark=detailed.landmark or result.landmark,
                mappls_pin=result.mappls_pin,
                provider_place_id=result.provider_place_id,
                kind=detailed.kind or result.kind,
                approximate=result.approximate,
                precision=detailed.precision or result.precision,
            )
        detailed.approximate = result.approximate
        return detailed

    def route(
        self,
        origin: LatLng | str,
        destination: LatLng | str,
        *,
        waypoints: list[LatLng | str] | None = None,
        travel_mode: str = "DRIVING",
    ) -> RouteResult:
        profile = self._profile(travel_mode)
        resource = self._settings.mappls_route_resource
        if profile == "walking" and resource != "route_adv":
            resource = "route_adv"
        path = ";".join(self._point_token(item) for item in [origin, *(waypoints or []), destination])
        traffic = resource in {"route_eta", "route_traffic"}
        payload = self._get(
            f"{self._settings.mappls_route_base_url}/route/direction/{resource}/{profile}/{path}",
            {
                "region": self._settings.mappls_region.lower() if profile == "driving" else None,
                "geometries": "polyline",
                "overview": "full",
                "steps": "false",
            },
            operation="route",
            empty_code=ROUTING_UNAVAILABLE,
        )
        if str(payload.get("code") or "").lower() == "noroute":
            raise LocationError(ROUTING_UNAVAILABLE, "No road route was found.", 404)
        routes = payload.get("routes") or []
        if not routes:
            raise LocationError(ROUTING_UNAVAILABLE, "Route preview unavailable.", 404)
        first = routes[0]
        geometry = first.get("geometry")
        points: list[LatLng] = []
        if isinstance(geometry, str) and geometry:
            points = decode_polyline(geometry, precision=5)
        elif isinstance(geometry, dict):
            for pair in geometry.get("coordinates") or []:
                if isinstance(pair, list) and len(pair) >= 2:
                    points.append(LatLng(latitude=float(pair[1]), longitude=float(pair[0])))
        return RouteResult(
            provider="mappls",
            distance_meters=float(first.get("distance") or 0),
            duration_seconds=float(first.get("duration") or 0),
            geometry=points,
            traffic_aware=traffic,
            generated_at=datetime.now(timezone.utc),
        )

    def distance_matrix(
        self,
        origin: LatLng,
        destinations: list[LatLng],
        *,
        travel_mode: str = "DRIVING",
    ) -> list[DistanceResult]:
        if not destinations:
            return []
        profile = self._profile(travel_mode)
        resource = self._settings.mappls_matrix_resource
        points = [origin, *destinations]
        path = ";".join(encode_lng_lat(item) for item in points)
        dest_indexes = ";".join(str(index) for index in range(1, len(points)))
        payload = self._get(
            f"{self._settings.mappls_route_base_url}/route/dm/{resource}/{profile}/{path}",
            {
                "region": self._settings.mappls_region.lower() if profile == "driving" else None,
                "sources": "0",
                "destinations": dest_indexes,
            },
            operation="distance_matrix",
            empty_code=ROUTING_UNAVAILABLE,
        )
        distances = payload.get("distances") or payload.get("distance") or []
        durations = payload.get("durations") or payload.get("duration") or []
        if distances and isinstance(distances[0], list):
            distances = distances[0]
        if durations and isinstance(durations[0], list):
            durations = durations[0]
        results: list[DistanceResult] = []
        for index, dest in enumerate(destinations):
            distance = distances[index] if index < len(distances) else None
            duration = durations[index] if index < len(durations) else None
            if distance is None:
                continue
            results.append(
                DistanceResult(
                    origin=origin,
                    destination=dest,
                    distance_meters=float(distance),
                    duration_seconds=float(duration or 0),
                    provider="mappls",
                )
            )
        return results

    def _profile(self, travel_mode: str) -> str:
        return TRAVEL_PROFILES.get(travel_mode.upper(), "driving")

    def _point_token(self, value: LatLng | str) -> str:
        if isinstance(value, str):
            return value.strip()
        return encode_lng_lat(validate_lat_lng(value.latitude, value.longitude))

    def _from_suggest(self, row: dict[str, Any], *, approximate: bool) -> LocationResult | None:
        tokens = row.get("addressTokens") or {}
        kind = str(row.get("type") or "place")
        address = row.get("placeAddress") or row.get("placeName") or ""
        if not address:
            return None
        lat = _optional_number(row.get("latitude") if row.get("latitude") is not None else row.get("lat"))
        lng = _optional_number(row.get("longitude") if row.get("longitude") is not None else row.get("lng"))
        if lat is None or lng is None or (lat == 0 and lng == 0):
            lat = None
            lng = None
        return LocationResult(
            provider="mappls",
            name=row.get("placeName"),
            formatted_address=address,
            locality=tokens.get("locality") or tokens.get("subLocality"),
            city=tokens.get("city"),
            state=tokens.get("state"),
            pincode=tokens.get("pincode"),
            landmark=tokens.get("poi"),
            latitude=lat,
            longitude=lng,
            mappls_pin=row.get("eLoc") or row.get("eloc"),
            provider_place_id=row.get("eLoc") or row.get("eloc"),
            kind=kind,
            approximate=approximate or kind.upper() in {"PINCODE", "CITY", "STATE", "DISTRICT"},
            precision=kind.lower(),
        )

    def _from_geocode(self, row: dict[str, Any]) -> LocationResult | None:
        address = row.get("formattedAddress") or row.get("formatted_address")
        if not address:
            return None
        lat = _optional_number(row.get("latitude") if "latitude" in row else row.get("lat"))
        lng = _optional_number(row.get("longitude") if "longitude" in row else row.get("lng"))
        return LocationResult(
            provider="mappls",
            name=row.get("poi") or row.get("houseName"),
            formatted_address=address,
            locality=row.get("locality"),
            city=row.get("city"),
            state=row.get("state"),
            pincode=row.get("pincode"),
            landmark=row.get("poi"),
            latitude=lat,
            longitude=lng,
            mappls_pin=row.get("eLoc") or row.get("eloc"),
            provider_place_id=row.get("eLoc") or row.get("eloc"),
            confidence=_optional_number(row.get("confidenceScore")),
            precision=row.get("geocodeLevel"),
            kind=row.get("geocodeLevel"),
            approximate=str(row.get("geocodeLevel") or "").lower() in {"pincode", "city", "locality", "state"},
        )

    def _from_reverse(self, row: dict[str, Any], point: LatLng) -> LocationResult:
        address = row.get("formatted_address") or row.get("formattedAddress") or ""
        lat = _optional_number(row.get("lat")) or point.latitude
        lng = _optional_number(row.get("lng")) or point.longitude
        return LocationResult(
            provider="mappls",
            name=row.get("poi"),
            formatted_address=address,
            locality=row.get("locality") or row.get("village"),
            city=row.get("city"),
            state=row.get("state"),
            pincode=row.get("pincode"),
            landmark=row.get("poi"),
            latitude=lat,
            longitude=lng,
            mappls_pin=row.get("eLoc") or row.get("eloc"),
            provider_place_id=row.get("eLoc") or row.get("eloc"),
            precision="reverse",
        )

    def _from_place(self, row: dict[str, Any], pin: str) -> LocationResult:
        lat = _optional_number(row.get("latitude"))
        lng = _optional_number(row.get("longitude"))
        return LocationResult(
            provider="mappls",
            name=row.get("name") or row.get("poi"),
            formatted_address=row.get("address") or row.get("formattedAddress") or row.get("name") or pin,
            locality=row.get("locality"),
            city=row.get("city"),
            state=row.get("state"),
            pincode=row.get("pincode"),
            landmark=row.get("poi"),
            latitude=lat,
            longitude=lng,
            mappls_pin=row.get("eloc") or row.get("eLoc") or pin,
            provider_place_id=row.get("eloc") or row.get("eLoc") or pin,
            kind=row.get("type"),
            precision=row.get("type"),
        )

    def _get(
        self,
        url: str,
        params: dict[str, Any],
        *,
        operation: str,
        empty_code: str,
    ) -> dict[str, Any]:
        if not self.configured():
            raise LocationError(
                LOCATION_NOT_CONFIGURED,
                "Mappls is not configured on this server.",
                503,
            )
        cleaned = {key: value for key, value in params.items() if value is not None}
        headers: dict[str, str] = {}
        if self._settings.mappls_access_token:
            cleaned["access_token"] = self._settings.mappls_access_token
        else:
            token, token_type = self._tokens.get_access_token()
            headers["Authorization"] = f"{token_type} {token}"
        started = time.perf_counter()
        try:
            response = httpx.get(
                url,
                params=cleaned,
                headers=headers,
                timeout=self._settings.mappls_timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            logger.info("mappls_%s status=timeout", operation)
            raise LocationError(MAP_PROVIDER_TIMEOUT, "The map service timed out.", 504) from exc
        except httpx.HTTPError as exc:
            logger.info("mappls_%s status=upstream_error", operation)
            raise LocationError(MAP_PROVIDER_UPSTREAM, "The map service is unavailable.", 503) from exc
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "mappls_%s status=%s duration_ms=%s",
            operation,
            response.status_code,
            duration_ms,
        )
        if response.status_code in {204}:
            raise LocationError(empty_code, "No location results.", 404)
        if response.status_code in {401, 403}:
            self._tokens.invalidate()
            if response.status_code == 403:
                raise LocationError(MAP_PROVIDER_RATE_LIMITED, "Map service is temporarily limited.", 429)
            raise LocationError(MAP_PROVIDER_AUTH_FAILED, "Map service authentication failed.", 503)
        if response.status_code == 429:
            raise LocationError(MAP_PROVIDER_RATE_LIMITED, "Map service is temporarily limited.", 429)
        if response.status_code >= 500:
            raise LocationError(MAP_PROVIDER_UPSTREAM, "The map service is unavailable.", 503)
        if response.status_code >= 400:
            raise LocationError(LOCATION_SEARCH_UNAVAILABLE, "Location search is unavailable right now.", 503)
        payload = response.json()
        if not isinstance(payload, dict):
            raise LocationError(MAP_PROVIDER_UPSTREAM, "The map service returned an unexpected result.", 503)
        return payload


def _optional_number(value: Any) -> float | None:
    if value is None or value == "" or value == "RESTRICTED":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
