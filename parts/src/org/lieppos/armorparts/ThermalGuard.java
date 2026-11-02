/*
 * Built-in Tiny2-C thermal camera support for ThermoVue (com.energy.tc2c).
 *
 * ThermoVue powers the camera itself: "1" to yft_tiny2c_usb/tiny2c_usb_mode
 * (1.8 V / 3.3 V / IO rails) then yft_extcon/tiny2c_mode (USB host role), and
 * "0" to both on a normal exit. Stock services.jar wrote 0 to both nodes when
 * the app died; without that a crash or force-stop leaves the camera powered
 * and the USB port stuck in host mode (no adb/MTP over the cable). This does
 * the same from the persistent ArmorParts process.
 *
 * It also grants ThermoVue "all files access" once (if still at the default):
 * it saves captures to Pictures/thermo_tc2c with plain file paths.
 */
package org.lieppos.armorparts;

import android.app.ActivityManager;
import android.app.AppOpsManager;
import android.app.IProcessObserver;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.RemoteException;
import android.util.Log;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;

final class ThermalGuard {
    private static final String TAG = "ArmorThermal";
    static final String PKG = "com.energy.tc2c";
    private static final String RAILS = "/sys/devices/platform/yft_tiny2c_usb/tiny2c_usb_mode";
    private static final String ROUTE = "/sys/class/yft_extcon/tiny2c_mode";

    private static Handler sIo;
    private static int sUid = -1;
    private static Context sContext;

    private ThermalGuard() {}

    static void start(Context context) {
        sContext = context.getApplicationContext();
        try {
            sUid = sContext.getPackageManager().getPackageUid(PKG, 0);
        } catch (PackageManager.NameNotFoundException e) {
            Log.i(TAG, PKG + " not installed");
            return;
        }
        HandlerThread t = new HandlerThread(TAG);
        t.start();
        sIo = new Handler(t.getLooper());
        sIo.post(ThermalGuard::grantAllFilesAccess);
        try {
            ActivityManager.getService().registerProcessObserver(OBSERVER);
        } catch (RemoteException | SecurityException e) {
            Log.e(TAG, "registerProcessObserver failed", e);
        }
        // Covers a crash of ThermoVue while ArmorParts itself was restarting.
        sIo.post(ThermalGuard::cleanupIfOrphaned);
    }

    private static final IProcessObserver OBSERVER = new IProcessObserver.Stub() {
        @Override
        public void onProcessStarted(int pid, int processUid, int packageUid,
                String packageName, String processName) {}

        @Override
        public void onForegroundActivitiesChanged(int pid, int uid, boolean fg) {}

        @Override
        public void onForegroundServicesChanged(int pid, int uid, int serviceTypes) {}

        @Override
        public void onProcessDied(int pid, int uid) {
            if (uid == sUid) sIo.postDelayed(ThermalGuard::cleanupIfOrphaned, 500);
        }
    };

    private static boolean appRunning() {
        ActivityManager am = sContext.getSystemService(ActivityManager.class);
        for (ActivityManager.RunningAppProcessInfo p : am.getRunningAppProcesses()) {
            if (p.uid == sUid) return true;
        }
        return false;
    }

    /** Power the camera off and release the USB host role, but only if it was left on. */
    private static void cleanupIfOrphaned() {
        if (appRunning()) return;
        boolean railsOn = read(RAILS).contains("=1");
        boolean routeOn = "1".equals(read(ROUTE));
        if (!railsOn && !routeOn) return;
        Log.w(TAG, PKG + " died with the thermal camera on; powering it off");
        write(RAILS, "0");
        write(ROUTE, "0");
    }

    private static void grantAllFilesAccess() {
        AppOpsManager ops = sContext.getSystemService(AppOpsManager.class);
        int mode = ops.unsafeCheckOpRawNoThrow(AppOpsManager.OPSTR_MANAGE_EXTERNAL_STORAGE, sUid, PKG);
        if (mode == AppOpsManager.MODE_DEFAULT) {
            ops.setUidMode(AppOpsManager.OPSTR_MANAGE_EXTERNAL_STORAGE, sUid, AppOpsManager.MODE_ALLOWED);
            Log.i(TAG, "granted all files access to " + PKG);
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

    private static void write(String path, String value) {
        try (FileWriter w = new FileWriter(path)) {
            w.write(value);
        } catch (IOException e) {
            Log.w(TAG, "write " + path + " failed: " + e);
        }
    }
}
