// SPDX-License-Identifier: Apache-2.0
#include "LiepposNfcLab.h"
#include <cassert>
#include <iostream>
#include <random>
#include <thread>
#include <vector>

int main() {
  using namespace lieppos::nfc_lab;
  const std::string cfg = "NDEF_NFCEE_ENABLE=1\nNCI_HAL_MODULE=\"nfc_nci.st21nfc\"\nSTNFC_FW_BIN_NAME=\"st21nfc_fw7.bin\"\n";
  assert(!EffectiveT4t(false, "gq5012bf1", false, cfg));
  assert(!EffectiveT4t(false, "other", true, cfg));
  assert(EffectiveT4t(false, "gq5012bf1", true, cfg));
  assert(EffectiveT4t(true, "other", false, ""));
  assert(!StConfigEnablesNdef("NDEF_NFCEE_ENABLE=1\n"));
  assert(!StConfigEnablesNdef(cfg + "NDEF_NFCEE_ENABLE=0\n"));
  assert(!StConfigEnablesNdef(cfg + "NCI_HAL_MODULE=\"other\"\n"));
  assert(!StConfigEnablesNdef(std::string(65537, 'x')));
  assert(Snapshot()[4] == -1);
  std::array<uint8_t, 33> reset{}; reset[0] = 0x60; reset[2] = 30; reset[3] = 1;
  reset[5] = 0x20; reset[6] = 2; reset[7] = 25; reset[8] = 4; reset[9] = 4;
  reset[10] = 1; reset[11] = 0x20; reset[12] = 0x92; reset[13] = 0x80;
  reset[14] = 2; reset[15] = 2; reset[16] = 1; reset[31] = 0x46; reset[32] = 0x46;
  Observe(reset.data(), reset.size()); auto v = Snapshot();
  assert(v[1] == 1 && v[4] == 4 && v[5] == 4 && v[6] == 0x01209280 && v[7] == 0x020201 && v[8] == 0x4646);
  std::array<uint8_t, 21> init{}; init[0] = 0x40; init[1] = 1; init[2] = 18;
  init[10] = 2; init[11] = 255; init[16] = 2; init[17] = 2; init[19] = 0x90;
  Observe(init.data(), init.size()); v = Snapshot();
  assert(v[10] == 2 && v[11] == 512 && v[12] == 255 && v[13] == 2 && v[14] == 0x90);
  init[18] = 255; Observe(init.data(), init.size()); assert(Snapshot()[10] == -1);
  auto unknown = reset; unknown[6] = 0xFF; Observe(unknown.data(), unknown.size());
  assert(Snapshot()[4] == -1 && Snapshot()[10] == -1);
  Observe(nullptr, 0);
  std::mt19937 random(21);
  for (int i = 0; i < 20000; ++i) {
    std::vector<uint8_t> b(random() % 300);
    for (auto& byte : b) byte = random() & 255;
    Observe(b.data(), b.size());
  }
  std::thread observer([&] { for (int i = 0; i < 1000; ++i) Observe(reset.data(), reset.size()); });
  for (int i = 0; i < 1000; ++i) { auto s = Snapshot(); assert(s[0] == 1); }
  observer.join();
  std::cout << "PASS native cache/compatibility assertions, 20000 malformed frames and concurrent snapshots\n";
}
