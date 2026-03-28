"""Offline data pack service — everything needed when internet dies."""

from datetime import datetime, timedelta, timezone

from app.models.offline import Embassy, EmergencyInfo, OfflinePack, SafeZone

# Emergency info by country code
_EMERGENCY_DATA: dict[str, EmergencyInfo] = {
    "BG": EmergencyInfo(
        country_code="BG", country_name="Bulgaria",
        emergency_number="112", police="166", ambulance="150", fire="160",
        language_tips=["'Pomosht' = Help", "'Bolnitsa' = Hospital", "'Politsiya' = Police"],
    ),
    "TR": EmergencyInfo(
        country_code="TR", country_name="Turkey",
        emergency_number="112", police="155", ambulance="112", fire="110",
        tourist_police="153",
        language_tips=["'Yardım' = Help", "'Hastane' = Hospital", "'Polis' = Police"],
    ),
    "GR": EmergencyInfo(
        country_code="GR", country_name="Greece",
        emergency_number="112", police="100", ambulance="166", fire="199",
        tourist_police="1571",
        language_tips=["'Voítheia' = Help", "'Nosokomío' = Hospital"],
    ),
    "JP": EmergencyInfo(
        country_code="JP", country_name="Japan",
        emergency_number="110", police="110", ambulance="119", fire="119",
        language_tips=["'Tasukete' = Help", "'Byōin' = Hospital", "Japan 171 = disaster message line"],
    ),
    "IL": EmergencyInfo(
        country_code="IL", country_name="Israel",
        emergency_number="100", police="100", ambulance="101", fire="102",
        language_tips=["'Ezra' = Help", "'Beit holim' = Hospital"],
    ),
    "UA": EmergencyInfo(
        country_code="UA", country_name="Ukraine",
        emergency_number="112", police="102", ambulance="103", fire="101",
        language_tips=["'Dopomoha' = Help", "'Likarnya' = Hospital"],
    ),
    "DE": EmergencyInfo(
        country_code="DE", country_name="Germany",
        emergency_number="112", police="110", ambulance="112", fire="112",
        language_tips=["'Hilfe' = Help", "'Krankenhaus' = Hospital"],
    ),
    "IT": EmergencyInfo(
        country_code="IT", country_name="Italy",
        emergency_number="112", police="113", ambulance="118", fire="115",
        language_tips=["'Aiuto' = Help", "'Ospedale' = Hospital"],
    ),
    "ES": EmergencyInfo(
        country_code="ES", country_name="Spain",
        emergency_number="112", police="091", ambulance="112", fire="080",
        language_tips=["'Ayuda' = Help", "'Hospital' = Hospital"],
    ),
    "FR": EmergencyInfo(
        country_code="FR", country_name="France",
        emergency_number="112", police="17", ambulance="15", fire="18",
        language_tips=["'Au secours' = Help", "'Hôpital' = Hospital"],
    ),
    "DEFAULT": EmergencyInfo(
        country_code="XX", country_name="Unknown",
        emergency_number="112",
        language_tips=["112 works in most countries", "Try English or use translation app"],
    ),
}

# Offline decision rules
_OFFLINE_RULES = [
    "IF you feel the ground shake: DROP, COVER, HOLD ON. Stay away from windows.",
    "IF you hear an explosion or gunfire: GET LOW, stay away from windows, move to interior room.",
    "IF you see flood water rising: MOVE TO HIGHER GROUND immediately. Never walk through flowing water.",
    "IF there is a fire nearby: EVACUATE in the opposite direction of smoke. Cover mouth with wet cloth.",
    "IF sirens sound: FOLLOW local instructions. If none, shelter indoors.",
    "IF you lose communication: GO TO your embassy or nearest police station.",
    "ALWAYS: Keep your passport, phone, water, and medication with you.",
    "ALWAYS: Note the nearest hospital, police station, and embassy address.",
    "ALWAYS: Call the local emergency number first, then your embassy.",
]


def get_offline_pack(country_code: str) -> OfflinePack:
    """Generate an offline data pack for a country."""
    now = datetime.now(timezone.utc)
    emergency = _EMERGENCY_DATA.get(country_code.upper(), _EMERGENCY_DATA["DEFAULT"])

    return OfflinePack(
        country_code=country_code.upper(),
        country_name=emergency.country_name,
        generated_at=now,
        valid_until=now + timedelta(days=7),
        emergency=emergency,
        embassies=[],   # Would be populated from a real embassy database
        safe_zones=[],  # Would be populated from OpenStreetMap hospitals/police
        offline_rules=_OFFLINE_RULES,
        last_known_threat_level="unknown",
        last_known_alerts_summary="",
    )
