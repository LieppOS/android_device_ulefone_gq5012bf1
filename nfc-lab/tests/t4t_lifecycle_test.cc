// SPDX-License-Identifier: Apache-2.0
// Fault injection over the SHIPPED lifecycle object (LiepposT4tLifecycle.h).
// Host-only: there is no controller, no RF and no NFA stack here. Passing
// proves the setup/cleanup decision logic, not device behaviour.
#include "LiepposT4tLifecycle.h"

#include <atomic>
#include <cassert>
#include <cstdio>
#include <string>
#include <thread>
#include <vector>

namespace {

int gChecks = 0;
void check(bool condition, const char* what) {
  ++gChecks;
  if (!condition) {
    std::fprintf(stderr, "FAIL: %s\n", what);
    std::abort();
  }
}

// Mock of the existing stack. Records every transport effect so tests can
// assert what was and was not done.
class MockDriver : public lieppos::t4t::Driver {
 public:
  bool discovery = true;      // Observed discovery state.
  bool stopTakesEffect = true;
  bool startTakesEffect = true;
  bool openOk = true;
  bool closeOk = true;
  bool nfcOff = false;

  int startCalls = 0, stopCalls = 0, openCalls = 0, closeCalls = 0;
  int busyTrue = 0, busyFalse = 0, nfcOffNotifications = 0;
  std::vector<std::string> trace;

  bool isDiscoveryStarted() override { return discovery; }
  void startRfDiscovery(bool start) override {
    if (start) {
      ++startCalls;
      trace.push_back("start");
      if (startTakesEffect) discovery = true;
    } else {
      ++stopCalls;
      trace.push_back("stop");
      if (stopTakesEffect) discovery = false;
    }
  }
  bool openConnection() override {
    ++openCalls;
    trace.push_back("open");
    return openOk;
  }
  bool closeConnection() override {
    ++closeCalls;
    trace.push_back("close");
    return closeOk;
  }
  void setBusy(bool busy) override {
    busy ? ++busyTrue : ++busyFalse;
    trace.push_back(busy ? "busy" : "idle");
  }
  bool isNfcOffTriggered() override { return nfcOff; }
  void notifyNfcOff() override {
    ++nfcOffNotifications;
    trace.push_back("nfcoff");
  }
};

void TestNominalRoundTrip() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  check(lifecycle.begin(d), "nominal begin succeeds");
  check(d.stopCalls == 1 && !d.discovery, "discovery stopped once for the operation");
  check(d.openCalls == 1, "connection opened once");
  check(lifecycle.active(), "session is in flight");
  check(lifecycle.finish(d), "nominal finish is clean");
  check(d.closeCalls == 1 && d.startCalls == 1 && d.discovery, "closed and discovery restored");
  check(!lifecycle.degraded() && lifecycle.degradedCount() == 0, "nominal run is not degraded");
  check(d.busyTrue == 1 && d.busyFalse == 1, "busy flag balanced");
}

void TestDiscoveryAlreadyStoppedIsNotRestarted() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  d.discovery = false;  // Reader mode off / stack already idle.
  check(lifecycle.begin(d), "begin succeeds with discovery already stopped");
  check(d.stopCalls == 0, "no redundant stop request");
  check(lifecycle.finish(d), "finish is clean");
  check(d.startCalls == 0 && !d.discovery, "never starts discovery it did not stop");
}

void TestStopRequestIgnoredRefusesToOpen() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  d.stopTakesEffect = false;  // Stack ignored or failed the stop.
  check(!lifecycle.begin(d), "begin fails when discovery is still running");
  check(d.openCalls == 0, "no connection opened under live discovery");
  check(d.startCalls == 0, "no spurious restart of discovery we never stopped");
  check(lifecycle.degraded(), "state reported degraded");
  check(!lifecycle.active(), "in-flight slot released on failure");
  check(d.busyTrue == 1 && d.busyFalse == 1, "busy released after refusal");
}

void TestOpenFailureUnwindsExactlyWhatItChanged() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  d.openOk = false;
  check(!lifecycle.begin(d), "begin fails when open fails");
  check(d.closeCalls == 0, "never closes a connection that never opened");
  check(d.startCalls == 1 && d.discovery, "restores the discovery it stopped");
  check(!lifecycle.active(), "slot released");
}

void TestOpenFailureWithDiscoveryAlreadyStopped() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  d.discovery = false;
  d.openOk = false;
  check(!lifecycle.begin(d), "begin fails");
  check(d.startCalls == 0 && !d.discovery, "no discovery started on the failure path either");
}

void TestCloseFailureIsSurfacedNotSwallowed() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  d.closeOk = false;
  check(lifecycle.begin(d), "begin succeeds");
  check(!lifecycle.finish(d), "close failure makes finish report degraded");
  check(lifecycle.degraded() && lifecycle.degradedCount() == 1, "degradation recorded for the gate");
  check(d.startCalls == 1 && d.discovery, "discovery still restored after a failed close");
}

void TestDiscoveryRestoreFailureIsDegraded() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  d.startTakesEffect = false;  // Restart request did not take effect.
  check(lifecycle.begin(d), "begin succeeds");
  check(!lifecycle.finish(d), "unrestored discovery is degraded");
  check(d.startCalls == 1, "exactly one restore attempt; no retry loop");
  check(!d.discovery, "mock still reports discovery down; no false claim of restoration");
}

void TestIdempotentCleanup() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  check(lifecycle.begin(d), "begin succeeds");
  check(lifecycle.finish(d), "first finish clean");
  const int closes = d.closeCalls, starts = d.startCalls, idles = d.busyFalse;
  check(lifecycle.finish(d) && lifecycle.finish(d), "repeat finish stays clean");
  check(d.closeCalls == closes && d.startCalls == starts && d.busyFalse == idles,
        "repeat finish performs no extra transport work");
  check(lifecycle.degradedCount() == 0, "idempotent calls do not inflate counters");
}

void TestIdempotentCleanupPreservesDegradedVerdict() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  d.closeOk = false;
  check(lifecycle.begin(d), "begin succeeds");
  check(!lifecycle.finish(d), "degraded verdict");
  check(!lifecycle.finish(d), "degraded verdict is sticky for the session");
  check(lifecycle.degradedCount() == 1, "counted once");
}

void TestReentrancyRejected() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  check(lifecycle.begin(d), "first begin succeeds");
  const int opens = d.openCalls, stops = d.stopCalls;
  check(!lifecycle.begin(d), "reentrant begin rejected");
  check(d.openCalls == opens && d.stopCalls == stops, "rejected call touches no transport");
  check(d.busyFalse == 0, "rejected call does not clear the active session's busy flag");
  check(lifecycle.finish(d), "the original session still completes cleanly");
}

void TestNfcOffKeepsExistingShutdownContract() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  check(lifecycle.begin(d), "begin succeeds");
  d.nfcOff = true;  // NFC turned off mid-operation.
  check(!lifecycle.finish(d), "NFC-off finish is not reported clean");
  check(d.nfcOffNotifications == 1, "shutdown waiter released exactly once");
  check(d.closeCalls == 0 && d.startCalls == 0,
        "does not close or restart discovery during shutdown");
  check(lifecycle.degraded(), "restoration explicitly unverified");
}

void TestAbandonFromShutdownPath() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  check(lifecycle.begin(d), "begin succeeds");
  lifecycle.abandon();  // onNfccShutdown closed outside this object.
  check(!lifecycle.active(), "slot released for the next NFC-on cycle");
  check(lifecycle.degraded(), "abandoned session is degraded");
  const int closes = d.closeCalls, starts = d.startCalls;
  check(!lifecycle.finish(d), "finish after abandon stays degraded");
  check(d.closeCalls == closes && d.startCalls == starts, "no double close/start after abandon");
}

void TestTimeoutShapedFailureStillCleansUpOnce() {
  // Models an operation whose wait timed out: the caller still calls cleanup.
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  check(lifecycle.begin(d), "begin succeeds");
  check(lifecycle.finish(d), "cleanup after a timed-out operation is clean");
  check(d.closeCalls == 1 && d.startCalls == 1, "exactly one close and one restore");
  // A later successful operation must not inherit the previous verdict.
  MockDriver second;
  check(lifecycle.begin(second), "next session begins");
  check(lifecycle.finish(second), "next session is independently clean");
}

void TestDegradedVerdictResetsPerSession() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver bad;
  bad.closeOk = false;
  check(lifecycle.begin(bad), "first begin");
  check(!lifecycle.finish(bad), "first session degraded");
  MockDriver good;
  check(lifecycle.begin(good), "second begin");
  check(lifecycle.finish(good), "second session clean");
  check(lifecycle.degradedCount() == 1, "cumulative counter retains the earlier degradation");
}

void TestConcurrentCallersSeeSingleOwner() {
  lieppos::t4t::Lifecycle lifecycle;
  MockDriver d;
  std::atomic<int> granted{0};
  std::atomic<int> rejected{0};
  std::atomic<int> maxConcurrent{0};
  std::atomic<int> concurrent{0};
  std::vector<std::thread> threads;
  for (int i = 0; i < 8; ++i) {
    threads.emplace_back([&] {
      for (int n = 0; n < 500; ++n) {
        if (lifecycle.begin(d)) {
          ++granted;
          int now = ++concurrent;
          int seen = maxConcurrent.load();
          while (now > seen && !maxConcurrent.compare_exchange_weak(seen, now)) {
          }
          --concurrent;
          lifecycle.finish(d);
        } else {
          ++rejected;
        }
      }
    });
  }
  for (auto& t : threads) t.join();
  check(maxConcurrent.load() == 1, "never more than one in-flight operation");
  check(granted.load() + rejected.load() == 8 * 500, "every attempt accounted for");
  check(granted.load() > 0, "progress was made");
  check(d.openCalls == granted.load(), "one open per granted session");
  check(d.closeCalls == granted.load(), "one close per granted session, no double close");
  check(!lifecycle.active(), "no session left in flight");
}

}  // namespace

int main() {
  TestNominalRoundTrip();
  TestDiscoveryAlreadyStoppedIsNotRestarted();
  TestStopRequestIgnoredRefusesToOpen();
  TestOpenFailureUnwindsExactlyWhatItChanged();
  TestOpenFailureWithDiscoveryAlreadyStopped();
  TestCloseFailureIsSurfacedNotSwallowed();
  TestDiscoveryRestoreFailureIsDegraded();
  TestIdempotentCleanup();
  TestIdempotentCleanupPreservesDegradedVerdict();
  TestReentrancyRejected();
  TestNfcOffKeepsExistingShutdownContract();
  TestAbandonFromShutdownPath();
  TestTimeoutShapedFailureStillCleansUpOnce();
  TestDegradedVerdictResetsPerSession();
  TestConcurrentCallersSeeSingleOwner();
  std::printf("PASS %d T4T lifecycle fault-injection assertions (host mocks, no RF)\n", gChecks);
  return 0;
}
