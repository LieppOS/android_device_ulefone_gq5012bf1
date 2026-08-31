# Audio

## VERIFIED

- One MediaTek ALSA card is exposed with a large PCM topology.
- The headset input is `mt6878-mt6369 Headset Jack` and reports headphone,
  microphone, line-out and physical-insert switches.
- An external `speaker_amp` driver binds at I2C `6-0034` through module
  `mtk_sp_spk_amp`.
- Stock vendor contains the MediaTek audio HAL, policy/configuration, mixer and
  DSP-facing dependencies captured by `proprietary-files.txt` and the ELF graph.

## UNKNOWN

- Exact external amplifier silicon behind the generic `speaker_amp` binding.
- Speaker count/channel topology and protection/calibration ownership.
- Voice-call, Bluetooth, USB audio, FM and headset routing under the new ROM.
- Whether any stock effects require framework-side compatibility changes.

A generic MTK policy is not a valid substitute. Full-ROM validation must cover
speaker, earpiece, microphones, headset detection, calls, Bluetooth and USB
with SELinux enforcing.
