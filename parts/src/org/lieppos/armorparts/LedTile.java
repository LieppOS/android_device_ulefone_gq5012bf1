package org.lieppos.armorparts;

import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;

/** Red / blue light: off -> low -> max -> off. */
abstract class LedTile extends TileService {
    abstract boolean red();
    private int mState = Lights.OFF;

    @Override
    public void onStartListening() {
        mState = Lights.ledState(red());
        update();
    }

    @Override
    public void onClick() {
        mState = (mState + 1) % 3;
        Lights.setLed(red(), mState);
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
