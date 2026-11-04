package org.lieppos.armorparts;

import android.app.Application;

/** Persistent process: starts the thermal camera guard, the uSmart notifier and the light intent API at boot. */
public class ArmorApp extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        ThermalGuard.start(this);
        UsmartNotifier.start(this);
        LightApi.start(this);
    }
}
