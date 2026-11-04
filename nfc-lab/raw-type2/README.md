# Raw Type2 owner — ordered evidence and preflight-diagnostics follow-ups

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

## Ordered preflight diagnostics

Apply `owner-preflight.patch` AFTER `owner-trace.patch`, at the same exact owner
base above. Before/after file hashes and patch identity are recorded in
`owner-preflight-provenance.json`. Never edit an old recovery worktree or reuse
a dirty source checkout as the patch base.

The diagnostic-only follow-up preserves ALL14 start predicates and their original
short-circuit order. A rejected start now has a named first-failing predicate,
one bounded numbered `PREFLIGHT_REFUSED` audit record and observation-only driver
flags. Existing restoration-error text stays separate and is not overwritten.
Ordinary later traffic is still consumed, but cannot replace the terminal refusal
with an apparently idle status. This does NOT enable retry or clear one-shot state.
No permission, lease, NCI command/configuration, routing, UID, RF model or
restoration check is relaxed.

The exact two-patch replay from pinned owner source passes68 ASan/UBSan host tests,
including17 preflight cases: refusal priority, no controller/snapshot side effects,
no gate acquisition before earlier checks pass, cancellation/overflow, pending or
faulted journal, missing/stopped discovery, host context, health/admission refusal,
retained restoration error and diagnostic persistence. These use actual owner
code/selected headers and simulated controller boundaries; they are NOT RF tests.
Nine additional restoration/audit boundary regressions and11 host collector tests
also pass. The full private Android JNI/APEX + sepolicy-neverallows build PASSED;
actual diagnostic370400002 payload/profile/ARM64/dependencies/outer signature/AVB
and matching-cert signed v2 client were checked offline. This is NOT device or RF
qualification. The exact hardware predicate that caused the earlier empty refusal
remains UNKNOWN until a separately approved diagnostic deployment. Research report:
`hardware/nfc/st21-owner-build-qualification/PREFLIGHT-DIAGNOSTICS.md`.

## Captured bootstrap interoperability and routing-read correction

Apply `owner-bootstrap-caps.patch` THIRD, after trace and preflight patches on the
same pinned base. `owner-bootstrap-caps-provenance.json` records all six old/new
file hashes (the new helper is absent before application).

A separately approved diagnostic run identified preflight-journal-fault. Decoding
its saved NFCSNOOP and replaying150 actual control packets through production
Journal reproduces the first poison at record27: paired read-only Android GET_CAPS
`2F 0C 01 00` -> legacy `4F 0C 01 05` (SYNTAX_ERROR). The correction classifies
ONLY that exact paired exchange during passive, unused, uncancelled observation.
It does not normalize the status to OK, clear any existing fault, invent discovery
or permit that response during maintenance. Default Journal mode stays strict.
The full captured replay then ends with fault0/pending0 and real discovery seen/on.

The same four-byte response was misread by the ordinary vendor callback as Android
sub-opcode5 followed by a nonexistent status byte. Exact-frame/bounds checks now
handle it as an error before sub-opcode dispatch; a fresh capability query clears
stale capabilities and status rather than returning invented support.

Independent protocol review also caught the old routing-read request using SET
opcode1. The selected nci_defs.h defines GET_ROUTING=2. Driver request, matched
response/notification and tests now use GET; the shared command is explicitly
checked against `21 02 00`. No SET-routing command is added or issued by this fix.
The earlier hardware attempts never reached this stage. Do not reuse the old
simulated opcode1 fixtures as evidence of a real controller response.

Exact three-patch replay/hashes/actual reverse-forward checks PASS.88 ASan/UBSan
native cases plus9 restoration/audit regressions PASS, including15 bootstrap cases
and5 independent routing-wire cases. Maintenance rejection, bad shape/status,
wrong sub-command/OID, unsolicited/mismatched/duplicate response and prior-fault
retention are covered. No RF result follows from these host tests. The first
unqualified build attempt was stopped for this routing safety audit; the corrected
full Android370400003 build PASSED in503.6s with source unchanged. Actual packaged
flags, JNI/ARM64/dependencies, outer certificate, trusted AVB payload and matching
v2-client signer checks PASS. The corrected bootstrap gate also passed on the
phone: BOOTSTRAP_ANDROID_GET_CAPS_UNSUPPORTED was recorded, followed by service
and native snapshot events. The session then stopped at native-baseline-unavailable
before controller stop/config/routing; no ready or reader resume. Factory NFC was
restored with original hashes and healthy services. GET_ROUTING remains offline
validated, not controller/RF verified. See the research bootstrap/native retest;
hardware RF remains UNKNOWN.

## Native eligibility diagnostics and correct discovery-state fence

Apply `owner-native-diagnostics.patch` FOURTH, then `owner-native-idle.patch` FIFTH.
Their provenance files pin all seven diagnostic and four corrective before/after
hashes. Both actual patch reverse/forward/replay checks pass. All production
resources remain default-off; these source patches do not autostart a session.

The diagnostic callback carries metadata-only rejection bits, state/flag/queue
counts and invalid cache-field ID/length/capacity. No UID, cache content, routing
entry or pointer is logged. The actor distinguishes failed reply, empty snapshot
and failed driver health in the original short-circuit order. Diagnostic input
is bounded; an exception/refusal does not grant a retry or clear one-shot state.
115 sanitizer cases plus9 extra regressions and16384 eligibility combinations
validated this observability-only stage; full Android370400004/package checks
passed. Actual diagnostic metadata then identified only mask8, nfc_state4.

Selected nfc_int.h defines IDLE4 as NORMAL DISCOVERY and OPEN5 as an ACTIVATED
link. Initialization/deactivation set IDLE; activation sets OPEN. The helper had
incorrectly required OPEN while the owner prohibits an activated link. The old
host fixture shared that error. The corrective patch REPLACES the requirement
with IDLE for capture and restoration; it does not accept both states or omit
state checking. All other fences/serialization/restoration/auth/NCI are unchanged.
Independent golden tests accept IDLE4 and reject OPEN5/all other native states;
the16384-combination matrix proves only the intended state4/state5 decision swap.
117 sanitizer cases pass on both corrected and replayed source;9 additional
restoration/audit regressions also pass. Full Android370400005 build passed871.4s
with source unchanged; actual APEX,
JNI/ABI/dependencies/profile, signing/AVB and matching-client checks pass.

The corrected snapshot passed on the phone:76 bytes, rejection mask0. Real
GET_ROUTING2/readbacks and explicit DH-A routing passed, the owner reached READY,
and the controller activated FRAME1 / T2T2 / listen-A80. One READ3004 reached the
validated NFA callback and one exact16-byte synthetic reply was queued through
NCI. Recovered audit1..72 was contiguous, with terminal done/restored1/error-empty,
matching final native snapshot and framework verification. Factory NFC rollback
was verified afterward. This is NOT yet the external three-read RF PASS: the host
collector misclassified its own paused=false resume acknowledgement and exited;
that separate collector fix belongs to the research collector. No full NTAG,
Classic, arbitrary UID or firmware-unlock claim follows.

No change here enables the experiment or authorizes installing, staging an APEX,
flashing the reader, changing phone routing/labels, or restarting NFC. Offline
passing tests and signed packages are not Type2 RF verification.
