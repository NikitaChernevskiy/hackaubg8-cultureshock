"""NASA EONET (Earth Observatory Natural Event Tracker) provider.

Real-time natural events: wildfires, volcanic eruptions, severe storms,
floods, sea/lake ice, landslides. Free, no API key.

API docs: https://eonet.gsfc.nasa.gov/docs/v3
"""

import logging
import math
from datetime import datetime, timezone

import httpx

from app.models.alerts import Alert
from app.models.common import DataSource, Location
from app.providers.base import AlertProvider

logger = logging.getLogger(__name__)

_EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"

# Map EONET category IDs to our alert types
_CATEGORY_MAP = {
    "wildfires": "wildfire",
    "volcanoes": "volcanic_eruption",
    "severeStorms": "hurricane",
    "floods": "flood",
    "earthquakes": "earthquake",
    "landslides": "landslide",
    "seaLakeIce": "other",
    "tempExtremes": "other",
    "snow": "other",
    "dustHaze": "other",
    "waterColor": "other",
    "manmade": "industrial_accident",
}

# Severity is approximate — EONET doesn't provide severity levels
_CATEGORY_SEVERITY = {
    "wildfires": "high",
    "volcanoes": "critical",
    "severeStorms": "high",
    "floods": "high",
    "earthquakes": "high",
    "landslides": "medium",
    "seaLakeIce": "low",
    "tempExtremes": "medium",
    "snow": "low",
    "dustHaze": "low",
    "manmade": "high",
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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


class EONETAlertProvider(AlertProvider):
    """Fetches real-time natural events from NASA EONET."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=15.0)

    async def get_alerts(self, location: Location, radius_km: float = 500) -> list[Alert]:
        try:
            # Fetch recent open events (last 30 days)
            resp = await self._client.get(
                _EONET_URL,
                params={"status": "open", "limit": 50, "days": 30},
            )
            resp.raise_for_status()
            data = resp.json()

            now = datetime.now(timezone.utc)
            source = DataSource(
                name="NASA EONET",
                url="https://eonet.gsfc.nasa.gov",
                retrieved_at=now,
                reliability="official",
            )

            alerts = []
            for event in data.get("events", []):
                # Get latest geometry point
                geometries = event.get("geometry", [])
                if not geometries:
                    continue

                latest_geo = geometries[-1]
                coords = latest_geo.get("coordinates", [])
                if len(coords) < 2:
                    continue

                ev_lon, ev_lat = coords[0], coords[1]

                # Check distance
                dist = _haversine_km(location.latitude, location.longitude, ev_lat, ev_lon)
                if dist > radius_km:
                    continue

                # Parse category
                categories = event.get("categories", [])
                cat_id = categories[0].get("id", "other") if categories else "other"
                cat_title = categories[0].get("title", "Natural Event") if categories else "Natural Event"

                alert_type = _CATEGORY_MAP.get(cat_id, "other")
                severity = _CATEGORY_SEVERITY.get(cat_id, "medium")

                # Parse date
                date_str = latest_geo.get("date", "")
                try:
                    issued_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    issued_at = now

                alerts.append(Alert(
                    id=f"eonet-{event.get('id', 'unknown')}",
                    type=alert_type,
                    severity=severity,
                    title=event.get("title", "Unknown Event"),
                    description=(
                        f"{cat_title} detected by NASA Earth Observatory, "
                        f"approximately {dist:.0f}km from your location. "
                        f"Event ID: {event.get('id', 'N/A')}."
                    ),
                    issued_at=issued_at,
                    expires_at=None,
                    location=Location(latitude=ev_lat, longitude=ev_lon),
                    radius_km=dist,
                    source=source,
                    official_url=event.get("link", ""),
                ))

            logger.info(
                "EONET: found %d events near (%.2f, %.2f) within %dkm",
                len(alerts), location.latitude, location.longitude, radius_km,
            )
            return alerts

        except Exception:
            logger.exception("NASA EONET fetch failed")
            return []

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(f"{_EONET_URL}?limit=1", timeout=10.0)
            return resp.status_code == 200
        except Exception:
            return False
