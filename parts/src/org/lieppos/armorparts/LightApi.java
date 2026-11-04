/*
 * Broadcast-intent API for the super flashlight and the red/blue LEDs, for
 * automation apps (Tasker, MacroDroid, Key Mapper) and adb. Only this system
 * app may write the yft_camplight nodes, so other apps go through here.
 * Reference: parts/LIGHTS-API.md.
 */
package org.lieppos.armorparts;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.PowerManager;
import android.os.Process;
import android.os.SystemClock;
import android.util.Log;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

final class LightApi {
    static final String ACTION = "org.lieppos.armorparts.action.LIGHT";
    static final String ACTION_OFF = "org.lieppos.armorparts.action.LIGHTS_OFF";

    private static final String TAG = "ArmorLightApi";
    private static final int MIN_MS = 10;
    private static final String RED = "red", BLUE = "blue", WHITE = "white", POLICE = "police";

    /** Everything below runs on this thread: receiver callbacks and strobe steps. */
    private static Handler sH;
    private static PowerManager.WakeLock sWake;
    private static final Set<String> sRunning = new HashSet<>();

    private LightApi() {}

    static void start(Context ctx) {
        HandlerThread t = new HandlerThread(TAG, Process.THREAD_PRIORITY_URGENT_DISPLAY);
        t.start();
        sH = new Handler(t.getLooper());
        sWake = ctx.getSystemService(PowerManager.class)
                .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "ArmorParts:lightStrobe");
        sWake.setReferenceCounted(false);
        IntentFilter f = new IntentFilter();
        f.addAction(ACTION);
        f.addAction(ACTION_OFF);
        // Exported: Tasker/MacroDroid/Key Mapper send plain implicit broadcasts.
        ctx.registerReceiver(RECEIVER, f, null, sH, Context.RECEIVER_EXPORTED);
    }

    private static final BroadcastReceiver RECEIVER = new BroadcastReceiver() {
        @Override
        public void onReceive(Context c, Intent i) {
            try {
                handle(i);
            } catch (RuntimeException e) {
                Log.w(TAG, "bad light command " + i.getExtras(), e);
            }
        }
    };

    private static void handle(Intent i) {
        if (ACTION_OFF.equals(i.getAction())) {
            allOff();
            return;
        }
        String light = str(i, "light", "").toLowerCase(Locale.ROOT);
        if ("flashlight".equals(light) || "torch".equals(light)) light = WHITE;
        String mode = str(i, "mode", "").toLowerCase(Locale.ROOT);
        boolean hasLevel = has(i, "level");
        int level = Math.max(0, Math.min(100, num(i, "level", 100)));
        boolean toggle = bool(i, "toggle", false);
        int onMs = num(i, "on_ms", 0);
        int offRaw = num(i, "off_ms", -1);
        int offMs = offRaw < 0 ? onMs : offRaw;
        int cycles = Math.max(0, num(i, "cycles", 0));
        Log.i(TAG, "light=" + light + " mode=" + mode + " level=" + (hasLevel ? level : "-")
                + " toggle=" + toggle + " on_ms=" + onMs + " off_ms=" + offMs + " cycles=" + cycles);

        switch (light) {
            case RED:
            case BLUE:
            case WHITE:
                break;
            case POLICE:
            case "redblue":
                police(level, toggle, onMs, Math.max(0, offRaw), cycles);
                return;
            case "all":
                if (level == 0 || toggle || !hasLevel) {
                    allOff();
                    return;
                }
                stopFor(RED);
                stopFor(BLUE);
                stopFor(WHITE);
                set(RED, level);
                set(BLUE, level);
                set(WHITE, level);
                return;
            default:
                Log.w(TAG, "unknown light '" + light + "' (red, blue, white, police, all)");
                return;
        }

        boolean wasStrobing = sRunning.contains(light);
        stopFor(light);

        if (!mode.isEmpty() && !"strobe".equals(mode)) {   // stock driver patterns
            if (toggle && isOn(light)) {
                set(light, 0);
            } else if (WHITE.equals(light) && ("blink".equals(mode) || "sos".equals(mode))) {
                Lights.flashlightModeNow("blink".equals(mode) ? 4 : 5);
            } else if (!WHITE.equals(light) && "flash".equals(mode)) {
                stopFor(RED.equals(light) ? BLUE : RED);
                Lights.ledPatternNow(RED.equals(light) ? 4 : 5);
            } else {
                Log.w(TAG, "mode '" + mode + "' not available for " + light);
            }
            return;
        }

        if (onMs > 0 || "strobe".equals(mode)) {
            if (toggle && wasStrobing) {
                set(light, 0);
                return;
            }
            if (onMs <= 0) onMs = 100;
            if (offMs <= 0) offMs = onMs;
            final String l = light;
            final int lvl = level == 0 ? 100 : level;
            List<Phase> p = new ArrayList<>();
            p.add(new Phase(() -> set(l, lvl), onMs));
            p.add(new Phase(() -> set(l, 0), offMs));
            run(light, p, cycles, () -> set(l, 0));
            return;
        }

        if (toggle) {
            set(light, isOn(light) ? 0 : (hasLevel && level > 0 ? level : 100));
        } else {
            set(light, level);
        }
    }

    /** Red/blue alternating: on_ms per colour, off_ms dark gap (default 0). */
    private static void police(int level, boolean toggle, int onMs, int offMs, int cycles) {
        boolean wasRunning = sRunning.contains(POLICE)
                || "RED_BLUE_FLASH".equals(Lights.ledMode());
        stopFor(POLICE);
        if (toggle && wasRunning) {
            set(RED, 0);
            set(BLUE, 0);
            return;
        }
        if (onMs <= 0) {
            Lights.ledPatternNow(6);       // stock 40 ms red/blue pattern in the kernel
            return;
        }
        int gap = offMs;
        final int lvl = level == 0 ? 100 : level;
        List<Phase> p = new ArrayList<>();
        p.add(new Phase(() -> { set(BLUE, 0); set(RED, lvl); }, onMs));
        if (gap > 0) p.add(new Phase(() -> set(RED, 0), gap));
        p.add(new Phase(() -> { set(RED, 0); set(BLUE, lvl); }, onMs));
        if (gap > 0) p.add(new Phase(() -> set(BLUE, 0), gap));
        run(POLICE, p, cycles, () -> { set(RED, 0); set(BLUE, 0); });
    }

    // ---- light primitives -----------------------------------------------------

    /** percent 0..100 for every light. */
    private static void set(String light, int percent) {
        if (WHITE.equals(light)) {
            Lights.flashlightNow(percent);
        } else {
            int raw = percent <= 0 ? 0 : percent >= 100 ? Lights.LED_MAX
                    : Math.max(1, Math.round(percent * Lights.LED_MAX / 100f));
            Lights.ledNow(RED.equals(light), raw);
        }
    }

    private static boolean isOn(String light) {
        if (WHITE.equals(light)) return Lights.flashlightOn();
        String m = Lights.ledMode();   // a stock flash pattern counts as on
        return Lights.ledOn(RED.equals(light)) || m.equals(light.toUpperCase(Locale.ROOT) + "_FLASH")
                || m.equals("RED_BLUE_FLASH");
    }

    private static void allOff() {
        for (String k : new ArrayList<>(sRunning)) stop(k);
        set(RED, 0);
        set(BLUE, 0);
        set(WHITE, 0);
    }

    // ---- sequencer --------------------------------------------------------------

    private static final class Phase {
        final Runnable action;
        final int ms;

        Phase(Runnable action, int ms) {
            this.action = action;
            this.ms = Math.max(MIN_MS, ms);
        }
    }

    /** Red/blue commands end the police sequence and vice versa. */
    private static void stopFor(String light) {
        stop(light);
        if (POLICE.equals(light)) {
            stop(RED);
            stop(BLUE);
        } else if (!WHITE.equals(light)) {
            stop(POLICE);
        }
    }

    private static void stop(String key) {
        if (sRunning.remove(key)) sH.removeCallbacksAndMessages(key);
        if (sRunning.isEmpty() && sWake.isHeld()) sWake.release();
    }

    /** Plays phases on a fixed timeline (no drift); cycles 0 = until stopped. */
    private static void run(String key, List<Phase> phases, int cycles, Runnable finish) {
        sRunning.add(key);
        if (!sWake.isHeld()) sWake.acquire();
        final long[] next = { SystemClock.uptimeMillis() };
        final int[] idx = { 0 };
        final int[] done = { 0 };
        Runnable step = new Runnable() {
            @Override
            public void run() {
                if (!sRunning.contains(key)) return;
                Phase ph = phases.get(idx[0]);
                ph.action.run();
                next[0] += ph.ms;
                idx[0]++;
                if (idx[0] == phases.size()) {
                    idx[0] = 0;
                    if (cycles > 0 && ++done[0] >= cycles) {
                        sH.postAtTime(() -> {
                            if (!sRunning.contains(key)) return;
                            stop(key);
                            finish.run();
                        }, key, next[0]);
                        return;
                    }
                }
                long now = SystemClock.uptimeMillis();
                if (next[0] < now) next[0] = now;   // late: skip ahead, never burst
                sH.postAtTime(this, key, next[0]);
            }
        };
        sH.postAtTime(step, key, next[0]);
    }

    // ---- extras: automation apps send numbers/booleans as strings too ------------

    private static boolean has(Intent i, String k) {
        Bundle b = i.getExtras();
        return b != null && b.get(k) != null;
    }

    private static String str(Intent i, String k, String d) {
        Bundle b = i.getExtras();
        Object o = b == null ? null : b.get(k);
        return o == null ? d : o.toString().trim();
    }

    private static int num(Intent i, String k, int d) {
        Bundle b = i.getExtras();
        Object o = b == null ? null : b.get(k);
        if (o instanceof Number) return ((Number) o).intValue();
        if (o instanceof String) {
            try {
                return Math.round(Float.parseFloat(((String) o).trim()));
            } catch (NumberFormatException e) {
                return d;
            }
        }
        return d;
    }

    private static boolean bool(Intent i, String k, boolean d) {
        Bundle b = i.getExtras();
        Object o = b == null ? null : b.get(k);
        if (o instanceof Boolean) return (Boolean) o;
        if (o instanceof Number) return ((Number) o).intValue() != 0;
        if (o instanceof String) {
            String s = ((String) o).trim().toLowerCase(Locale.ROOT);
            return s.equals("true") || s.equals("1") || s.equals("yes") || s.equals("on");
        }
        return d;
    }
}
