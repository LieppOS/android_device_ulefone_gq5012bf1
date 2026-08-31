# Kernel module map

## VERIFIED

- Stock `vendor_dlkm` is EROFS and contains 215 `.ko` files in the extracted
  image; the generated package list has 219 DLKM entries when dependency/load
  metadata is included.
- The broader inventory records 471 module copies because modules also appear
  in the stock `vendor_boot` platform ramdisk and other DLKM partitions.
- Each record includes SHA-256, vermagic, dependencies, aliases and source
  partition where `modinfo` exposes them.
- Runtime snapshots separately record stock and recovery loaded-module sets.

High-value device modules include FT3680 touch, Hynitron rear touch,
CO5300 rear LCD, Microarray fingerprint, YFT tiny2c USB, AW2013 RGB LED,
ST21NFC, camera/flash/actuator modules, MT6375/SH366003 gauges, SC8571/SC851x
chargers, speaker amp and YFT GPIO keys.

## Packaging model

Modules remain assigned to `vendor_dlkm`/`odm_dlkm`; they are not copied into a
generic recovery ramdisk. Recovery continues to rely on the stock PLATFORM
fragment and its verified recovery load ordering.

## UNKNOWN

A full build must validate depmod output, signing/vermagic, early-vs-late load
ordering, firmware dependencies and exact stock `modules.load*` semantics.
