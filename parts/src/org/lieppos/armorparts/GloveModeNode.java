// SPDX-License-Identifier: Apache-2.0
package org.lieppos.armorparts;

import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Main FT3680 only. Never discover nodes by walking sysfs (rear touch is unsafe). */
final class GloveModeNode {
    static final String PATH = "/sys/bus/spi/devices/spi3.0/fts_glove_mode";
    private static final Pattern MODE = Pattern.compile("(?m)^Glove Mode:[ \\t]*(On|Off)[ \\t]*$");
    private static final Pattern REGISTER = Pattern.compile(
            "(?m)^Glove Reg\\(0xC0\\):[ \\t]*([01])[ \\t]*$");

    interface Access {
        String read() throws IOException;
        void write(String value) throws IOException;
    }

    private final Access access;

    GloveModeNode() {
        this(new Access() {
            @Override public String read() throws IOException {
                try (FileReader reader = new FileReader(PATH)) {
                    char[] buffer = new char[256];
                    StringBuilder text = new StringBuilder();
                    int count;
                    while ((count = reader.read(buffer)) != -1) {
                        if (text.length() + count > 512) {
                            throw new IOException("Unexpected glove status size");
                        }
                        text.append(buffer, 0, count);
                    }
                    return text.toString();
                }
            }
            @Override public void write(String value) throws IOException {
                try (FileWriter writer = new FileWriter(PATH)) {
                    writer.write(value);
                }
            }
        });
    }

    GloveModeNode(Access access) {
        this.access = access;
    }

    static boolean parse(String text) throws IOException {
        Matcher mode = MODE.matcher(text);
        Matcher register = REGISTER.matcher(text);
        if (!mode.find() || !register.find()) {
            throw new IOException("Glove status is unavailable");
        }
        boolean enabled = "On".equals(mode.group(1));
        // C0 can read zero shortly after enable while glove touch still works.
        // The mode flag reports the driver's accepted request; the register is
        // diagnostic, not a reliable steady-state indicator on this firmware.
        if (mode.find() || register.find()) {
            throw new IOException("Glove controller status is inconsistent");
        }
        return enabled;
    }

    boolean readEnabled() throws IOException {
        return parse(access.read());
    }

    /** Return the previous driver-reported state. On failure, attempt to restore it. */
    boolean setEnabled(boolean enabled) throws IOException {
        boolean previous = readEnabled();
        if (previous == enabled) return previous;
        try {
            access.write(enabled ? "1\n" : "0\n");
            if (readEnabled() != enabled) {
                throw new IOException("Glove controller did not accept the change");
            }
        } catch (IOException failure) {
            try {
                access.write(previous ? "1\n" : "0\n");
                if (readEnabled() != previous) {
                    throw new IOException("Previous glove state could not be verified");
                }
            } catch (IOException rollback) {
                failure.addSuppressed(rollback);
            }
            throw failure;
        }
        return previous;
    }
}
