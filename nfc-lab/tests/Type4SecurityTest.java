// SPDX-License-Identifier: Apache-2.0
// Ownership, serialization, state-transition and teardown tests for the real
// Type4LabController. Host JVM only: Binder, AMS permission enforcement and the
// controller are not present here, so this is policy evidence, not runtime proof.
import com.android.nfc.lab.Type4LabController;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

public final class Type4SecurityTest {
    static int checks;
    static void check(boolean b, String what) { checks++; if (!b) throw new AssertionError(what); }
    static void reject(Runnable r, String what) {
        checks++;
        try { r.run(); } catch (IllegalStateException | IllegalArgumentException | SecurityException expected) { return; }
        throw new AssertionError("Expected rejection: " + what);
    }

    /** Models the NFC-owner port, including native lifecycle degradation. */
    static final class Port implements Type4LabController.Port {
        volatile boolean enabled = true;
        volatile boolean degraded = false;
        final AtomicInteger inFlight = new AtomicInteger();
        final AtomicInteger maxInFlight = new AtomicInteger();
        final AtomicInteger reads = new AtomicInteger(), writes = new AtomicInteger();
        volatile byte[] message = {1, 2, 3};
        final byte[] cc = {0, 15, 0x20, 0, (byte) 255, 0, (byte) 255, 4, 6, (byte) 0xE1, 4, 0x20, 0, 0, 0};

        public boolean ready() { return enabled && !degraded; }
        private void enter(int fileId) {
            if (!Thread.holdsLock(this)) throw new AssertionError("Owner transaction monitor missing");
            if (degraded) throw new IllegalStateException("Type4 lifecycle degraded; RF restoration unverified");
            int now = inFlight.incrementAndGet();
            maxInFlight.accumulateAndGet(now, Math::max);
            if (fileId != 0xE103 && fileId != 0xE104) throw new AssertionError("Non-allowlisted file");
        }
        public byte[] read(int f) {
            enter(f);
            try { reads.incrementAndGet(); return f == 0xE103 ? cc.clone() : message.clone(); }
            finally { inFlight.decrementAndGet(); }
        }
        public int write(int f, byte[] b) {
            enter(f);
            try {
                if (f != 0xE104) throw new AssertionError();
                writes.incrementAndGet(); message = b.clone(); return b.length;
            } finally { inFlight.decrementAndGet(); }
        }
    }

    static void testSessionStateTransitions() {
        Port p = new Port();
        Type4LabController c = new Type4LabController(p);
        check(c.status().equals("PASSIVE"), "starts passive");
        c.begin(1000, 11, 0, false);
        check(c.status().equals("APPROVED_SESSION"), "approved after begin");
        reject(() -> c.begin(1001, 12, 1, false), "second session while one is live");
        c.end(1000, 11);
        check(c.status().equals("PASSIVE"), "passive again after end");
        reject(() -> c.read(1000, 11, 2), "token replay after end");
        // A new owner may take over only once the previous session ended.
        c.begin(2000, 13, 3, false);
        check(c.read(2000, 13, 4).length == 3, "new owner can read");
        c.end(2000, 13);
    }

    static void testUnauthorizedCallersRejected() {
        Port p = new Port();
        Type4LabController c = new Type4LabController(p);
        c.begin(1000, 21, 0, true);
        reject(() -> c.read(1001, 21, 1), "different uid, correct token");
        reject(() -> c.read(1000, 22, 1), "correct uid, forged token");
        reject(() -> c.write(1001, 21, 1, new byte[] {7}), "different uid write");
        checks++;
        try { c.end(1001, 21); throw new AssertionError("foreign end accepted"); }
        catch (SecurityException expected) { /* only the owner may end the session */ }
        check(p.reads.get() == 0 && p.writes.get() == 0, "rejected callers performed no controller IO");
        check(c.read(1000, 21, 1).length == 3, "legitimate owner still works after rejections");
        c.end(1000, 21);
    }

    static void testExpiryAndReadOnly() {
        Port p = new Port();
        Type4LabController c = new Type4LabController(p);
        c.begin(1000, 31, 0, false);
        reject(() -> c.write(1000, 31, 1, new byte[] {1}), "write without consent");
        reject(() -> c.read(1000, 31, 60_001), "expired session read");
        check(c.status().equals("PASSIVE"), "expiry releases ownership instead of pinning the slot");
        check(p.reads.get() == 0, "expired session performed no controller IO");
        Type4LabController d = new Type4LabController(p);
        d.begin(1000, 32, 0, true);
        check(d.write(1000, 32, 1, new byte[] {4, 5}) == 2, "consented write succeeds");
        d.end(1000, 32);
    }

    static void testDegradedLifecycleFailsStop() {
        Port p = new Port();
        Type4LabController c = new Type4LabController(p);
        c.begin(1000, 41, 0, true);
        p.degraded = true;  // Native cleanup reported unverified RF restoration.
        reject(() -> c.read(1000, 41, 1), "read refused while lifecycle degraded");
        check(c.status().startsWith("FAULTED"), "degraded backend faults and closes the session");
        reject(() -> c.begin(1000, 42, 2, false), "no new session on a degraded backend");
        p.degraded = false;
        reject(() -> c.begin(1000, 43, 3, false), "fault stays sticky; no silent auto-recovery");
    }

    static void testTeardownReleasesOwnership() {
        Port p = new Port();
        Type4LabController c = new Type4LabController(p);
        c.begin(1000, 51, 0, true);
        c.cancel();  // Models Binder death / service destruction.
        check(c.status().equals("PASSIVE"), "cancel releases ownership");
        reject(() -> c.read(1000, 51, 1), "token invalid after teardown");
        c.begin(1001, 52, 2, false);  // Another owner may now take the slot.
        c.end(1001, 52);
    }

    static void testConcurrentCallersAreSerialized() throws Exception {
        Port p = new Port();
        Type4LabController c = new Type4LabController(p);
        final int threads = 8, iterations = 200;
        CountDownLatch start = new CountDownLatch(1);
        ArrayBlockingQueue<Throwable> failures = new ArrayBlockingQueue<>(threads * 4);
        AtomicInteger accepted = new AtomicInteger(), refused = new AtomicInteger();
        Thread[] pool = new Thread[threads];
        for (int t = 0; t < threads; t++) {
            final int uid = 1000 + t;
            pool[t] = new Thread(() -> {
                try {
                    start.await();
                    for (int i = 0; i < iterations; i++) {
                        long nonce = (uid * 1_000_003L) + i + 1;
                        try {
                            c.begin(uid, nonce, 0, true);
                        } catch (RuntimeException busy) {
                            refused.incrementAndGet();
                            continue;
                        }
                        accepted.incrementAndGet();
                        try {
                            c.read(uid, nonce, 1);
                            c.write(uid, nonce, 1, new byte[] {(byte) uid});
                        } finally {
                            c.end(uid, nonce);
                        }
                    }
                } catch (Throwable e) { failures.offer(e); }
            });
            pool[t].start();
        }
        start.countDown();
        for (Thread t : pool) t.join(60_000);
        for (Thread t : pool) check(!t.isAlive(), "no thread deadlocked");
        Throwable first = failures.poll();
        check(first == null, "no unexpected failure: " + first);
        check(accepted.get() + refused.get() == threads * iterations, "every attempt accounted for");
        check(accepted.get() > 0, "sessions were granted under contention");
        check(p.maxInFlight.get() == 1, "controller operations never overlapped on the port");
        check(c.status().equals("PASSIVE"), "no session leaked after contention");
    }

    static void testFaultedBackendStopsEverything() {
        Port p = new Port();
        Type4LabController c = new Type4LabController(p);
        c.begin(1000, 61, 0, true);
        p.message = new byte[] {9};
        // Readback mismatch: write path must fail-stop without retrying.
        Type4LabController.Port lying = new Type4LabController.Port() {
            public boolean ready() { return true; }
            public byte[] read(int f) { return f == 0xE103 ? p.cc.clone() : new byte[] {0}; }
            public int write(int f, byte[] b) { return b.length; }
        };
        Type4LabController m = new Type4LabController(lying);
        m.begin(1000, 62, 0, true);
        reject(() -> m.write(1000, 62, 1, new byte[] {1, 2}), "readback mismatch rejected");
        check(m.status().startsWith("FAULTED"), "mismatch faults the controller");
        c.end(1000, 61);
    }

    public static void main(String[] args) throws Exception {
        testSessionStateTransitions();
        testUnauthorizedCallersRejected();
        testExpiryAndReadOnly();
        testDegradedLifecycleFailsStop();
        testTeardownReleasesOwnership();
        testConcurrentCallersAreSerialized();
        testFaultedBackendStopsEverything();
        AtomicReference<String> note = new AtomicReference<>(
                "host JVM policy simulation; no Binder, AMS permission check or controller");
        System.out.println("PASS " + checks + " Type4 security/concurrency checks (" + note.get() + ")");
    }
}
