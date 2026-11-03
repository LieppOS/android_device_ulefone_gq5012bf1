// SPDX-License-Identifier: Apache-2.0
package com.android.nfc.lab;

import android.app.Service;
import android.content.Intent;
import android.nfc.NdefMessage;
import android.os.*;
import org.lieppos.nfclab.ipc.ILabType4;
import java.security.SecureRandom;

/** Disabled-default, signature-protected operational endpoint in the existing NFC process.
 * No firmware/configuration/reset/raw-command/routing API. The existing native Type4
 * setup/cleanup owns discovery transitions; failures stop further laboratory operations.
 */
public final class LabType4Service extends Service {
    public static final String PERMISSION = "org.lieppos.permission.NFC_LAB_TYPE4";
    private static volatile Type4LabController controller;
    public static void attachPort(Type4LabController.Port port) { controller = new Type4LabController(port); }
    private final SecureRandom random = new SecureRandom();
    private final Object ownership = new Object();
    private IBinder lifetime;
    private IBinder.DeathRecipient death;
    private long currentToken;
    private int currentUid = -1;
    private Type4LabController require() {
        enforceCallingOrSelfPermission(PERMISSION, "NFC-owner Type4 permission required");
        int id = getResources().getIdentifier("lieppos_nfc_lab_type4_enabled", "bool", getPackageName());
        if (id == 0 || !getResources().getBoolean(id) || controller == null) throw new IllegalStateException("Type4 lab build/profile unavailable");
        return controller;
    }
    private void unlink() {
        if (lifetime != null && death != null) try { lifetime.unlinkToDeath(death, 0); }
        catch (java.util.NoSuchElementException alreadyDead) { /* Binder has already removed this death recipient. */ }
        lifetime = null; death = null; currentToken = 0; currentUid = -1;
    }
    private final ILabType4.Stub api = new ILabType4.Stub() {
        @Override public long beginSession(IBinder owner, boolean allowWrites) throws RemoteException {
            Type4LabController c = require(); if (owner == null) throw new IllegalArgumentException("A Binder lifetime is required");
            synchronized (ownership) {
                if (lifetime != null) throw new IllegalStateException("End the previous lab session first");
                final int uid = Binder.getCallingUid(); long value; do { value = random.nextLong(); } while (value == 0);
                final long nonce = value;
                c.begin(uid, nonce, SystemClock.elapsedRealtime(), allowWrites);
                lifetime = owner; currentToken = nonce; currentUid = uid;
                death = () -> { synchronized (ownership) {
                    if (currentToken != nonce || currentUid != uid) return;
                    try { c.end(uid, nonce); } catch (SecurityException alreadyEnded) { /* The controller may have failed closed first. */ }
                    unlink();
                } };
                try { owner.linkToDeath(death, 0); } catch (RemoteException dead) { c.end(uid, nonce); unlink(); throw dead; }
                return nonce;
            }
        }
        @Override public byte[] readNdef(long token) {
            Type4LabController c = require(); synchronized (ownership) {
                byte[] bytes = c.read(Binder.getCallingUid(), token, SystemClock.elapsedRealtime());
                if (bytes.length != 0) try { new NdefMessage(bytes); } catch (android.nfc.FormatException e) { throw new IllegalStateException("Controller returned non-NDEF data"); }
                return bytes;
            }
        }
        @Override public int writeNdef(long token, byte[] message) {
            Type4LabController c = require();
            if (message == null || message.length == 0 || message.length > 8190) throw new IllegalArgumentException("Bounded NDEF required");
            try { new NdefMessage(message); } catch (android.nfc.FormatException e) { throw new IllegalArgumentException("Invalid NDEF"); }
            synchronized (ownership) { return c.write(Binder.getCallingUid(), token, SystemClock.elapsedRealtime(), message); }
        }
        @Override public void endSession(long token) {
            Type4LabController c = require(); synchronized (ownership) {
                int uid = Binder.getCallingUid();
                if (uid != currentUid || token != currentToken) throw new SecurityException("Not the session owner");
                try { c.end(uid, token); } finally { unlink(); }
            }
        }
    };
    @Override public IBinder onBind(Intent i) {
        // Manifest permission is enforced by AMS. require() checks the remote
        // caller and the build gate on every operational transaction instead.
        return api;
    }
    @Override public void onDestroy() {
        synchronized (ownership) { if (controller != null && currentToken != 0) controller.cancel(); unlink(); }
        super.onDestroy();
    }
}
