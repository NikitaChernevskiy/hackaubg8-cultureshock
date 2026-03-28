"""UK Foreign, Commonwealth & Development Office (FCDO) travel advisory provider.

Official UK government travel advice for 226 countries. Covers:
- Geopolitical warnings (conflict, civil unrest, terrorism)
- "Advise against all travel" / "advise against all but essential travel"
- Entry requirements, safety info
- Updated frequently by UK diplomats

API: https://www.gov.uk/api/content/foreign-travel-advice/{country-slug}
Free, no API key, structured JSON.
"""

import logging
import re
from datetime import datetime, timezone

import httpx

from app.models.alerts import Alert
from app.models.common import DataSource, Location
from app.providers.base import AlertProvider

logger = logging.getLogger(__name__)

_FCDO_INDEX_URL = "https://www.gov.uk/api/content/foreign-travel-advice"
_FCDO_COUNTRY_URL = "https://www.gov.uk/api/content/foreign-travel-advice/{slug}"

# Reverse geocoding: lat/lon → country slug
# We use a simple centroid-based lookup. For a production system you'd use
# a proper reverse geocoding API, but this covers the key regions.
_COUNTRY_CENTROIDS: list[tuple[str, str, float, float]] = [
    # slug, display_name, lat, lon
    ("bulgaria", "Bulgaria", 42.73, 25.49),
    ("turkey", "Turkey", 38.96, 35.24),
    ("greece", "Greece", 39.07, 21.82),
    ("romania", "Romania", 45.94, 24.97),
    ("serbia", "Serbia", 44.02, 21.01),
    ("north-macedonia", "North Macedonia", 41.51, 21.75),
    ("albania", "Albania", 41.15, 20.17),
    ("kosovo", "Kosovo", 42.60, 20.90),
    ("montenegro", "Montenegro", 42.71, 19.37),
    ("bosnia-and-herzegovina", "Bosnia and Herzegovina", 43.92, 17.68),
    ("croatia", "Croatia", 45.10, 15.20),
    ("hungary", "Hungary", 47.16, 19.50),
    ("ukraine", "Ukraine", 48.38, 31.17),
    ("russia", "Russia", 61.52, 105.32),
    ("italy", "Italy", 41.87, 12.57),
    ("israel", "Israel", 31.05, 34.85),
    ("palestine", "Palestine", 31.95, 35.23),
    ("lebanon", "Lebanon", 33.85, 35.86),
    ("syria", "Syria", 34.80, 38.99),
    ("iraq", "Iraq", 33.22, 43.68),
    ("iran", "Iran", 32.43, 53.69),
    ("yemen", "Yemen", 15.55, 48.52),
    ("libya", "Libya", 26.34, 17.23),
    ("sudan", "Sudan", 12.86, 30.22),
    ("south-sudan", "South Sudan", 6.88, 31.31),
    ("somalia", "Somalia", 5.15, 46.20),
    ("ethiopia", "Ethiopia", 9.15, 40.49),
    ("eritrea", "Eritrea", 15.18, 39.78),
    ("afghanistan", "Afghanistan", 33.94, 67.71),
    ("pakistan", "Pakistan", 30.38, 69.35),
    ("india", "India", 20.59, 78.96),
    ("myanmar", "Myanmar", 21.91, 95.96),
    ("china", "China", 35.86, 104.20),
    ("north-korea", "North Korea", 40.34, 127.51),
    ("japan", "Japan", 36.20, 138.25),
    ("indonesia", "Indonesia", -0.79, 113.92),
    ("philippines", "Philippines", 12.88, 121.77),
    ("usa", "United States", 37.09, -95.71),
    ("mexico", "Mexico", 23.63, -102.55),
    ("colombia", "Colombia", 4.57, -74.30),
    ("venezuela", "Venezuela", 6.42, -66.59),
    ("haiti", "Haiti", 18.97, -72.29),
    ("kenya", "Kenya", -0.02, 37.91),
    ("democratic-republic-of-the-congo", "DRC", -4.04, 21.76),
    ("egypt", "Egypt", 26.82, 30.80),
    ("tunisia", "Tunisia", 33.89, 9.54),
    ("morocco", "Morocco", 31.79, -7.09),
    ("algeria", "Algeria", 28.03, 1.66),
    ("saudi-arabia", "Saudi Arabia", 23.89, 45.08),
    ("jordan", "Jordan", 30.59, 36.24),
    ("georgia", "Georgia", 42.32, 43.36),
    ("armenia", "Armenia", 40.07, 45.04),
    ("azerbaijan", "Azerbaijan", 40.14, 47.58),
    ("moldova", "Moldova", 47.41, 28.37),
    ("belarus", "Belarus", 53.71, 27.95),
    ("poland", "Poland", 51.92, 19.15),
    ("germany", "Germany", 51.17, 10.45),
    ("france", "France", 46.23, 2.21),
    ("spain", "Spain", 40.46, -3.75),
    ("portugal", "Portugal", 39.40, -8.22),
    ("united-kingdom", "United Kingdom", 55.38, -3.44),
    ("thailand", "Thailand", 15.87, 100.99),
    ("malaysia", "Malaysia", 4.21, 101.98),
    ("australia", "Australia", -25.27, 133.78),
    ("new-zealand", "New Zealand", -40.90, 174.89),
    ("brazil", "Brazil", -14.24, -51.93),
    ("argentina", "Argentina", -38.42, -63.62),
    ("chile", "Chile", -35.68, -71.54),
    ("peru", "Peru", -9.19, -75.02),
    ("cuba", "Cuba", 21.52, -77.78),
    ("nigeria", "Nigeria", 9.08, 8.68),
    ("south-africa", "South Africa", -30.56, 22.94),
    ("bangladesh", "Bangladesh", 23.68, 90.36),
    ("nepal", "Nepal", 28.39, 84.12),
    ("sri-lanka", "Sri Lanka", 7.87, 80.77),
    ("cambodia", "Cambodia", 12.57, 104.99),
    ("laos", "Laos", 19.86, 102.50),
    ("vietnam", "Vietnam", 14.06, 108.28),
]

# Phrases that indicate serious geopolitical warnings
_SEVERE_PHRASES = [
    "advises against all travel",
    "advise against all travel",
    "do not travel",
    "armed conflict",
    "ongoing conflict",
    "active conflict",
    "military operations",
    "war zone",
    "martial law",
]

_ELEVATED_PHRASES = [
    "advises against all but essential travel",
    "advise against all but essential travel",
    "terrorism",
    "kidnapping",
    "civil unrest",
    "political instability",
    "coup",
    "state of emergency",
    "border closure",
    "curfew",
]


def _strip_html(text: str) -> str:
    """Remove HTML tags."""
    return re.sub(r"<[^>]+>", "", text).strip()


def _distance_approx(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate distance in km (good enough for country-level matching)."""
    import math
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


class FCDOAlertProvider(AlertProvider):
    """Fetches geopolitical travel advisories from UK FCDO.

    For a given location:
    1. Find the country the user is in (nearest centroid match)
    2. Also check neighboring countries within radius
    3. Fetch FCDO advice for each
    4. Extract warnings, classify severity
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": "CultureShock-Emergency-App/0.3"},
        )

    async def get_alerts(self, location: Location, radius_km: float = 500) -> list[Alert]:
        # Find countries within range
        nearby_countries = []
        for slug, name, clat, clon in _COUNTRY_CENTROIDS:
            dist = _distance_approx(location.latitude, location.longitude, clat, clon)
            if dist < radius_km:
                nearby_countries.append((slug, name, dist))

        # Sort by distance (check user's country first)
        nearby_countries.sort(key=lambda x: x[2])

        # Limit to closest 5 countries to avoid too many API calls
        nearby_countries = nearby_countries[:5]

        if not nearby_countries:
            return []

        now = datetime.now(timezone.utc)
        source = DataSource(
            name="UK FCDO Travel Advice",
            url="https://www.gov.uk/foreign-travel-advice",
            retrieved_at=now,
            reliability="official",
        )

        alerts: list[Alert] = []
        for slug, country_name, dist in nearby_countries:
            try:
                advice = await self._fetch_country_advice(slug)
                if not advice:
                    continue

                warnings_text = advice.get("warnings", "")
                safety_text = advice.get("safety", "")
                updated = advice.get("updated", "")
                full_text = f"{warnings_text} {safety_text}".lower()

                # Classify severity based on FCDO language
                severity = "info"
                alert_type = "geopolitical"

                for phrase in _SEVERE_PHRASES:
                    if phrase in full_text:
                        severity = "critical"
                        break

                if severity != "critical":
                    for phrase in _ELEVATED_PHRASES:
                        if phrase in full_text:
                            severity = "high"
                            break

                if severity == "info":
                    # Skip countries with no significant warnings
                    # (no point alerting about normal travel advice)
                    continue

                # Find the centroid for this country
                centroid_lat, centroid_lon = 0.0, 0.0
                for s, n, clat, clon in _COUNTRY_CENTROIDS:
                    if s == slug:
                        centroid_lat, centroid_lon = clat, clon
                        break

                # Build a concise description from the warnings
                description = warnings_text[:500] if warnings_text else safety_text[:500]

                title_prefix = "FCDO advises against ALL travel" if severity == "critical" else "FCDO: elevated risk"
                title = f"{title_prefix} — {country_name}"

                try:
                    issued_at = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    issued_at = now

                alerts.append(Alert(
                    id=f"fcdo-{slug}",
                    type=alert_type,
                    severity=severity,
                    title=title,
                    description=description,
                    issued_at=issued_at,
                    expires_at=None,
                    location=Location(latitude=centroid_lat, longitude=centroid_lon),
                    radius_km=dist,
                    source=source,
                    official_url=f"https://www.gov.uk/foreign-travel-advice/{slug}",
                ))

            except Exception:
                logger.exception("FCDO fetch failed for %s", slug)
                continue

        logger.info(
            "FCDO: found %d travel advisories for %d countries near (%.2f, %.2f)",
            len(alerts), len(nearby_countries),
            location.latitude, location.longitude,
        )
        return alerts

    async def _fetch_country_advice(self, slug: str) -> dict | None:
        """Fetch and parse FCDO advice for a single country."""
        try:
            url = _FCDO_COUNTRY_URL.format(slug=slug)
            resp = await self._client.get(url)
            if resp.status_code != 200:
                return None
            data = resp.json()

            parts = data.get("details", {}).get("parts", [])
            warnings = ""
            safety = ""

            for part in parts:
                title = part.get("title", "").lower()
                body = _strip_html(part.get("body", ""))
                if "warning" in title or "insurance" in title:
                    warnings = body
                elif "safety" in title or "security" in title:
                    safety = body

            return {
                "warnings": warnings,
                "safety": safety,
                "updated": data.get("public_updated_at", ""),
            }
        except Exception:
            logger.exception("Failed to fetch FCDO advice for %s", slug)
            return None

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(
                "https://www.gov.uk/api/content/foreign-travel-advice",
                timeout=10.0,
            )
            return resp.status_code == 200
        except Exception:
            return False
