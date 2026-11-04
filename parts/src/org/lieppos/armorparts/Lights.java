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
    private static volatile int sRedLevel = -1, sBlueLevel = -1;

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

    // ---- automation API (LightApi): synchronous, call from a worker thread ----

    /** Red/blue now at 0..255 (0 = off; 1..254 = hardware PWM, 40 steps). */
    static void ledNow(boolean red, int level) {
        level = Math.max(0, Math.min(LED_MAX, level));
        if (red) sRedLevel = level; else sBlueLevel = level;
        write(LEDS, (red ? "red " : "blue ") + level);
    }

    /** Driver mode string: ALL_OFF, RED_ON, BLUE_ON, ALL_ON, RED_FLASH, BLUE_FLASH, RED_BLUE_FLASH. */
    static String ledMode() {
        return read(LEDS);
    }

    static boolean ledOn(boolean red) {
        return ledState(red) != OFF;
    }

    /** Stock red/blue patterns of the driver: 4 red flash, 5 blue flash, 6 red-blue flash. */
    static void ledPatternNow(int mode) {
        sRedLevel = 0;
        sBlueLevel = 0;
        write(LEDS, Integer.toString(mode));
    }

    /** Super flashlight now at 0..100 % (0 = off), mapped onto the driver's 1..94. */
    static void flashlightNow(int percent) {
        if (!"OFF".equals(read(MODE))) write(MODE, "0"); // leave a stock blink/SOS
        if (percent <= 0) {
            write(BRIGHTNESS, "0");
            return;
        }
        percent = Math.min(100, percent);
        int raw = LEVEL_LOW + Math.round((percent - 1) * (LEVEL_MAX - LEVEL_LOW) / 99f);
        write(BRIGHTNESS, Integer.toString(raw));
    }

    static boolean flashlightOn() {
        return flashlightState() != OFF;
    }

    /** Stock super-flashlight patterns of the driver: 4 blink (50/50 ms), 5 SOS. */
    static void flashlightModeNow(int mode) {
        write(BRIGHTNESS, "0");
        write(MODE, Integer.toString(mode));
    }
}
