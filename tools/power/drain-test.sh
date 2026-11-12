#!/system/bin/sh
# LieppOS standby drain test (runs on the phone as root, survives adb disconnect).
#   adb push drain-test.sh /data/local/tmp/ && adb shell 'setsid nohup sh /data/local/tmp/drain-test.sh >/dev/null 2>&1 &'
# Waits for the charger to be unplugged -> START snapshot (+ batterystats reset),
# then samples the SH366003 gauge while discharging (only when the CPU is awake
# anyway: plain sleep is CLOCK_MONOTONIC and never wakes the phone), and on
# replug writes the END snapshot. Results: /data/local/tmp/drain/<start-time>/.
D0=/data/local/tmp/drain
GAUGE=/sys/class/3rd-gauge/battery_info
BAT=/sys/class/power_supply/battery

plugged() { [ "$(cat /sys/class/power_supply/mtk-master-charger/online 2>/dev/null)" = 1 ]; }
mono_ns() { grep -m1 '^now at' /proc/timer_list | awk '{print $3}'; }

snap() { # dir
  mkdir -p "$1"; cd "$1"
  date +%s > epoch; cat /proc/uptime > uptime; mono_ns > mono_ns
  cat $GAUGE > gauge 2>&1
  for f in capacity charge_counter voltage_now current_now temp status; do echo "$f=$(cat $BAT/$f)"; done > battery
  for f in /sys/power/suspend_stats/*; do echo "${f##*/}=$(cat $f)"; done > suspend_stats
  cat /sys/kernel/debug/wakeup_sources > wakeup_sources 2>/dev/null
  cat /proc/interrupts > interrupts
  { for k in wifi_on wifi_scan_always_enabled ble_scan_always_enabled mobile_data airplane_mode_on bluetooth_on; do echo "$k=$(settings get global $k)"; done
    echo "location_mode=$(settings get secure location_mode)"; echo "nfc=$(dumpsys nfc | grep -m1 -i 'mState=')"
    echo "tinylcd_power=$(cat /sys/bus/spi/drivers/spi_tiny_lcd_co5300/tiny_lcd_power_enable)"
    echo "charge_pause=$(getprop sys.lieppos.charge_pause)"; } > state
}

mkdir -p $D0; echo "waiting for unplug $(date)" > $D0/status
while plugged; do sleep 20; done
T=$(date +%Y%m%d-%H%M%S); D=$D0/$T
dumpsys batterystats --reset >/dev/null 2>&1
snap $D/start
echo "running $T (unplugged $(date))" > $D0/status
while ! plugged; do
  { echo "epoch=$(date +%s) mono_ns=$(mono_ns)"; cat $GAUGE; cat $BAT/capacity; } > $D/last.tmp 2>&1
  mv $D/last.tmp $D/last_discharging
  sleep 60
done
snap $D/end
cd $D/end
dumpsys batterystats > batterystats.txt 2>&1
dumpsys suspend_control_internal > suspend_control.txt 2>&1
dumpsys alarm > alarm.txt 2>&1
dumpsys deviceidle > deviceidle.txt 2>&1
dumpsys power > power.txt 2>&1
echo "done $T (replugged $(date))" > $D0/status
