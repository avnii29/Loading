"""OpenStreetMap geocoding (Nominatim) and routing (OSRM). No invented coordinates."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.config import Settings
from app.services.location.coords import LatLng, is_indian_pincode, validate_lat_lng
from app.services.location.errors import (
    LOCATION_SEARCH_UNAVAILABLE,
    MAP_PROVIDER_TIMEOUT,
    MAP_PROVIDER_UPSTREAM,
    NO_LOCATION_RESULTS,
    ROUTING_UNAVAILABLE,
    LocationError,
)
from app.services.location.types import DistanceResult, LocationResult, RouteResult

USER_AGENT = "Anuvarthan/1.0 (local surplus logistics)"

# Nominatim place types that name an area, not a door or building.
BROAD_PLACE_TYPES = frozenset(
    {
        "postcode",
        "administrative",
        "city",
        "town",
        "village",
        "suburb",
        "neighbourhood",
        "quarter",
        "city_district",
        "municipality",
        "county",
        "state",
        "region",
        "hamlet",
        "locality",
        "district",
        "state_district",
    }
)


def place_is_broad(kind: str | None, *, query_is_area: bool = False) -> bool:
    return query_is_area or (kind or "") in BROAD_PLACE_TYPES


class OsmService:
    def __init__(self, settings: Settings) -> None:
        self._timeout = settings.mappls_timeout_seconds or 8

    def configured(self) -> bool:
        return True

    def search_places(self, query: str, *, bias: LatLng | None = None) -> list[LocationResult]:
        text = query.strip()
        if not text:
            return []
        if len(text) > 80:
            raise LocationError("INVALID_QUERY", "Search text is too long.", 400)
        params: dict[str, str] = {
            "format": "jsonv2",
            "addressdetails": "1",
            "limit": "6",
            "countrycodes": "in",
        }
        if is_indian_pincode(text):
            params["postalcode"] = text
        else:
            params["q"] = text
        if bias:
            params["lat"] = str(bias.latitude)
            params["lon"] = str(bias.longitude)
        rows = self._get_json("https://nominatim.openstreetmap.org/search", params, operation="search")
        if not isinstance(rows, list):
            return []
        return [self._from_nominatim(row, approximate=is_indian_pincode(text)) for row in rows if isinstance(row, dict)]

    def geocode(self, address: str) -> list[LocationResult]:
        return self.search_places(address)

    def reverse_geocode(self, point: LatLng) -> LocationResult:
        validate_lat_lng(point.latitude, point.longitude)
        payload = self._get_json(
            "https://nominatim.openstreetmap.org/reverse",
            {
                "format": "jsonv2",
                "addressdetails": "1",
                "lat": str(point.latitude),
                "lon": str(point.longitude),
            },
            operation="reverse",
        )
        if not isinstance(payload, dict) or not payload.get("display_name"):
            raise LocationError(NO_LOCATION_RESULTS, "No address was found for that point.", 404)
        return self._from_nominatim(payload, approximate=False)

    def resolve_place(self, result: LocationResult) -> LocationResult:
        return result

    def get_place_details(self, mappls_pin: str) -> LocationResult:
        raise LocationError(NO_LOCATION_RESULTS, "Place pins from Mappls are not used. Search OpenStreetMap instead.", 404)

    def route(
        self,
        origin: LatLng | str,
        destination: LatLng | str,
        *,
        waypoints: list[LatLng | str] | None = None,
        travel_mode: str = "DRIVING",
    ) -> RouteResult:
        profile = "walking" if travel_mode.upper() in {"WALKING", "WALK"} else "driving"
        coords = [self._as_point(item) for item in [origin, *(waypoints or []), destination]]
        path = ";".join(f"{point.longitude},{point.latitude}" for point in coords)
        payload = self._get_json(
            f"https://router.project-osrm.org/route/v1/{profile}/{path}",
            {"overview": "full", "geometries": "geojson"},
            operation="route",
        )
        if not isinstance(payload, dict) or str(payload.get("code") or "").lower() != "ok":
            raise LocationError(ROUTING_UNAVAILABLE, "No road route was found.", 404)
        routes = payload.get("routes") or []
        if not routes:
            raise LocationError(ROUTING_UNAVAILABLE, "Route preview unavailable.", 404)
        first = routes[0]
        geometry = (first.get("geometry") or {}).get("coordinates") or []
        points = [
            LatLng(latitude=float(pair[1]), longitude=float(pair[0]))
            for pair in geometry
            if isinstance(pair, list) and len(pair) >= 2
        ]
        if len(points) < 2:
            raise LocationError(ROUTING_UNAVAILABLE, "Route preview unavailable.", 404)
        return RouteResult(
            provider="osrm",
            distance_meters=float(first.get("distance") or 0),
            duration_seconds=float(first.get("duration") or 0),
            geometry=points,
            traffic_aware=False,
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
        profile = "walking" if travel_mode.upper() in {"WALKING", "WALK"} else "driving"
        points = [origin, *destinations]
        path = ";".join(f"{point.longitude},{point.latitude}" for point in points)
        dest_indexes = ";".join(str(index) for index in range(1, len(points)))
        payload = self._get_json(
            f"https://router.project-osrm.org/table/v1/{profile}/{path}",
            {"sources": "0", "destinations": dest_indexes, "annotations": "distance,duration"},
            operation="matrix",
        )
        if not isinstance(payload, dict) or str(payload.get("code") or "").lower() != "ok":
            raise LocationError(ROUTING_UNAVAILABLE, "Road distance is unavailable.", 503)
        distances = (payload.get("distances") or [[]])[0]
        durations = (payload.get("durations") or [[]])[0]
        results: list[DistanceResult] = []
        for index, dest in enumerate(destinations):
            if index >= len(distances) or distances[index] is None:
                continue
            results.append(
                DistanceResult(
                    origin=origin,
                    destination=dest,
                    distance_meters=float(distances[index]),
                    duration_seconds=float(durations[index]) if index < len(durations) and durations[index] is not None else 0,
                    provider="osrm",
                )
            )
        return results

    def _as_point(self, value: LatLng | str) -> LatLng:
        if isinstance(value, LatLng):
            validate_lat_lng(value.latitude, value.longitude)
            return value
        raise LocationError(ROUTING_UNAVAILABLE, "OpenStreetMap routing needs coordinates, not a place pin.", 422)

    def _get_json(self, url: str, params: dict[str, str], *, operation: str):
        try:
            response = httpx.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise LocationError(MAP_PROVIDER_TIMEOUT, "The map service timed out.", 504) from exc
        except httpx.HTTPError as exc:
            raise LocationError(MAP_PROVIDER_UPSTREAM, "The map service is unavailable.", 503) from exc
        if response.status_code == 429:
            raise LocationError(LOCATION_SEARCH_UNAVAILABLE, "Map service is temporarily limited.", 429)
        if response.status_code >= 400:
            raise LocationError(MAP_PROVIDER_UPSTREAM, f"OpenStreetMap {operation} failed.", 503)
        return response.json()

    def _from_nominatim(self, row: dict, *, approximate: bool) -> LocationResult:
        address = row.get("address") or {}
        lat = row.get("lat")
        lon = row.get("lon")
        kind = str(row.get("type") or row.get("class") or "")
        postcode = address.get("postcode")
        return LocationResult(
            provider="osm",
            formatted_address=str(row.get("display_name") or ""),
            name=row.get("name"),
            locality=address.get("suburb") or address.get("neighbourhood") or address.get("quarter"),
            city=address.get("city") or address.get("town") or address.get("village"),
            state=address.get("state"),
            pincode=str(postcode) if postcode else None,
            latitude=float(lat) if lat is not None else None,
            longitude=float(lon) if lon is not None else None,
            provider_place_id=str(row.get("place_id")) if row.get("place_id") is not None else None,
            kind=kind or None,
            approximate=place_is_broad(kind, query_is_area=approximate),
            precision="pincode" if approximate or kind == "postcode" else "area" if place_is_broad(kind) else "place",
        )
