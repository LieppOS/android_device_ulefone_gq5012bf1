// SPDX-License-Identifier: Apache-2.0
package org.lieppos.armorparts;

import java.io.IOException;

/** Host lifecycle tests, not a claim that Android alarms or GNSS hardware ran. */
public final class PrecisionGnssSessionTest {
    private static int checks;
    private static void check(boolean condition, String name) {
        checks++;
        if (!condition) throw new AssertionError(name);
    }
    private interface Attempt { void run() throws IOException; }
    private static IOException fails(Attempt attempt) {
        checks++;
        try { attempt.run(); } catch (IOException expected) { return expected; }
        throw new AssertionError("Expected IOException");
    }
    private static final class Access implements PrecisionGnssSession.Access {
        int arms, acquires, releases, cancels;
        long armedDeadline;
        boolean live, reject, failArm, failAcquire, failRelease, failCancel;
        String order = "";
        public void armDeadline(long deadline) throws IOException {
            arms++; order += "arm "; armedDeadline = deadline;
            if (failArm) throw new IOException("arm failed");
        }
        public boolean acquire() throws IOException {
            acquires++; order += "acquire "; live = true;
            if (failAcquire) throw new IOException("partial acquire failed");
            return !reject;
        }
        public void release() throws IOException {
            releases++; order += "release ";
            if (failRelease) throw new IOException("release failed");
            live = false;
        }
        public void cancelDeadline() throws IOException {
            cancels++; order += "cancel ";
            if (failCancel) throw new IOException("cancel failed");
            armedDeadline = 0;
        }
    }
    public static void main(String[] args) throws Exception {
        Access a = new Access(); PrecisionGnssSession s = new PrecisionGnssSession(a);
        check(PrecisionGnssSession.DURATION_MS == 900000, "owner's15-minute limit");
        check(s.state() == PrecisionGnssSession.State.OFF && s.deadline() == 0, "default Off");
        check(a.arms == 0 && a.acquires == 0, "constructor never activates");
        check(!s.expire(9999999), "expiry while Off harmless");
        s.stop(); check(a.releases == 0, "stop while Off idempotent");
        check(s.start(5000), "first start accepted");
        check(s.deadline() == 905000 && a.armedDeadline == s.deadline(), "elapsed deadline armed");
        check(a.order.equals("arm acquire "), "arm BEFORE acquisition");
        check(a.live && s.state() == PrecisionGnssSession.State.ACTIVE, "request active");
        check(!s.start(100000), "duplicate does not start");
        check(s.deadline() == 905000 && a.acquires == 1 && a.arms == 1, "duplicate never extends");
        check(!s.expire(904999) && a.live, "not before deadline");
        check(s.expire(905000), "exact boundary expires");
        check(!a.live && s.deadline() == 0 && s.state() == PrecisionGnssSession.State.OFF, "released Off");
        check(a.releases == 1 && a.cancels == 1, "release and cancel exactly once");
        s.stop(); check(a.releases == 1, "repeat stop harmless");
        check(s.start(2000000), "explicit new session allowed");
        check(!s.expire(2000001), "stale early alarm cannot stop new session");
        check(s.deadline() == 2900000, "new deadline unaffected");
        check(s.expire(999999999), "elapsed jump/deep sleep expires immediately on wake");
        check(!a.live, "no extending for missed uptime");

        a = new Access(); a.failArm = true; s = new PrecisionGnssSession(a);
        PrecisionGnssSession arm = s; fails(() -> arm.start(0));
        check(a.acquires == 0, "deadline failure never acquires");
        check(!a.live && s.state() == PrecisionGnssSession.State.OFF, "arm failure cleaned up");
        check(a.cancels == 1, "partial alarm canceled");
        for (boolean rejected : new boolean[] {true, false}) {
            a = new Access(); a.reject = rejected; a.failAcquire = !rejected;
            s = new PrecisionGnssSession(a); PrecisionGnssSession acquisition = s;
            fails(() -> acquisition.start(10));
            check(!a.live, "rejected/partial registration released");
            check(a.releases == 1 && a.cancels == 1, "rollback removes request and deadline");
            check(s.state() == PrecisionGnssSession.State.OFF && s.deadline() == 0, "rollback Off");
        }
        a = new Access(); s = new PrecisionGnssSession(a); s.start(100);
        a.failRelease = true; PrecisionGnssSession stopping = s;
        fails(stopping::stop);
        check(s.state() == PrecisionGnssSession.State.STOPPING && a.live, "removal failure not false Off");
        check(s.deadline() == 900100 && a.cancels == 0, "original deadline retained for cleanup");
        check(!s.start(500) && a.acquires == 1, "cannot acquire over failed cleanup");
        a.failRelease = false; s.stop();
        check(s.state() == PrecisionGnssSession.State.OFF && !a.live, "cleanup retry succeeds");

        a = new Access(); a.failAcquire = true; a.failRelease = true;
        s = new PrecisionGnssSession(a); PrecisionGnssSession partial = s;
        IOException error = fails(() -> partial.start(5));
        check(error.getSuppressed().length == 1, "retain both acquisition and cleanup errors");
        check(s.state() == PrecisionGnssSession.State.STOPPING, "partial cleanup retained");
        a.failRelease = false; s.stop(); check(!a.live, "later cleanup releases partial acquisition");

        a = new Access(); s = new PrecisionGnssSession(a); s.start(100);
        a.failCancel = true; PrecisionGnssSession cancelled = s; fails(cancelled::stop);
        check(!a.live && s.state() == PrecisionGnssSession.State.OFF, "cancel failure cannot retain GNSS");
        check(!s.expire(9999999), "leftover expiry cannot acquire GNSS");
        a.failCancel = false; s.start(2000000);
        check(!s.expire(900100), "old alarm cannot stop unexpired replacement");
        s.stop();
        a = new Access(); s = new PrecisionGnssSession(a); PrecisionGnssSession clock = s;
        fails(() -> clock.start(-1)); fails(() -> clock.start(Long.MAX_VALUE));
        check(a.arms == 0 && a.acquires == 0, "invalid clock never arms or acquires");
        check(s.state() == PrecisionGnssSession.State.OFF, "invalid clock leaves Off");
        check(new PrecisionGnssSession(new Access()).state() == PrecisionGnssSession.State.OFF,
                "new process model has no session restoration");
        PrecisionGnssSession.StartGate gate = new PrecisionGnssSession.StartGate();
        check(!gate.consume(1, false), "cold process rejects old start intent");
        long token = gate.issue();
        check(token != 0 && gate.issue() == 0, "only one pending user start");
        check(!gate.consume(token + 1, false), "wrong token cannot start");
        check(gate.consume(token, false), "fresh user intent accepted once");
        check(!gate.consume(token, false), "same intent cannot replay");
        token = gate.issue();
        check(!gate.consume(token, true), "framework retry/redelivery cannot resume");
        check(!gate.consume(token, false), "retry also consumes old authorization");
        token = gate.issue(); gate.cancel();
        check(!gate.consume(token, false), "Stop invalidates a queued Start");
        long old = token; token = gate.issue(); gate.discard(old);
        check(gate.consume(token, false), "old failed launcher cannot clear newer request");
        token = gate.issue(); gate.discard(token);
        check(!gate.consume(token, false), "failed foreground launch leaves no authorization");
        check(!new PrecisionGnssSession.StartGate().consume(gate.issue(), false),
                "authorization is not restored in a recreated process");
        System.out.println("PrecisionGnssSessionTest: " + checks + " checks passed");
    }
}
