// SPDX-License-Identifier: Apache-2.0
package org.lieppos.armorparts;

import android.location.SettingInjectorService;

/** Location > Location services summary only. Reading it never starts GNSS. */
public final class PrecisionGnssSettingsService extends SettingInjectorService {
    public PrecisionGnssSettingsService() { super("PrecisionGnssSettings"); }
    @Override protected String onGetSummary() { return PrecisionGnssService.summary(this); }
    @Override protected boolean onGetEnabled() {
        return PrecisionGnssService.snapshot.requested() || (PrecisionGnssService.readyToStart()
                && PrecisionGnssService.locationEnabled(this));
    }
}
