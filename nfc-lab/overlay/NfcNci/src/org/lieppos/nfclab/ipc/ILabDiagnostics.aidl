// SPDX-License-Identifier: Apache-2.0
package org.lieppos.nfclab.ipc;
import android.os.Bundle;
/** Read-only, schema-versioned snapshots. No command, routing, recovery or firmware API. */
interface ILabDiagnostics {
    Bundle snapshot();
}
