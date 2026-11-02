// SPDX-License-Identifier: Apache-2.0
#ifndef LIEPPOS_T4T_LIFECYCLE_H
#define LIEPPOS_T4T_LIFECYCLE_H

#include <atomic>
#include <mutex>

// Transport-independent setup/cleanup policy for the existing T4T NDEF NFCEE
// path. The real NativeT4tNfcee adapter and the offline fault-injection tests
// drive the SAME object through Driver, so the tests exercise shipped logic
// rather than a copy of it.
//
// Deliberate limits:
//   * This never starts RF discovery that it did not itself stop.
//   * It does not suppress, replace or retry the existing NFCC recovery path.
//     startRfDiscovery() may still time out and trigger the stack's own
//     recovery; that remains the stack's decision, and the result is only
//     reported here as "degraded", never silently repaired.
//   * A degraded result means restoration is UNVERIFIED, not that it failed
//     safely. Callers must fail-stop, not retry.
namespace lieppos::t4t {

class Driver {
 public:
  virtual ~Driver() = default;
  // Observed RF discovery state of the existing stack.
  virtual bool isDiscoveryStarted() = 0;
  // Requests the existing stack to start/stop discovery. May internally fail
  // or trigger the stack's own timeout recovery; the result is re-observed.
  virtual void startRfDiscovery(bool start) = 0;
  // true when the underlying operation reported NFA_STATUS_OK.
  virtual bool openConnection() = 0;
  virtual bool closeConnection() = 0;
  virtual void setBusy(bool busy) = 0;
  // NFC OFF handling keeps the existing contract: do not close or restart,
  // just release the shutdown waiter.
  virtual bool isNfcOffTriggered() = 0;
  virtual void notifyNfcOff() = 0;
};

class Lifecycle {
 public:
  // Acquires the single in-flight slot, stops discovery only if it is running,
  // then opens the connection. Returns false without leaving state behind when
  // another operation is in flight, the stop did not take effect, or the open
  // failed. On false the caller must NOT call finish(): unwinding already ran.
  bool begin(Driver& driver) {
    if (mInFlight.exchange(true)) return false;  // Reject reentrancy; do not disturb the active session.
    std::lock_guard<std::mutex> lock(mMutex);
    mActive = true;
    mDegraded = false;
    mStoppedDiscovery = false;
    mConnectionOpen = false;
    driver.setBusy(true);
    if (driver.isDiscoveryStarted()) {
      driver.startRfDiscovery(false);
      // Re-observe instead of assuming the request took effect.
      mStoppedDiscovery = !driver.isDiscoveryStarted();
      if (!mStoppedDiscovery) {
        mDegraded = true;  // Discovery still running: refuse to open a connection under it.
        finishLocked(driver);
        return false;
      }
    }
    if (!driver.openConnection()) {
      finishLocked(driver);
      return false;
    }
    mConnectionOpen = true;
    return true;
  }

  // Idempotent. Returns true only when the connection closed cleanly and any
  // discovery state this object changed was observed restored.
  bool finish(Driver& driver) {
    std::lock_guard<std::mutex> lock(mMutex);
    return finishLocked(driver);
  }

  // For the existing NFC-OFF shutdown path, which closes outside this object.
  // Restoration cannot be confirmed there, so the session ends degraded.
  void abandon() {
    std::lock_guard<std::mutex> lock(mMutex);
    if (!mActive && !mInFlight.load()) return;
    mActive = false;
    mConnectionOpen = false;
    mStoppedDiscovery = false;
    mDegraded = true;
    mInFlight = false;
  }

  bool active() const { return mInFlight.load(); }
  bool degraded() const {
    std::lock_guard<std::mutex> lock(mMutex);
    return mDegraded;
  }
  unsigned degradedCount() const {
    std::lock_guard<std::mutex> lock(mMutex);
    return mDegradedCount;
  }

 private:
  bool finishLocked(Driver& driver) {
    if (!mActive) return !mDegraded;  // Second call performs no extra transport work.
    mActive = false;
    if (driver.isNfcOffTriggered()) {
      // Existing contract: release the shutdown waiter and return. The shutdown
      // path owns closing; discovery restoration is not attempted or claimed.
      driver.notifyNfcOff();
      mConnectionOpen = false;
      mStoppedDiscovery = false;
      mDegraded = true;
      return release(driver);
    }
    if (mConnectionOpen) {
      if (!driver.closeConnection()) mDegraded = true;  // Surfaced, not just logged.
      mConnectionOpen = false;
    }
    if (mStoppedDiscovery) {
      if (!driver.isDiscoveryStarted()) driver.startRfDiscovery(true);
      if (!driver.isDiscoveryStarted()) mDegraded = true;  // Restoration unverified.
      mStoppedDiscovery = false;
    }
    return release(driver);
  }

  bool release(Driver& driver) {
    if (mDegraded && mDegradedCount < 0xFFFFFFFFu) ++mDegradedCount;
    driver.setBusy(false);
    mInFlight = false;
    return !mDegraded;
  }

  mutable std::mutex mMutex;
  std::atomic<bool> mInFlight{false};
  bool mActive = false;
  bool mStoppedDiscovery = false;
  bool mConnectionOpen = false;
  bool mDegraded = false;
  unsigned mDegradedCount = 0;
};

}  // namespace lieppos::t4t
#endif
