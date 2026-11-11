/*
 * Snapshot of the SH366003 pack gauge, read from the sh366003_fg driver's
 * /sys/class/3rd-gauge/battery_info (one "key=value" per line, the gauge's own
 * units: mV, mA with + = charging, mAh, tenths of a degree C, %). Reading the
 * node makes the driver query the chip (about 40 ms), so call it off the main
 * thread. Labelled lieppos_gauge_sysfs (system_ext policy), readable by
 * system_app.
 */
package org.lieppos.armorparts;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

final class BatteryInfo {
    static final String NODE = "/sys/class/3rd-gauge/battery_info";
    /** Ulefone: 21200 mAh "equivalent" = 10600 mAh at 7.74 V for this 2S pack. */
    static final int RATED_MAH = 10600;
    /** Cell voltage difference above which the pack is shown as unbalanced. */
    static final int CELL_IMBALANCE_MV = 50;

    private final Map<String, String> mValues;

    private BatteryInfo(Map<String, String> values) {
        mValues = values;
    }

    /** Null if the node is missing (older kernel) or unreadable. */
    static BatteryInfo read() {
        Map<String, String> values = new HashMap<>();
        try (BufferedReader r = new BufferedReader(new FileReader(NODE))) {
            String line;
            while ((line = r.readLine()) != null) {
                int eq = line.indexOf('=');
                if (eq > 0) values.put(line.substring(0, eq).trim(), line.substring(eq + 1).trim());
            }
        } catch (IOException | SecurityException e) {
            return null;
        }
        return values.isEmpty() ? null : new BatteryInfo(values);
    }

    boolean has(String key) {
        return mValues.containsKey(key);
    }

    String str(String key) {
        String v = mValues.get(key);
        return v == null ? "" : v;
    }

    int num(String key, int fallback) {
        String v = mValues.get(key);
        if (v == null) return fallback;
        try {
            return v.startsWith("0x") ? Integer.parseInt(v.substring(2), 16) : Integer.parseInt(v);
        } catch (NumberFormatException e) {
            return fallback;
        }
    }

    /** Learned full-charge capacity as a percentage of the rated capacity, or -1. */
    int healthPercent() {
        int fcc = num("fcc_mah", -1);
        return fcc > 0 ? Math.round(fcc * 100f / RATED_MAH) : -1;
    }
}
