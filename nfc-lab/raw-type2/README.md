# Raw Type2 owner — ordered test-evidence follow-up

`owner-trace.patch` applies to the actual NFC module at owner commit
`b69857f13212d403a2db9526c58ca83d97cd7844`, not clean AOSP upstream.
The original upstream/inherited/owner patch series and provenance remain in
research `hardware/nfc/st21-owner-integration/` (research commit `f2cc904b`).
Do not apply the inherited architecture twice or overwrite a dirty checkout.

This small source-owned follow-up changes only bounded maintenance auditing:

- unique monotonically increasing record IDs, so the existing client does not
  collapse identical packets and the collector can detect overwritten records;
- complete NCI packets up to the actual 258-byte bound, not a 96-byte prefix;
- both raw data directions while admission is held, audit-only. Validated
  NFA_DATA_EVT remains the sole command source; wire data cannot drive the model.

The RF model, authorization, UID policy, controller operations, restoration and
both default-false resources are unchanged. The updated research collector
requires contiguous audit IDs from1, refuses legacy/incomplete traces and pauses
the reader after a detected gap while continuing to collect restoration. Keep
raw traces private: routing tables can contain unrelated application AIDs.

Use a reviewed build input at the exact base above; `patch -p1 --dry-run -i
<absolute owner-trace.patch>` must succeed before application. Build under the
workspace NUMA binding in a private host mount namespace with actual canonical
product/vendor inputs. This is not a live-process injection or a deployment
method. Full build/ABI/signing and hardware-readiness evidence are in research
`hardware/nfc/st21-owner-build-qualification/`.

No change here enables the experiment or authorizes installing, staging an APEX,
flashing the reader, changing phone routing/labels, or restarting NFC. Offline
passing tests and signed packages are not Type2 RF verification.
