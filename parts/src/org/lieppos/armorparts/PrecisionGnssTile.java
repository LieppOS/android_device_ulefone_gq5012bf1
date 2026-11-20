// SPDX-License-Identifier: Apache-2.0
package org.lieppos.armorparts;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Handler;
import android.os.Looper;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;
import android.widget.Toast;

/** Optional user-added tile. Starting requires unlock; stopping is always safe. */
public final class PrecisionGnssTile extends TileService {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean listening;
    private final BroadcastReceiver changes = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) { update(); }
    };
    private final Runnable tick = new Runnable() {
        @Override public void run() { if (listening) { update(); handler.postDelayed(this, 1000); } }
    };
    @Override public void onStartListening() {
        if (listening) return;
        listening = true;
        IntentFilter filter = new IntentFilter(PrecisionGnssService.CHANGED);
        filter.addAction(android.location.LocationManager.PROVIDERS_CHANGED_ACTION);
        registerReceiver(changes, filter, Context.RECEIVER_NOT_EXPORTED);
        handler.post(tick);
    }
    @Override public void onStopListening() {
        if (listening) unregisterReceiver(changes);
        listening = false;
        handler.removeCallbacksAndMessages(null);
    }
    @Override public void onDestroy() { onStopListening(); super.onDestroy(); }
    @Override public void onClick() {
        if (PrecisionGnssService.snapshot.requested()) {
            change(false);
        } else if (isLocked()) {
            unlockAndRun(() -> {
                // Read again after unlocking, never invert a stale tile state.
                if (!PrecisionGnssService.snapshot.requested()) change(true);
            });
        } else change(true);
    }
    private void change(boolean start) {
        try {
            if (start) PrecisionGnssService.start(this);
            else PrecisionGnssService.stop(this);
        } catch (RuntimeException failure) {
            Toast.makeText(this, R.string.precision_gnss_failed, Toast.LENGTH_LONG).show();
        }
        update();
    }
    private void update() {
        Tile tile = getQsTile();
        if (tile == null) return;
        PrecisionGnssService.Snapshot state = PrecisionGnssService.snapshot;
        tile.setState(state.requested() ? Tile.STATE_ACTIVE
                : PrecisionGnssService.readyToStart() && PrecisionGnssService.locationEnabled(this)
                        ? Tile.STATE_INACTIVE : Tile.STATE_UNAVAILABLE);
        tile.setSubtitle(PrecisionGnssService.summary(this));
        tile.updateTile();
    }
}
