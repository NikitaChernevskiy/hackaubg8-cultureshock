"""ReliefWeb API provider — UN OCHA humanitarian data.

Covers: conflicts, humanitarian crises, disaster reports, epidemics.
Free, no API key required (just a User-Agent / appname).

API docs: https://apidoc.reliefweb.int/
"""

import logging
import math
from datetime import datetime, timezone

import httpx

from app.models.alerts import Alert
from app.models.common import DataSource, Location
from app.providers.base import AlertProvider

logger = logging.getLogger(__name__)

_RELIEFWEB_URL = "https://api.reliefweb.int/v1/disasters"

# Map ReliefWeb disaster types to our types
_TYPE_MAP = {
    "Earthquake": "earthquake",
    "Flood": "flood",
    "Tropical Cyclone": "hurricane",
    "Volcano": "volcanic_eruption",
    "Tsunami": "tsunami",
    "Epidemic": "pandemic",
    "Fire": "wildfire",
    "Drought": "other",
    "Land Slide": "landslide",
    "Insect Infestation": "other",
    "Cold Wave": "other",
    "Heat Wave": "other",
    "Storm Surge": "flood",
    "Flash Flood": "flood",
    "Complex Emergency": "geopolitical",
    "Technological Disaster": "industrial_accident",
    "Other": "other",
}

# Country name → approximate centroid coordinates for distance check
# (ReliefWeb only gives country names, not precise coordinates)
_COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "Bulgaria": (42.73, 25.49),
    "Turkey": (38.96, 35.24),
    "Türkiye": (38.96, 35.24),
    "Greece": (39.07, 21.82),
    "Romania": (45.94, 24.97),
    "Serbia": (44.02, 21.01),
    "North Macedonia": (41.51, 21.75),
    "Albania": (41.15, 20.17),
    "Italy": (41.87, 12.57),
    "Ukraine": (48.38, 31.17),
    "Syria": (34.80, 38.99),
    "Iraq": (33.22, 43.68),
    "Iran": (32.43, 53.69),
    "Japan": (36.20, 138.25),
    "Indonesia": (-0.79, 113.92),
    "Philippines": (12.88, 121.77),
    "India": (20.59, 78.96),
    "China": (35.86, 104.20),
    "United States of America": (37.09, -95.71),
    "Mexico": (23.63, -102.55),
    "Chile": (-35.68, -71.54),
    "Colombia": (4.57, -74.30),
    "Afghanistan": (33.94, 67.71),
    "Pakistan": (30.38, 69.35),
    "Myanmar": (21.91, 95.96),
    "Nepal": (28.39, 84.12),
    "Bangladesh": (23.68, 90.36),
    "Ethiopia": (9.15, 40.49),
    "Kenya": (-0.02, 37.91),
    "Somalia": (5.15, 46.20),
    "Sudan": (12.86, 30.22),
    "South Sudan": (6.88, 31.31),
    "Democratic Republic of the Congo": (-4.04, 21.76),
    "Haiti": (18.97, -72.29),
    "Yemen": (15.55, 48.52),
    "Libya": (26.34, 17.23),
    "Lebanon": (33.85, 35.86),
    "Palestine": (31.95, 35.23),
    "Israel": (31.05, 34.85),
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


class ReliefWebAlertProvider(AlertProvider):
    """Fetches humanitarian disaster data from UN OCHA ReliefWeb."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": "CultureShock-Emergency-App/0.2.0"},
        )

    async def get_alerts(self, location: Location, radius_km: float = 500) -> list[Alert]:
        try:
            resp = await self._client.get(
                _RELIEFWEB_URL,
                params={
                    "appname": "cultureshock",
                    "preset": "latest",
                    "limit": 30,
                    "fields[include][]": [
                        "name", "status", "date", "type", "country", "url", "description-html",
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()

            now = datetime.now(timezone.utc)
            source = DataSource(
                name="ReliefWeb (UN OCHA)",
                url="https://reliefweb.int",
                retrieved_at=now,
                reliability="official",
            )

            alerts = []
            for item in data.get("data", []):
                fields = item.get("fields", {})

                # Check if any affected country is within range
                countries = fields.get("country", [])
                min_dist = float("inf")
                nearest_lat, nearest_lon = 0.0, 0.0

                for country in countries:
                    cname = country.get("name", "")
                    coords = _COUNTRY_COORDS.get(cname)
                    if coords:
                        dist = _haversine_km(location.latitude, location.longitude, coords[0], coords[1])
                        if dist < min_dist:
                            min_dist = dist
                            nearest_lat, nearest_lon = coords

                if min_dist > radius_km:
                    continue

                # Parse type
                types = fields.get("type", [])
                type_name = types[0].get("name", "Other") if types else "Other"
                alert_type = _TYPE_MAP.get(type_name, "other")

                # Determine severity from status
                status = fields.get("status", "current")
                severity = "high" if status == "current" else "medium"

                # Parse date
                date_info = fields.get("date", {})
                created = date_info.get("created", "")
                try:
                    issued_at = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    issued_at = now

                name = fields.get("name", "Unknown Disaster")
                country_names = ", ".join(c.get("name", "") for c in countries)

                alerts.append(Alert(
                    id=f"reliefweb-{item.get('id', 'unknown')}",
                    type=alert_type,
                    severity=severity,
                    title=name,
                    description=(
                        f"UN OCHA ReliefWeb disaster report. "
                        f"Affected countries: {country_names}. "
                        f"Type: {type_name}. Status: {status}."
                    ),
                    issued_at=issued_at,
                    expires_at=None,
                    location=Location(latitude=nearest_lat, longitude=nearest_lon),
                    radius_km=min_dist,
                    source=source,
                    official_url=fields.get("url", ""),
                ))

            logger.info(
                "ReliefWeb: found %d disasters near (%.2f, %.2f) within %dkm",
                len(alerts), location.latitude, location.longitude, radius_km,
            )
            return alerts

        except Exception:
            logger.exception("ReliefWeb fetch failed")
            return []

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(
                _RELIEFWEB_URL,
                params={"appname": "cultureshock", "limit": 1},
                timeout=10.0,
            )
            return resp.status_code == 200
        except Exception:
            return False
