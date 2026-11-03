# RevampedFMRadio for GQ5012BF1

In-tree import of **iusmac/RevampedFMRadio**, branch `mtk`, commit
`02a4f9991434e60931c539e67a0b5e24cf0a2c35` ("RevampedFMRadio: Bump to v3.1.3",
2026-04-24): <https://github.com/iusmac/RevampedFMRadio/tree/mtk>.
License: Apache-2.0 (AOSP FMRadio file headers; upstream ships no separate file).

Chosen over imnathanzero/RevampedFMRadioMTK: that fork stops at upstream v3.1.1
(Feb 2025) plus a JNI rework. The iusmac `mtk` branch carries v3.1.2 (Android 16 crash
fixes) and v3.1.3, as well as the property-based JNI configuration this SoC needs.

## Device facts it relies on

See `research/ulefone-gq5012bf1/reverse-engineering/connectivity/fm/` and the LieppOS
microG/FM integration notes in the research repository.

- Kernel: stock `fmradio_drv_connac2x.ko` (`/dev/fm`, `media:media 0660`, `fm_device`).
  The A-die is an MT6637; the driver reports it as `0x6635`, so `ro.fm.chip=0x6635`.
- Audio: digital CONNSYS I2S into the AFE through the stock `audio.primary.mediatek`
  (`AudioALSAFMController`). The policy lists `FM Tuner In` only for wired headset,
  headphones and USB. Speaker output therefore uses the app's audio-session
  (capture plus playback) path, which upstream enables by default on MTK.
- Antenna: the headset cable. Reception needs a wired headset or cable even when the
  audio plays from the speaker.
- Stock app `YftFmRadio` (same package name) needs `libyftfmjni.so`, which is not in
  the extracted vendor payload. This app overrides it.

## Local changes (all marked `LieppOS` in the source)

1. Build: `Android.mk` files replaced with `Android.bp`. The app, JNI library and
   recordings provider install to `system_ext` (priv-app). The app overrides `FMRadio`
   and `YftFmRadio`, and the provider overrides `FmRecordingsProvider`. `libmtkfmjni`
   no longer links `libmedia`, which it never used.
2. `AndroidManifest.xml`:
   - Removed `android:sharedUserId="android.uid.system"`. The app runs in
     `platform_app` like the stock FM app. The stock vendor policy already lets that
     domain open `/dev/fm`, so no system UID and no new SELinux rule are needed.
     `ACCESS_BROADCAST_RADIO` (privileged allowlist) supplies the `media` group.
   - Removed `INTERNET` (FM is offline-only and nothing used it) and the unused
     `ACCESS_MOCK_LOCATION`.
   - Added `READ`/`WRITE_EXTERNAL_STORAGE`, because recordings to `Recordings/`
     no longer inherit system-UID storage access.
3. `FmMainActivity.powerUpFm()`: asks for storage in the same first-run prompt as the
   microphone. Power-up stays gated on `RECORD_AUDIO` only.
4. `FmRecorder`: MediaStore indexing failures are logged and no longer crash the
   service. The recording file is kept.

Updating: re-import a newer upstream revision over this directory, then re-apply the
changes above.
