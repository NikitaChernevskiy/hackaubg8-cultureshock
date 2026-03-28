"""Real alert provider — USGS Earthquake API + GDACS disaster feed.

Both are free, require no API key, and provide real-time data.
- USGS: https://earthquake.usgs.gov/fdsnws/event/1/
- GDACS: https://www.gdacs.org/xml/rss.xml
"""

import logging
import math
from datetime import datetime, timezone
from xml.etree import ElementTree

import httpx

from app.models.alerts import Alert
from app.models.common import DataSource, Location
from app.providers.base import AlertProvider

logger = logging.getLogger(__name__)

_USGS_SOURCE = DataSource(
    name="USGS Earthquake Hazards Program",
    url="https://earthquake.usgs.gov",
    retrieved_at=datetime.now(timezone.utc),
    reliability="official",
)

_GDACS_SOURCE = DataSource(
    name="GDACS (Global Disaster Alert and Coordination System)",
    url="https://www.gdacs.org",
    retrieved_at=datetime.now(timezone.utc),
    reliability="official",
)

# Approximate km per degree of latitude
_KM_PER_DEG = 111.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in km."""
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


def _mag_to_severity(mag: float) -> str:
    """Map earthquake magnitude to severity level."""
    if mag >= 7.0:
        return "critical"
    if mag >= 5.5:
        return "high"
    if mag >= 4.0:
        return "medium"
    if mag >= 2.5:
        return "low"
    return "info"


class USGSAlertProvider(AlertProvider):
    """Fetches real earthquake data from USGS + disaster alerts from GDACS."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=15.0)

    async def get_alerts(self, location: Location, radius_km: float = 100) -> list[Alert]:
        alerts: list[Alert] = []

        # Fetch from both sources in parallel-ish (sequential for simplicity, both are fast)
        usgs_alerts = await self._fetch_usgs(location, radius_km)
        alerts.extend(usgs_alerts)

        gdacs_alerts = await self._fetch_gdacs(location, radius_km)
        alerts.extend(gdacs_alerts)

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 5))

        return alerts

    async def _fetch_usgs(self, location: Location, radius_km: float) -> list[Alert]:
        """Fetch recent earthquakes from USGS within radius."""
        try:
            # USGS API: earthquakes in last 7 days, magnitude 2.5+, within radius
            max_radius_deg = radius_km / _KM_PER_DEG
            url = (
                "https://earthquake.usgs.gov/fdsnws/event/1/query"
                f"?format=geojson"
                f"&latitude={location.latitude}"
                f"&longitude={location.longitude}"
                f"&maxradiuskm={min(radius_km, 500)}"
                f"&minmagnitude=2.5"
                f"&orderby=magnitude"
                f"&limit=20"
            )
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()

            now = datetime.now(timezone.utc)
            source = DataSource(
                name="USGS Earthquake Hazards Program",
                url="https://earthquake.usgs.gov",
                retrieved_at=now,
                reliability="official",
            )

            alerts = []
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                coords = feature.get("geometry", {}).get("coordinates", [0, 0, 0])
                eq_lon, eq_lat, eq_depth = coords[0], coords[1], coords[2] if len(coords) > 2 else 0

                mag = props.get("mag", 0) or 0
                place = props.get("place", "Unknown location")
                time_ms = props.get("time", 0)
                eq_time = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc) if time_ms else now
                usgs_url = props.get("url", "")

                dist = _haversine_km(location.latitude, location.longitude, eq_lat, eq_lon)

                alerts.append(Alert(
                    id=f"usgs-{feature.get('id', 'unknown')}",
                    type="earthquake",
                    severity=_mag_to_severity(mag),
                    title=f"M{mag:.1f} Earthquake — {place}",
                    description=(
                        f"A magnitude {mag:.1f} earthquake occurred at depth {eq_depth:.0f}km, "
                        f"approximately {dist:.0f}km from your location. "
                        f"Location: {place}."
                    ),
                    issued_at=eq_time,
                    expires_at=None,
                    location=Location(latitude=eq_lat, longitude=eq_lon),
                    radius_km=dist,
                    source=source,
                    official_url=usgs_url,
                ))

            logger.info("USGS: fetched %d earthquakes near (%.2f, %.2f)", len(alerts), location.latitude, location.longitude)
            return alerts

        except Exception:
            logger.exception("USGS earthquake fetch failed")
            return []

    async def _fetch_gdacs(self, location: Location, radius_km: float) -> list[Alert]:
        """Fetch recent disaster alerts from GDACS RSS feed."""
        try:
            resp = await self._client.get("https://www.gdacs.org/xml/rss.xml")
            resp.raise_for_status()

            root = ElementTree.fromstring(resp.text)
            now = datetime.now(timezone.utc)
            source = DataSource(
                name="GDACS",
                url="https://www.gdacs.org",
                retrieved_at=now,
                reliability="official",
            )

            # GDACS namespace
            gdacs_ns = "http://www.gdacs.org"
            geo_ns = "http://www.georss.org/georss"

            alerts = []
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                description = item.findtext("description", "")
                link = item.findtext("link", "")

                # Parse location from georss:point
                point = item.findtext(f"{{{geo_ns}}}point", "")
                if not point:
                    continue
                try:
                    parts = point.strip().split()
                    alert_lat = float(parts[0])
                    alert_lon = float(parts[1])
                except (ValueError, IndexError):
                    continue

                # Check if within radius
                dist = _haversine_km(location.latitude, location.longitude, alert_lat, alert_lon)
                if dist > radius_km:
                    continue

                # Parse severity from GDACS alertlevel
                alert_level = item.findtext(f"{{{gdacs_ns}}}alertlevel", "Green")
                severity_map = {"Red": "critical", "Orange": "high", "Yellow": "medium", "Green": "low"}
                severity = severity_map.get(alert_level, "info")

                # Parse event type
                event_type = item.findtext(f"{{{gdacs_ns}}}eventtype", "other")
                type_map = {"EQ": "earthquake", "TC": "hurricane", "FL": "flood", "VO": "volcanic_eruption", "TS": "tsunami", "DR": "drought"}
                alert_type = type_map.get(event_type, "other")

                # Parse date
                pub_date_str = item.findtext("pubDate", "")
                try:
                    from email.utils import parsedate_to_datetime
                    issued_at = parsedate_to_datetime(pub_date_str).replace(tzinfo=timezone.utc)
                except Exception:
                    issued_at = now

                event_id = item.findtext(f"{{{gdacs_ns}}}eventid", "unknown")

                alerts.append(Alert(
                    id=f"gdacs-{event_type}-{event_id}",
                    type=alert_type,
                    severity=severity,
                    title=title,
                    description=description,
                    issued_at=issued_at,
                    expires_at=None,
                    location=Location(latitude=alert_lat, longitude=alert_lon),
                    radius_km=dist,
                    source=source,
                    official_url=link,
                ))

            logger.info("GDACS: fetched %d alerts near (%.2f, %.2f) within %dkm", len(alerts), location.latitude, location.longitude, radius_km)
            return alerts

        except Exception:
            logger.exception("GDACS fetch failed")
            return []

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(
                "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&limit=1&minmagnitude=5",
                timeout=10.0,
            )
            return resp.status_code == 200
        except Exception:
            return False
