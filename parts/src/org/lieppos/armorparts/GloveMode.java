// SPDX-License-Identifier: Apache-2.0
package org.lieppos.armorparts;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Looper;
import android.util.Log;

import java.io.IOException;

/** Serialized access; choices are saved only after the driver accepts the mode. */
final class GloveMode {
    private static final String TAG = "ArmorGloveMode";
    private static final String PREFS = "glove_mode";
    private static final String ENABLED = "enabled";
    private static final GloveModeNode NODE = new GloveModeNode();
    private static final Handler MAIN = new Handler(Looper.getMainLooper());
    private static final Handler IO;
    static {
        HandlerThread thread = new HandlerThread(TAG);
        thread.start();
        IO = new Handler(thread.getLooper());
    }

    static final class Result {
        final Boolean enabled; // null means unknown, never an assumed Off
        final IOException error;
        Result(Boolean enabled, IOException error) {
            this.enabled = enabled;
            this.error = error;
        }
    }

    interface Callback {
        void onResult(Result result);
    }

    private interface Action {
        boolean run() throws IOException;
    }

    private GloveMode() {}

    private static SharedPreferences prefs(Context context) {
        // The application defaults to device-protected storage for direct boot.
        return context.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private static void submit(Action action, Callback callback) {
        IO.post(() -> {
            Result result;
            try {
                result = new Result(action.run(), null);
            } catch (IOException failure) {
                Log.w(TAG, "Glove operation failed", failure);
                Boolean actual = null;
                try {
                    actual = NODE.readEnabled();
                } catch (IOException unavailable) {
                    failure.addSuppressed(unavailable);
                }
                result = new Result(actual, failure);
            }
            Result finished = result;
            MAIN.post(() -> callback.onResult(finished));
        });
    }

    static void read(Callback callback) {
        submit(NODE::readEnabled, callback);
    }

    private static boolean apply(Context context, boolean enabled) throws IOException {
        boolean previous = NODE.setEnabled(enabled);
        if (!prefs(context).edit().putBoolean(ENABLED, enabled).commit()) {
            IOException failure = new IOException("Could not save the glove choice");
            try {
                NODE.setEnabled(previous);
            } catch (IOException rollback) {
                failure.addSuppressed(rollback);
            }
            throw failure;
        }
        return enabled;
    }

    static void setEnabled(Context context, boolean enabled, Callback callback) {
        Context app = context.getApplicationContext();
        submit(() -> apply(app, enabled), callback);
    }

    static void toggle(Context context, Callback callback) {
        Context app = context.getApplicationContext();
        // Read and change in one IO job, not from a potentially stale tile state.
        submit(() -> apply(app, !NODE.readEnabled()), callback);
    }

    static void restore(Context context) {
        Context app = context.getApplicationContext();
        // Installing/updating the app never invents a choice or changes the default.
        if (prefs(app).contains(ENABLED)) IO.post(() -> restore(app, 0));
    }

    private static void restore(Context context, int attempt) {
        SharedPreferences saved = prefs(context);
        if (!saved.contains(ENABLED)) return;
        try {
            // Read afresh on every retry so a newer user choice always wins.
            NODE.setEnabled(saved.getBoolean(ENABLED, false));
        } catch (IOException failure) {
            if (attempt < 4) {
                IO.postDelayed(() -> restore(context, attempt + 1), 1000);
            } else {
                Log.w(TAG, "Could not restore the saved glove choice", failure);
            }
        }
    }
}
