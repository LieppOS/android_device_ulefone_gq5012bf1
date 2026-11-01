package org.lieppos.armorparts;

import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;

/** Super flashlight: off -> lowest -> maximum -> off. */
public class FlashlightTile extends TileService {
    private int mState = Lights.OFF;

    @Override
    public void onStartListening() {
        mState = Lights.flashlightState();
        update();
    }

    @Override
    public void onClick() {
        int next = (mState + 1) % 3;
        Lights.setFlashlight(mState, next);
        mState = next;
        update();
    }

    private void update() {
        Tile t = getQsTile();
        if (t == null) return;
        t.setState(mState == Lights.OFF ? Tile.STATE_INACTIVE : Tile.STATE_ACTIVE);
        t.setSubtitle(getString(mState == Lights.LOW ? R.string.state_low
                : mState == Lights.MAX ? R.string.state_max : R.string.state_off));
        t.updateTile();
    }
}
