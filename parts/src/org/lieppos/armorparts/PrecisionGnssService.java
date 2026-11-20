// SPDX-License-Identifier: Apache-2.0
package org.lieppos.armorparts;

import android.Manifest;
import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.BroadcastReceiver;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.location.GnssMeasurementRequest;
import android.location.GnssMeasurementsEvent;
import android.location.LocationManager;
import android.location.SettingInjectorService;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.SystemClock;
import android.service.quicksettings.TileService;
import android.util.Log;
import java.io.IOException;

/** User-started, non-sticky location FGS. No active state is ever persisted. */
public final class PrecisionGnssService extends Service {
    static final String CHANGED = "org.lieppos.armorparts.PRECISION_GNSS_CHANGED";
    private static final String START = "precision.start";
    private static final String START_TOKEN = "user_start_token";
    private static final PrecisionGnssSession.StartGate START_GATE = new PrecisionGnssSession.StartGate();
    private static final String STOP = "precision.stop";
    private static final String EXPIRE = "precision.expire";
    private static final String CHANNEL = "precision_gnss";
    private static final int NOTIFICATION = 701;
    private static final Handler MAIN = new Handler(Looper.getMainLooper());
    // Retain failed cleanup within this process, not an enabled preference. Process
    // death removes the callback's Binder registration; a new process starts Off.
    private static RuntimeAccess runtime;
    private static PrecisionGnssService current;
    private static volatile boolean startupReady;
    static volatile Snapshot snapshot = new Snapshot(PrecisionGnssSession.State.OFF, 0,
            R.string.precision_gnss_off);
    private boolean receiverRegistered;
    private int stopReason = R.string.precision_gnss_off;

    static final class Snapshot {
        final PrecisionGnssSession.State state;
        final long deadline;
        final int reason;
        Snapshot(PrecisionGnssSession.State state, long deadline, int reason) {
            this.state = state; this.deadline = deadline; this.reason = reason;
        }
        boolean requested() { return state != PrecisionGnssSession.State.OFF; }
        boolean stopping() {
            return state == PrecisionGnssSession.State.STOPPING
                    || (requested() && SystemClock.elapsedRealtime() >= deadline);
        }
    }

    /** Cleanup only; never register a listener or restore a saved session. */
    static void resetAfterProcessStart(Context context) {
        if (startupReady) return;
        Context app = context.getApplicationContext();
        START_GATE.cancel();
        try {
            // A non-sticky service can still leave an app=null restarting AMS
            // record for this persistent package. An action sent via startService
            // queues behind that record; stopService removes it directly.
            app.stopService(new Intent(app, PrecisionGnssService.class));
            PendingIntent stale = PendingIntent.getService(app, 703,
                    new Intent(app, PrecisionGnssService.class).setAction(EXPIRE),
                    PendingIntent.FLAG_NO_CREATE | PendingIntent.FLAG_IMMUTABLE);
            if (stale != null) {
                app.getSystemService(AlarmManager.class).cancel(stale);
                stale.cancel();
            }
            app.getSystemService(NotificationManager.class).cancel(NOTIFICATION);
            startupReady = true;
            notifyState(app);
        } catch (RuntimeException failure) {
            Log.w("ArmorPrecisionGnss", "Startup removal of stale GNSS state failed", failure);
            MAIN.postDelayed(() -> resetAfterProcessStart(app), 1000);
        }
    }
    static boolean readyToStart() { return startupReady; }

    static void start(Context context) {
        if (!startupReady) throw new IllegalStateException("Previous GNSS state cleanup pending");
        if (snapshot.requested()) return;
        long token = START_GATE.issue();
        if (token == 0) return;
        try {
            context.startForegroundService(new Intent(context, PrecisionGnssService.class)
                    .setAction(START).putExtra(START_TOKEN, token));
        } catch (RuntimeException failure) { START_GATE.discard(token); throw failure; }
    }
    static void stop(Context context) {
        START_GATE.cancel();
        context.startService(new Intent(context, PrecisionGnssService.class).setAction(STOP));
    }
    static String summary(Context context) {
        if (!startupReady) return context.getString(R.string.precision_gnss_stopping);
        Snapshot s = snapshot;
        if (s.stopping()) return context.getString(R.string.precision_gnss_stopping);
        if (!s.requested()) return context.getString(s.reason);
        long minutes = Math.max(1, (s.deadline - SystemClock.elapsedRealtime() + 59999) / 60000);
        return context.getString(R.string.precision_gnss_remaining, minutes);
    }
    static boolean locationEnabled(Context context) {
        LocationManager manager = context.getSystemService(LocationManager.class);
        return manager != null && manager.isLocationEnabled();
    }

    @Override public void onCreate() {
        super.onCreate();
        if (runtime == null) runtime = new RuntimeAccess(getApplicationContext());
        current = this;
        NotificationChannel channel = new NotificationChannel(CHANNEL,
                getString(R.string.precision_gnss_title), NotificationManager.IMPORTANCE_LOW);
        channel.setDescription(getString(R.string.precision_gnss_channel_description));
        channel.setShowBadge(false);
        runtime.notifications.createNotificationChannel(channel);
    }
    @Override public IBinder onBind(Intent intent) { return null; }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? null : intent.getAction();
        if (START.equals(action) && !START_GATE.consume(intent.getLongExtra(START_TOKEN, 0),
                (flags & (START_FLAG_REDELIVERY | START_FLAG_RETRY)) != 0)) {
            if (runtime.session.state() == PrecisionGnssSession.State.OFF) stopSelf();
            return START_NOT_STICKY;
        }
        if (EXPIRE.equals(action)) {
            if (runtime.session.state() == PrecisionGnssSession.State.ACTIVE
                    && SystemClock.elapsedRealtime() < runtime.session.deadline()) return START_NOT_STICKY;
            finishRequest(R.string.precision_gnss_expired);
        } else if (STOP.equals(action) || !START.equals(action)) {
            START_GATE.cancel();
            // Null/unknown commands never recreate a tracking request.
            finishRequest(R.string.precision_gnss_off);
        } else if (runtime.session.state() != PrecisionGnssSession.State.OFF) {
            // Duplicate starts cannot restart or extend a session.
            if (runtime.session.state() == PrecisionGnssSession.State.STOPPING) finishRequest(stopReason);
            else if (SystemClock.elapsedRealtime() >= runtime.session.deadline())
                finishRequest(R.string.precision_gnss_expired);
        } else {
            int blocked = blockedReason();
            if (blocked != 0) {
                stopReason = blocked;
                publish(blocked); stopSelf(); return START_NOT_STICKY;
            }
            try {
                // Notification and exact deadline must exist before registration.
                startForeground(NOTIFICATION, notification(false),
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION);
                registerReceiver(providerChanged, new IntentFilter(LocationManager.PROVIDERS_CHANGED_ACTION),
                        Context.RECEIVER_NOT_EXPORTED);
                receiverRegistered = true;
                runtime.session.start(SystemClock.elapsedRealtime());
                publish(R.string.precision_gnss_active);
                runtime.notifications.notify(NOTIFICATION, notification(false));
                MAIN.removeCallbacks(watchdog); MAIN.post(watchdog);
            } catch (RuntimeException | IOException failure) {
                Log.w("ArmorPrecisionGnss", "Could not start bounded GNSS request", failure);
                finishRequest(R.string.precision_gnss_failed);
            }
        }
        return START_NOT_STICKY;
    }

    private int blockedReason() {
        if (!locationEnabled(this)) return R.string.precision_gnss_location_off;
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED)
            return R.string.precision_gnss_permission_missing;
        NotificationChannel channel = runtime.notifications.getNotificationChannel(CHANNEL);
        if (!runtime.notifications.areNotificationsEnabled()
                || (channel != null && channel.getImportance() == NotificationManager.IMPORTANCE_NONE))
            return R.string.precision_gnss_notifications_off;
        if (!runtime.alarms.canScheduleExactAlarms()) return R.string.precision_gnss_alarm_unavailable;
        return 0;
    }
    private final BroadcastReceiver providerChanged = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            if (!locationEnabled(context)) finishRequest(R.string.precision_gnss_location_off);
        }
    };
    private final Runnable watchdog = new Runnable() {
        @Override public void run() {
            if (current != PrecisionGnssService.this) return;
            if (runtime.session.state() == PrecisionGnssSession.State.STOPPING) {
                finishRequest(stopReason); return;
            }
            if (runtime.session.state() == PrecisionGnssSession.State.OFF) return;
            if (SystemClock.elapsedRealtime() >= runtime.session.deadline()) {
                finishRequest(R.string.precision_gnss_expired); return;
            }
            int blocked = blockedReason();
            if (blocked != 0) { finishRequest(blocked); return; }
            MAIN.postDelayed(this, 5000); // Wakeup alarm, not this uptime timer, enforces expiry.
        }
    };

    private void finishRequest(int reason) {
        START_GATE.cancel();
        stopReason = reason;
        MAIN.removeCallbacks(watchdog);
        try { runtime.session.stop(); }
        catch (IOException failure) {
            Log.w("ArmorPrecisionGnss", "GNSS request cleanup failed", failure);
        }
        if (runtime.session.state() != PrecisionGnssSession.State.OFF) {
            publish(R.string.precision_gnss_stopping);
            runtime.notifications.notify(NOTIFICATION, notification(true));
            MAIN.postDelayed(watchdog, 1000);
            return; // Keep removal failure visible; never claim Off or acquire again.
        }
        publish(reason);
        if (receiverRegistered) { unregisterReceiver(providerChanged); receiverRegistered = false; }
        stopForeground(STOP_FOREGROUND_REMOVE);
        runtime.notifications.cancel(NOTIFICATION);
        stopSelf();
    }
    private void publish(int reason) {
        Snapshot old = snapshot;
        Snapshot next = new Snapshot(runtime.session.state(), runtime.session.deadline(), reason);
        if (old.state == next.state && old.deadline == next.deadline && old.reason == next.reason) return;
        snapshot = next;
        notifyState(this);
    }
    private static void notifyState(Context context) {
        context.sendBroadcast(new Intent(CHANGED).setPackage(context.getPackageName()));
        SettingInjectorService.refreshSettings(context);
        try { TileService.requestListeningState(context, new ComponentName(context, PrecisionGnssTile.class)); }
        catch (RuntimeException ignored) { /* An absent tile must not affect request cleanup. */ }
    }
    private Notification notification(boolean stopping) {
        Intent page = new Intent(this, PrecisionGnssActivity.class);
        PendingIntent content = PendingIntent.getActivity(this, 701, page,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        PendingIntent stop = PendingIntent.getService(this, 702,
                new Intent(this, PrecisionGnssService.class).setAction(STOP),
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        long remaining = runtime.session.state() == PrecisionGnssSession.State.OFF
                ? PrecisionGnssSession.DURATION_MS
                : Math.max(0, runtime.session.deadline() - SystemClock.elapsedRealtime());
        return new Notification.Builder(this, CHANNEL)
                .setSmallIcon(R.drawable.ic_precision_gnss)
                .setContentTitle(getString(R.string.precision_gnss_title))
                .setContentText(getString(stopping ? R.string.precision_gnss_stopping
                        : R.string.precision_gnss_notification))
                .setContentIntent(content).setOngoing(true).setOnlyAlertOnce(true)
                .setCategory(Notification.CATEGORY_SERVICE)
                .setWhen(System.currentTimeMillis() + remaining)
                .setUsesChronometer(!stopping).setChronometerCountDown(true)
                .addAction(new Notification.Action.Builder(R.drawable.ic_precision_gnss,
                        getString(R.string.precision_gnss_stop), stop).build()).build();
    }
    @Override public void onDestroy() {
        MAIN.removeCallbacks(watchdog);
        if (receiverRegistered) { unregisterReceiver(providerChanged); receiverRegistered = false; }
        if (current == this) {
            try { runtime.session.stop(); }
            catch (IOException failure) { Log.w("ArmorPrecisionGnss", "Cleanup on destroy failed", failure); }
            if (runtime.session.state() == PrecisionGnssSession.State.OFF) {
                publish(stopReason); runtime.notifications.cancel(NOTIFICATION);
            } else {
                publish(R.string.precision_gnss_stopping);
                // Retry removal only. The app process is persistent; never restart acquisition.
                Context app = getApplicationContext();
                MAIN.postDelayed(new Runnable() {
                    @Override public void run() {
                        if (runtime.session.state() == PrecisionGnssSession.State.OFF) return;
                        try { stop(app); }
                        catch (RuntimeException failure) {
                            Log.w("ArmorPrecisionGnss", "Removal retry could not reach service", failure);
                            MAIN.postDelayed(this, 1000);
                        }
                    }
                }, 1000);
            }
            current = null;
        }
        super.onDestroy();
    }

    private static final class RuntimeAccess implements PrecisionGnssSession.Access {
        final Context app;
        final LocationManager locations;
        final AlarmManager alarms;
        final NotificationManager notifications;
        final PrecisionGnssSession session = new PrecisionGnssSession(this);
        GnssMeasurementsEvent.Callback callback;
        PendingIntent expiry;
        int generation;
        RuntimeAccess(Context context) {
            app = context;
            locations = app.getSystemService(LocationManager.class);
            alarms = app.getSystemService(AlarmManager.class);
            notifications = app.getSystemService(NotificationManager.class);
        }
        @Override public void armDeadline(long deadline) throws IOException {
            try {
                expiry = PendingIntent.getService(app, 703,
                        new Intent(app, PrecisionGnssService.class).setAction(EXPIRE),
                        PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
                alarms.setExactAndAllowWhileIdle(AlarmManager.ELAPSED_REALTIME_WAKEUP, deadline, expiry);
            } catch (RuntimeException failure) { throw new IOException("Cannot arm GNSS deadline", failure); }
        }
        @Override public boolean acquire() throws IOException {
            final int request = ++generation;
            callback = new GnssMeasurementsEvent.Callback() {
                private boolean live() { return request == generation
                        && session.state() == PrecisionGnssSession.State.ACTIVE; }
                @Override public void onGnssMeasurementsReceived(GnssMeasurementsEvent ignored) {
                    // No payload getters, coordinate/range access, logging or sample storage.
                    if (live() && SystemClock.elapsedRealtime() >= session.deadline())
                        app.startService(new Intent(app, PrecisionGnssService.class).setAction(EXPIRE));
                }
                @Override public void onStatusChanged(int status) {
                    if (!live()) return;
                    if (status == STATUS_NOT_SUPPORTED || status == STATUS_LOCATION_DISABLED) {
                        if (current != null) current.finishRequest(status == STATUS_NOT_SUPPORTED
                                ? R.string.precision_gnss_unsupported : R.string.precision_gnss_location_off);
                        else stop(app);
                    }
                }
            };
            try {
                return locations.registerGnssMeasurementsCallback(
                        new GnssMeasurementRequest.Builder().setFullTracking(true)
                                .setIntervalMillis(1000).build(), app.getMainExecutor(), callback);
            } catch (RuntimeException failure) { throw new IOException("Cannot request GNSS tracking", failure); }
        }
        @Override public void release() throws IOException {
            ++generation; // Queued callbacks from an old request cannot stop a newer one.
            if (callback == null) return;
            try { locations.unregisterGnssMeasurementsCallback(callback); callback = null; }
            catch (RuntimeException failure) { throw new IOException("Cannot remove GNSS request", failure); }
        }
        @Override public void cancelDeadline() throws IOException {
            if (expiry == null) return;
            try { alarms.cancel(expiry); expiry = null; }
            catch (RuntimeException failure) { throw new IOException("Cannot cancel old GNSS deadline", failure); }
        }
    }
}
