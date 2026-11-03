// SPDX-License-Identifier: Apache-2.0
package com.android.nfc.lab;

import java.util.Arrays;

/** Pure ownership/bounds policy; only the NFC-owner adapter supplies the real transport. */
public final class Type4LabController {
    public interface Port {
        boolean ready(); // Cached flags only, must not trigger initialization.
        byte[] read(int fileId);
        int write(int fileId, byte[] message);
        default Object mutex() { return this; }
    }
    private final Port port;
    private long token, deadline;
    private int uid = -1;
    private boolean writes, faulted;
    public Type4LabController(Port port) { this.port = port; }
    public synchronized void begin(int caller, long nonce, long now, boolean writeConsent) {
        if (faulted || !port.ready()) throw new IllegalStateException("Type4 backend unavailable/faulted");
        if (nonce == 0 || caller < 0 || (token != 0 && now <= deadline)) throw new IllegalStateException("Invalid or busy session");
        token = nonce; uid = caller; writes = writeConsent; deadline = now + 60000;
    }
    private void check(int caller, long nonce, long now) {
        // Identity first: a foreign or forged caller is rejected without changing
        // any session state, so it cannot fault or close someone else's session.
        if (faulted || token == 0 || nonce != token || caller != uid) throw new IllegalStateException("No current approved Type4 session");
        if (now > deadline) { cancel(); throw new IllegalStateException("Approved Type4 session expired"); }
        // Backend unavailability (including a degraded native lifecycle) is a
        // fail-stop condition, not a retryable error: close the session too.
        if (!port.ready()) { faulted = true; cancel(); throw new IllegalStateException("Type4 backend unavailable or lifecycle degraded; session closed"); }
    }
    public synchronized void end(int caller, long nonce) {
        if (caller != uid || nonce != token) throw new SecurityException("Not the session owner");
        cancel();
    }
    public synchronized void cancel() { token = 0; uid = -1; writes = false; }
    private int capacity(boolean requireWrite) {
        byte[] c = port.read(0xE103);
        if (c == null || c.length < 15 || c.length > 255 || c[0] != 0 || (c[1] & 255) < 15 || (c[1] & 255) > c.length
                || c[2] != 0x20 || c[7] != 4 || c[8] != 6 || (c[9] & 255) != 0xE1 || c[10] != 4 || c[13] != 0 || (requireWrite && c[14] != 0))
            throw new IllegalStateException("Unrecognized/read-protected Type4 CC or write denied");
        int size = ((c[11] & 255) << 8) | (c[12] & 255);
        if (size < 2 || size > 8192) throw new IllegalStateException("Unvalidated Type4 capacity");
        return size - 2;
    }
    public synchronized byte[] read(int caller, long nonce, long now) {
        check(caller, nonce, now);
        synchronized (port.mutex()) {
            try {
                int maximum = capacity(false); byte[] value = port.read(0xE104);
                if (value == null || value.length > maximum) throw new IllegalStateException("Type4 read failed/out of bounds");
                return value.clone();
            } catch (RuntimeException e) { faulted = true; cancel(); throw e; }
        }
    }
    public synchronized int write(int caller, long nonce, long now, byte[] ndef) {
        check(caller, nonce, now);
        if (!writes) throw new SecurityException("Session is read-only");
        if (ndef == null || ndef.length == 0 || ndef.length > 8190) throw new IllegalArgumentException("Invalid NDEF length");
        byte[] copy = ndef.clone();
        synchronized (port.mutex()) {
            try {
                int maximum = capacity(true);
                if (copy.length > maximum) throw new IllegalArgumentException("NDEF exceeds CC capacity");
                int count = port.write(0xE104, copy);
                if (count != copy.length || !Arrays.equals(copy, port.read(0xE104))) throw new IllegalStateException("Type4 write/readback failed; do not retry automatically");
                return count;
            } catch (RuntimeException e) { faulted = true; cancel(); throw e; }
        }
    }
    public synchronized String status() { return faulted ? "FAULTED: route restoration unverified; no automatic recovery" : token == 0 ? "PASSIVE" : "APPROVED_SESSION"; }
}
