#!/system/bin/sh
# LieppOS power meter: samples the SH366003 pack gauge (/sys/class/3rd-gauge/power_now)
# and reports average current/power and energy used.
#
#   powermeter.sh [-i interval_s] [-t duration_s] [-o out.csv] [-w]
#     -i  sample interval (default 1; 0.2 works, the gauge updates ~1 s)
#     -t  stop after N seconds (default: until Ctrl-C / SIGTERM)
#     -o  CSV output (default /data/local/tmp/powermeter-<time>.csv)
#     -w  wait until the charger is unplugged before starting
#
# Measure UNPLUGGED: on a charger the gauge sees charger minus phone (or 0 while
# the charge limit pauses charging). Run it on the phone in the background, e.g.
#   adb shell 'setsid nohup sh /data/local/tmp/powermeter.sh -w -t 600 >/dev/null 2>&1 &'
# then unplug, do the thing to measure, replug and read the .summary file.
# Current is the gauge's sign: negative = discharging. Reported power/energy is
# the discharge (positive numbers = consumed).
NODE=/sys/class/3rd-gauge/power_now
CHG=/sys/class/power_supply/mtk-master-charger/online
I=1; T=0; WAIT=0; OUT=/data/local/tmp/powermeter-$(date +%Y%m%d-%H%M%S).csv
while getopts "i:t:o:w" o; do case $o in i) I=$OPTARG;; t) T=$OPTARG;; o) OUT=$OPTARG;; w) WAIT=1;; *) exit 2;; esac; done
[ -r $NODE ] || { echo "no $NODE (kernel without the power_now node)"; exit 1; }
if [ $WAIT = 1 ]; then while [ "$(cat $CHG)" = 1 ]; do sleep 2; done; fi
[ "$(cat $CHG)" = 1 ] && echo "warning: charger connected, readings are battery current, not phone consumption" >&2

now() { cut -d' ' -f1 /proc/uptime; }
echo "t_s,voltage_mv,current_ma,avg_current_ma,rc_mah,plugged" > $OUT
T0=$(now)
summary() {
  awk -F, -v out="$OUT" 'NR==1{next} {n++; t=$1; v=$2; i=$3; p=-v*i/1000.0;
      if (n>1){dt=t-pt; mah+=-(i+pi)/2*dt/3600; mwh+=(p+pp)/2*dt/3600}
      if (n==1){t0=t; rc0=$5} rc1=$5; si+=i; sp+=p; if(i<mn||n==1)mn=i; if(i>mx||n==1)mx=i; if($6==1)pl++;
      pt=t; pi=i; pp=p}
    END{ if(n<2){print "not enough samples"; exit}
      d=t-t0; printf "samples %d over %.1f s (%.1f min)%s\n", n, d, d/60, (pl? sprintf(", %d PLUGGED samples - not phone consumption", pl):"");
      printf "average current  %.1f mA discharge (min %d, max %d mA as read)\n", -si/n, mn, mx;
      printf "average power    %.0f mW\n", sp/n;
      printf "energy           %.2f mAh, %.1f mWh (integrated)\n", mah, mwh;
      printf "gauge RC delta   %d mAh (%d -> %d, 1 mAh resolution)\n", rc0-rc1, rc0, rc1;
      if (d>0) printf "projection       %.1f h for the full 8864 mAh pack at this rate\n", (mah>0? 8864/(mah/(d/3600)) : 0) }' $OUT
}
trap 'summary | tee ${OUT%.csv}.summary; exit 0' INT TERM
while :; do
  t=$(now); s=$(cat $NODE 2>/dev/null); pl=$(cat $CHG)
  set -- $(echo "$s" | tr '=' ' ')
  # voltage_mv X current_ma Y avg_current_ma Z rc_mah W
  [ -n "$8" ] && echo "$(awk -v a=$t -v b=$T0 'BEGIN{printf "%.2f", a-b}'),$2,$4,$6,$8,$pl" >> $OUT
  if [ "$T" != 0 ] && [ "$(awk -v a=$t -v b=$T0 -v d=$T 'BEGIN{print (a-b>=d)}')" = 1 ]; then break; fi
  sleep $I
done
summary | tee ${OUT%.csv}.summary
