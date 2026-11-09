/*
 * Battery saver CPU cap.
 *
 * The stock MediaTek power HAL has no low-power scenario, so battery saver
 * changes nothing at the CPU level. This mirrors the battery saver state into
 * sys.lieppos.powersave (system_prop, settable by system_app); the init trigger
 * in system_ext/etc/init/lieppos-powersave.rc then caps the big cluster
 * (policy4) at persist.sys.lieppos.powersave_big_khz (default 2.0 GHz instead
 * of 2.6 GHz) and restores the full range when battery saver turns off.
 * The cap holds through the power HAL's launch/touch boosts (they raise
 * scaling_min_freq, which the kernel clamps to scaling_max_freq).
 */
package org.lieppos.armorparts;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.PowerManager;
import android.os.SystemProperties;
import android.util.Log;

final class PowerSaveCap {
    private static final String TAG = "ArmorPowerSave";
    static final String PROP = "sys.lieppos.powersave";

    private PowerSaveCap() {}

    static void start(Context context) {
        final Context app = context.getApplicationContext();
        app.registerReceiver(new BroadcastReceiver() {
            @Override
            public void onReceive(Context c, Intent intent) {
                apply(app);
            }
        }, new IntentFilter(PowerManager.ACTION_POWER_SAVE_MODE_CHANGED));
        apply(app);
    }

    private static void apply(Context context) {
        boolean on = context.getSystemService(PowerManager.class).isPowerSaveMode();
        String value = on ? "1" : "0";
        if (value.equals(SystemProperties.get(PROP))) return;
        try {
            SystemProperties.set(PROP, value);
            Log.i(TAG, "battery saver " + (on ? "on: big cores capped" : "off: full range"));
        } catch (RuntimeException e) {
            Log.e(TAG, "set " + PROP + " failed", e);
        }
    }
}
