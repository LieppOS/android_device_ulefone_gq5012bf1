package com.android.internal.telephony.metrics;

/** No-op replacement for the TelephonyMetrics class removed in Android 17. */
public final class TelephonyMetrics {
    private static final TelephonyMetrics INSTANCE = new TelephonyMetrics();
    private TelephonyMetrics() {}
    public static TelephonyMetrics getInstance() { return INSTANCE; }
    public void writeOnRilSolicitedResponse(int phoneId, int rilSerial, int rilError, int rilRequest, Object ret) {}
    public void writeOnRilTimeoutResponse(int phoneId, int rilSerial, int rilRequest) {}
    public void writeRilAnswer(int phoneId, int rilSerial) {}
    public void writeRilSendSms(int phoneId, int rilSerial, int tech, int format, long messageId) {}
}
