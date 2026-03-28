# Amygdala — Technical Architecture for Pitch

## One-Liner
**SDK for travel insurance companies that monitors 7 government data sources in real-time and sends AI-generated emergency briefings via email + SMS when disasters strike near insured travelers.**

---

## How It Works (3 Steps)

### Step 1: Insurance company integrates our SDK
```
POST /sdk/register
{ email, phone, destination, gdpr_consent }
```
One API call. User is now monitored 24/7.

### Step 2: We monitor 7 data sources in parallel
Every check scans USGS, GDACS, NASA, UK FCDO, Meteoalarm, ReliefWeb, and OpenStreetMap simultaneously. When a threat is detected near a registered user's destination:

### Step 3: Automated notification pipeline
1. **Decision engine** (deterministic rules, not AI) picks ONE action: SHELTER / STAY / MOVE / EVACUATE / MONITOR
2. **Trust scoring** cross-verifies across sources (single source = low trust, multiple = high)
3. **GPT-4o** generates a situation-specific briefing about what's happening
4. **Email** (Azure Communication Services) + **SMS** (Twilio) delivered instantly
5. Email contains a **map link** → opens navigation to nearest safe transport

---

## Architecture Components

### Backend (Python / FastAPI)
- **FastAPI** async framework — handles all 25 API endpoints
- **Decision Engine** — deterministic rule-based, NOT AI. Decision tree:
  - Immediate lethal threat → SHELTER
  - Unsafe to move → STAY
  - Exit viable → MOVE / EVACUATE
  - No threat → MONITOR
- **Trust Scoring** — `trust = source_weight × cross_source_agreement × time_decay`
- **Proximity Filtering** — only alerts within actionable distance trigger notifications (earthquake < 150km, flood < 80km, geopolitical < 300km)
- **Translation Service** — static translations for 9 languages + GPT-4o fallback

### Azure Resources
| Resource | Service | Purpose | Cost |
|---|---|---|---|
| **Container App** | Azure Container Apps | Hosts the API (0.5 vCPU, 1GB) | ~$15/mo |
| **Container Registry** | ACR Basic | Docker image storage | ~$5/mo |
| **Azure OpenAI** | GPT-4o (GlobalStandard) | Situation briefings + translation | Pay-per-use |
| **Communication Services** | Azure Email | Real email alerts (HTML) | Free tier (100/day) |
| **Log Analytics** | Auto-created | Container App logs | ~$1/mo |
| **Total** | | | **~$25/mo** |

### External Services
| Service | Purpose | Cost |
|---|---|---|
| **Twilio** | SMS alerts | $15.50 credit (trial) |

### Data Sources (7 APIs — all free, no keys)
Covered in separate slide.

---

## Decision Engine — Why NOT AI for the Final Call

The decision engine is **deterministic rules**, not AI. Why:

1. **Predictability** — AI can hallucinate. Rules don't. "M7.0 earthquake 15km away → SHELTER" is always correct.
2. **Speed** — Rule evaluation: <1ms. GPT-4o call: 2-5 seconds. In an earthquake, milliseconds matter.
3. **Auditability** — Every decision can be traced to a specific rule. Critical for insurance liability.
4. **Offline** — Rules work without internet. AI doesn't.

AI is used ONLY for:
- Generating human-readable situation briefings (after the decision is made)
- Translation to user's language
- Never for the GO/STAY/SHELTER decision itself

---

## Trust Scoring

```
trust_score = source_weight × cross_source_agreement × time_decay
```

| Source | Weight | Why |
|---|---|---|
| USGS | 0.95 | US Government, gold standard for seismic |
| GDACS | 0.90 | UN-backed global system |
| UK FCDO | 0.90 | UK Government diplomatic intelligence |
| NASA EONET | 0.85 | Satellite-verified |
| ReliefWeb | 0.85 | UN OCHA humanitarian data |
| Meteoalarm | 0.85 | EU official weather service |
| OpenStreetMap | 0.70 | Community-verified infrastructure |

- 1 source confirms → trust 0.4 (low)
- 2 sources confirm → trust 0.7 (medium)
- 3+ sources confirm → trust 0.9+ (high)
- Sources conflict → trust downgraded

---

## Notification Pipeline

```
Threat detected
    ↓
Decision Engine → SHELTER / STAY / MOVE / EVACUATE
    ↓
GPT-4o generates situation briefing (once per event)
    ↓
For each affected user:
    ├── Email (Azure Comm Services) — HTML with briefing + map link
    └── SMS (Twilio) — concise instruction + map link
    ↓
Admin panel logs everything in real-time
```

### What the user receives (email):
- **Red banner**: "SHELTER — Istanbul, Turkey"
- **AI briefing**: "A magnitude 7.0 earthquake struck central Istanbul. Major building damage reported. Tsunami risk for Marmara Sea. You may want to consider seeking shelter in a sturdy structure..."
- **Map button**: Opens `/map?lat=41.01&lon=28.98` with threat markers + route to safety
- **Emergency number**: Correct for the country (GPS-based, not hardcoded)

---

## GDPR Compliance

- Consent required before registration (checkbox + backend enforcement)
- Data used solely for emergency alerts — not shared with third parties
- AI disclosure: explains GPT-4o usage and data sources
- Legal basis: Art. 6(1)(a) consent + Art. 6(1)(d) vital interests
- User can withdraw consent at any time

---

## Historical Event Simulations (for demo)

4 real events with actual USGS/FCDO data:

| Event | Date | Data |
|---|---|---|
| Turkey M7.8 + M7.5 | Feb 6, 2023 | USGS us6000jllz, us6000jlqa |
| Israel-Gaza conflict | Oct 7, 2023 | FCDO "advise against all travel" |
| Valencia DANA flood | Oct 29, 2024 | AEMET red alert, 400mm/8h |
| Japan Noto M7.5 + tsunami | Jan 1, 2024 | USGS us6000m0xl, JMA warning |

---

## Admin Panel (for insurance risk managers)

Live dashboard at `/admin`:
- Registered users, notifications sent, success rate
- ROI estimation (claims prevented vs. platform cost)
- Notification log with full audit trail
- Data source status (all 7 green)
- Auto-refreshes every 10 seconds

---

## Tech Stack Summary

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI (async) |
| AI | Azure OpenAI GPT-4o |
| Email | Azure Communication Services |
| SMS | Twilio |
| Hosting | Azure Container Apps |
| Container | Docker → Azure Container Registry |
| Map | Leaflet.js + OpenStreetMap |
| Frontend | React + Vite + Tailwind CSS |
| Data | 7 free government/scientific APIs |

---

## URLs

| Page | URL |
|---|---|
| Landing page | https://cultureshock-api.happywater-e6483408.eastus2.azurecontainerapps.io/ |
| Admin panel | .../admin |
| Navigation map | .../map |
| API docs (Swagger) | .../docs |
| GitHub | https://github.com/NikitaChernevskiy/hackaubg8-cultureshock (branch: nch-dev) |
