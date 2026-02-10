# CustomDose (customdose.ai)

Supplement stack tracker with Oura Ring biometric correlation. Track what you take, measure how you feel, see what works.

## Tech Stack

| Layer | Stack |
|-------|-------|
| Mobile | React Native 0.81.5 / Expo SDK 54 / React 19 / TypeScript 5.9 |
| Backend | FastAPI 0.109.0 / SQLAlchemy 2.0 / Pydantic v2 / Python 3.11 |
| Database | Supabase PostgreSQL |
| Deployment | Railway (backend) / Expo (mobile) |
| Integrations | Oura Ring OAuth, Whoop (backend only), OpenAI |

## Architecture

Mobile (`mobile/`) → REST API (`app/`) → Supabase PostgreSQL. Engine layer (`app/engine/`) handles recommendation/intelligence logic. Oura/Whoop integrations in `app/integrations/`. 76 total endpoints, 21 wired to mobile.

## File Structure

| Directory | Purpose |
|-----------|---------|
| `app/api/` | FastAPI routers — users, analytics, mixes, integrations, checkins, interactions, dispenser, upload |
| `app/models/` | Pydantic request/response schemas |
| `app/engine/` | Intelligence engine, recommender, rules, LLM, interactions, metric rules |
| `app/integrations/` | Oura, Whoop, mock data providers |
| `app/db/` | SQLAlchemy + Supabase database setup |
| `mobile/src/screens/` | 6 screens — Auth, Onboarding, Dashboard, Analytics, Settings, Mixes |
| `mobile/src/components/` | 11 reusable UI components (Text, Card, Button, MetricCircle, modals, etc.) |
| `mobile/src/services/` | ApiService singleton + AsyncStorage wrapper |
| `mobile/src/hooks/` | useAppState — React Context state management |
| `mobile/src/types/` | All TypeScript type definitions |
| `mobile/src/constants/` | Theme tokens (colors, spacing, typography) |
| `scripts/` | Utility/migration scripts |
| `.context/` | Project documentation (architecture, endpoints, bugs, research) |

## How to Run

**Backend:**
```bash
cd health-platform && source venv/bin/activate && uvicorn app.main:app --reload
```

**Mobile:**
```bash
cd health-platform/mobile && npm start
```

## Coding Conventions

### Mobile (TypeScript)
- PascalCase for components, camelCase for functions, UPPER_SNAKE for constants
- StyleSheet at bottom of file
- React Context for state (`useAppState` hook)
- Barrel exports from `index.ts` in components/ and screens/
- Theme tokens from `constants/theme.ts` — never hardcode colors/spacing

### Backend (Python)
- FastAPI routers in `app/api/`, one file per domain
- SQLAlchemy models in `app/models/`
- Pydantic schemas inline or in models/
- `HTTPException` for error responses
- Engine logic separated from API handlers

### Commits
- Imperative present tense: "Add feature", "Fix: bug description", "Remove unused code"

## Common Mistakes

- **Timezone/date bugs** — Always use local date strings (`YYYY-MM-DD`), never UTC Date objects
- **Race conditions on supplement logging** — Check `inFlightRef` pattern in DashboardScreen before duplicating
- **Oura token refresh** — Tokens expire; must handle the refresh flow in integrations
- **Stale state after mutations** — Always call `refreshData()` after API writes
- **Missing null checks on Oura data** — Oura fields can be null if user hasn't synced

## Deep Context

Read these for full project context:
- `.context/architecture.md` — System architecture, state management, API coverage
- `.context/api-endpoints.md` — All 76 endpoints, 21 wired, priority tiers
- `.context/bugs-and-debt.md` — Known bugs, tech debt, fixed items
- `.context/competitive.md` — Market positioning, threats, monetization
- `.context/research.md` — Evidence-graded supplement-wearable research
