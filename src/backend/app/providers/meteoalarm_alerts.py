"""Meteoalarm provider — EU-wide severe weather alerts.

Covers 30+ European countries with structured CAP-based alerts:
storms, floods, fire risk, extreme temperatures, snow, avalanches, etc.

This is the same data that feeds national alert systems like BG-Alert,
KATWARN (Germany), NL-Alert (Netherlands), IT-alert (Italy), etc.

API: https://feeds.meteoalarm.org/api/v1/warnings/feeds-{country}
Free, no API key.
"""

import logging
import math
from datetime import datetime, timezone

import httpx

from app.models.alerts import Alert
from app.models.common import DataSource, Location
from app.providers.base import AlertProvider

logger = logging.getLogger(__name__)

_FEED_URL = "https://feeds.meteoalarm.org/api/v1/warnings/feeds-{country}"

# Country slug → centroid (lat, lon) for proximity matching
_COUNTRIES: list[tuple[str, str, float, float]] = [
    ("bulgaria", "Bulgaria", 42.73, 25.49),
    ("greece", "Greece", 39.07, 21.82),
    ("romania", "Romania", 45.94, 24.97),
    ("serbia", "Serbia", 44.02, 21.01),
    ("north-macedonia", "North Macedonia", 41.51, 21.75),
    ("albania", "Albania", 41.15, 20.17),
    ("croatia", "Croatia", 45.10, 15.20),
    ("bosnia-and-herzegovina", "Bosnia and Herzegovina", 43.92, 17.68),
    ("montenegro", "Montenegro", 42.71, 19.37),
    ("slovenia", "Slovenia", 46.15, 14.99),
    ("hungary", "Hungary", 47.16, 19.50),
    ("austria", "Austria", 47.52, 14.55),
    ("slovakia", "Slovakia", 48.67, 19.70),
    ("italy", "Italy", 41.87, 12.57),
    ("germany", "Germany", 51.17, 10.45),
    ("france", "France", 46.23, 2.21),
    ("spain", "Spain", 40.46, -3.75),
    ("portugal", "Portugal", 39.40, -8.22),
    ("united-kingdom", "United Kingdom", 55.38, -3.44),
    ("ireland", "Ireland", 53.14, -7.69),
    ("netherlands", "Netherlands", 52.13, 5.29),
    ("belgium", "Belgium", 50.50, 4.47),
    ("luxembourg", "Luxembourg", 49.82, 6.13),
    ("switzerland", "Switzerland", 46.82, 8.23),
    ("poland", "Poland", 51.92, 19.15),
    ("denmark", "Denmark", 56.26, 9.50),
    ("sweden", "Sweden", 60.13, 18.64),
    ("norway", "Norway", 60.47, 8.47),
    ("finland", "Finland", 61.92, 25.75),
    ("iceland", "Iceland", 64.96, -19.02),
    ("estonia", "Estonia", 58.60, 25.01),
    ("latvia", "Latvia", 56.88, 24.60),
    ("lithuania", "Lithuania", 55.17, 23.88),
    ("cyprus", "Cyprus", 35.13, 33.43),
    ("malta", "Malta", 35.94, 14.38),
    ("moldova", "Moldova", 47.41, 28.37),
]

# Meteoalarm severity → our severity
_SEVERITY_MAP = {
    "Extreme": "critical",
    "Severe": "high",
    "Moderate": "medium",
    "Minor": "low",
}

# Map common Meteoalarm event types to our alert types
_EVENT_TYPE_MAP = {
    "wind": "hurricane",
    "storm": "hurricane",
    "gust": "hurricane",
    "thunderstorm": "hurricane",
    "rain": "flood",
    "flood": "flood",
    "snow": "other",
    "ice": "other",
    "fog": "other",
    "avalanche": "landslide",
    "fire": "wildfire",
    "heat": "other",
    "cold": "other",
    "tsunami": "tsunami",
    "coastal": "flood",
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


def _classify_event(event_text: str) -> str:
    """Map Meteoalarm event description to our alert type."""
    lower = event_text.lower()
    for keyword, alert_type in _EVENT_TYPE_MAP.items():
        if keyword in lower:
            return alert_type
    return "other"


class MeteoalarmProvider(AlertProvider):
    """Fetches real-time severe weather alerts from Meteoalarm (EU-wide).

    Checks nearby countries within the search radius and returns
    actual hazardous weather warnings (filters out "no hazard" entries).
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=12.0,
            headers={"User-Agent": "CultureShock-Emergency-App/0.4"},
        )

    async def get_alerts(self, location: Location, radius_km: float = 500) -> list[Alert]:
        # Find countries within range
        nearby = []
        for slug, name, clat, clon in _COUNTRIES:
            dist = _haversine_km(location.latitude, location.longitude, clat, clon)
            if dist < radius_km:
                nearby.append((slug, name, dist))

        nearby.sort(key=lambda x: x[2])
        nearby = nearby[:3]  # Limit to 3 closest countries to avoid slow responses

        if not nearby:
            return []

        now = datetime.now(timezone.utc)
        all_alerts: list[Alert] = []

        for slug, country_name, dist in nearby:
            try:
                alerts = await self._fetch_country(slug, country_name, dist, now)
                all_alerts.extend(alerts)
            except Exception:
                logger.exception("Meteoalarm fetch failed for %s", slug)

        logger.info(
            "Meteoalarm: found %d weather alerts for %d countries near (%.2f, %.2f)",
            len(all_alerts), len(nearby),
            location.latitude, location.longitude,
        )
        return all_alerts

    async def _fetch_country(
        self, slug: str, country_name: str, dist: float, now: datetime
    ) -> list[Alert]:
        """Fetch and filter alerts for a single country."""
        url = _FEED_URL.format(country=slug)
        resp = await self._client.get(url)
        if resp.status_code != 200:
            return []
        data = resp.json()

        source = DataSource(
            name=f"Meteoalarm ({country_name})",
            url=f"https://meteoalarm.org/en/live/page/{slug}",
            retrieved_at=now,
            reliability="official",
        )

        alerts = []
        seen: set[str] = set()

        for warning in data.get("warnings", []):
            alert_obj = warning.get("alert", {})

            for info in alert_obj.get("info", []):
                lang = info.get("language", "")
                # Prefer English, skip duplicates
                if lang != "en":
                    continue

                severity_raw = info.get("severity", "Minor")
                event = info.get("event", "")
                headline = info.get("headline", "")
                description = info.get("description", "")
                onset = info.get("onset", "")
                expires = info.get("expires", "")

                # Skip "no hazard" entries
                if "no hazard" in event.lower() or severity_raw == "Minor":
                    continue

                severity = _SEVERITY_MAP.get(severity_raw, "low")
                alert_type = _classify_event(event)

                # Parse areas
                areas = [a.get("areaDesc", "") for a in info.get("area", [])]
                area_str = ", ".join(areas[:5])

                # Deduplicate by event type
                dedup_key = f"{slug}-{event}-{area_str[:30]}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                # Get country centroid for location
                centroid_lat, centroid_lon = 0.0, 0.0
                for s, n, clat, clon in _COUNTRIES:
                    if s == slug:
                        centroid_lat, centroid_lon = clat, clon
                        break

                # Parse onset time
                try:
                    issued_at = datetime.fromisoformat(onset)
                except (ValueError, TypeError):
                    issued_at = now

                try:
                    expires_at = datetime.fromisoformat(expires)
                except (ValueError, TypeError):
                    expires_at = None

                desc = headline or description or f"{event} in {country_name}"
                if area_str:
                    desc += f" Affected areas: {area_str}."

                alerts.append(Alert(
                    id=f"meteoalarm-{slug}-{alert_obj.get('identifier', 'unknown')[:40]}",
                    type=alert_type,
                    severity=severity,
                    title=f"{event} — {country_name}",
                    description=desc[:500],
                    issued_at=issued_at,
                    expires_at=expires_at,
                    location=Location(latitude=centroid_lat, longitude=centroid_lon),
                    radius_km=dist,
                    source=source,
                    official_url=f"https://meteoalarm.org/en/live/page/{slug}",
                ))

        return alerts

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(
                _FEED_URL.format(country="germany"),
                timeout=10.0,
            )
            return resp.status_code == 200
        except Exception:
            return False
