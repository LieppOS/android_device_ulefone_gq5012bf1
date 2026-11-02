// SPDX-License-Identifier: Apache-2.0
#ifndef LIEPPOS_NFC_LAB_H
#define LIEPPOS_NFC_LAB_H

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <mutex>
#include <sstream>
#include <string>

namespace lieppos::nfc_lab {
// One inline state object in libnfc_nci_jni (libnfc-nci is statically linked there).
// No frame/payload, AID, UID, APDU, key or general NFCEE data is retained.
struct Cache {
  std::mutex mutex;
  std::array<int32_t, 40> values;
  Cache() { values.fill(-1); values[0] = 1; values[1] = 0; values[31] = 0; }
};
inline Cache& cache() { static Cache c; return c; }
inline std::array<int32_t, 40> Snapshot() {
  auto& c = cache(); std::lock_guard<std::mutex> lock(c.mutex); return c.values;
}
inline void SetType4Configured(bool configured) {
  auto& c = cache(); std::lock_guard<std::mutex> lock(c.mutex); c.values[34] = configured ? 1 : 0;
}
inline void Observe(const uint8_t* b, size_t n) {
  if (!b || n < 3 || n != size_t(b[2]) + 3 || (b[0] & 0x10) != 0) return;
  auto& c = cache(); std::lock_guard<std::mutex> lock(c.mutex); auto& v = c.values;
  if (v[31] < std::numeric_limits<int32_t>::max()) ++v[31];
  // The last NCI MT/GID/OID only, never data contents. Data packets are not described.
  if ((b[0] & 0xE0) == 0x40 || (b[0] & 0xE0) == 0x60) v[32] = (int32_t(b[0]) << 8) | b[1];
  if (b[0] == 0x60 && b[1] == 0 && n >= 8 && (b[5] == 0x20 || b[5] == 0x21) && size_t(b[7]) == n - 8) {
    if (v[1] < std::numeric_limits<int32_t>::max()) ++v[1];
    std::fill(v.begin() + 2, v.begin() + 31, -1); // Never mix capabilities across resets.
    v[2] = b[5]; v[3] = b[6];
    // Narrow vendor decoder from the inspected ST reset parser. Unknown layouts stay unknown.
    if (b[6] == 2 && b[3] == 1 && n >= 33 && b[8] == 4) {
      v[4] = b[8]; v[5] = b[9];
      v[6] = int32_t((uint32_t(b[10]) << 24) | (uint32_t(b[11]) << 16) | (uint32_t(b[12]) << 8) | b[13]);
      v[7] = (int32_t(b[14]) << 16) | (int32_t(b[15]) << 8) | b[16];
      v[8] = (int32_t(b[31]) << 8) | b[32];
    }
  }
  if (b[0] != 0x40 || b[1] != 1 || n < 4) return;
  v[9] = b[3]; std::fill(v.begin() + 10, v.begin() + 31, -1);
  // NCI2 CORE_INIT layout, matched to nfc_main.cc at the pinned source revision.
  if (b[3] != 0 || v[2] < 0x20 || n < 17 || b[16] > 16) return;
  size_t cursor = 17; const size_t count = b[16]; std::array<int32_t, 16> interfaces{};
  for (size_t i = 0; i < count; ++i) {
    if (cursor + 2 > n) return;
    interfaces[i] = b[cursor++]; size_t ext = b[cursor++];
    if (ext > n - cursor) return;
    cursor += ext;
  }
  if (cursor != n) return;
  v[10] = int32_t(count); v[11] = int32_t(b[9]) | (int32_t(b[10]) << 8); v[12] = b[11];
  for (size_t i = 0; i < count; ++i) v[13 + i] = interfaces[i];
}
inline std::string Trim(std::string s) {
  const auto first = s.find_first_not_of(" \t\r");
  if (first == std::string::npos) return {};
  return s.substr(first, s.find_last_not_of(" \t\r") - first + 1);
}
inline bool StConfigEnablesNdef(const std::string& config) {
  if (config.size() > 65536) return false;
  std::istringstream stream(config); std::string line;
  int enable = -1; bool module = false, firmware = false;
  bool seenModule = false, seenFirmware = false;
  while (std::getline(stream, line)) {
    line = Trim(line.substr(0, line.find('#'))); auto separator = line.find('=');
    if (separator == std::string::npos) continue;
    auto key = Trim(line.substr(0, separator)), value = Trim(line.substr(separator + 1));
    if (key == "NDEF_NFCEE_ENABLE") {
      if (enable != -1 || (value != "0" && value != "1")) return false;
      enable = value == "1" ? 1 : 0;
    } else if (key == "NCI_HAL_MODULE") {
      if (seenModule) return false;
      seenModule = true;
      module = value == "\"nfc_nci.st21nfc\"";
    } else if (key == "STNFC_FW_BIN_NAME") {
      if (seenFirmware) return false;
      seenFirmware = true;
      firmware = value == "\"st21nfc_fw7.bin\"";
    }
  }
  return enable == 1 && module && firmware;
}
inline bool EffectiveT4t(bool halAdvertised, const std::string& board, bool labOptIn, const std::string& config) {
  return halAdvertised || (board == "gq5012bf1" && labOptIn && StConfigEnablesNdef(config));
}
}  // namespace lieppos::nfc_lab
#endif
