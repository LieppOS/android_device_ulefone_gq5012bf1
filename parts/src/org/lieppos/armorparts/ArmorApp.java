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
        // Cleanup only: persistent-process death can leave an AMS foreground record.
        PrecisionGnssService.resetAfterProcessStart(this);
        ThermalGuard.start(this);
        UsmartNotifier.start(this);
        LightApi.start(this);
        PowerSaveCap.start(this);
        ChargeLimit.start(this);
        GloveMode.restore(this);
    }
}
