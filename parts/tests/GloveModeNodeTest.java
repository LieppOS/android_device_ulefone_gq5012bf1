// SPDX-License-Identifier: Apache-2.0
package org.lieppos.armorparts;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/** Host tests of the driver contract, not a claim that real gloves were tested. */
public final class GloveModeNodeTest {
    private static int checks;

    interface IoAction { void run() throws IOException; }

    private static void check(boolean condition, String message) {
        ++checks;
        if (!condition) throw new AssertionError(message);
    }

    private static IOException expectIo(IoAction action) {
        ++checks;
        try {
            action.run();
        } catch (IOException expected) {
            return expected;
        }
        throw new AssertionError("Expected an IOException");
    }

    private static final class Driver implements GloveModeNode.Access {
        boolean enabled;
        boolean ignoreEnable;
        boolean ignoreDisable;
        int failRead;
        int failWrite;
        int reads;
        int writes;
        final List<String> values = new ArrayList<>();

        @Override public String read() throws IOException {
            if (++reads == failRead) throw new IOException("Read failed");
            return "Glove Mode:" + (enabled ? "On" : "Off")
                    + "\nGlove Reg(0xC0):" + (enabled ? "1" : "0") + "\n";
        }

        @Override public void write(String value) throws IOException {
            values.add(value);
            if (++writes == failWrite) throw new IOException("Write failed");
            check("1\n".equals(value) || "0\n".equals(value), "Only boolean mode writes");
            if ("1\n".equals(value) && !ignoreEnable) enabled = true;
            if ("0\n".equals(value) && !ignoreDisable) enabled = false;
        }
    }

    public static void main(String[] args) throws Exception {
        check(GloveModeNode.parse("Glove Mode:On\nGlove Reg(0xC0):1\n"), "On");
        check(!GloveModeNode.parse("Glove Mode:Off\nGlove Reg(0xC0):0\n"), "Off");
        check(GloveModeNode.parse("Glove Mode: On \nGlove Reg(0xC0): 1 \n"), "Whitespace");
        expectIo(() -> GloveModeNode.parse(""));
        expectIo(() -> GloveModeNode.parse("Glove Mode:Off\n"));
        check(GloveModeNode.parse("Glove Mode:On\nGlove Reg(0xC0):0\n"),
                "Non-sticky register must not hide an accepted On request");
        check(!GloveModeNode.parse("Glove Mode:Off\nGlove Reg(0xC0):1\n"),
                "Diagnostic register must not override the driver's Off state");
        expectIo(() -> GloveModeNode.parse("Glove Mode:On\nGlove Reg(0xC0):2\n"));
        expectIo(() -> GloveModeNode.parse("Glove Mode:On\nGlove Mode:Off\nGlove Reg(0xC0):1\n"));

        Driver driver = new Driver();
        GloveModeNode node = new GloveModeNode(driver);
        check(!node.readEnabled(), "Initial off");
        check(!node.setEnabled(true), "Returns previous off");
        check(driver.enabled && node.readEnabled(), "Enable verified");
        check(node.setEnabled(false), "Returns previous on");
        check(!driver.enabled && driver.writes == 2, "Disable verified");
        node.setEnabled(false);
        check(driver.writes == 2, "No write for already verified state");

        driver = new Driver();
        driver.failRead = 1;
        final Driver unreadable = driver;
        expectIo(() -> new GloveModeNode(unreadable).setEnabled(true));
        check(driver.writes == 0, "No writes when initial state unknown");

        driver = new Driver();
        driver.failWrite = 1;
        final Driver denied = driver;
        expectIo(() -> new GloveModeNode(denied).setEnabled(true));
        check(!driver.enabled && driver.writes == 2, "Failed write restores previous state");

        driver = new Driver();
        driver.ignoreEnable = true;
        final Driver ignored = driver;
        expectIo(() -> new GloveModeNode(ignored).setEnabled(true));
        check(!driver.enabled && driver.values.get(1).equals("0\n"), "Ignored change rolls back");

        driver = new Driver();
        driver.failRead = 2;
        final Driver lostReadback = driver;
        expectIo(() -> new GloveModeNode(lostReadback).setEnabled(true));
        check(!driver.enabled && driver.writes == 2, "Lost readback rolls back");

        driver = new Driver();
        driver.ignoreEnable = true;
        driver.failWrite = 2;
        final Driver badRollback = driver;
        IOException failure = expectIo(() -> new GloveModeNode(badRollback).setEnabled(true));
        check(failure.getSuppressed().length == 1, "Rollback error is retained, not hidden");

        driver = new Driver();
        driver.enabled = true;
        driver.ignoreDisable = true;
        final Driver cannotDisable = driver;
        expectIo(() -> new GloveModeNode(cannotDisable).setEnabled(false));
        check(driver.enabled && driver.values.get(1).equals("1\n"), "Rollback can restore On");
        System.out.println("GloveModeNodeTest: " + checks + " checks passed");
    }
}
