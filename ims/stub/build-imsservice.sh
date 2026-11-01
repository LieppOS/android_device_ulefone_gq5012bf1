#!/bin/bash
# Reproduce ims/prebuilt/ImsService.apk from the upstream unified MediaTek ImsService.
#   $1 = upstream ImsService.apk (xiaomi-mediatek-devs/android_vendor_mediatek_ims @ bd54a92,
#        sha256 fca8d69f1d9e79d9162ce9e2ab58cd138abf377bc4246419548099e249ceac4b)
#   $2 = lineage source root (for zipalign, r8/d8, apksigner, platform test key)
# The upstream classes.dex is unchanged; only classes2.dex (no-op TelephonyMetrics)
# is added, then the APK is re-aligned and signed with the build's platform key.
set -euo pipefail
IN=$1; L=$2; HERE=$(cd "$(dirname "$0")" && pwd); T=$(mktemp -d)
echo "fca8d69f1d9e79d9162ce9e2ab58cd138abf377bc4246419548099e249ceac4b  $IN" | sha256sum -c -
javac --release 8 -d "$T/cls" "$HERE/com/android/internal/telephony/metrics/TelephonyMetrics.java"
mkdir "$T/dex"
java -cp "$L/prebuilts/r8/r8.jar" com.android.tools.r8.D8 --min-api 33 --release --output "$T/dex" \
    "$T/cls/com/android/internal/telephony/metrics/TelephonyMetrics.class"
cp "$IN" "$T/u.apk"
zip -d "$T/u.apk" 'META-INF/*.SF' 'META-INF/*.RSA' 'META-INF/*.EC' 'META-INF/*.DSA' 'META-INF/MANIFEST.MF' >/dev/null 2>&1 || true
cp "$T/dex/classes.dex" "$T/classes2.dex"; (cd "$T" && zip -0 -X u.apk classes2.dex >/dev/null)
"$L/out/host/linux-x86/bin/zipalign" -f -p 4 "$T/u.apk" "$T/a.apk"
java -jar "$L/prebuilts/sdk/tools/linux/lib/apksigner.jar" sign \
    --key "$L/build/make/target/product/security/platform.pk8" \
    --cert "$L/build/make/target/product/security/platform.x509.pem" --out "$HERE/../prebuilt/ImsService.apk" "$T/a.apk"
rm -rf "$T" "$HERE/../prebuilt/ImsService.apk.idsig"
sha256sum "$HERE/../prebuilt/ImsService.apk"
