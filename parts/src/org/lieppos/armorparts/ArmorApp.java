package org.lieppos.armorparts;

import android.app.Application;

/** Persistent process: starts the thermal camera guard and the uSmart notifier at boot. */
public class ArmorApp extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        ThermalGuard.start(this);
        UsmartNotifier.start(this);
    }
}
