/*
 * Settings > Battery > Charge limit (injected through the
 * com.android.settings.category.ia.battery tile category). Built from the same
 * SettingsLib pieces as Settings' own pages: collapsing toolbar, main switch
 * bar, slider and footer. The charging logic lives in ChargeLimit.
 */
package org.lieppos.armorparts;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.view.View;
import android.view.ViewParent;
import android.widget.TextView;

import androidx.preference.Preference;
import androidx.preference.PreferenceFragmentCompat;
import androidx.preference.PreferenceScreen;
import androidx.preference.SwitchPreferenceCompat;

import com.android.settingslib.collapsingtoolbar.CollapsingToolbarBaseActivity;
import com.android.settingslib.widget.FooterPreference;
import com.android.settingslib.widget.MainSwitchPreference;
import com.android.settingslib.widget.SliderPreference;

public class ChargeLimitActivity extends CollapsingToolbarBaseActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (savedInstanceState == null) {
            getSupportFragmentManager().beginTransaction()
                    .replace(com.android.settingslib.collapsingtoolbar.R.id.content_frame,
                            new ChargeLimitFragment())
                    .commit();
        }
    }

    public static class ChargeLimitFragment extends PreferenceFragmentCompat {
        private MainSwitchPreference mSwitch;
        private SliderPreference mSlider;
        private Preference mStatus;
        private SwitchPreferenceCompat mHeat;
        private FooterPreference mFooter;

        private final BroadcastReceiver mBattery = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                // ArmorApp's receiver (registered at boot) has already updated ChargeLimit.
                refresh();
            }
        };

        @Override
        public void onCreatePreferences(Bundle savedInstanceState, String rootKey) {
            Context context = getPreferenceManager().getContext();
            PreferenceScreen screen = getPreferenceManager().createPreferenceScreen(context);

            mSwitch = new MainSwitchPreference(context);
            mSwitch.setKey("charge_limit_enabled");
            mSwitch.setTitle(R.string.charge_limit_switch);
            mSwitch.setPersistent(false);
            mSwitch.setChecked(ChargeLimit.isEnabled(context));
            mSwitch.setOnPreferenceChangeListener((p, value) -> {
                ChargeLimit.setEnabled(requireContext(), (Boolean) value);
                refresh();
                return true;
            });
            screen.addPreference(mSwitch);

            mSlider = new SliderPreference(context);
            mSlider.setKey("charge_limit_level");
            mSlider.setPersistent(false);
            mSlider.setMin(ChargeLimit.MIN_LIMIT);
            mSlider.setMax(ChargeLimit.MAX_LIMIT);
            mSlider.setSliderIncrement(ChargeLimit.STEP);
            mSlider.setTickVisible(true);
            mSlider.setUpdatesContinuously(false);
            mSlider.setHapticFeedbackMode(SliderPreference.HAPTIC_FEEDBACK_MODE_ON_TICKS);
            mSlider.setValue(ChargeLimit.getLimit(context));
            mSlider.setTitle(getString(R.string.charge_limit_value, ChargeLimit.getLimit(context)));
            // Live title while dragging; the limit is applied when the finger lifts.
            // Write the TextView directly: Preference.setTitle() would rebind the row
            // (resetting the thumb mid-drag, or crashing if called during layout).
            mSlider.setExtraChangeListener((slider, value, fromUser) -> {
                if (!fromUser) return;
                TextView title = findTitle(slider);
                if (title != null) {
                    title.setText(getString(R.string.charge_limit_value, (int) value));
                }
            });
            // Runs before the slider stores the value, so pass the new value on.
            mSlider.setOnPreferenceChangeListener((p, value) -> {
                ChargeLimit.setLimit(requireContext(), (Integer) value);
                refresh();
                showLimit((Integer) value);
                return true;
            });
            screen.addPreference(mSlider);

            mStatus = new Preference(context);
            mStatus.setKey("charge_limit_status");
            mStatus.setSelectable(false);
            mStatus.setPersistent(false);
            screen.addPreference(mStatus);

            // Independent of the limit switch above.
            mHeat = new SwitchPreferenceCompat(context);
            mHeat.setKey("charge_heat_pause");
            mHeat.setPersistent(false);
            mHeat.setTitle(R.string.heat_pause_title);
            mHeat.setSummary(getString(R.string.heat_pause_summary,
                    ChargeLimit.HOT_PAUSE_DC / 10, ChargeLimit.HOT_RESUME_DC / 10));
            mHeat.setChecked(ChargeLimit.isHeatPauseEnabled(context));
            mHeat.setOnPreferenceChangeListener((p, value) -> {
                ChargeLimit.setHeatPauseEnabled(requireContext(), (Boolean) value);
                refresh();
                return true;
            });
            screen.addPreference(mHeat);

            mFooter = new FooterPreference(context);
            mFooter.setKey(FooterPreference.KEY_FOOTER);
            screen.addPreference(mFooter);

            setPreferenceScreen(screen);
            refresh();
        }

        @Override
        public void onResume() {
            super.onResume();
            requireContext().registerReceiver(mBattery,
                    new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            refresh();
        }

        @Override
        public void onPause() {
            super.onPause();
            requireContext().unregisterReceiver(mBattery);
        }

        /** The android:id/title TextView of the preference row containing {@code v}. */
        private static TextView findTitle(View v) {
            for (ViewParent p = v.getParent(); p instanceof View; p = p.getParent()) {
                View t = ((View) p).findViewById(android.R.id.title);
                if (t instanceof TextView) return (TextView) t;
            }
            return null;
        }

        private void showLimit(int limit) {
            mSlider.setTitle(getString(R.string.charge_limit_value, limit));
            if (limit >= ChargeLimit.MAX_LIMIT) {
                mFooter.setSummary(R.string.charge_limit_note_full);
            } else {
                mFooter.setSummary(getString(R.string.charge_limit_note,
                        limit - ChargeLimit.RESUME_GAP));
            }
        }

        private void refresh() {
            if (mSwitch == null) return;
            Context context = requireContext();
            boolean enabled = ChargeLimit.isEnabled(context);
            int limit = ChargeLimit.getLimit(context);
            mSlider.setEnabled(enabled);
            showLimit(limit);

            int level = ChargeLimit.getLevel();
            mStatus.setVisible(level >= 0);
            mStatus.setIcon(R.drawable.ic_charge_limit);
            if (ChargeLimit.isPaused() && ChargeLimit.isHot()) {
                mStatus.setTitle(getString(R.string.heat_pause_status_title,
                        ChargeLimit.getTemp() / 10.0f));
                mStatus.setSummary(getString(R.string.heat_pause_status_summary,
                        ChargeLimit.HOT_RESUME_DC / 10));
            } else if (!enabled) {
                mStatus.setTitle(R.string.charge_limit_status_off);
                mStatus.setSummary(null);
            } else if (ChargeLimit.isPaused()) {
                mStatus.setTitle(getString(R.string.charge_limit_status_paused_title, level));
                mStatus.setSummary(R.string.charge_limit_status_paused_summary);
            } else if (ChargeLimit.isPlugged()) {
                mStatus.setTitle(getString(R.string.charge_limit_status_charging, level, limit));
                mStatus.setSummary(null);
            } else {
                mStatus.setTitle(getString(R.string.charge_limit_status_unplugged, level));
                mStatus.setSummary(null);
            }
        }
    }
}
