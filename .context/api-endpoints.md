# Backend API Endpoints (76 total)

## Legend
- [x] = Used by mobile app
- [ ] = Exists but NOT used by mobile

---

## Users `/users` (7 endpoints)
- [x] `POST /users` - Create user
- [x] `POST /users/signin` - Sign in by email
- [x] `GET /users/{user_id}` - Get user
- [x] `PATCH /users/{user_id}` - Update user profile
- [ ] `DELETE /users/{user_id}` - Delete user (needed for GDPR)
- [x] `POST /users/{user_id}/reset` - Reset account data
- [ ] `GET /users/{user_id}/progress` - Progress data (health metrics + dispense logs timeline)

## Analytics `/analytics` (17 endpoints)
- [x] `POST /analytics/{user_id}/supplement-logs` - Log supplement intake
- [ ] `POST /analytics/{user_id}/daily-checkin` - Batch check-in for multiple supplements at once
- [ ] `GET /analytics/{user_id}/supplement-logs` - Get logs (filterable by supplement_id, days)
- [x] `DELETE /analytics/{user_id}/supplement-logs/{log_id}` - Delete a log
- [x] `POST /analytics/{user_id}/supplement-starts` - Record starting a supplement
- [ ] `GET /analytics/{user_id}/supplement-starts` - List all supplement start records
- [x] `PATCH /analytics/{user_id}/supplement-starts/{start_id}` - Update supplement start
- [x] `DELETE /analytics/{user_id}/supplement-starts/{start_id}` - Delete supplement start
- [ ] `GET /analytics/supplement-library` - Common supplements with typical doses/frequencies
- [x] `POST /analytics/{user_id}/life-events` - Log a life event
- [ ] `GET /analytics/{user_id}/life-events` - Get life events
- [x] `GET /analytics/{user_id}/life-events/types` - Get event types
- [x] `DELETE /analytics/{user_id}/life-events/{event_id}` - Delete life event
- [x] `GET /analytics/{user_id}/analytics` - Combined analytics data (main data fetch)
- [x] `GET /analytics/{user_id}/outcome-analysis/{supplement_id}` - Before/after for a supplement
- [x] `GET /analytics/{user_id}/correlations` - Correlation insights
- [x] `GET /analytics/{user_id}/supplement-insights` - Comprehensive supplement insights

## Integrations `/integrations` (14 endpoints)
- [x] `GET /integrations/{user_id}/oura/auth` - Start Oura OAuth
- [ ] `GET /integrations/{user_id}/oura/callback` - Oura OAuth callback (GET)
- [ ] `POST /integrations/{user_id}/oura/callback` - Oura OAuth callback (POST)
- [x] `GET /integrations/{user_id}/oura/status` - Check Oura connection
- [x] `DELETE /integrations/{user_id}/oura` - Disconnect Oura
- [x] `GET /integrations/{user_id}/oura/history` - Fetch historical Oura data
- [ ] `GET /integrations/{user_id}/oura/debug` - Raw Oura API debug
- [ ] `POST /integrations/{user_id}/simulate-oura` - Simulate Oura (testing)
- [ ] `POST /integrations/{user_id}/test-scenario` - Set test scenario
- [ ] `GET /integrations/{user_id}/whoop/auth` - Start Whoop OAuth
- [ ] `POST /integrations/{user_id}/whoop/callback` - Whoop callback
- [ ] `POST /integrations/{user_id}/sync` - Sync all wearables
- [ ] `POST /integrations/{user_id}/mock` - Add mock health data
- [ ] `POST /integrations/{user_id}/mock-history` - Add mock historical data

## Mixes `/mixes` (11 endpoints)
- [ ] `GET /mixes/available` - Time-aware mix recommendations
- [x] `GET /mixes/all` - All mixes
- [x] `GET /mixes/catalog` - Full supplement catalog with PubMed links
- [ ] `POST /mixes/suggest-blend` - AI-powered blend suggestion (uses LLM)
- [ ] `GET /mixes/{user_id}/smart` - Smart mix based on health data
- [ ] `GET /mixes/{user_id}/history` - Dispense history
- [ ] `GET /mixes/{user_id}/{mix_id}` - Personalized mix details
- [ ] `POST /mixes/{user_id}/{mix_id}/dispense` - Dispense a mix
- [x] `GET /mixes/{user_id}/tracking/daily` - Daily supplement tracking vs limits
- [ ] `GET /mixes/{user_id}/tracking/weekly` - Weekly totals
- [ ] `GET /mixes/{user_id}/tracking/saturation` - Saturation status (e.g., creatine loading)

## Custom Blends `/mixes/blends` (5 endpoints)
- [ ] `GET /mixes/blends/{user_id}` - List custom blends
- [ ] `POST /mixes/blends/{user_id}` - Create blend
- [ ] `DELETE /mixes/blends/{user_id}/{blend_id}` - Delete blend
- [ ] `GET /mixes/blends/{user_id}/{blend_id}/preview` - Preview with personalized doses
- [ ] `POST /mixes/blends/{user_id}/{blend_id}/dispense` - Dispense blend

## Check-ins `/checkins` (5 endpoints)
- [ ] `POST /checkins/{user_id}/checkin` - Daily subjective check-in (energy, stress, mood, focus, sleep 1-5)
- [ ] `GET /checkins/{user_id}/checkins` - Check-in history
- [ ] `POST /checkins/{user_id}/baseline/calculate` - Calculate personal baseline
- [ ] `GET /checkins/{user_id}/baseline` - Get baseline
- [ ] `GET /checkins/{user_id}/deviations` - Current vs personal baseline

## Interactions `/interactions` (6 endpoints)
- [x] `POST /interactions/check` - Check interactions between supplements
- [ ] `GET /interactions/timing/{supplements}` - Timing conflicts (comma-separated IDs)
- [ ] `GET /interactions/cycle/{supplement_id}` - Cycling protocol
- [ ] `GET /interactions/dose/{supplement_id}` - Personalized dose recommendation
- [ ] `GET /interactions/{user_id}/safety-check` - Comprehensive safety check
- [x] `GET /interactions/supplements` - All supplement info

## Dispenser `/dispense` (3 endpoints)
- [ ] `GET /dispense/{user_id}` - Dispense recommendation
- [ ] `POST /dispense/{user_id}/confirm` - Confirm dispensed
- [ ] `GET /dispense/{user_id}/detailed` - Detailed recommendation with health context

## Upload `/upload` (1 endpoint)
- [ ] `POST /upload/{user_id}/oura-csv` - Upload Oura CSV export

## Root-level (7 endpoints)
- [ ] `GET /` - Serves index.html or API info
- [ ] `GET /health` - Health check
- [ ] `GET /privacy` - Privacy policy
- [ ] `GET /terms` - Terms of service
- [ ] `GET /api/oura/auth` - Legacy Oura OAuth (deprecated)
- [ ] `GET /api/oura/callback` - Legacy Oura callback
- [ ] `GET /api/migrate` - Run migrations

---

## High-Value Unused Endpoints (build features around these)

### Tier 1 - Immediate Value
| Endpoint | Feature It Enables |
|----------|-------------------|
| `POST /checkins/{user_id}/checkin` | Daily "How do you feel?" card |
| `GET /checkins/{user_id}/deviations` | "Your HRV is 1.5 SD below YOUR normal" |
| `GET /mixes/{user_id}/smart` | AI-powered daily recommendation |
| `GET /interactions/timing/{supplements}` | "Take zinc 2h away from magnesium" |
| `GET /interactions/cycle/{supplement_id}` | "Ashwagandha: 4 weeks on, 1 week off" |
| `GET /interactions/dose/{supplement_id}` | Personalized dose by weight/age/sex |
| `POST /analytics/{user_id}/daily-checkin` | One-tap "log all" at end of day |

### Tier 2 - Growth Features
| Endpoint | Feature It Enables |
|----------|-------------------|
| Custom Blends (5 endpoints) | User-created supplement combos |
| `POST /mixes/suggest-blend` | AI chatbot: "Build me a stack for sleep" |
| `GET /mixes/{user_id}/tracking/saturation` | Creatine loading progress bar |
| `GET /integrations/{user_id}/whoop/auth` | Whoop wearable support |
| `DELETE /users/{user_id}` | GDPR account deletion |
