# vendor_boot DTB

`gq5012bf1-hbm.dtb` is the stock vendor_boot DTB table (sha256 `bc156c29…`)
with exactly two bytes changed: `/mtk-leds/backlight` `max-brightness` and
`max-hw-brightness` `0x7ff -> 0xfff`. This exposes the VTDR6115 panel's full
12-bit DBV range (2047 ≈ 513 nits normal max, 4095 ≈ 926 nits HBM). The
framework display config (`rootdir/etc/displayconfig/`) caps normal use at
DBV 2047 and uses HBM only for HDR content.
sha256 `73b6250bea56e93bba70e32ff96fd5d93a14dd32ae3be5a987d0b2caabae92cb`.
