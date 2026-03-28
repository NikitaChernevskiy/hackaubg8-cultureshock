"""Simulation endpoint — for demos and testing.

Returns realistic fake alert data for specific disaster scenarios
so the decision engine can be tested without waiting for real events.
The decision engine processes these exactly like real alerts.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from app.models.alerts import Alert
from app.models.common import DataSource, Location
from app.models.decision import DecisionResponse
from app.models.transport import TransportOption
from app.services.decision_service import make_decision

router = APIRouter(prefix="/simulate", tags=["Simulation (Demo)"])

_NOW = lambda: datetime.now(timezone.utc)  # noqa: E731


def _src(name: str) -> DataSource:
    return DataSource(name=name, url=None, retrieved_at=_NOW(), reliability="simulated")


_SCENARIOS: dict[str, dict] = {
    "earthquake_nearby": {
        "name": "Earthquake Nearby (M6.2, 15km)",
        "description": "A strong earthquake strikes 15km from your location. Buildings damaged, aftershocks expected.",
        "alerts": lambda lat, lon: [
            Alert(
                id="sim-eq-001", type="earthquake", severity="critical",
                title="M6.2 Earthquake — 15km from your location",
                description="A magnitude 6.2 earthquake struck 15km away. Significant shaking felt. Aftershocks likely. Infrastructure damage reported.",
                issued_at=_NOW() - timedelta(minutes=2),
                location=Location(latitude=lat + 0.1, longitude=lon + 0.05),
                radius_km=15, source=_src("USGS (simulated)"), official_url="",
            ),
            Alert(
                id="sim-eq-002", type="earthquake", severity="high",
                title="Aftershock M4.8 — 18km from your location",
                description="Aftershock detected. More aftershocks expected in the coming hours.",
                issued_at=_NOW() - timedelta(minutes=1),
                location=Location(latitude=lat + 0.12, longitude=lon + 0.06),
                radius_km=18, source=_src("USGS (simulated)"), official_url="",
            ),
            Alert(
                id="sim-infra-001", type="infrastructure_failure", severity="high",
                title="Power outage reported in your area",
                description="Widespread power outages following the earthquake. Mobile networks intermittent.",
                issued_at=_NOW(), location=Location(latitude=lat, longitude=lon),
                radius_km=5, source=_src("Local reports (simulated)"), official_url="",
            ),
        ],
        "transport": lambda lat, lon: [
            TransportOption(
                id="sim-t1", type="train_station", name="Central Railway Station",
                location=Location(latitude=lat + 0.01, longitude=lon - 0.01),
                status="disrupted", status_detail="Services suspended pending safety inspection.",
                distance_km=1.5, estimated_travel_minutes=5, source=_src("Transport (simulated)"), last_updated=_NOW(),
            ),
            TransportOption(
                id="sim-t2", type="airport", name="International Airport",
                location=Location(latitude=lat + 0.15, longitude=lon + 0.1),
                status="closed", status_detail="Airport closed due to runway damage.",
                distance_km=18, estimated_travel_minutes=40, source=_src("Transport (simulated)"), last_updated=_NOW(),
            ),
            TransportOption(
                id="sim-t3", type="bus_station", name="Central Bus Terminal",
                location=Location(latitude=lat - 0.005, longitude=lon + 0.01),
                status="operational", status_detail="Limited services running. Expect delays.",
                distance_km=0.8, estimated_travel_minutes=3, source=_src("Transport (simulated)"), last_updated=_NOW(),
            ),
        ],
    },
    "geopolitical_crisis": {
        "name": "Geopolitical Crisis (Conflict Escalation)",
        "description": "Armed conflict escalates in the region. FCDO advises against all travel. Embassy evacuation underway.",
        "alerts": lambda lat, lon: [
            Alert(
                id="sim-geo-001", type="geopolitical", severity="critical",
                title="FCDO advises against ALL travel — your country",
                description="Due to escalating armed conflict, the UK Foreign Office advises against all travel. Embassy is organizing evacuation flights.",
                issued_at=_NOW() - timedelta(hours=2),
                location=Location(latitude=lat, longitude=lon),
                radius_km=0, source=_src("UK FCDO (simulated)"), official_url="",
            ),
            Alert(
                id="sim-geo-002", type="civil_unrest", severity="high",
                title="Civil unrest — protests and roadblocks reported",
                description="Large-scale protests reported in the city center. Some roads blocked. Security forces deployed.",
                issued_at=_NOW() - timedelta(hours=1),
                location=Location(latitude=lat + 0.02, longitude=lon - 0.01),
                radius_km=5, source=_src("ReliefWeb (simulated)"), official_url="",
            ),
            Alert(
                id="sim-geo-003", type="geopolitical", severity="critical",
                title="Airspace closed — all flights grounded",
                description="National airspace closed due to military operations. No commercial flights operating.",
                issued_at=_NOW() - timedelta(minutes=30),
                location=Location(latitude=lat, longitude=lon),
                radius_km=0, source=_src("NOTAM (simulated)"), official_url="",
            ),
        ],
        "transport": lambda lat, lon: [
            TransportOption(
                id="sim-gt1", type="airport", name="International Airport",
                location=Location(latitude=lat + 0.15, longitude=lon + 0.1),
                status="closed", status_detail="All flights cancelled. Airspace closed.",
                distance_km=18, estimated_travel_minutes=40, source=_src("Transport (simulated)"), last_updated=_NOW(),
            ),
            TransportOption(
                id="sim-gt2", type="bus_station", name="Intercity Bus Terminal",
                location=Location(latitude=lat - 0.01, longitude=lon + 0.02),
                status="disrupted", status_detail="Some routes operating to border. Long queues.",
                distance_km=2.1, estimated_travel_minutes=8, source=_src("Transport (simulated)"), last_updated=_NOW(),
            ),
        ],
    },
    "flood_warning": {
        "name": "Severe Flood (River Overflow)",
        "description": "Flash flooding after heavy rains. River overflowing, low-lying areas evacuated.",
        "alerts": lambda lat, lon: [
            Alert(
                id="sim-fl-001", type="flood", severity="high",
                title="Flash flood warning — river overflow imminent",
                description="Heavy rainfall has caused the river to overflow. Low-lying areas should evacuate immediately. Water levels rising.",
                issued_at=_NOW() - timedelta(minutes=20),
                location=Location(latitude=lat - 0.01, longitude=lon),
                radius_km=5, source=_src("Meteoalarm (simulated)"), official_url="",
            ),
            Alert(
                id="sim-fl-002", type="flood", severity="critical",
                title="Severe weather — extreme rainfall continues",
                description="200mm of rainfall recorded in the last 6 hours. More expected. Flash flooding likely in urban areas.",
                issued_at=_NOW() - timedelta(minutes=10),
                location=Location(latitude=lat, longitude=lon),
                radius_km=10, source=_src("Meteoalarm (simulated)"), official_url="",
            ),
        ],
        "transport": lambda lat, lon: [
            TransportOption(
                id="sim-ft1", type="train_station", name="Central Station",
                location=Location(latitude=lat + 0.01, longitude=lon),
                status="closed", status_detail="Flooded tracks. All services suspended.",
                distance_km=1.2, estimated_travel_minutes=5, source=_src("Transport (simulated)"), last_updated=_NOW(),
            ),
            TransportOption(
                id="sim-ft2", type="bus_station", name="Highland Bus Terminal",
                location=Location(latitude=lat + 0.05, longitude=lon + 0.03),
                status="operational", status_detail="Routes to higher ground operating.",
                distance_km=6.5, estimated_travel_minutes=15, source=_src("Transport (simulated)"), last_updated=_NOW(),
            ),
        ],
    },
    "all_clear": {
        "name": "All Clear (No Threats)",
        "description": "No active threats detected. Normal conditions.",
        "alerts": lambda lat, lon: [],
        "transport": lambda lat, lon: [
            TransportOption(
                id="sim-ct1", type="train_station", name="Central Station",
                location=Location(latitude=lat + 0.01, longitude=lon),
                status="operational", status_detail="All services running normally.",
                distance_km=1.2, estimated_travel_minutes=5, source=_src("Transport (simulated)"), last_updated=_NOW(),
            ),
            TransportOption(
                id="sim-ct2", type="airport", name="International Airport",
                location=Location(latitude=lat + 0.15, longitude=lon + 0.1),
                status="operational", status_detail="Normal operations.",
                distance_km=18, estimated_travel_minutes=35, source=_src("Transport (simulated)"), last_updated=_NOW(),
            ),
        ],
    },
}


@router.get(
    "/scenarios",
    summary="List available simulation scenarios",
)
async def list_scenarios():
    return {
        name: {"name": s["name"], "description": s["description"]}
        for name, s in _SCENARIOS.items()
    }


@router.post(
    "/{scenario}",
    response_model=DecisionResponse,
    summary="Run a simulation scenario through the decision engine",
    description=(
        "Feeds realistic simulated alert data into the decision engine. "
        "The engine processes it exactly like real data. Use for demos."
    ),
)
async def run_simulation(
    scenario: str,
    lat: float = Query(42.01, description="Latitude (default: Blagoevgrad)"),
    lon: float = Query(23.10, description="Longitude (default: Blagoevgrad)"),
):
    if scenario not in _SCENARIOS:
        from fastapi import HTTPException
        raise HTTPException(404, f"Unknown scenario. Available: {list(_SCENARIOS.keys())}")

    s = _SCENARIOS[scenario]
    alerts = s["alerts"](lat, lon)
    transport = s["transport"](lat, lon)
    location = Location(latitude=lat, longitude=lon)

    sources = list({a.source.name: a.source for a in alerts}.values())
    sources += list({t.source.name: t.source for t in transport}.values())

    return make_decision(
        alerts=alerts,
        transport=transport,
        location=location,
        data_sources=sources,
    )
