// SPDX-License-Identifier: Apache-2.0
package org.lieppos.armorparts;

import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;
import android.widget.Toast;

/** Optional tile; always reads the controller rather than assuming the saved choice. */
public class GloveModeTile extends TileService {
    private boolean mBusy;
    private int mRequest;

    @Override
    public void onStartListening() {
        mBusy = true;
        int request = ++mRequest;
        GloveMode.read(result -> {
            if (request != mRequest) return;
            mBusy = false;
            update(result);
        });
    }

    @Override
    public void onStopListening() {
        ++mRequest;
        mBusy = false;
    }

    @Override
    public void onClick() {
        if (mBusy) return;
        if (isLocked()) {
            unlockAndRun(this::change);
        } else {
            change();
        }
    }

    private void change() {
        if (mBusy) return;
        mBusy = true;
        int request = ++mRequest;
        GloveMode.toggle(this, result -> {
            if (request != mRequest) return;
            mBusy = false;
            update(result);
            if (result.error != null) {
                Toast.makeText(this, R.string.glove_mode_error, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void update(GloveMode.Result result) {
        Tile tile = getQsTile();
        if (tile == null) return;
        tile.setState(result.enabled == null ? Tile.STATE_UNAVAILABLE
                : result.enabled ? Tile.STATE_ACTIVE : Tile.STATE_INACTIVE);
        tile.setSubtitle(getString(result.enabled == null ? R.string.glove_mode_tile_unavailable
                : result.enabled ? R.string.glove_mode_on : R.string.state_off));
        tile.updateTile();
    }
}
