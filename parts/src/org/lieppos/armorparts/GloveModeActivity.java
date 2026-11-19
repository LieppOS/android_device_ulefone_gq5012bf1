// SPDX-License-Identifier: Apache-2.0
package org.lieppos.armorparts;

import android.content.Context;
import android.os.Bundle;
import android.widget.Toast;

import androidx.preference.Preference;
import androidx.preference.PreferenceFragmentCompat;
import androidx.preference.PreferenceScreen;

import com.android.settingslib.collapsingtoolbar.CollapsingToolbarBaseActivity;
import com.android.settingslib.widget.FooterPreference;
import com.android.settingslib.widget.MainSwitchPreference;

/** Settings > Display > Glove sensitivity, using the existing Settings components. */
public class GloveModeActivity extends CollapsingToolbarBaseActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (savedInstanceState == null) {
            getSupportFragmentManager().beginTransaction()
                    .replace(com.android.settingslib.collapsingtoolbar.R.id.content_frame,
                            new GloveModeFragment())
                    .commit();
        }
    }

    public static class GloveModeFragment extends PreferenceFragmentCompat {
        private MainSwitchPreference mSwitch;
        private Preference mStatus;
        private boolean mBinding;
        private int mRequest;

        @Override
        public void onCreatePreferences(Bundle savedInstanceState, String rootKey) {
            Context context = getPreferenceManager().getContext();
            PreferenceScreen screen = getPreferenceManager().createPreferenceScreen(context);

            mSwitch = new MainSwitchPreference(context);
            mSwitch.setKey("glove_mode");
            mSwitch.setTitle(R.string.glove_mode_switch);
            mSwitch.setPersistent(false);
            mSwitch.setEnabled(false);
            mSwitch.setOnPreferenceChangeListener((preference, value) -> {
                if (mBinding) return true;
                mSwitch.setEnabled(false);
                int request = ++mRequest;
                GloveMode.setEnabled(requireContext(), (Boolean) value, result -> {
                    if (getContext() == null || request != mRequest) return;
                    show(result);
                    if (result.error != null) {
                        Toast.makeText(requireContext(), R.string.glove_mode_error,
                                Toast.LENGTH_LONG).show();
                    }
                });
                // The accepted driver mode, not an optimistic click, owns the switch state.
                return false;
            });
            screen.addPreference(mSwitch);

            mStatus = new Preference(context);
            mStatus.setKey("glove_mode_status");
            mStatus.setTitle(R.string.glove_mode_status);
            mStatus.setIcon(R.drawable.ic_glove);
            mStatus.setSelectable(false);
            mStatus.setPersistent(false);
            mStatus.setSummary(R.string.glove_mode_checking);
            screen.addPreference(mStatus);

            FooterPreference footer = new FooterPreference(context);
            footer.setKey(FooterPreference.KEY_FOOTER);
            footer.setSummary(R.string.glove_mode_note);
            screen.addPreference(footer);
            setPreferenceScreen(screen);
        }

        @Override
        public void onResume() {
            super.onResume();
            mSwitch.setEnabled(false);
            int request = ++mRequest;
            GloveMode.read(result -> {
                if (getContext() != null && request == mRequest) show(result);
            });
        }

        @Override
        public void onPause() {
            ++mRequest; // Ignore old UI callbacks; a user-requested write still completes.
            super.onPause();
        }

        private void show(GloveMode.Result result) {
            mBinding = true;
            mSwitch.setChecked(Boolean.TRUE.equals(result.enabled));
            mBinding = false;
            mSwitch.setEnabled(result.enabled != null);
            mStatus.setSummary(result.enabled == null ? R.string.glove_mode_unavailable
                    : result.enabled ? R.string.glove_mode_confirmed_on
                    : R.string.glove_mode_confirmed_off);
        }
    }
}
