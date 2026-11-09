/*
 * Settings > Battery > Charge limit (injected through the
 * com.android.settings.category.ia.battery tile category).
 */
package org.lieppos.armorparts;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.view.MenuItem;
import android.view.View;
import android.widget.SeekBar;
import android.widget.Switch;
import android.widget.TextView;

public class ChargeLimitActivity extends Activity {
    private Switch mSwitch;
    private SeekBar mSeek;
    private TextView mLimitText;
    private TextView mStatus;
    private TextView mNote;

    private final BroadcastReceiver mBattery = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            // ArmorApp's receiver runs first (same process, registered at boot).
            refresh();
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.charge_limit);
        if (getActionBar() != null) getActionBar().setDisplayHomeAsUpEnabled(true);

        mSwitch = findViewById(R.id.charge_limit_switch);
        mSeek = findViewById(R.id.charge_limit_seek);
        mLimitText = findViewById(R.id.charge_limit_value);
        mStatus = findViewById(R.id.charge_limit_status);
        mNote = findViewById(R.id.charge_limit_note);

        mSeek.setMax((ChargeLimit.MAX_LIMIT - ChargeLimit.MIN_LIMIT) / ChargeLimit.STEP);
        mSeek.setProgress((ChargeLimit.getLimit(this) - ChargeLimit.MIN_LIMIT) / ChargeLimit.STEP);
        mSwitch.setChecked(ChargeLimit.isEnabled(this));

        findViewById(R.id.charge_limit_switch_row).setOnClickListener(v -> mSwitch.toggle());
        mSwitch.setOnCheckedChangeListener((b, checked) -> {
            ChargeLimit.setEnabled(this, checked);
            refresh();
        });
        mSeek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                showLimit(limitFor(progress));
            }

            @Override
            public void onStartTrackingTouch(SeekBar seekBar) {}

            @Override
            public void onStopTrackingTouch(SeekBar seekBar) {
                ChargeLimit.setLimit(ChargeLimitActivity.this, limitFor(seekBar.getProgress()));
                refresh();
            }
        });
        refresh();
    }

    @Override
    protected void onResume() {
        super.onResume();
        registerReceiver(mBattery, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        refresh();
    }

    @Override
    protected void onPause() {
        super.onPause();
        unregisterReceiver(mBattery);
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        if (item.getItemId() == android.R.id.home) {
            finish();
            return true;
        }
        return super.onOptionsItemSelected(item);
    }

    private static int limitFor(int progress) {
        return ChargeLimit.MIN_LIMIT + progress * ChargeLimit.STEP;
    }

    private void showLimit(int limit) {
        mLimitText.setText(getString(R.string.charge_limit_value, limit));
        if (limit >= ChargeLimit.MAX_LIMIT) {
            mNote.setText(R.string.charge_limit_note_full);
        } else {
            mNote.setText(getString(R.string.charge_limit_note, limit - ChargeLimit.RESUME_GAP));
        }
    }

    private void refresh() {
        boolean enabled = ChargeLimit.isEnabled(this);
        int limit = ChargeLimit.getLimit(this);
        mSeek.setEnabled(enabled);
        mLimitText.setEnabled(enabled);
        showLimit(limitFor(mSeek.getProgress()));

        int level = ChargeLimit.getLevel();
        String state;
        if (!enabled) {
            state = getString(R.string.charge_limit_status_off);
        } else if (ChargeLimit.isPaused()) {
            state = getString(R.string.charge_limit_status_paused, level);
        } else if (ChargeLimit.isPlugged()) {
            state = getString(R.string.charge_limit_status_charging, level, limit);
        } else {
            state = getString(R.string.charge_limit_status_unplugged, level);
        }
        mStatus.setText(state);
        mStatus.setVisibility(level < 0 ? View.GONE : View.VISIBLE);
    }
}
