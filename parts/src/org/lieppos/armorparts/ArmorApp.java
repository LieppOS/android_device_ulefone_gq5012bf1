package org.lieppos.armorparts;

import android.app.Application;

/**
 * Persistent process: starts the thermal camera guard, the uSmart notifier, the light intent API
 * the battery saver CPU cap and the charge limit at boot.
 */
public class ArmorApp extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        ThermalGuard.start(this);
        UsmartNotifier.start(this);
        LightApi.start(this);
        PowerSaveCap.start(this);
        ChargeLimit.start(this);
    }
}
