// SPDX-License-Identifier: Apache-2.0
import com.android.nfc.lab.Type4LabController;

public final class Type4ControllerTest {
    static int checks;
    static void check(boolean b) { checks++; if (!b) throw new AssertionError(); }
    static void reject(Runnable r) { checks++; try { r.run(); } catch (IllegalStateException | IllegalArgumentException | SecurityException expected) { return; } throw new AssertionError("Expected rejection"); }
    static final class Port implements Type4LabController.Port {
        boolean enabled = true; int reads, writes; byte[] message = {1, 2, 3};
        byte[] cc = {0, 15, 0x20, 0, (byte)255, 0, (byte)255, 4, 6, (byte)0xE1, 4, 0x20, 0, 0, 0};
        public boolean ready() { return enabled; }
        public byte[] read(int f) { if (!Thread.holdsLock(this)) throw new AssertionError("Owner transaction monitor missing"); reads++; if (f == 0xE103) return cc.clone(); if (f == 0xE104) return message.clone(); throw new AssertionError("Non-allowlisted file"); }
        public int write(int f, byte[] b) { if (!Thread.holdsLock(this)) throw new AssertionError("Owner transaction monitor missing"); if (f != 0xE104) throw new AssertionError(); writes++; message = b.clone(); return b.length; }
    }
    public static void main(String[] args) {
        Port p = new Port(); Type4LabController c = new Type4LabController(p);
        reject(() -> c.read(1000, 1, 0)); check(p.reads == 0);
        p.enabled = false; reject(() -> c.begin(1000, 1, 0, false)); check(p.reads == 0); p.enabled = true;
        c.begin(1000, 1, 0, false); check(p.reads == 0); // Session creation never issues RF/controller IO.
        reject(() -> c.read(1001, 1, 0)); reject(() -> c.read(1000, 2, 0));
        reject(() -> c.write(1000, 1, 1, new byte[] {4})); check(p.writes == 0);
        check(c.read(1000, 1, 1).length == 3); c.end(1000, 1);
        c.begin(1000, 2, 100, true); check(c.write(1000, 2, 101, new byte[] {4, 5}) == 2); check(p.writes == 1); c.end(1000, 2);
        // An expired session releases ownership itself; ending it again is rejected.
        c.begin(1000, 3, 200, true); reject(() -> c.read(1000, 3, 60201)); check(c.status().equals("PASSIVE")); reject(() -> c.end(1000, 3));
        c.begin(1000, 4, 300, true); reject(() -> c.write(1000, 4, 301, new byte[8191])); check(p.writes == 1); c.end(1000, 4);
        c.begin(1000, 5, 400, true); p.cc[14] = (byte)255; reject(() -> c.write(1000, 5, 401, new byte[] {9}));
        check(p.writes == 1); check(c.status().startsWith("FAULTED")); reject(() -> c.begin(1000, 6, 402, false));
        Port q = new Port(); Type4LabController d = new Type4LabController(q);
        d.begin(1000, 7, 0, false); q.cc[9] = 1; reject(() -> d.read(1000, 7, 1)); check(q.reads == 1);
        System.out.println("PASS " + checks + " Type4 ownership, expiry, read-only, bounds, CC and fail-stop checks (simulated port, no RF)");
    }
}
