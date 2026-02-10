# CustomDose Architecture Reference

## Product
- **Name:** CustomDose (customdose.ai)
- **What it does:** Supplement stack tracker with Oura Ring biometric correlation
- **User ID:** 2e54fb24-307b-436c-8247-b12de9b43dea

## Tech Stack
- **Mobile:** React Native 0.81.5, Expo SDK 54, React 19, TypeScript
- **Backend:** FastAPI (Python), hosted on Railway
- **Backend URL:** `https://health-platform-production-94aa.up.railway.app`
- **Pending DNS:** `api.customdose.ai` (Namecheap, not yet propagated)
- **Database:** Supabase (PostgreSQL)
- **Wearable:** Oura Ring OAuth integration (Whoop backend exists but not wired to mobile)

## Mobile App Structure (`mobile/src/`)

```
mobile/src/
  types/index.ts          - All TypeScript types (User, AnalyticsData, StackSupplement, etc.)
  constants/theme.ts      - Colors, Spacing, BorderRadius, Typography design tokens
  services/
    api.ts                - ApiService class, singleton export, all backend calls
    storage.ts            - AsyncStorage wrapper (user ID, user data cache)
  hooks/
    useAppState.tsx        - Monolithic context provider (AppStateProvider + useAppState hook)
  components/
    index.ts              - Barrel export for all components
    Text.tsx              - Themed text with variants (h1-h3, body, caption, label)
    Card.tsx              - Themed card container with padding variants
    Button.tsx            - Primary/secondary/danger button
    MetricCircle.tsx      - Circular progress indicator (sleep, HRV, recovery scores)
    DateNavigator.tsx     - Date picker with prev/next arrows
    SupplementPill.tsx    - Tappable pill for supplement logging (with animation)
    SupplementEditModal.tsx - Edit supplement dose/timing
    AddSupplementModal.tsx  - Add new supplement to stack
    LifeEventModal.tsx    - Add/view/delete life events
    HealthAlertCard.tsx   - Smart health recommendation cards
  screens/
    AuthScreen.tsx        - Email sign-in / create account
    OnboardingScreen.tsx  - 7-step onboarding wizard
    DashboardScreen.tsx   - Main screen: Oura metrics + supplement stack + health alerts
    AnalyticsScreen.tsx   - Trend charts, insights, life events, data table
    SettingsScreen.tsx    - Profile editing, Oura connection, account management
    MixesScreen.tsx       - Browse supplement mixes/catalog
  navigation/
    AppNavigator.tsx      - Conditional auth/onboarding/main tab navigator
```

## State Management
- **Pattern:** Single React Context (`AppStateProvider`) with one massive hook (`useAppState`)
- **Known debt:** Should be split into focused hooks (`useAuth`, `useSupplements`, `useOura`, `useAnalytics`)
- **Context value:** Memoized with `useMemo` (fixed in bug fix session)
- **Local storage:** AsyncStorage via `storage.ts` (user ID + cached user data)
- **Security issue:** User ID in plaintext AsyncStorage (should use `expo-secure-store`)

## Navigation
- **Library:** React Navigation (native stack + bottom tabs)
- **Flow:** AuthScreen -> OnboardingScreen (if !onboarding_complete) -> Main Tabs
- **Main Tabs:** Dashboard, Analytics, Mixes, Settings

## Key Patterns
- **Optimistic updates:** Supplement logging uses optimistic UI with revert on error
- **Race condition guard:** `useRef` in-flight lock on supplement toggling
- **Date handling:** Mix of `new Date(str + 'T00:00:00')` (local) and `new Date(str)` (UTC) -- inconsistent
- **Supplement ID normalization:** `.toLowerCase().replace(/-/g, '_')` used in ~8 places (should be utility)
- **No auth tokens:** All API calls are unauthenticated; user UUID in URL is the only "auth"

## Backend Structure (`app/`)

```
app/
  main.py               - FastAPI app, CORS, static files, legacy Oura routes, migration
  database.py           - Supabase client setup
  models.py             - Pydantic request/response models
  api/
    users.py            - User CRUD, signin, reset, progress
    analytics.py        - Supplement logs, starts, life events, insights, correlations
    integrations.py     - Oura/Whoop OAuth, sync, mock data, test scenarios
    mixes.py            - Mix catalog, smart recommendations, custom blends, tracking
    interactions.py     - Supplement interactions, timing, cycling, dosing, safety
    checkins.py         - Subjective daily check-ins, baselines, deviations
    dispenser.py        - Hardware dispenser recommendations
    upload.py           - CSV data import
  data/
    supplements.py      - Supplement database with mechanisms, interactions, cycling
    mixes.py            - Pre-built mix definitions
```

## What's Been Built (as of Feb 2026)
- Full 7-step onboarding flow
- Dashboard with Oura metrics, supplement stack (morning/intraday/evening), health alerts
- Analytics with trend charts, supplement insights, life events, data table
- Settings with editable profile, Oura management, account reset
- Mixes browsing screen
- 21 of 76 backend endpoints wired to mobile
