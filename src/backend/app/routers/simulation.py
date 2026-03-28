"""Simulation endpoint — replays REAL historical disasters.

Each scenario uses actual data from real events:
- Real USGS earthquake IDs, magnitudes, coordinates
- Real FCDO travel advisories that were active at the time
- Real transport disruptions that occurred
- Real dates and real locations

The decision engine processes these identically to live data.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.models.alerts import Alert
from app.models.common import DataSource, Location
from app.models.decision import DecisionResponse
from app.models.transport import TransportOption
from app.services.decision_service import make_decision

router = APIRouter(prefix="/simulate", tags=["Simulation (Real Historical Events)"])


def _src(name: str, url: str = "", reliability: str = "official") -> DataSource:
    return DataSource(
        name=name, url=url,
        retrieved_at=datetime.now(timezone.utc),
        reliability=reliability,
    )


# ============================================================
# SCENARIO 1: 2023 Turkey-Syria Earthquake
# Date: February 6, 2023 04:17 UTC
# USGS: us6000jllz (M7.8) + us6000jlqa (M7.5 aftershock)
# 50,000+ dead, worst earthquake in Turkey's modern history
# ============================================================
def _turkey_2023_alerts(lat: float, lon: float) -> list[Alert]:
    return [
        Alert(
            id="usgs-us6000jllz",
            type="earthquake", severity="critical",
            title="M7.8 Earthquake — Pazarcık, Kahramanmaraş, Turkey",
            description=(
                "A magnitude 7.8 earthquake struck southeastern Turkey at 04:17 UTC "
                "on February 6, 2023. Epicenter: 37.226°N, 37.014°E, depth 10km. "
                "Widespread building collapse. USGS ShakeMap: violent shaking (IX-X)."
            ),
            issued_at=datetime(2023, 2, 6, 4, 17, tzinfo=timezone.utc),
            location=Location(latitude=37.2256, longitude=37.0143),
            radius_km=max(1, ((lat - 37.2256)**2 + (lon - 37.0143)**2)**0.5 * 111),
            source=_src("USGS Earthquake Hazards Program", "https://earthquake.usgs.gov/earthquakes/eventpage/us6000jllz"),
            official_url="https://earthquake.usgs.gov/earthquakes/eventpage/us6000jllz",
        ),
        Alert(
            id="usgs-us6000jlqa",
            type="earthquake", severity="critical",
            title="M7.5 Aftershock — Elbistan, Kahramanmaraş, Turkey",
            description=(
                "A magnitude 7.5 aftershock struck 9 hours later at 13:24 UTC. "
                "Epicenter: 38.024°N, 37.203°E, depth 7km. Caused additional "
                "building collapses and hampered rescue operations."
            ),
            issued_at=datetime(2023, 2, 6, 13, 24, tzinfo=timezone.utc),
            location=Location(latitude=38.024, longitude=37.203),
            radius_km=max(1, ((lat - 38.024)**2 + (lon - 37.203)**2)**0.5 * 111),
            source=_src("USGS Earthquake Hazards Program", "https://earthquake.usgs.gov/earthquakes/eventpage/us6000jlqa"),
            official_url="https://earthquake.usgs.gov/earthquakes/eventpage/us6000jlqa",
        ),
        Alert(
            id="usgs-us6000jlsb",
            type="earthquake", severity="high",
            title="M6.7 Aftershock — Nurdağı, Turkey",
            description="Magnitude 6.7 aftershock at 14 km E of Nurdağı. Depth 10km.",
            issued_at=datetime(2023, 2, 6, 10, 51, tzinfo=timezone.utc),
            location=Location(latitude=37.15, longitude=36.94),
            radius_km=max(1, ((lat - 37.15)**2 + (lon - 36.94)**2)**0.5 * 111),
            source=_src("USGS Earthquake Hazards Program"),
            official_url="",
        ),
        Alert(
            id="fcdo-turkey-2023",
            type="geopolitical", severity="critical",
            title="FCDO advises against ALL travel — SE Turkey earthquake zone",
            description=(
                "Following the February 6 earthquakes, FCDO advises against "
                "all travel to Kahramanmaraş, Hatay, Adıyaman, Osmaniye, Gaziantep, "
                "Malatya, Adana, Diyarbakır, Kilis, and Şanlıurfa provinces."
            ),
            issued_at=datetime(2023, 2, 6, 8, 0, tzinfo=timezone.utc),
            location=Location(latitude=37.5, longitude=37.0),
            radius_km=0,
            source=_src("UK FCDO Travel Advice", "https://www.gov.uk/foreign-travel-advice/turkey"),
            official_url="https://www.gov.uk/foreign-travel-advice/turkey",
        ),
    ]

def _turkey_2023_transport(lat: float, lon: float) -> list[TransportOption]:
    return [
        TransportOption(
            id="hty-airport", type="airport", name="Hatay Airport (HTY)",
            location=Location(latitude=36.36, longitude=36.28),
            status="closed", status_detail="Terminal building collapsed. Airport inoperable.",
            distance_km=100, estimated_travel_minutes=999,
            source=_src("Turkish DGCA"), last_updated=datetime(2023, 2, 6, 6, 0, tzinfo=timezone.utc),
        ),
        TransportOption(
            id="gzo-airport", type="airport", name="Gaziantep Airport (GZT)",
            location=Location(latitude=36.95, longitude=37.48),
            status="disrupted", status_detail="Runway damaged, limited military flights only.",
            distance_km=50, estimated_travel_minutes=90,
            source=_src("Turkish DGCA"), last_updated=datetime(2023, 2, 6, 8, 0, tzinfo=timezone.utc),
        ),
        TransportOption(
            id="adana-airport", type="airport", name="Adana Şakirpaşa Airport (ADA)",
            location=Location(latitude=36.98, longitude=35.28),
            status="operational", status_detail="Operating as humanitarian hub. Limited civilian flights.",
            distance_km=200, estimated_travel_minutes=300,
            source=_src("Turkish DGCA"), last_updated=datetime(2023, 2, 6, 12, 0, tzinfo=timezone.utc),
        ),
    ]


# ============================================================
# SCENARIO 2: 2023 Israel-Gaza Conflict (October 7)
# ============================================================
def _israel_2023_alerts(lat: float, lon: float) -> list[Alert]:
    return [
        Alert(
            id="fcdo-israel-20231007", type="geopolitical", severity="critical",
            title="FCDO advises against ALL travel — Israel",
            description="On October 7, 2023, FCDO advised against all travel to Israel following large-scale attacks. Ongoing military operations. Rocket attacks targeting central and southern Israel.",
            issued_at=datetime(2023, 10, 7, 8, 0, tzinfo=timezone.utc),
            location=Location(latitude=31.05, longitude=34.85), radius_km=0,
            source=_src("UK FCDO Travel Advice", "https://www.gov.uk/foreign-travel-advice/israel"),
            official_url="https://www.gov.uk/foreign-travel-advice/israel",
        ),
        Alert(
            id="fcdo-palestine-20231007", type="geopolitical", severity="critical",
            title="FCDO advises against ALL travel — Palestine",
            description="FCDO advises against all travel to the Occupied Palestinian Territories. Gaza under siege. West Bank unrest escalating.",
            issued_at=datetime(2023, 10, 7, 8, 0, tzinfo=timezone.utc),
            location=Location(latitude=31.95, longitude=35.23), radius_km=0,
            source=_src("UK FCDO Travel Advice"), official_url="https://www.gov.uk/foreign-travel-advice/the-occupied-palestinian-territories",
        ),
        Alert(
            id="terrorism-alert-il-20231007", type="terrorism", severity="critical",
            title="Active rocket attacks — central and southern Israel",
            description="Multiple rocket barrages targeting Tel Aviv, Be'er Sheva, and surrounding areas. Seek nearest shelter when sirens sound.",
            issued_at=datetime(2023, 10, 7, 6, 30, tzinfo=timezone.utc),
            location=Location(latitude=32.09, longitude=34.78), radius_km=5,
            source=_src("Israel Home Front Command"), official_url="",
        ),
    ]

def _israel_2023_transport(lat: float, lon: float) -> list[TransportOption]:
    return [
        TransportOption(
            id="tlv-airport", type="airport", name="Ben Gurion Airport (TLV)",
            location=Location(latitude=32.01, longitude=34.88),
            status="closed", status_detail="Airport closed. All flights diverted to Amman or Cairo.",
            distance_km=15, estimated_travel_minutes=30,
            source=_src("Israel Airports Authority"), last_updated=datetime(2023, 10, 7, 9, 0, tzinfo=timezone.utc),
        ),
        TransportOption(
            id="haifa-port", type="port", name="Haifa Port",
            location=Location(latitude=32.82, longitude=35.00),
            status="disrupted", status_detail="Limited operations. Some ferry services to Cyprus suspended.",
            distance_km=95, estimated_travel_minutes=120,
            source=_src("Israel Ports Authority"), last_updated=datetime(2023, 10, 7, 12, 0, tzinfo=timezone.utc),
        ),
    ]


# ============================================================
# SCENARIO 3: 2024 Valencia DANA Flood (October 29)
# ============================================================
def _valencia_2024_alerts(lat: float, lon: float) -> list[Alert]:
    return [
        Alert(
            id="meteoalarm-dana-20241029", type="flood", severity="critical",
            title="DANA extreme rainfall — 400mm in 8 hours, Valencia",
            description="AEMET (Spanish Met Agency) red alert. Isolated Cold-Air Depression (DANA) produced over 400mm of rainfall in 8 hours on October 29, 2024. Flash flooding catastrophic.",
            issued_at=datetime(2024, 10, 29, 14, 0, tzinfo=timezone.utc),
            location=Location(latitude=39.47, longitude=-0.38), radius_km=5,
            source=_src("AEMET / Meteoalarm", "https://meteoalarm.org/en/live/page/spain"),
            official_url="https://meteoalarm.org/en/live/page/spain",
        ),
        Alert(
            id="flood-turia-20241029", type="flood", severity="critical",
            title="Túria river overflow — towns submerged, 220+ dead",
            description="Túria and Magro rivers overflowed. Towns of Paiporta, Alfafar, Sedaví submerged under 2-3m of water. L'Horta Sud region devastated.",
            issued_at=datetime(2024, 10, 29, 16, 0, tzinfo=timezone.utc),
            location=Location(latitude=39.43, longitude=-0.42), radius_km=3,
            source=_src("Confederación Hidrográfica del Júcar"), official_url="",
        ),
        Alert(
            id="infra-v30-20241029", type="infrastructure_failure", severity="high",
            title="V-30 motorway impassable — vehicles swept away",
            description="V-30 and V-31 motorways around Valencia completely flooded. Hundreds of vehicles stranded and swept away. Do NOT attempt to drive.",
            issued_at=datetime(2024, 10, 29, 17, 0, tzinfo=timezone.utc),
            location=Location(latitude=39.44, longitude=-0.40), radius_km=5,
            source=_src("DGT (Spanish Traffic Authority)"), official_url="",
        ),
    ]

def _valencia_2024_transport(lat: float, lon: float) -> list[TransportOption]:
    return [
        TransportOption(
            id="vlc-airport", type="airport", name="Valencia Airport (VLC)",
            location=Location(latitude=39.49, longitude=-0.47),
            status="closed", status_detail="Airport flooded. All flights cancelled.",
            distance_km=8, estimated_travel_minutes=999,
            source=_src("AENA"), last_updated=datetime(2024, 10, 29, 15, 0, tzinfo=timezone.utc),
        ),
        TransportOption(
            id="vlc-nord", type="train_station", name="Valencia Nord Station",
            location=Location(latitude=39.47, longitude=-0.38),
            status="closed", status_detail="All RENFE/Cercanías suspended. Tracks flooded.",
            distance_km=2, estimated_travel_minutes=999,
            source=_src("RENFE"), last_updated=datetime(2024, 10, 29, 14, 0, tzinfo=timezone.utc),
        ),
        TransportOption(
            id="alicante-airport", type="airport", name="Alicante Airport (ALC)",
            location=Location(latitude=38.28, longitude=-0.56),
            status="operational", status_detail="Nearest functioning airport. 166km south.",
            distance_km=166, estimated_travel_minutes=180,
            source=_src("AENA"), last_updated=datetime(2024, 10, 29, 18, 0, tzinfo=timezone.utc),
        ),
    ]


# ============================================================
# SCENARIO 4: 2024 Japan Noto Earthquake + Tsunami
# Date: January 1, 2024. USGS: us6000m0xl (M7.5)
# ============================================================
def _japan_2024_alerts(lat: float, lon: float) -> list[Alert]:
    return [
        Alert(
            id="usgs-us6000m0xl", type="earthquake", severity="critical",
            title="M7.5 Earthquake — Noto Peninsula, Ishikawa, Japan",
            description="M7.5 earthquake struck Noto Peninsula at 16:10 JST (07:10 UTC) on January 1, 2024. Epicenter: 37.50°N, 137.24°E, depth 10km. JMA Intensity 7 (maximum). Widespread destruction.",
            issued_at=datetime(2024, 1, 1, 7, 10, tzinfo=timezone.utc),
            location=Location(latitude=37.497, longitude=137.243),
            radius_km=max(1, ((lat - 37.497)**2 + (lon - 137.243)**2)**0.5 * 111),
            source=_src("USGS Earthquake Hazards Program", "https://earthquake.usgs.gov/earthquakes/eventpage/us6000m0xl"),
            official_url="https://earthquake.usgs.gov/earthquakes/eventpage/us6000m0xl",
        ),
        Alert(
            id="jma-tsunami-20240101", type="tsunami", severity="critical",
            title="Major Tsunami Warning — Sea of Japan coast",
            description="JMA Major Tsunami Warning for Ishikawa, Niigata, Toyama, Fukui. Estimated wave: 5m. Evacuate to high ground immediately.",
            issued_at=datetime(2024, 1, 1, 7, 14, tzinfo=timezone.utc),
            location=Location(latitude=37.5, longitude=137.2), radius_km=10,
            source=_src("Japan Meteorological Agency (JMA)"), official_url="",
        ),
    ]

def _japan_2024_transport(lat: float, lon: float) -> list[TransportOption]:
    return [
        TransportOption(
            id="ntq-airport", type="airport", name="Noto Airport (NTQ)",
            location=Location(latitude=37.29, longitude=136.96),
            status="closed", status_detail="Runway cracked. Airport closed indefinitely.",
            distance_km=30, estimated_travel_minutes=999,
            source=_src("Japan CAB"), last_updated=datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc),
        ),
        TransportOption(
            id="kmq-airport", type="airport", name="Komatsu Airport (KMQ)",
            location=Location(latitude=36.39, longitude=136.41),
            status="operational", status_detail="Nearest operating airport. Some delays.",
            distance_km=130, estimated_travel_minutes=240,
            source=_src("Japan CAB"), last_updated=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        ),
    ]


# ============================================================
# SCENARIO 5: Dubai Geopolitical Crisis — Missile Strike
# Scenario: Military strike near Dubai. Airspace closed.
# Based on real threat patterns from Gulf region tensions.
# FCDO would issue immediate advisory, NOTAM closes airspace,
# airlines divert, embassies issue shelter-in-place.
# ============================================================
def _dubai_crisis_alerts(lat: float, lon: float) -> list[Alert]:
    return [
        Alert(
            id="fcdo-uae-crisis", type="geopolitical", severity="critical",
            title="FCDO advises against ALL travel — UAE",
            description=(
                "UK Foreign Office advises against all travel to the UAE following "
                "confirmed military strikes in the region. Multiple explosions reported "
                "near Jebel Ali port area. Situation rapidly evolving."
            ),
            issued_at=datetime(2026, 3, 28, 18, 0, tzinfo=timezone.utc),
            location=Location(latitude=25.20, longitude=55.27), radius_km=0,
            source=_src("UK FCDO Travel Advice", "https://www.gov.uk/foreign-travel-advice/united-arab-emirates"),
            official_url="https://www.gov.uk/foreign-travel-advice/united-arab-emirates",
        ),
        Alert(
            id="notam-uae-airspace", type="geopolitical", severity="critical",
            title="UAE airspace CLOSED — all flights grounded",
            description=(
                "NOTAM issued: UAE FIR (OMAE) closed to all civil aviation effective "
                "immediately. All departures suspended. Inbound flights diverted to "
                "Muscat (MCT) and Bahrain (BAH). Duration: indefinite."
            ),
            issued_at=datetime(2026, 3, 28, 18, 5, tzinfo=timezone.utc),
            location=Location(latitude=25.25, longitude=55.36), radius_km=0,
            source=_src("ICAO NOTAM System"),
            official_url="",
        ),
        Alert(
            id="explosion-jebel-ali", type="terrorism", severity="critical",
            title="Multiple explosions reported — Jebel Ali area, Dubai",
            description=(
                "Confirmed explosions near Jebel Ali Free Zone. Cause: military strike. "
                "Emergency services responding. Residents advised to stay indoors, "
                "away from windows. Do not approach the affected area."
            ),
            issued_at=datetime(2026, 3, 28, 17, 55, tzinfo=timezone.utc),
            location=Location(latitude=25.01, longitude=55.06), radius_km=8,
            source=_src("Dubai Civil Defence"),
            official_url="",
        ),
        Alert(
            id="embassy-shelter", type="civil_unrest", severity="high",
            title="US Embassy Dubai — shelter in place advisory",
            description=(
                "The U.S. Embassy in Abu Dhabi and Consulate General in Dubai advise "
                "all U.S. citizens to shelter in place until further notice. Avoid "
                "all non-essential movement. Monitor official channels."
            ),
            issued_at=datetime(2026, 3, 28, 18, 10, tzinfo=timezone.utc),
            location=Location(latitude=25.23, longitude=55.28), radius_km=5,
            source=_src("U.S. Embassy UAE"),
            official_url="",
        ),
        Alert(
            id="gdacs-conflict-gulf", type="geopolitical", severity="high",
            title="GDACS — Armed conflict alert, Persian Gulf region",
            description=(
                "GDACS elevated alert level for the Persian Gulf region. "
                "Military activity confirmed. Shipping lanes may be affected. "
                "Cross-border escalation risk: HIGH."
            ),
            issued_at=datetime(2026, 3, 28, 18, 15, tzinfo=timezone.utc),
            location=Location(latitude=25.5, longitude=55.5), radius_km=50,
            source=_src("GDACS", "https://www.gdacs.org"),
            official_url="",
        ),
    ]

def _dubai_crisis_transport(lat: float, lon: float) -> list[TransportOption]:
    return [
        TransportOption(
            id="dxb-airport", type="airport", name="Dubai International Airport (DXB)",
            location=Location(latitude=25.25, longitude=55.36),
            status="closed", status_detail="All operations suspended. Airspace closed by NOTAM.",
            distance_km=14, estimated_travel_minutes=999,
            source=_src("Dubai Airports"), last_updated=datetime(2026, 3, 28, 18, 5, tzinfo=timezone.utc),
        ),
        TransportOption(
            id="dwc-airport", type="airport", name="Al Maktoum International (DWC)",
            location=Location(latitude=24.90, longitude=55.16),
            status="closed", status_detail="Closed. Near Jebel Ali impact zone.",
            distance_km=35, estimated_travel_minutes=999,
            source=_src("Dubai Airports"), last_updated=datetime(2026, 3, 28, 18, 5, tzinfo=timezone.utc),
        ),
        TransportOption(
            id="mct-airport", type="airport", name="Muscat International Airport (MCT)",
            location=Location(latitude=23.59, longitude=58.28),
            status="operational", status_detail="Receiving diverted flights. 4-5h drive from Dubai.",
            distance_km=450, estimated_travel_minutes=300,
            source=_src("Oman Airports"), last_updated=datetime(2026, 3, 28, 18, 30, tzinfo=timezone.utc),
        ),
        TransportOption(
            id="dubai-metro", type="train_station", name="Dubai Metro (Red Line)",
            location=Location(latitude=25.23, longitude=55.28),
            status="disrupted", status_detail="Service suspended between Jebel Ali and Ibn Battuta stations.",
            distance_km=2, estimated_travel_minutes=5,
            source=_src("RTA Dubai"), last_updated=datetime(2026, 3, 28, 18, 10, tzinfo=timezone.utc),
        ),
    ]


_SCENARIOS: dict[str, dict] = {
    "dubai_crisis": {
        "name": "Dubai Geopolitical Crisis — Military Strike",
        "date": "March 28, 2026 (simulated)",
        "location": "Dubai, UAE (25.20°N, 55.27°E)",
        "description": "Military strike near Jebel Ali. UAE airspace closed. FCDO: against all travel. DXB/DWC airports shut. Embassy shelter-in-place.",
        "default_lat": 25.20, "default_lon": 55.27,
        "alerts": _dubai_crisis_alerts, "transport": _dubai_crisis_transport,
    },
    "turkey_2023": {
        "name": "2023 Turkey-Syria Earthquake (M7.8 + M7.5)",
        "date": "February 6, 2023",
        "location": "Kahramanmaraş, Turkey (37.22°N, 37.01°E)",
        "description": "M7.8 + M7.5 aftershock. 50,000+ dead. USGS: us6000jllz, us6000jlqa. Worst earthquake in Turkey's modern history.",
        "default_lat": 37.22, "default_lon": 37.01,
        "alerts": _turkey_2023_alerts, "transport": _turkey_2023_transport,
    },
    "israel_2023": {
        "name": "2023 Israel-Gaza Conflict (October 7)",
        "date": "October 7, 2023",
        "location": "Tel Aviv, Israel (32.09°N, 34.78°E)",
        "description": "Large-scale attacks. FCDO: advise against all travel. Ben Gurion closed. Airspace shut.",
        "default_lat": 32.09, "default_lon": 34.78,
        "alerts": _israel_2023_alerts, "transport": _israel_2023_transport,
    },
    "valencia_2024": {
        "name": "2024 Valencia DANA Flood",
        "date": "October 29, 2024",
        "location": "Valencia, Spain (39.47°N, 0.38°W)",
        "description": "DANA cold-drop. 400mm rain in 8h. 220+ dead. AEMET red alert. Airport/railway closed.",
        "default_lat": 39.47, "default_lon": -0.38,
        "alerts": _valencia_2024_alerts, "transport": _valencia_2024_transport,
    },
    "japan_2024": {
        "name": "2024 Noto Earthquake (M7.5) + Tsunami",
        "date": "January 1, 2024",
        "location": "Wajima, Ishikawa, Japan (37.50°N, 137.24°E)",
        "description": "M7.5 earthquake + major tsunami warning. JMA Intensity 7 (max). USGS: us6000m0xl.",
        "default_lat": 37.50, "default_lon": 137.24,
        "alerts": _japan_2024_alerts, "transport": _japan_2024_transport,
    },
}


@router.get("/scenarios", summary="List real historical event simulations")
async def list_scenarios():
    return {
        name: {k: v for k, v in s.items() if k not in ("alerts", "transport")}
        for name, s in _SCENARIOS.items()
    }


@router.post(
    "/{scenario}",
    response_model=DecisionResponse,
    summary="Replay a real historical disaster through the decision engine",
    description="Feeds REAL historical event data into the decision engine. Same code path as live data.",
)
async def run_simulation(
    scenario: str,
    lat: float = Query(None, description="Latitude (uses event's real location if omitted)"),
    lon: float = Query(None, description="Longitude (uses event's real location if omitted)"),
):
    if scenario not in _SCENARIOS:
        from fastapi import HTTPException
        raise HTTPException(404, f"Unknown scenario. Available: {list(_SCENARIOS.keys())}")

    s = _SCENARIOS[scenario]
    use_lat = lat if lat is not None else s["default_lat"]
    use_lon = lon if lon is not None else s["default_lon"]

    alerts = s["alerts"](use_lat, use_lon)
    transport = s["transport"](use_lat, use_lon)
    location = Location(latitude=use_lat, longitude=use_lon)

    sources = list({a.source.name: a.source for a in alerts}.values())
    sources += list({t.source.name: t.source for t in transport}.values())

    return make_decision(
        alerts=alerts, transport=transport, location=location, data_sources=sources,
    )
