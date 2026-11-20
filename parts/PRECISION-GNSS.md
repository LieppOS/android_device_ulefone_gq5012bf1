# Timed Precision GNSS sessions

Implementation status: **build and on-device lifecycle validated**.62 lifetime/
authorization checks,37 glove regressions and the real Android target pass.
The matching installed APK passes start, Stop-action dispatch, actual UI Stop,
process-restart cleanup and one real15-minute screen-off expiry. The Location
services entry is visible and opens Off without starting tracking. The earlier independent
four-minute probe established L5-family use and the vendor request path, not a
causal accuracy gain, RTK readiness or this service's alarm behavior.

## User control

**Settings > Location > Location services > Precision GNSS**, using Android's
`SettingInjectorService` contract, and an optional user-added QS tile. Opening the
page or querying its summary does not start GNSS. Starting requires an explicit
user switch/tile action; tile starts require unlock. Stop is also available through
the ongoing notification and does not require unlocking. No tiles are added or
rearranged automatically.

Each session is limited to the owner-selected15 minutes. Repeated Start commands
do not extend an existing deadline. Stop then a new explicit Start is needed for
another session. The page shows **full tracking requested**, not verified better
accuracy. Other applications' GNSS requests are independent; stopping this request
does not disable global Location or force other applications out of full tracking.

## Actual request and privacy

A private, non-sticky location foreground service registers one public
`GnssMeasurementRequest` with full tracking enabled and interval1000ms. It makes
no separate position request, requests no correlation vectors, and never calls
getters on the measurement callback payload. No coordinates, NMEA, ranges,
receiver-clock data or measurement samples are processed, logged or saved. Normal
framework callback objects necessarily exist transiently in volatile process
memory. There is no network/storage functionality, firmware/NVRAM operation,
global developer-setting change or root/shell helper.

Full tracking can keep the receiver active and use more power even after leaving
a navigation application. The prior single ordinary-then-full run was warmed up
in the second phase: more L5 participation and lower reported uncertainty do not
prove that true positional error improved. Survey-grade carrier phase and5/10Hz
operation have not been established. No permanent enablement is proposed.

## Lifetime and failure behavior

- No enabled preference, boot receiver, startup activation or active-session
  restoration. Process death removes the listener's Binder registration. A
  cleanup-only application-start hook explicitly stops any old service record,
  cancels its old expiry intent and removes its stale notification. Live testing
  found AMS can retain an app=null restarting foreground record for a persistent
  package even when startRequested=false and stopIfKilled=true; sending a Stop
  action through startService merely queues behind that record. No new session
  may start until the direct stopService cleanup succeeds.
- User starts carry a one-shot in-process authorization. Null/unknown intents,
  stale tokens and framework retry/redelivery cannot recreate a session. New
  process authorization defaults empty, even if an old START intent is retained.
- The foreground notification and exact elapsed-realtime wakeup alarm are required
  before the GNSS request is acquired. Wall-clock changes do not move its deadline;
  a Handler uptime timer is not used as the sole screen-off timeout mechanism.
- This existing app has system shared UID. The current framework exempts core
  UIDs from exact-alarm permission; the service still checks availability and
  refuses to start rather than falling back to an unbounded/inexact deadline.
- An early/stale expiry command cannot stop a newer unexpired session. Expiry
  commands can only remove a request, never acquire one.
- Disabled Location, missing fine-location permission, hidden/blocked notifications
  or unavailable exact expiry prevents a start. Location disable/unsupported
  measurements also stops a live session. A watchdog backs up the alarm and checks
  policy/notification availability while the process runs.
- Partial registration failures attempt removal. Failed removal is shown as
  **Stopping**, retried, and blocks acquisition; it is never represented as
  confirmed Off. Alarm cancellation failure after successful removal cannot
  recreate GNSS. Queued callbacks from an old generation cannot stop a newer one.
- The tracking service is not exported; the read-only settings injector is
  protected by BIND_LOCATION_PROVIDER, and the tile by BIND_QUICK_SETTINGS_TILE.
  Activity intents/extras do not auto-start tracking.

New declarations are coarse/fine location and foreground-service/location type
permissions. Existing notification permission is reused. No background-location,
exact-alarm special-access declaration, SELinux change or new privileged helper.

## Validation

Run the pure lifetime-model tests outside source Git under the workspace CPU/NUMA
binding, compiling `PrecisionGnssSession.java` and
`tests/PrecisionGnssSessionTest.java`. They model arm-before-acquire, exact boundary,
elapsed jumps, idempotence, stale expiry, rollback, failed removal/retry, cancel
failure, overflow and one-shot/replay authorization. They are not an Android alarm
or hardware test. Re-run the glove regression tests and build the real
`ArmorPartsGq5012bf1` target as well.

Fresh owner approval is required before a persistent-app staged update/apply reboot
and active GNSS validation. Closed glove/probe approvals must not be reused. Leave
sessions Off, verify notification Stop, automatic15-minute expiry including screen
off, no restart restoration, disabled-location handling and read-only Settings
injection separately. Do not shorten production timeouts with a hidden external
intent just to claim the real15-minute expiry passed. Record untested paths as such.

### On-device validation snapshot

- Installed APK hash/signature matches the built artifact. The original and
  corrective apply reboots were each separately approved; both remained on B.
- Cold boot starts Off. Opening Location > Location services > Precision GNSS
  shows the real injected entry and never creates a tracking service.
- Actual UI Start/Stop and production notification STOP-action dispatch pass;
  the notification was observed, but its action was dispatched through the same
  private service intent rather than a physical shade-button tap.
- The first candidate's process-death test exposed a retained AMS foreground
  record/notification. The negative assertion was preserved. The cleanup-only
  correction passes an actual exact-package process restart: no request returns,
  no service record remains and no stale notification survives. Starting a new
  explicit session afterward also passes.
- The one genuine900000ms test was active in the same process with the screen
  asleep at500s and870s. By913.62s it had stopped without a manual expiry command,
  process restart or shortened timeout; its service and notification were gone.
  Alarm history recorded one precision.expire wakeup. Opening the page afterward
  showed Off — session expired, with no tracking service created.
- This was USB-powered screen-off validation, NOT an unplugged/forced-deep-Doze
  experiment or proof of hard-real-time scheduling under arbitrary OS failure.
  Global Location and the developer force-full-tracking setting stayed unchanged.
- The optional tile was not added/rearranged or interactively exercised. Runtime
  location-disable/permission-denial paths and interruption of an active session
  by a real reboot were not separately exercised; do not turn model/code review
  into claims that those hardware scenarios ran. No accuracy or power benchmark
  was repeated as part of this feature's lifecycle test.
- Final state is Off; no coordinates, NMEA, ranges or raw payload samples were
  saved. Private lifecycle evidence remains outside source Git under
  build/precision-gnss, including the original failure and correction recheck.
