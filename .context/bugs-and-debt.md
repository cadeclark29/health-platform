# Bugs & Technical Debt

## Fixed (Feb 2026 session)
- [x] `api.ts:226` - checkInteractions sent `{ supplements }` instead of `{ supplement_ids: supplements }` (422 on every call)
- [x] `DashboardScreen.tsx` - Race condition on rapid supplement toggling (added useRef in-flight lock)
- [x] `DashboardScreen.tsx` - Missing error handling on handleEditSave, handleEditDelete, handleAddSupplement
- [x] `DashboardScreen.tsx` - Unused `Animated` import
- [x] `useAppState.tsx` - Context value not memoized (cascading re-renders on every state change)
- [x] `useAppState.tsx` - ouraConnected check only looked at health data, not Oura status API
- [x] `OnboardingScreen.tsx` - parseInt NaN handling (empty string -> NaN sent to API)
- [x] `OnboardingScreen.tsx` - Dead conditional logic (ternary with identical branches)
- [x] `LifeEventModal.tsx` - No date validation on freeform text input

---

## Remaining Bugs (unfixed)

### Critical
- **SEC-01: No authentication** - All API calls are unauthenticated. User UUID in URL is the only "auth". Anyone with a UUID can access any user's data. Needs: JWT or session tokens, Authorization headers, backend middleware.
- **SEC-03: User ID in plaintext AsyncStorage** - Should use `expo-secure-store`. Currently equivalent to storing a password in plaintext.

### High Priority
- **BUG-02: signIn error leaves user in broken state** - If `loadData` fails after sign-in, user appears authenticated but has no data. No retry mechanism.
- **BUG-04: Timezone inconsistency** - `new Date(str + 'T00:00:00')` (local time) vs `new Date(str)` (UTC) used in different files. Near midnight, dates can differ by a day.
  - Local time: `useAppState.tsx:444`, `LifeEventModal.tsx:101`
  - UTC: `AnalyticsScreen.tsx:89`
- **BUG-08: Oura OAuth has no completion callback** - OnboardingScreen opens external URL but has no deep link handler or polling to detect if OAuth succeeded.
- **BUG-09: Duplicate supplement IDs from onboarding** - Quick Stack + manual selection can add omega_3 and fish_oil (same supplement, different IDs).
- **ERR-05/06: handleAddSupplement, handleEditSave, handleEditDelete had no error handling** - FIXED in bug session
- **ERR-07: Onboarding silently swallows supplement add failures** - Empty catch in loop, user sees completion screen even if all API calls failed.
- **ERR-08: Linking.openURL not caught** - 3 files call Linking.openURL without .catch (DashboardScreen, SettingsScreen, OnboardingScreen).

### Medium Priority
- **PERF-01/02: getStackSupplements() and getTodaysLogs() not memoized** - Called every render in DashboardScreen, iterate full arrays each time. Should be useMemo.
- **PERF-05: SVG chart path not memoized** - buildChartPath in AnalyticsScreen recomputes every render.
- **PERF-06: StackTimeSection not wrapped in React.memo** - But isTaken callback also needs memoization for memo to help.
- **UX-02: No offline handling** - No network detection, no offline queue, no graceful degradation.
- **UX-03: No accessibility labels** - Zero accessibilityLabel/Role/Hint on any interactive element.
- **UX-06: Hard-coded tab bar height (85px)** - Doesn't account for device safe areas.
- **UX-07: LifeEventModal ScrollView maxHeight: 500** - Hard-coded, wrong on small/large devices.
- **UX-09: Dimensions.get('window') at module level** - Doesn't update on rotation/multitasking.
- **ERR-01: initializeApp silently logs user out** - If stored user ID is invalid, catch block removes it without telling user.
- **ERR-02: loadData errors not propagated** - Sign-in succeeds but data load failures are invisible.
- **ERR-03: Insights fetch errors silently swallowed** - `.catch(() => {})` hides persistent failures.
- **ERR-09: storage.ts swallows all errors** - Every method has try/catch that logs and returns default. Quota issues invisible.

### Low Priority (Code Quality)
- **QUAL-02: Duplicate formatSupplementName** - Same function in DashboardScreen, AnalyticsScreen, SupplementEditModal.
- **QUAL-03: Duplicate TIME_SLOTS and COMMON_UNITS arrays** - In SupplementEditModal and AddSupplementModal.
- **QUAL-04: Duplicate formatting helpers** - SettingsScreen and OnboardingScreen have near-identical formatGoal/formatActivity/etc.
- **QUAL-06: Button textColor logic is dead code** - Computed but overridden by inline style.
- **QUAL-07: supplement_id normalization not centralized** - `.toLowerCase().replace(/-/g, '_')` in ~8 places.
- **QUAL-08: RootStackParamList type defined but unused** - Navigation uses conditional rendering.
- **QUAL-09: Inconsistent api import** - Some screens import `api` directly, others go through useAppState.
- **QUAL-10: No React Error Boundary** - Any render throw crashes entire app.
- **TYPE-01: 14 API methods return Promise<any>** - Zero type safety on response shapes.
- **TYPE-02: Unsafe `as any` casts in onboarding/settings** - Profile fields cast instead of typed.
- **TYPE-04: User.oura_token typed as `object`** - Provides no property access.
- **TYPE-06: userTimings cast as TimeSlot** - Could contain invalid strings from AsyncStorage.

---

## Architecture Debt
1. **Monolithic useAppState** - Single 400+ line hook manages all state. Should split into useAuth, useSupplements, useOura, useAnalytics.
2. **No error boundary** - App crashes on any render error.
3. **No retry/offline logic** - Every failed API call shows Alert.alert with no retry option.
4. **Functions in context not wrapped in useCallback** - Only the value object is memoized, not individual functions.
