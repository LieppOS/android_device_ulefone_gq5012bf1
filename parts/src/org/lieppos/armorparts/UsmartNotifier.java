/*
 * Notification while an accessory is attached through the uSmart connector.
 *
 * uSmart is the 6-pin rear expansion connector. The kernel (extcon-mtk-usb)
 * detects an accessory through its ID pin: it powers the connector, routes USB
 * data to it and switches the phone's only USB controller to host, so the
 * accessory enumerates as an ordinary USB device. While the ID pin is asserted
 * /sys/devices/platform/extcon-usb/uvc_insert_status reads 1, which tells uSmart
 * devices apart from USB-C OTG devices and the internal thermal camera (same
 * controller, ID pin released).
 *
 * Contacts bounce while an accessory is being seated (the driver does not
 * debounce the ID pin), so a device is only announced once it has stayed
 * attached for SETTLE_MS. The notification goes away when it is detached.
 */
package org.lieppos.armorparts;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbManager;
import android.os.Handler;
import android.os.HandlerThread;
import android.text.TextUtils;
import android.util.Log;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

final class UsmartNotifier {
    private static final String TAG = "ArmorUsmart";
    private static final String CHANNEL = "usmart";
    private static final String STATUS = "/sys/devices/platform/extcon-usb/uvc_insert_status";
    private static final long SETTLE_MS = 800;

    private static Context sContext;
    private static Handler sHandler;
    private static UsbManager sUsb;
    private static NotificationManager sNm;
    private static final Map<String, Runnable> sPending = new HashMap<>();

    private UsmartNotifier() {}

    static void start(Context context) {
        sContext = context.getApplicationContext();
        sUsb = sContext.getSystemService(UsbManager.class);
        sNm = sContext.getSystemService(NotificationManager.class);
        if (sUsb == null || sNm == null) return;

        NotificationChannel channel = new NotificationChannel(CHANNEL,
                sContext.getString(R.string.usmart_channel), NotificationManager.IMPORTANCE_HIGH);
        channel.setDescription(sContext.getString(R.string.usmart_channel_desc));
        channel.setShowBadge(false);
        sNm.createNotificationChannel(channel);

        HandlerThread t = new HandlerThread(TAG);
        t.start();
        sHandler = new Handler(t.getLooper());

        IntentFilter filter = new IntentFilter();
        filter.addAction(UsbManager.ACTION_USB_DEVICE_ATTACHED);
        filter.addAction(UsbManager.ACTION_USB_DEVICE_DETACHED);
        sContext.registerReceiver(RECEIVER, filter, null, sHandler,
                Context.RECEIVER_NOT_EXPORTED);

        // Accessories already attached when this process (re)started.
        sHandler.post(() -> {
            for (UsbDevice d : sUsb.getDeviceList().values()) attached(d);
        });
    }

    private static final BroadcastReceiver RECEIVER = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            UsbDevice d = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE, UsbDevice.class);
            if (d == null) return;
            if (UsbManager.ACTION_USB_DEVICE_ATTACHED.equals(intent.getAction())) {
                attached(d);
            } else {
                detached(d);
            }
        }
    };

    private static void attached(UsbDevice d) {
        if (!isUsmartAttached()) return;          // USB-C OTG device or thermal camera
        final String name = d.getDeviceName();
        Runnable post = () -> {
            sPending.remove(name);
            if (isUsmartAttached() && sUsb.getDeviceList().containsKey(name)) notify(d);
        };
        Runnable old = sPending.put(name, post);
        if (old != null) sHandler.removeCallbacks(old);
        sHandler.postDelayed(post, SETTLE_MS);
    }

    private static void detached(UsbDevice d) {
        Runnable pending = sPending.remove(d.getDeviceName());
        if (pending != null) sHandler.removeCallbacks(pending);
        sNm.cancel(d.getDeviceName(), 0);
    }

    private static void notify(UsbDevice d) {
        String product = d.getProductName();
        if (TextUtils.isEmpty(product)) product = sContext.getString(R.string.usmart_unnamed);
        String ids = String.format("%04x:%04x", d.getVendorId(), d.getProductId());
        String chip = chipHint(d.getVendorId(), d.getProductId());
        String maker = d.getManufacturerName();

        StringBuilder text = new StringBuilder(product);
        if (!TextUtils.isEmpty(maker)) text.append(" \u00b7 ").append(maker);
        text.append(" (").append(chip != null ? chip + ", " : "").append(ids).append(')');

        Notification n = new Notification.Builder(sContext, CHANNEL)
                .setSmallIcon(R.drawable.ic_usmart)
                .setContentTitle(sContext.getString(R.string.usmart_connected))
                .setContentText(text)
                .setStyle(new Notification.BigTextStyle().bigText(
                        text + "\n" + sContext.getString(R.string.usmart_usb_c_note)))
                .setCategory(Notification.CATEGORY_STATUS)
                .setOnlyAlertOnce(true)
                .setShowWhen(true)
                .build();
        sNm.notify(d.getDeviceName(), 0, n);
        Log.i(TAG, "uSmart accessory " + ids + " \"" + product + "\" at " + d.getDeviceName());
    }

    /** Common USB bridges and MCUs, to make a bare "USB Serial" recognisable. */
    private static String chipHint(int vid, int pid) {
        switch (vid) {
            case 0x1a86: return pid == 0x55d4 ? "CH9102" : "CH340";
            case 0x10c4: return "CP210x";
            case 0x0403: return "FTDI";
            case 0x303a: return "Espressif USB";
            case 0x2e8a: return "Raspberry Pi RP2040";
            case 0x067b: return "PL2303";
            default: return null;
        }
    }

    private static boolean isUsmartAttached() {
        try (BufferedReader r = new BufferedReader(new FileReader(STATUS))) {
            String s = r.readLine();
            return s != null && "1".equals(s.trim());
        } catch (IOException e) {
            Log.w(TAG, "cannot read " + STATUS, e);
            return false;
        }
    }
}
