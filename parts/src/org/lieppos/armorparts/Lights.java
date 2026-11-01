/*
 * GQ5012BF1 "super flashlight" (LN2403 camping light) and red/blue LEDs.
 * Driver: drivers/leds/leds-ln2403 (platform device yft_camplight). The nodes are
 * labelled sysfs_yft_file, writable by system_app in the stock vendor policy.
 */
package org.lieppos.armorparts;

import android.os.Handler;
import android.os.HandlerThread;
import android.util.Log;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;

final class Lights {
    private static final String TAG = "ArmorLights";
    private static final String NODE = "/sys/devices/platform/yft_camplight/";
    private static final String MODE = NODE + "camplight_mode";              // OFF/LOW/NORMAL/HIGH/BLINK/SOS
    private static final String BRIGHTNESS = NODE + "camplight_set_brightness";
    private static final String LEDS = NODE + "leds_ctl";

    // camplight_set_brightness takes 1..94 and reads back the PWM duty (100 - value).
    static final int LEVEL_LOW = 1;
    static final int LEVEL_MAX = 94;
    static final int OFF = 0, LOW = 1, MAX = 2;

    /** All hardware writes run here, never on the tile's main thread. */
    private static final Handler IO;
    static {
        HandlerThread t = new HandlerThread(TAG);
        t.start();
        IO = new Handler(t.getLooper());
    }

    private Lights() {}

    private static void write(String path, String value) {
        try (FileWriter w = new FileWriter(path)) {
            w.write(value);
        } catch (IOException e) {
            Log.w(TAG, "write " + path + " failed: " + e);
        }
    }

    private static String read(String path) {
        try (BufferedReader r = new BufferedReader(new FileReader(path))) {
            String s = r.readLine();
            return s == null ? "" : s.trim();
        } catch (IOException e) {
            return "";
        }
    }

    // ---- super flashlight --------------------------------------------------
    static int flashlightState() {
        int duty;
        try {
            duty = Integer.parseInt(read(BRIGHTNESS));
        } catch (NumberFormatException e) {
            duty = 0;
        }
        if (duty > 0) return duty >= 50 ? LOW : MAX;
        String mode = read(MODE);
        return mode.isEmpty() || "OFF".equals(mode) ? OFF : MAX; // lit by a stock mode
    }

    static void setFlashlight(int from, int to) {
        IO.post(() -> {
            if (from == MAX && !"OFF".equals(read(MODE))) write(MODE, "0"); // stock blink/SOS
            if (to == OFF) write(BRIGHTNESS, "0");
            else write(BRIGHTNESS, Integer.toString(to == LOW ? LEVEL_LOW : LEVEL_MAX));
        });
    }

    // ---- red / blue ---------------------------------------------------------
    // Low = 10 % duty. The driver keeps the per-colour level; this process keeps
    // the last level it set so the tile can tell Low from Max.
    static final int LED_LOW = 26, LED_MAX = 255;
    private static int sRedLevel = -1, sBlueLevel = -1;

    static int ledState(boolean red) {
        String s = read(LEDS);
        boolean on = red ? ("RED_ON".equals(s) || "ALL_ON".equals(s))
                : ("BLUE_ON".equals(s) || "ALL_ON".equals(s));
        if (!on) return OFF;
        int lvl = red ? sRedLevel : sBlueLevel;
        return lvl == LED_LOW ? LOW : MAX;
    }

    static void setLed(boolean red, int state) {
        int level = state == LOW ? LED_LOW : state == MAX ? LED_MAX : 0;
        if (red) sRedLevel = level; else sBlueLevel = level;
        setColor(red, level);
    }

    /** level 0..255; the LieppOS driver dims 1..254 with hardware PWM. */
    static void setColor(boolean red, int level) {
        IO.post(() -> write(LEDS, (red ? "red " : "blue ") + level));
    }
}
