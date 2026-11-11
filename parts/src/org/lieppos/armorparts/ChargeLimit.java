/*
 * Charge limit: stop charging at a chosen battery level.
 *
 * The MediaTek charger driver has a "discharging" command
 * (/proc/mtk_battery_cmd/current_cmd: "0 1" pauses, "0 0" resumes) that turns
 * the charger IC's charging off but keeps its power path: while paused the
 * phone runs from the charger and the battery current is 0 (measured), so the
 * level stays at the limit instead of cycling. The driver re-applies the pause
 * in every charger loop until it is cleared.
 *
 * This process only decides; it mirrors the decision into
 * sys.lieppos.charge_pause (system_prop) and system_ext/etc/init/
 * lieppos-chargelimit.rc writes the proc node as init (labelled
 * lieppos_charge_proc in the system_ext policy). The pause is cleared when the
 * charger is unplugged, when the feature is turned off, and below
 * limit - RESUME_GAP (heavy use can exceed the charger's supply).
 * Settings live in device-protected storage, so the limit also applies while
 * the phone is charging before the first unlock.
 *
 * Heat pause (independent of the limit switch, on by default): charging also
 * pauses while the battery is at or above HOT_PAUSE_DC and resumes at or below
 * HOT_RESUME_DC. Stock only stops charging at 55 degC (max-charge-temp).
 */
package org.lieppos.armorparts;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.BatteryManager;
import android.os.SystemProperties;
import android.util.Log;

final class ChargeLimit {
    private static final String TAG = "ArmorChargeLimit";
    static final String PROP = "sys.lieppos.charge_pause";
    private static final String PREFS = "charge_limit";
    private static final String KEY_ENABLED = "enabled";
    private static final String KEY_LIMIT = "limit";
    private static final String KEY_HEAT = "heat_pause";

    static final int MIN_LIMIT = 50;
    static final int MAX_LIMIT = 100;
    static final int STEP = 5;
    static final int DEFAULT_LIMIT = 80;
    static final int RESUME_GAP = 3;
    /** Battery temperature, tenths of a degree C (BatteryManager.EXTRA_TEMPERATURE). */
    static final int HOT_PAUSE_DC = 400;
    static final int HOT_RESUME_DC = 370;

    static final String AUTHORITY = "org.lieppos.armorparts.chargelimit";
    /** Settings observes this uri for the Battery page summary. */
    static final Uri SUMMARY_URI =
            Uri.parse("content://" + AUTHORITY + "/getDynamicSummary/charge_limit");

    private static int sLevel = -1;
    private static boolean sPlugged;
    private static boolean sPaused;
    private static int sTemp = Integer.MIN_VALUE;
    private static boolean sHot;

    private ChargeLimit() {}

    static void start(Context context) {
        final Context app = context.getApplicationContext();
        sPaused = "1".equals(SystemProperties.get(PROP));
        app.registerReceiver(new BroadcastReceiver() {
            @Override
            public void onReceive(Context c, Intent intent) {
                update(app, intent);
            }
        }, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
    }

    private static SharedPreferences prefs(Context context) {
        return context.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static boolean isEnabled(Context context) {
        return prefs(context).getBoolean(KEY_ENABLED, false);
    }

    static int getLimit(Context context) {
        int limit = prefs(context).getInt(KEY_LIMIT, DEFAULT_LIMIT);
        return Math.max(MIN_LIMIT, Math.min(MAX_LIMIT, limit));
    }

    static boolean isPaused() {
        return sPaused;
    }

    /** Paused (or would be, when plugged) because the battery is hot. */
    static boolean isHot() {
        return sHot;
    }

    static int getTemp() {
        return sTemp;
    }

    static boolean isHeatPauseEnabled(Context context) {
        return prefs(context).getBoolean(KEY_HEAT, true);
    }

    static void setHeatPauseEnabled(Context context, boolean enabled) {
        prefs(context).edit().putBoolean(KEY_HEAT, enabled).apply();
        settingsChanged(context);
    }

    static int getLevel() {
        return sLevel;
    }

    static boolean isPlugged() {
        return sPlugged;
    }

    static void setEnabled(Context context, boolean enabled) {
        prefs(context).edit().putBoolean(KEY_ENABLED, enabled).apply();
        settingsChanged(context);
    }

    static void setLimit(Context context, int limit) {
        prefs(context).edit().putInt(KEY_LIMIT, limit).apply();
        settingsChanged(context);
    }

    private static void settingsChanged(Context context) {
        // A changed limit is applied as set: raising it above the level resumes
        // charging right away, the resume gap only damps level fluctuations.
        evaluate(context, false);
        notifySummary(context);
    }

    private static void update(Context context, Intent battery) {
        int level = battery.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
        int scale = battery.getIntExtra(BatteryManager.EXTRA_SCALE, 100);
        boolean plugged = battery.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0) != 0;
        int temp = battery.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Integer.MIN_VALUE);
        if (level >= 0 && scale > 0) level = level * 100 / scale;
        if (level == sLevel && plugged == sPlugged && temp == sTemp) return;
        sLevel = level;
        sPlugged = plugged;
        sTemp = temp;
        evaluate(context, true);
    }

    private static void evaluate(Context context, boolean hysteresis) {
        boolean enabled = isEnabled(context);
        int limit = getLimit(context);
        // At 100 % there is nothing to stop: the charger finishes on its own.
        boolean full = enabled && limit < MAX_LIMIT && sPlugged && sLevel >= 0
                && (sLevel >= limit
                        || (hysteresis && sPaused && !sHot && sLevel > limit - RESUME_GAP));
        boolean known = sTemp != Integer.MIN_VALUE;
        boolean wasHot = sHot;
        sHot = isHeatPauseEnabled(context) && known
                && (sTemp >= HOT_PAUSE_DC || (sHot && sTemp > HOT_RESUME_DC));
        boolean pause = full || (sHot && sPlugged);
        String value = pause ? "1" : "0";
        if (pause == sPaused && value.equals(SystemProperties.get(PROP))) {
            if (sHot != wasHot) notifySummary(context);
            return;
        }
        try {
            SystemProperties.set(PROP, value);
            Log.i(TAG, (pause ? "pausing" : "resuming") + " charging at " + sLevel
                    + "% (limit " + (enabled ? limit + "%" : "off") + ", temp " + sTemp
                    + ", hot=" + sHot + ", plugged=" + sPlugged + ")");
            sPaused = pause;
        } catch (RuntimeException e) {
            Log.e(TAG, "set " + PROP + " failed", e);
        }
        notifySummary(context);
    }

    /** Best effort: a failed Settings summary refresh must not take down this process. */
    private static void notifySummary(Context context) {
        try {
            context.getContentResolver().notifyChange(SUMMARY_URI, null);
        } catch (RuntimeException e) {
            Log.w(TAG, "summary notify failed: " + e);
        }
    }

    static String summary(Context context) {
        if (sPaused && sHot) {
            return context.getString(R.string.charge_limit_summary_hot, sTemp / 10);
        }
        if (!isEnabled(context)) return context.getString(R.string.charge_limit_summary_off);
        int limit = getLimit(context);
        if (sPaused) return context.getString(R.string.charge_limit_summary_paused, sLevel);
        return context.getString(R.string.charge_limit_summary_on, limit);
    }
}
