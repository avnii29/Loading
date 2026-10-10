from __future__ import annotations

from dataclasses import dataclass

from app.services.location.errors import INVALID_COORDINATES, LocationError


@dataclass(frozen=True, slots=True)
class LatLng:
    latitude: float
    longitude: float


def validate_lat_lng(latitude: float, longitude: float) -> LatLng:
    if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
        raise LocationError(INVALID_COORDINATES, "Those coordinates are not valid.", 422)
    return LatLng(latitude=float(latitude), longitude=float(longitude))


def encode_lng_lat(point: LatLng) -> str:
    """Mappls route/matrix path segment: longitude,latitude."""
    return f"{point.longitude},{point.latitude}"


def encode_polyline(points: list[LatLng], precision: int = 5) -> str:
    factor = 10**precision
    output: list[str] = []
    prev_lat = 0
    prev_lng = 0
    for point in points:
        lat = int(round(point.latitude * factor))
        lng = int(round(point.longitude * factor))
        output.append(_encode_value(lat - prev_lat))
        output.append(_encode_value(lng - prev_lng))
        prev_lat = lat
        prev_lng = lng
    return "".join(output)


def _encode_value(value: int) -> str:
    value = ~(value << 1) if value < 0 else value << 1
    chars: list[str] = []
    while value >= 0x20:
        chars.append(chr((0x20 | (value & 0x1F)) + 63))
        value >>= 5
    chars.append(chr(value + 63))
    return "".join(chars)


def decode_polyline(encoded: str, precision: int = 5) -> list[LatLng]:
    """Decode a Google-style polyline into latitude/longitude pairs."""
    points: list[LatLng] = []
    index = 0
    lat = 0
    lng = 0
    factor = 10**precision
    length = len(encoded)
    while index < length:
        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        lat += ~(result >> 1) if result & 1 else result >> 1
        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        lng += ~(result >> 1) if result & 1 else result >> 1
        points.append(LatLng(latitude=lat / factor, longitude=lng / factor))
    return points


def is_indian_pincode(query: str) -> bool:
    stripped = query.strip()
    return len(stripped) == 6 and stripped.isdigit()
