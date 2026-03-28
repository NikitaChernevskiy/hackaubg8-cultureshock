"""Real transport provider — OpenStreetMap Overpass API.

Finds real airports, train stations, bus stations, and ferry terminals
near the user's coordinates. Free, no API key required.

Overpass API: https://overpass-api.de/
"""

import logging
import math
from datetime import datetime, timezone

import httpx

from app.models.common import DataSource, Location
from app.models.transport import TransportOption
from app.providers.base import TransportProvider

logger = logging.getLogger(__name__)

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass query to find transport infrastructure within a radius
_QUERY_TEMPLATE = """
[out:json][timeout:15];
(
  node["aeroway"="aerodrome"](around:{radius},{lat},{lon});
  way["aeroway"="aerodrome"](around:{radius},{lat},{lon});
  node["railway"="station"](around:{radius},{lat},{lon});
  way["railway"="station"](around:{radius},{lat},{lon});
  node["amenity"="bus_station"](around:{radius},{lat},{lon});
  way["amenity"="bus_station"](around:{radius},{lat},{lon});
  node["amenity"="ferry_terminal"](around:{radius},{lat},{lon});
  way["amenity"="ferry_terminal"](around:{radius},{lat},{lon});
);
out center 30;
"""


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _classify_element(tags: dict) -> str | None:
    """Determine transport type from OSM tags."""
    if tags.get("aeroway") == "aerodrome":
        return "airport"
    if tags.get("railway") == "station":
        return "train_station"
    if tags.get("amenity") == "bus_station":
        return "bus_station"
    if tags.get("amenity") == "ferry_terminal":
        return "port"
    return None


def _estimate_travel_minutes(distance_km: float) -> int:
    """Rough estimate of travel time assuming city driving ~30km/h."""
    return max(1, int(distance_km / 0.5))  # ~30km/h average


class OSMTransportProvider(TransportProvider):
    """Finds real transport infrastructure using OpenStreetMap data."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=20.0)

    async def get_transport_options(self, location: Location) -> list[TransportOption]:
        try:
            # Search within 50km for airports, 25km for ground transport
            search_radius = 50000  # meters

            query = _QUERY_TEMPLATE.format(
                radius=search_radius,
                lat=location.latitude,
                lon=location.longitude,
            )

            resp = await self._client.post(
                _OVERPASS_URL,
                data={"data": query},
            )
            resp.raise_for_status()
            data = resp.json()

            now = datetime.now(timezone.utc)
            source = DataSource(
                name="OpenStreetMap",
                url="https://www.openstreetmap.org",
                retrieved_at=now,
                reliability="verified",
            )

            options = []
            seen_names: set[str] = set()  # Deduplicate

            for element in data.get("elements", []):
                tags = element.get("tags", {})
                transport_type = _classify_element(tags)
                if not transport_type:
                    continue

                # Get coordinates (center for ways)
                if "center" in element:
                    el_lat = element["center"]["lat"]
                    el_lon = element["center"]["lon"]
                elif "lat" in element and "lon" in element:
                    el_lat = element["lat"]
                    el_lon = element["lon"]
                else:
                    continue

                name = (
                    tags.get("name")
                    or tags.get("name:en")
                    or tags.get("official_name")
                    or tags.get("iata", "")
                    or f"Unnamed {transport_type.replace('_', ' ')}"
                )

                # Skip duplicates
                dedup_key = f"{transport_type}:{name}"
                if dedup_key in seen_names:
                    continue
                seen_names.add(dedup_key)

                distance = _haversine_km(location.latitude, location.longitude, el_lat, el_lon)

                # Build a useful status detail
                iata = tags.get("iata", "")
                name_display = f"{name} ({iata})" if iata else name

                options.append(TransportOption(
                    id=f"osm-{element.get('id', 'unknown')}",
                    type=transport_type,
                    name=name_display,
                    location=Location(latitude=el_lat, longitude=el_lon),
                    status="unknown",  # OSM doesn't have real-time status
                    status_detail="Real-time operational status not available. Check with the operator directly.",
                    distance_km=round(distance, 1),
                    estimated_travel_minutes=_estimate_travel_minutes(distance),
                    source=source,
                    last_updated=now,
                ))

            # Sort by distance
            options.sort(key=lambda o: o.distance_km or 9999)

            # Limit to top results per type
            limited: list[TransportOption] = []
            type_counts: dict[str, int] = {}
            for opt in options:
                count = type_counts.get(opt.type, 0)
                if count < 5:  # Max 5 per type
                    limited.append(opt)
                    type_counts[opt.type] = count + 1

            logger.info(
                "OSM: found %d transport options near (%.2f, %.2f)",
                len(limited), location.latitude, location.longitude,
            )
            return limited

        except Exception:
            logger.exception("OSM transport fetch failed")
            return []

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(
                "https://overpass-api.de/api/status",
                timeout=10.0,
            )
            return resp.status_code == 200
        except Exception:
            return False
