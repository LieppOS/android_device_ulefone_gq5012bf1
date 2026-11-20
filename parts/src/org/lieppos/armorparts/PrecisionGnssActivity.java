// SPDX-License-Identifier: Apache-2.0
package org.lieppos.armorparts;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Toast;
import androidx.preference.Preference;
import androidx.preference.PreferenceFragmentCompat;
import androidx.preference.PreferenceScreen;
import com.android.settingslib.collapsingtoolbar.CollapsingToolbarBaseActivity;
import com.android.settingslib.widget.FooterPreference;
import com.android.settingslib.widget.MainSwitchPreference;

/** Read-only on entry: only a user's switch starts the bounded request. */
public final class PrecisionGnssActivity extends CollapsingToolbarBaseActivity {
    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (savedInstanceState == null) getSupportFragmentManager().beginTransaction()
                .replace(com.android.settingslib.collapsingtoolbar.R.id.content_frame, new Page()).commit();
    }
    public static final class Page extends PreferenceFragmentCompat {
        private final Handler handler = new Handler(Looper.getMainLooper());
        private MainSwitchPreference toggle;
        private Preference status;
        private boolean binding;
        private final BroadcastReceiver changes = new BroadcastReceiver() {
            @Override public void onReceive(Context context, Intent intent) { refresh(); }
        };
        private final Runnable tick = new Runnable() {
            @Override public void run() { refresh(); handler.postDelayed(this, 1000); }
        };
        @Override public void onCreatePreferences(Bundle savedInstanceState, String rootKey) {
            Context context = getPreferenceManager().getContext();
            PreferenceScreen screen = getPreferenceManager().createPreferenceScreen(context);
            toggle = new MainSwitchPreference(context);
            toggle.setKey("precision_gnss_session");
            toggle.setPersistent(false);
            toggle.setTitle(R.string.precision_gnss_switch);
            toggle.setOnPreferenceChangeListener((preference, value) -> {
                if (binding) return true;
                toggle.setEnabled(false);
                try {
                    if ((Boolean) value) PrecisionGnssService.start(requireContext());
                    else PrecisionGnssService.stop(requireContext());
                } catch (RuntimeException failure) {
                    Toast.makeText(requireContext(), R.string.precision_gnss_failed, Toast.LENGTH_LONG).show();
                    refresh();
                }
                return false;
            });
            screen.addPreference(toggle);
            status = new Preference(context);
            status.setKey("precision_gnss_status");
            status.setPersistent(false);
            status.setSelectable(false);
            status.setTitle(R.string.precision_gnss_request_status);
            status.setIcon(R.drawable.ic_precision_gnss);
            screen.addPreference(status);
            FooterPreference footer = new FooterPreference(context);
            footer.setKey(FooterPreference.KEY_FOOTER);
            footer.setSummary(R.string.precision_gnss_note);
            screen.addPreference(footer);
            setPreferenceScreen(screen);
        }
        @Override public void onResume() {
            super.onResume();
            IntentFilter filter = new IntentFilter(PrecisionGnssService.CHANGED);
            filter.addAction(android.location.LocationManager.PROVIDERS_CHANGED_ACTION);
            requireContext().registerReceiver(changes, filter, Context.RECEIVER_NOT_EXPORTED);
            handler.post(tick);
        }
        @Override public void onPause() {
            handler.removeCallbacksAndMessages(null);
            requireContext().unregisterReceiver(changes);
            super.onPause();
        }
        private void refresh() {
            Context context = getContext();
            if (context == null || toggle == null) return;
            PrecisionGnssService.Snapshot state = PrecisionGnssService.snapshot;
            binding = true;
            toggle.setChecked(state.requested());
            binding = false;
            toggle.setEnabled(!state.stopping()
                    && (state.requested() || (PrecisionGnssService.readyToStart()
                            && PrecisionGnssService.locationEnabled(context))));
            status.setSummary(!state.requested() && !PrecisionGnssService.locationEnabled(context)
                    ? getString(R.string.precision_gnss_location_off) : PrecisionGnssService.summary(context));
        }
    }
}
