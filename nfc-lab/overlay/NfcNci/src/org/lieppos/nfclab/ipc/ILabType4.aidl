// SPDX-License-Identifier: Apache-2.0
package org.lieppos.nfclab.ipc;
/** Operational NFCEE access, separate from passive diagnostics. Disabled by default. */
interface ILabType4 {
    long beginSession(IBinder lifetime, boolean allowOwnedTestWrites);
    byte[] readNdef(long token);
    int writeNdef(long token, in byte[] message);
    void endSession(long token);
}
