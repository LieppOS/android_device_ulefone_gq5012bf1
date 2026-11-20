// SPDX-License-Identifier: Apache-2.0
package org.lieppos.armorparts;

import java.io.IOException;

/** Single-threaded lifetime model. All times are elapsed realtime, never wall time. */
final class PrecisionGnssSession {
    static final long DURATION_MS = 15 * 60 * 1000L;
    enum State { OFF, ACTIVE, STOPPING }
    interface Access {
        void armDeadline(long elapsedDeadline) throws IOException;
        boolean acquire() throws IOException;
        void release() throws IOException;
        void cancelDeadline() throws IOException;
    }
    /** One-shot UI authorization in RAM; old service intents cannot resume after death. */
    static final class StartGate {
        private long sequence;
        private long pending;
        synchronized long issue() {
            if (pending != 0) return 0; // One pending user start, no queued duplicates.
            pending = ++sequence;
            return pending;
        }
        synchronized void discard(long token) { if (pending == token) pending = 0; }
        synchronized void cancel() { pending = 0; }
        synchronized boolean consume(long token, boolean replayed) {
            if (token == 0 || token != pending) return false;
            pending = 0;
            return !replayed;
        }
    }
    private final Access access;
    private State state = State.OFF;
    private long deadline;

    PrecisionGnssSession(Access access) { this.access = access; }
    State state() { return state; }
    long deadline() { return deadline; }

    /** Repeated starts never extend a live session or bypass failed cleanup. */
    boolean start(long elapsedNow) throws IOException {
        if (state != State.OFF) return false;
        if (elapsedNow < 0 || elapsedNow > Long.MAX_VALUE - DURATION_MS) {
            throw new IOException("Invalid elapsed clock");
        }
        deadline = elapsedNow + DURATION_MS;
        state = State.STOPPING; // Fail closed until both deadline and request exist.
        try {
            access.armDeadline(deadline); // Must succeed BEFORE acquiring GNSS.
            if (!access.acquire()) throw new IOException("GNSS registration rejected");
            state = State.ACTIVE;
            return true;
        } catch (IOException failure) {
            try { stop(); } catch (IOException cleanup) { failure.addSuppressed(cleanup); }
            throw failure;
        }
    }

    void stop() throws IOException {
        if (state == State.OFF) return;
        state = State.STOPPING;
        access.release(); // Do not report Off or allow restart if removal failed.
        state = State.OFF;
        deadline = 0;
        // A leftover alarm can only request expiry, never start GNSS.
        access.cancelDeadline();
    }

    /** Early/stale alarm delivery cannot stop a newer, unexpired session. */
    boolean expire(long elapsedNow) throws IOException {
        if (state == State.OFF) return false;
        if (state == State.ACTIVE && elapsedNow < deadline) return false;
        stop();
        return true;
    }
}
