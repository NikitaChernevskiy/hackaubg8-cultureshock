"""Reverse geocoding and country-specific data.

Uses coordinate-to-country mapping for emergency numbers,
language detection, and location context. No external API needed.
"""

import math

# Country centroids with emergency info
# (slug, name, iso2, lat, lon, emergency, police, ambulance, fire)
_COUNTRIES: list[tuple[str, str, str, float, float, str, str, str, str]] = [
    ("bulgaria", "Bulgaria", "BG", 42.73, 25.49, "112", "166", "150", "160"),
    ("turkey", "Turkey", "TR", 38.96, 35.24, "112", "155", "112", "110"),
    ("greece", "Greece", "GR", 39.07, 21.82, "112", "100", "166", "199"),
    ("romania", "Romania", "RO", 45.94, 24.97, "112", "112", "112", "112"),
    ("serbia", "Serbia", "RS", 44.02, 21.01, "112", "192", "194", "193"),
    ("north-macedonia", "North Macedonia", "MK", 41.51, 21.75, "112", "192", "194", "193"),
    ("albania", "Albania", "AL", 41.15, 20.17, "112", "129", "127", "128"),
    ("croatia", "Croatia", "HR", 45.10, 15.20, "112", "192", "194", "193"),
    ("hungary", "Hungary", "HU", 47.16, 19.50, "112", "107", "104", "105"),
    ("ukraine", "Ukraine", "UA", 48.38, 31.17, "112", "102", "103", "101"),
    ("russia", "Russia", "RU", 61.52, 105.32, "112", "102", "103", "101"),
    ("germany", "Germany", "DE", 51.17, 10.45, "112", "110", "112", "112"),
    ("france", "France", "FR", 46.23, 2.21, "112", "17", "15", "18"),
    ("spain", "Spain", "ES", 40.46, -3.75, "112", "091", "112", "080"),
    ("portugal", "Portugal", "PT", 39.40, -8.22, "112", "112", "112", "112"),
    ("italy", "Italy", "IT", 41.87, 12.57, "112", "113", "118", "115"),
    ("united-kingdom", "United Kingdom", "GB", 55.38, -3.44, "999", "999", "999", "999"),
    ("ireland", "Ireland", "IE", 53.14, -7.69, "112", "112", "112", "112"),
    ("netherlands", "Netherlands", "NL", 52.13, 5.29, "112", "112", "112", "112"),
    ("belgium", "Belgium", "BE", 50.50, 4.47, "112", "101", "112", "112"),
    ("austria", "Austria", "AT", 47.52, 14.55, "112", "133", "144", "122"),
    ("switzerland", "Switzerland", "CH", 46.82, 8.23, "112", "117", "144", "118"),
    ("poland", "Poland", "PL", 51.92, 19.15, "112", "997", "999", "998"),
    ("sweden", "Sweden", "SE", 60.13, 18.64, "112", "112", "112", "112"),
    ("norway", "Norway", "NO", 60.47, 8.47, "112", "112", "113", "110"),
    ("finland", "Finland", "FI", 61.92, 25.75, "112", "112", "112", "112"),
    ("denmark", "Denmark", "DK", 56.26, 9.50, "112", "112", "112", "112"),
    ("israel", "Israel", "IL", 31.05, 34.85, "100", "100", "101", "102"),
    ("palestine", "Palestine", "PS", 31.95, 35.23, "100", "100", "101", "102"),
    ("lebanon", "Lebanon", "LB", 33.85, 35.86, "112", "112", "140", "175"),
    ("syria", "Syria", "SY", 34.80, 38.99, "112", "112", "110", "113"),
    ("jordan", "Jordan", "JO", 30.59, 36.24, "911", "911", "911", "911"),
    ("egypt", "Egypt", "EG", 26.82, 30.80, "122", "122", "123", "180"),
    ("japan", "Japan", "JP", 36.20, 138.25, "110", "110", "119", "119"),
    ("south-korea", "South Korea", "KR", 35.91, 127.77, "112", "112", "119", "119"),
    ("china", "China", "CN", 35.86, 104.20, "110", "110", "120", "119"),
    ("india", "India", "IN", 20.59, 78.96, "112", "100", "108", "101"),
    ("thailand", "Thailand", "TH", 15.87, 100.99, "191", "191", "1669", "199"),
    ("indonesia", "Indonesia", "ID", -0.79, 113.92, "112", "110", "118", "113"),
    ("philippines", "Philippines", "PH", 12.88, 121.77, "911", "911", "911", "911"),
    ("australia", "Australia", "AU", -25.27, 133.78, "000", "000", "000", "000"),
    ("new-zealand", "New Zealand", "NZ", -40.90, 174.89, "111", "111", "111", "111"),
    ("usa", "United States", "US", 37.09, -95.71, "911", "911", "911", "911"),
    ("canada", "Canada", "CA", 56.13, -106.35, "911", "911", "911", "911"),
    ("mexico", "Mexico", "MX", 23.63, -102.55, "911", "911", "911", "911"),
    ("brazil", "Brazil", "BR", -14.24, -51.93, "190", "190", "192", "193"),
    ("argentina", "Argentina", "AR", -38.42, -63.62, "911", "911", "107", "100"),
    ("colombia", "Colombia", "CO", 4.57, -74.30, "123", "123", "123", "119"),
    ("chile", "Chile", "CL", -35.68, -71.54, "131", "133", "131", "132"),
    ("south-africa", "South Africa", "ZA", -30.56, 22.94, "10111", "10111", "10177", "10111"),
    ("nigeria", "Nigeria", "NG", 9.08, 8.68, "199", "199", "199", "199"),
    ("kenya", "Kenya", "KE", -0.02, 37.91, "999", "999", "999", "999"),
    ("morocco", "Morocco", "MA", 31.79, -7.09, "19", "19", "15", "15"),
    ("saudi-arabia", "Saudi Arabia", "SA", 23.89, 45.08, "911", "999", "997", "998"),
    ("uae", "United Arab Emirates", "AE", 23.42, 53.85, "999", "999", "998", "997"),
]


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def lookup_country(lat: float, lon: float) -> dict:
    """Find the nearest country to GPS coordinates.

    Returns dict with: name, iso2, emergency, police, ambulance, fire.
    """
    best = None
    best_dist = float("inf")
    for slug, name, iso2, clat, clon, emerg, police, amb, fire in _COUNTRIES:
        d = _haversine(lat, lon, clat, clon)
        if d < best_dist:
            best_dist = d
            best = {
                "slug": slug, "name": name, "iso2": iso2,
                "emergency": emerg, "police": police,
                "ambulance": amb, "fire": fire,
                "distance_km": round(d, 0),
            }
    return best or {
        "slug": "unknown", "name": "Unknown", "iso2": "XX",
        "emergency": "112", "police": "112", "ambulance": "112", "fire": "112",
        "distance_km": 0,
    }
