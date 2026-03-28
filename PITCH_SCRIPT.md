# CultureShock / Amygdala — Judge-Proof Tech Slide Script

> **Ground rule**: Every claim in this script is verified against the actual codebase.
> If something is not built yet, it says "roadmap" or "next step." No bluffing.

---

## Source Count — The One True Number

The codebase has **5 alert provider classes** inside `MultiAlertProvider`:

| # | Provider Class           | Actual APIs Queried                    |
|---|--------------------------|----------------------------------------|
| 1 | `USGSAlertProvider`      | USGS Earthquake API **+ GDACS RSS** (2 APIs inside 1 provider) |
| 2 | `EONETAlertProvider`     | NASA EONET                             |
| 3 | `ReliefWebAlertProvider` | UN OCHA ReliefWeb                      |
| 4 | `FCDOAlertProvider`      | UK FCDO (gov.uk)                       |
| 5 | `MeteoalarmProvider`     | Meteoalarm (EU CAP feeds)              |

That produces **6 distinct threat intelligence sources**:
USGS · GDACS · NASA EONET · UK FCDO · Meteoalarm · ReliefWeb

Plus **OpenStreetMap** via Overpass API for transport = **7 external data sources total**.

The admin dashboard (`admin_service.py` line 92–93) itself confirms:
`"count": 7, "sources": ["USGS", "GDACS", "NASA EONET", "UK FCDO", "Meteoalarm", "ReliefWeb", "OpenStreetMap"]`

### The single sentence to use everywhere:

> **"We query 6 threat intelligence sources — USGS, GDACS, NASA, UK FCDO, Meteoalarm, and ReliefWeb — plus OpenStreetMap for exit routing."**

If someone asks "so is it 5, 6, or 7?":

> "5 provider modules, querying 6 intelligence APIs, plus OpenStreetMap for transport — 7 external data sources total."

---

## SLIDE 1 — Problem Statement

### SAY THIS:
> "300 million international trips per year. When a crisis hits — earthquake, conflict, flood — a traveler in a foreign country has seconds to act. They don't know the local emergency number. They don't speak the language. They don't know which airport is still open. And in a few minutes, their internet may go down."

> "Insurance companies cover these travelers, but right now they have no way to reach them in real time with actionable guidance."

### AVOID SAYING:
- ❌ "Our AI tells travelers what to do" — frames it as AI-commanded, creates liability concern
- ❌ "We solve all travel emergencies" — too broad; you solve the **decision and delivery** problem
- ❌ "This has never been done before" — alert apps exist; your differentiator is the decision layer

---

## SLIDE 2 — Product Overview (30-second version)

### SAY THIS:
> "Amygdala is a real-time survival decision engine. We aggregate 6 trusted intelligence sources, compute a multi-source trust score, and output exactly one advisory action: SHELTER, STAY, MOVE, EVACUATE, or MONITOR. Then we deliver it via email and SMS — because SMS may be the traveler's last message before internet fails."

> "AI writes the situation briefing. Rules make the decision."

### AVOID SAYING:
- ❌ "AI-powered decision system" — the decision is deterministic, not AI. Say "AI-assisted" only if referring to the briefing
- ❌ "We send push notifications" — Firebase push is configured but not wired end-to-end. Stick to "email and SMS"
- ❌ "We monitor travelers 24/7" — the hackathon version triggers checks on demand. Say "continuous monitoring" only with the production caveat (see Slide 7)

---

## SLIDE 3 — Architecture (Technical Judges)

### SAY THIS:
> "The backend is FastAPI on Azure Container Apps. On each check, we query 6 intelligence APIs in parallel using asyncio.gather — USGS and GDACS for seismic data, NASA EONET for wildfires and volcanoes, UK FCDO for geopolitical travel advisories, Meteoalarm for European severe weather, and UN ReliefWeb for humanitarian crises. We also query OpenStreetMap Overpass API for the nearest airports, train stations, bus stations, and ferry terminals."

> "These are heterogeneous — JSON, XML RSS, CAP alert feeds — and we normalize everything into a unified Pydantic alert model."

> "Then three layers process the data:"
> 1. "Trust scoring — per-source reliability weights, exponential time decay, cross-source agreement"
> 2. "Proximity filtering — type-specific distance thresholds so a distant earthquake doesn't trigger a false alarm"
> 3. "Deterministic decision tree — phase-aware, priority-ordered, outputs exactly one action"

> "AI enters only at the end: GPT-4o generates a 3-to-4 sentence situation briefing, post-processed by an imperative language filter for legal safety."

### AVOID SAYING:
- ❌ "7 sources" without explaining the split — say "6 intelligence sources plus OpenStreetMap"
- ❌ "Real-time transport status" — OSM gives infrastructure locations, not live operational status. If asked, say: "We know where the airports and stations are and how far away. Real-time operational status — whether flights are running — is a production integration on our roadmap."
- ❌ "Our AI decides" — always say "rules decide, AI explains"

### IF JUDGES ASK about transport status:
> "Today we identify the nearest transport infrastructure — airports, train stations, bus stations, ferry terminals — using OpenStreetMap. We compute distance and estimated travel time. What we don't yet have is live departure status. That's a clear next integration — flight tracker APIs, rail APIs. But knowing *where* to go is the critical first step."

---

## SLIDE 4 — Decision Engine Deep Dive

### SAY THIS:
> "The decision engine is the core innovation. It is entirely deterministic — zero AI. It takes the trust-scored, proximity-filtered alerts, plus transport data and GPS coordinates, and walks a priority decision tree."

> "First, it determines crisis phase from alert age: SURVIVE for the first 5 minutes, STABILIZE for the first hour, EVALUATE for the first 24 hours, ESCAPE beyond that."

> "Then the decision tree, in priority order:"
> - "If there is a nearby lethal threat — earthquake, tsunami, tornado, volcano — and we are in the SURVIVE or STABILIZE phase: **SHELTER**"
> - "If the same lethal threat exists but we are in a later phase: **STAY** and assess before moving"
> - "If an evacuation trigger is active — flood, wildfire, geopolitical — and transport is available: **EVACUATE** or **MOVE**"
> - "If mobility is unsafe but no immediate lethal threat: **STAY**"
> - "Otherwise: **MONITOR**"

> "Every decision includes a fallback instruction in case conditions change. And the output is advisory, not commanding — that is a deliberate legal design."

### IF JUDGES ASK "What does advisory mean exactly?":
> "We output one clear action from five options, but it is framed as a recommendation, not a command. The system never says 'go to' or 'you must.' It says 'consider' or 'you may want to.' We enforce this with a system prompt, a post-processing imperative language filter, and mandatory legal disclaimers on every response. This is a conscious design decision — in a crisis, commanding users creates legal liability."

### IF JUDGES ASK "Does AI ever override the rules?":
> "Never. AI produces the briefing text — the explanation of what is happening. The decision — SHELTER, STAY, MOVE, EVACUATE, MONITOR — is always made by the rule engine. If AI fails entirely, the decision still works. The briefing degrades to a list of alert titles."

### AVOID SAYING:
- ❌ "Our AI decides what to do" — immediate credibility hit
- ❌ "Smart decision engine" without saying *how* — always describe the actual tree
- ❌ "We guarantee safety" — you guarantee *information delivery*, not outcomes

---

## SLIDE 5 — Trust Scoring

### SAY THIS:
> "We do not act on a single noisy signal. Every alert passes through a trust scoring engine."

> "Three factors: source reliability — USGS gets 0.95, user reports get 0.30. Time decay — exponential, 24-hour half-life, so a 1-hour-old alert retains 97% trust, a 24-hour-old alert drops to 50%. And cross-source agreement — one source confirming gets a 0.4 agreement factor. Two sources: 0.6. Three or more: 0.8 to 1.0."

> "If sources conflict — one says critical, others say low — trust is automatically downgraded by 30% and the conflict is logged."

> "The result: if trust is low, the system defaults to MONITOR instead of escalating. We do not create panic from unreliable data."

### IF JUDGES ASK "Does the user see the trust score?":
> "The decision response includes the trust score, number of sources agreeing, and confidence level. The insurer's admin panel also shows source coverage. So both see it — the traveler as a confidence indicator, the insurer as a data quality metric."

### IF JUDGES ASK "Is trust per alert or per decision?":
> "Trust is computed across all alerts for that location. It is a composite — reflecting how many independent sources confirm the overall threat picture, not individual events."

### AVOID SAYING:
- ❌ "Our trust algorithm is proprietary" — it is a weighted formula, be transparent
- ❌ "We verify every alert" — you cross-reference; you do not independently verify

---

## SLIDE 6 — Live Demo

### SAY THIS (before the demo):
> "I am going to replay a real historical disaster through the exact same code path that live data uses. The decision engine, trust scoring, proximity filtering, AI briefing, email delivery — all identical to production."

> "For demo reliability, we use our simulation endpoint, which feeds verified historical event data — real USGS earthquake IDs, real FCDO advisories — into the pipeline. This way the demo does not depend on whether there happens to be an earthquake right now."

### DURING THE DEMO:
Show one of the 5 scenarios. The Turkey 2023 earthquake is the strongest because:
- Real USGS event IDs (`us6000jllz` for M7.8, `us6000jlqa` for M7.5)
- Multiple sources confirm (USGS + FCDO + GDACS)
- Transport disruptions are real (Hatay Airport collapsed, Gaziantep damaged, Adana operational)
- Decision is dramatic: SHELTER → phase SURVIVE

Then show a **live data fetch** separately:
> "And here is a live query against our real alert sources right now — [hit the decision endpoint with a real location]. This is live, not simulated."

### IF JUDGES ASK "Is this real or simulated?":
> "The simulation replays real historical event data through the exact same decision pipeline. The logic is live — the same code that processes live earthquakes today. We also have a fully live endpoint that queries all 6 sources right now, which I can show you."

> "We built the simulation engine specifically so we can prove the system produces correct decisions for verified real events — like the Turkey M7.8 earthquake where the USGS event ID is us6000jllz and you can look it up."

### AVOID SAYING:
- ❌ "This is all happening live right now" (when running a simulation) — be precise about which part is live and which is replayed
- ❌ "We detected this earthquake" — you replayed it. Say "our engine processed this earthquake"
- ❌ "Watch the SMS arrive" (unless you actually configured Twilio for live sending) — if SMS is not live, say "in production this triggers an SMS with [show the content]"

### What IS live right now (be ready to prove):
- ✅ Alert fetching from USGS, GDACS, NASA, FCDO, Meteoalarm, ReliefWeb — the `/api/v1/decision` endpoint queries them live
- ✅ Transport lookup from OpenStreetMap — real Overpass API queries
- ✅ AI briefing from Azure OpenAI GPT-4o — real API call
- ✅ Email delivery via Azure Communication Services — if configured with connection string
- ✅ Decision engine logic — identical code path for live and simulated

### What requires configuration to be live:
- ⚠️ SMS via Twilio — requires `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` env vars
- ⚠️ Email — requires `AZURE_COMM_CONNECTION_STRING` env var

---

## SLIDE 7 — Business Model / Insurance Integration

### SAY THIS:
> "The buyer is the insurance company. The end user is the traveler. The operations team monitors through the admin panel."

> "Integration is straightforward: the insurer calls one API endpoint to register a policyholder with their destination, email, phone, and language. From that point, we monitor their destination and send alerts when threats are detected."

> "In the hackathon version, threat checks are triggered on demand — the insurer or our system calls a check endpoint. In production, this becomes a scheduled automated monitoring service — a cron job or Azure Function running every 5 to 15 minutes."

> "The admin panel gives the insurer real-time ROI: how many travelers protected, how many notifications sent, delivery success rates, and exact cost per user — we show real numbers, not estimates."

### IF JUDGES ASK "What exactly does the insurer integrate?":
> "For the pilot: a REST API. Two endpoints — register a traveler, check their status. The insurer's backend calls our API when a policy is activated for a trip. We handle everything else: data aggregation, decision-making, notification delivery."

> "Over time, this becomes an embedded SDK inside their mobile app — same backend, but with push notifications and a native map view."

### IF JUDGES ASK "Is the monitoring automatic?":
> "In the hackathon build, checks are triggered via API call — either manually or by calling our check-all endpoint. The architecture is ready for automation: it is one Azure Function Timer Trigger away from fully autonomous monitoring. We chose to prove the decision engine first, not the scheduler."

### AVOID SAYING:
- ❌ "We monitor travelers 24/7" — not yet automatic; say "we can check all travelers in one API call, and production adds a scheduler"
- ❌ "One API call does everything" — registration is one call; monitoring/notification is a separate flow
- ❌ "We are an SDK" — right now it is an API. SDK implies a client library, which is not built yet

---

## SLIDE 8 — Data & Privacy

### SAY THIS:
> "We store only the minimum needed for alerting: email, phone, destination coordinates, preferred language, and GDPR consent status. We do not track live location — we store the trip destination, not where the traveler is right now."

> "Registration requires explicit GDPR consent. The API rejects the request with a 422 error if consent is not given."

> "Notification logs record what was sent and when, for audit purposes. AI-generated text is logged to an audit trail but is not stored long-term against user identity."

### IF JUDGES ASK "How does deletion work?":
> "In the hackathon version, data is in-memory — it does not persist across restarts. For production, the plan is Cosmos DB with TTL-based auto-expiration and an explicit deletion endpoint for right-to-be-forgotten requests."

### IF JUDGES ASK "Do you store GPS history?":
> "No. We store the destination — where the traveler is going. Not a continuous location trace. We never track real-time movement."

### AVOID SAYING:
- ❌ "We are fully GDPR compliant" — you have consent enforcement and data minimization, but no deletion endpoint or DPO yet. Say "we designed for GDPR from day one" and describe what is built
- ❌ "No data is stored" — that is false; user registration data is stored. Say "minimal data"

---

## SLIDE 9 — What We Proved in 48 Hours

### SAY THIS:
> "What we proved in 48 hours is not an alert demo, but the core decision engine: trusted data in, one clear action out."

> "Specifically, what is built and working:"
> - "6 live data source integrations — real APIs, not mocks"
> - "Multi-source trust scoring with conflict detection"
> - "Proximity filtering with type-specific distance thresholds"
> - "Phase-aware deterministic decision tree"
> - "AI-generated situation briefings with legal-safe language enforcement"
> - "Email delivery via Azure Communication Services"
> - "SMS delivery via Twilio"
> - "Translation system — 8 languages static, GPT fallback for others"
> - "Simulation engine replaying 5 verified real disasters"
> - "Admin dashboard with real cost metrics"
> - "Landing page with user registration"

> "What is explicitly not built yet, and we are honest about it:"
> - "Persistent storage — currently in-memory, production uses Cosmos DB"
> - "Authentication — no API keys or user auth yet"
> - "Automated scheduled monitoring — checks are on-demand"
> - "Real-time transport status — we have locations, not departure boards"
> - "Push notifications — Firebase configured but not wired"

### THE KEY FRAMING:
> "The hard part we chose to prove in 48 hours was the decision engine and the data pipeline. The next production layer is persistence, authentication, and queued delivery. Those are solved problems. Multi-source trust-weighted emergency decisions are not."

### AVOID SAYING:
- ❌ "This is production-ready" — it is not, and saying so loses credibility. Say "the core logic is production-grade; the infrastructure wrapping is hackathon-grade"
- ❌ "We just need to deploy it" — you need persistence, auth, scheduling, and retry queues. Be specific about what is left
- ❌ "We built everything from scratch in 48 hours" — only if literally true for all team members

---

## SLIDE 10 — Technical Innovation

### SAY THIS:
> "Our core innovation is separating deterministic emergency decisions from AI-generated explanation."

> "Most systems either show raw alerts or ask GPT what to do. We do neither. We aggregate 6 sources, score trust mathematically, filter by proximity, and use a rule tree that accounts for crisis phase. AI only writes the human-readable briefing."

> "This matters because:"
> - "Rules do not hallucinate — the decision is auditable and reproducible"
> - "If AI is down, the system still works"
> - "The decision is legally defensible because it is deterministic"
> - "Trust scoring prevents false alarms from single noisy sources"

### SUPPORTING POINTS (use if time permits):
> - "We filter proximity by event type — a wildfire threshold is 50km, an earthquake is 150km, a pandemic is 500km"
> - "We detect source conflicts and automatically downgrade trust"
> - "We budget SMS character space to maximize the AI briefing because it may be the user's last communication"
> - "We validate our decisions against 5 real historical disasters with verifiable event IDs"

### AVOID SAYING:
- ❌ "We invented trust scoring" — you did not; you applied a well-designed version to this domain
- ❌ "No one else does this" — hard to prove; say "this is uncommon in hackathon projects" or "this is how production safety-critical systems work"

---

## COMMON JUDGE QUESTIONS — Answer Cheat Sheet

### "What if all your data sources are down?"
> "Each provider is wrapped in exception handling. If one fails, the others continue — `asyncio.gather` with `return_exceptions=True`. If all fail, confidence drops to 0.5 and the system outputs MONITOR with low urgency. Partial data is better than no data."

### "How do you handle rate limits on free APIs?"
> "For the hackathon demo, request volume is low. At scale, the production plan is a Redis cache with 30-to-60-second TTL on alert data, so we batch-check users against the same cached alerts instead of hammering the APIs per-user."

### "Why not just use one good source like USGS?"
> "USGS only covers earthquakes. A traveler in Ukraine needs geopolitical data. A traveler in Valencia needs flood data. A traveler in Abu Dhabi needs terrorism data. No single source covers all threat types. And even for earthquakes, cross-referencing USGS with GDACS catches discrepancies."

### "Is the AI responsible for the decision?"
> "No. The AI writes the explanation. The decision is a deterministic rule tree. If you give it the same inputs, you get the same output every time. AI is optional — the system works without it."

### "What if the decision is wrong?"
> "Every decision includes a fallback action — if SHELTER does not work, here is the alternative. The system also outputs confidence and trust scores so the user knows how reliable the guidance is. And mandatory disclaimers make clear this is advisory, not a command."

### "What is your competitive advantage over Google Crisis Alerts?"
> "Google tells you what happened. We tell you what to do. Google shows alerts. We cross-reference multiple sources, score trust, compute proximity relevance, determine crisis phase, and output one specific action with a fallback. And we deliver it to the insurer's policyholders specifically — not to the general public."

### "How much does it cost to run?"
> "The admin dashboard shows real numbers. Platform: about $25/month on Azure Container Apps. Email: $0.01 per message via Azure Communication Services. SMS: $0.08 per message via Twilio. All 6 intelligence sources are free government and UN APIs — zero data cost. At 1,000 travelers, that is roughly $0.03 per user per month for the platform alone."

### "Could this scale to millions?"
> "The architecture is built for it. Azure Container Apps auto-scales. All data calls are async. The bottleneck at scale is the free API rate limits — which we solve with a caching layer — and in-memory storage — which we solve with Cosmos DB. The provider factory pattern means swapping implementations is a config change, not a code rewrite."

---

## Absolute Don'ts — Things That Lose Credibility Instantly

| ❌ Never say | ✅ Say instead |
|---|---|
| "Our AI decides what to do" | "AI writes the briefing. Rules make the decision." |
| "We monitor 24/7" | "Checks are triggered on demand. Production adds a scheduler." |
| "We have 7 data sources" (inconsistently) | "6 intelligence sources plus OpenStreetMap for transport." |
| "This is production-ready" | "The decision engine is production-grade. The infrastructure is hackathon-grade with a clear production path." |
| "We know if the airport is open" | "We know where the airports are and how far. Live operational status is a roadmap item." |
| "We are fully GDPR compliant" | "We designed for GDPR from day one: explicit consent, minimal data, no location tracking." |
| "We built an SDK" | "We built a REST API for insurance integration. The SDK is the next step." |
| "No other system does this" | "This approach — separating deterministic decisions from AI explanation — is uncommon in this space." |
| "One API call does everything" | "Registration is one call. Monitoring and notification is the automated pipeline behind it." |

---

## The Five Lines to Memorize

These are the five sentences that, if delivered clearly, make the technical pitch airtight:

1. **Source count**: "We query 6 threat intelligence sources — USGS, GDACS, NASA, UK FCDO, Meteoalarm, and ReliefWeb — plus OpenStreetMap for exit routing."

2. **AI vs rules**: "AI writes the explanation, but the rules make the decision. If AI is unavailable, the decision still works."

3. **What is live**: "The product logic is live and the data sources are real. For demo reliability, we also replay verified historical disasters through the exact same pipeline."

4. **Honest limitations**: "The hard part we proved in 48 hours is the decision engine. The next layer is persistence, auth, and scheduled monitoring — solved problems."

5. **Innovation**: "Our innovation is separating deterministic emergency decisions from AI-generated explanation, with multi-source trust scoring and phase-aware action selection."

---

## Quick Reference: What Is True Right Now

| Claim | Status | Honest framing |
|---|---|---|
| 6 threat intelligence sources live | ✅ BUILT | All 6 are queried live via real APIs |
| OpenStreetMap transport lookup | ✅ BUILT | Real Overpass API, real results |
| Trust scoring with source weights | ✅ BUILT | Fully implemented formula |
| Proximity filtering by type | ✅ BUILT | 13 event types with specific thresholds |
| Phase-aware decision tree | ✅ BUILT | SURVIVE/STABILIZE/EVALUATE/ESCAPE |
| AI briefing via GPT-4o | ✅ BUILT | Real Azure OpenAI calls |
| Imperative language filter | ✅ BUILT | Blocklist + replacement |
| Translation (8 languages static + GPT) | ✅ BUILT | Static dictionaries + fallback |
| Email delivery | ✅ BUILT | Azure Communication Services, real sends |
| SMS delivery | ✅ BUILT | Twilio integration, real sends (needs config) |
| 5 historical disaster simulations | ✅ BUILT | Real USGS IDs, real FCDO text |
| Admin dashboard with costs | ✅ BUILT | Real metrics, live numbers |
| User registration with GDPR consent | ✅ BUILT | 422 rejection if no consent |
| User reporting with rate limiting | ✅ BUILT | 5/hour/device, trust capped at 0.5 |
| Offline survival pack | ✅ BUILT | Emergency numbers, language tips, rules |
| Persistent database | ❌ ROADMAP | In-memory only; Cosmos DB planned |
| Authentication | ❌ ROADMAP | No auth on any endpoint |
| Automated monitoring scheduler | ❌ ROADMAP | Manual trigger; Azure Functions planned |
| Real-time transport status | ❌ ROADMAP | Locations only, not live departures |
| Push notifications | ❌ ROADMAP | Firebase configured, not wired |
| Notification retry queue | ❌ ROADMAP | No retries on failure |
| GDPR deletion endpoint | ❌ ROADMAP | No explicit delete; data is ephemeral |
