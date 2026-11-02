// SPDX-License-Identifier: Apache-2.0
package com.android.nfc.lab;

import android.app.Service;
import android.content.Intent;
import android.nfc.NfcAdapter;
import android.os.*;
import org.lieppos.nfclab.ipc.ILabDiagnostics;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.function.Supplier;

/** Runs in the NFC owner process. Snapshot only: never opens the controller or issues a command. */
public final class LabDiagnosticsService extends Service {
    public static final String PERMISSION = "org.lieppos.permission.NFC_LAB_DIAGNOSTICS";
    private static volatile Supplier<int[]> source;
    public static void attachSource(Supplier<int[]> currentOwnerCache) { source = currentOwnerCache; }
    private final ILabDiagnostics.Stub api = new ILabDiagnostics.Stub() {
        @Override public Bundle snapshot() {
            enforceCallingOrSelfPermission(PERMISSION, "NFC Lab diagnostics requires the NFC signing identity");
            Bundle b = new Bundle(); b.putInt("schema_version", 1); b.putString("source", "NFC owner; cached normal initialization only");
            NfcAdapter a = NfcAdapter.getDefaultAdapter(LabDiagnosticsService.this);
            b.putString("adapter_state", a == null ? "absent" : a.isEnabled() ? "enabled" : "disabled");
            b.putString("driver_version", readDriverVersion());
            for (String key : new String[] {"controller_identity", "nci_capabilities", "routing", "secure_elements", "irq", "power", "recovery", "type4_nfcee", "type4_lifecycle", "cache_generation"}) b.putString(key, "UNKNOWN: no verified cached observation");
            PowerManager power = getSystemService(PowerManager.class);
            b.putString("power", power == null ? "UNKNOWN" : "screen interactive=" + power.isInteractive() + "; autonomous CE power UNKNOWN");
            Supplier<int[]> current = source;
            if (current != null) {
                int[] v;
                try { v = current.get(); } catch (IllegalStateException notReady) { return b; }
                if (v == null || v.length != 40 || v[0] != 1) return b;
                b.putString("cache_generation", Integer.toString(v[1]) + "; observed framed packets=" + v[31]);
                if (v[34] >= 0) b.putString("type4_nfcee", v[34] == 1 ? "CONFIGURED in owner; operational service separately build-disabled by default; RF unverified" : "DISABLED by effective owner configuration");
                b.putString("type4_lifecycle", v[35] < 0 ? "UNKNOWN: no completed Type4 operation observed"
                        : (v[35] == 1 ? "DEGRADED: last cleanup left RF restoration unverified; no automatic recovery" : "CLEAN at last cleanup; not a claim about current RF state")
                        + "; degraded cleanups=" + (v[36] < 0 ? "UNKNOWN" : Integer.toString(v[36])));
                if (v[4] >= 0) b.putString("controller_identity", "CACHED ST layout: hw=" + hex(v[4]) + ", revision=" + hex(v[5]) + ", firmware=" + hex(v[6]) + ", loader=" + hex(v[7]) + ", customer=" + hex(v[8]));
                if (v[2] >= 0) {
                    StringBuilder caps = new StringBuilder("CACHED NCI=" + hex(v[2]) + "; CORE_INIT status=" + hex(v[9]) + "; interfaces=");
                    if (v[10] < 0 || v[10] > 16) caps.append("UNKNOWN");
                    else for (int i = 0; i < v[10]; i++) caps.append(hex(v[13 + i])).append(' ');
                    caps.append("; routing capacity=").append(v[11]).append("; control payload=").append(v[12]);
                    b.putString("nci_capabilities", caps.toString());
                }
                b.putString("recovery", "Recovery invocation/result UNKNOWN; reset-notification generation=" + v[1]);
            }
            // getRoutingTable(), NFCEE queries and recovery methods are intentionally NOT called.
            return b;
        }
    };
    private static String hex(int n) { return n < 0 ? "UNKNOWN" : "0x" + Integer.toHexString(n); }
    private static String readDriverVersion() {
        try {
            byte[] bytes = Files.readAllBytes(Paths.get("/sys/module/st21nfc/version"));
            if (bytes.length > 64) return "UNKNOWN: unexpected sysfs value";
            String value = new String(bytes, StandardCharsets.US_ASCII).trim();
            return value.matches("[0-9.]{1,32}") ? value : "UNKNOWN: unrecognized driver version";
        } catch (java.io.IOException | SecurityException unavailable) { return "UNKNOWN: sysfs read not permitted/available"; }
    }
    @Override public IBinder onBind(Intent intent) {
        // AMS enforces the manifest permission at bind time; each transaction
        // rechecks the remote caller. onBind itself runs as the service UID.
        return api;
    }
}
