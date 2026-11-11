/*
 * Settings > Battery > Battery info: what the SH366003 pack gauge measures
 * (health against the rated capacity, the gauge's own estimate, cycles, both
 * cell voltages, current, temperatures, protection status). Refreshed every
 * 2 s while visible; the gauge is read on a background thread.
 */
package org.lieppos.armorparts;

import android.content.Context;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Looper;
import androidx.preference.Preference;
import androidx.preference.PreferenceCategory;
import androidx.preference.PreferenceFragmentCompat;
import androidx.preference.PreferenceScreen;
import com.android.settingslib.collapsingtoolbar.CollapsingToolbarBaseActivity;
import com.android.settingslib.widget.FooterPreference;

public class BatteryInfoActivity extends CollapsingToolbarBaseActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (savedInstanceState == null) {
            getSupportFragmentManager().beginTransaction()
                    .replace(com.android.settingslib.collapsingtoolbar.R.id.content_frame,
                            new BatteryInfoFragment())
                    .commit();
        }
    }

    public static class BatteryInfoFragment extends PreferenceFragmentCompat {
        private static final long REFRESH_MS = 2000;

        private final Handler mMain = new Handler(Looper.getMainLooper());
        private HandlerThread mThread;
        private Handler mIo;
        private boolean mResumed;

        private Preference mUnavailable;
        private PreferenceCategory mHealthCat, mNowCat, mStatusCat;
        private Preference mHealth, mGaugeSoh, mCycles, mMade;
        private Preference mCharge, mCurrent, mVoltage, mCells, mTemp;
        private Preference mProtection;

        private final Runnable mRead = new Runnable() {
            @Override
            public void run() {
                BatteryInfo info = BatteryInfo.read();
                mMain.post(() -> show(info));
                if (mResumed) mIo.postDelayed(this, REFRESH_MS);
            }
        };

        @Override
        public void onCreatePreferences(Bundle savedInstanceState, String rootKey) {
            Context c = getPreferenceManager().getContext();
            PreferenceScreen screen = getPreferenceManager().createPreferenceScreen(c);
            setPreferenceScreen(screen);

            mUnavailable = row(c, screen, R.string.batt_unavailable);
            mUnavailable.setSummary(R.string.batt_unavailable_summary);
            mUnavailable.setVisible(false);

            mHealthCat = category(c, screen, R.string.batt_cat_health);
            mHealth = row(c, mHealthCat, R.string.batt_health);
            mGaugeSoh = row(c, mHealthCat, R.string.batt_gauge_soh);
            mCycles = row(c, mHealthCat, R.string.batt_cycles);
            mMade = row(c, mHealthCat, R.string.batt_made);

            mNowCat = category(c, screen, R.string.batt_cat_now);
            mCharge = row(c, mNowCat, R.string.batt_charge);
            mCurrent = row(c, mNowCat, R.string.batt_current);
            mVoltage = row(c, mNowCat, R.string.batt_voltage);
            mCells = row(c, mNowCat, R.string.batt_cells);
            mTemp = row(c, mNowCat, R.string.batt_temp);

            mStatusCat = category(c, screen, R.string.batt_cat_status);
            mProtection = row(c, mStatusCat, R.string.batt_protection);

            FooterPreference footer = new FooterPreference(c);
            footer.setKey(FooterPreference.KEY_FOOTER);
            footer.setSummary(getString(R.string.batt_footer, BatteryInfo.RATED_MAH));
            screen.addPreference(footer);
        }

        private static PreferenceCategory category(Context c, PreferenceScreen screen, int title) {
            PreferenceCategory cat = new PreferenceCategory(c);
            cat.setTitle(title);
            cat.setPersistent(false);
            screen.addPreference(cat);
            return cat;
        }

        private static Preference row(Context c, androidx.preference.PreferenceGroup group,
                int title) {
            Preference p = new Preference(c);
            p.setTitle(title);
            p.setSelectable(false);
            p.setPersistent(false);
            p.setKey("batt_" + title);
            group.addPreference(p);
            return p;
        }

        @Override
        public void onResume() {
            super.onResume();
            mThread = new HandlerThread("BatteryInfo");
            mThread.start();
            mIo = new Handler(mThread.getLooper());
            mResumed = true;
            mIo.post(mRead);
        }

        @Override
        public void onPause() {
            super.onPause();
            mResumed = false;
            mIo.removeCallbacksAndMessages(null);
            mThread.quitSafely();
        }

        private void show(BatteryInfo info) {
            if (!isAdded()) return;
            boolean ok = info != null && info.has("fcc_mah");
            mUnavailable.setVisible(!ok);
            mHealthCat.setVisible(ok);
            mNowCat.setVisible(ok);
            mStatusCat.setVisible(ok);
            if (!ok) return;

            int fcc = info.num("fcc_mah", 0);
            mHealth.setSummary(getString(R.string.batt_health_value, info.healthPercent(),
                    fcc, BatteryInfo.RATED_MAH));
            mGaugeSoh.setSummary(getString(R.string.batt_gauge_soh_value, info.num("soh", 0)));
            mCycles.setSummary(String.valueOf(info.num("cycle_count", 0)));
            mMade.setSummary(info.str("manufacture_date"));

            mCharge.setSummary(getString(R.string.batt_charge_value, info.num("soc", 0),
                    info.num("rc_mah", 0)));
            int ma = info.num("current_ma", 0);
            mCurrent.setSummary(getString(ma > 0 ? R.string.batt_current_charging
                    : ma < 0 ? R.string.batt_current_discharging : R.string.batt_current_idle,
                    Math.abs(ma)));
            mVoltage.setSummary(getString(R.string.batt_mv, info.num("voltage_mv", 0)));
            if (info.has("cell1_mv")) {
                int c1 = info.num("cell1_mv", 0), c2 = info.num("cell2_mv", 0);
                int diff = Math.abs(c1 - c2);
                mCells.setSummary(getString(diff > BatteryInfo.CELL_IMBALANCE_MV
                        ? R.string.batt_cells_unbalanced : R.string.batt_cells_value,
                        c1, c2, diff));
            } else {
                mCells.setSummary(R.string.batt_not_read);
            }
            mTemp.setSummary(getString(R.string.batt_temp_value,
                    info.num("temp_dc", 0) / 10f, info.num("chip_temp_dc", 0) / 10f));

            if (info.has("safety_status")) {
                int sa = info.num("safety_alert", 0), ss = info.num("safety_status", 0);
                int pa = info.num("pf_alert", 0), pf = info.num("pf_status", 0);
                mProtection.setSummary(sa == 0 && ss == 0 && pa == 0 && pf == 0
                        ? getString(R.string.batt_protection_ok)
                        : getString(R.string.batt_protection_flags, sa, ss, pa, pf));
            } else {
                mProtection.setSummary(R.string.batt_not_read);
            }
        }
    }
}
