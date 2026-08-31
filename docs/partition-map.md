# Partition and boot map

## VERIFIED

- A/B and Virtual A/B are enabled.
- Dynamic partitions live in `super`; metadata version is 10.2 and the
  `virtual_ab_device` header flag is set.
- `super` size: **9,663,676,416 bytes**.
- Stock groups `main_a` and `main_b` each advertise a maximum of
  **9,661,579,264 bytes**.
- Logical partitions: `system`, `system_ext`, `product`, `vendor`,
  `system_dlkm`, `vendor_dlkm`, and `odm_dlkm`.
- Stock logical filesystems are EROFS.
- Boot-chain partitions include `boot`, `init_boot`, `vendor_boot`, `dtbo`,
  `vbmeta`, `vbmeta_system`, and `vbmeta_vendor`.
- `vendor_boot` is header v4, 64 MiB, and carries a PLATFORM fragment plus the
  type-2 RECOVERY fragment and wrapped DTB.
- `metadata` and `userdata` are F2FS.
- Userdata uses
  `aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized` with metadata keys under
  `/metadata/vold/metadata_encryption`.

## Safety invariant

Recovery packaging must reconstruct the final 64 MiB `vendor_boot` from the
stock PLATFORM fragment, generated RECOVERY fragment and stock DTB, then apply
and validate AVB. The raw build output is not automatically flash-safe.

## UNKNOWN / offline validation remaining

- Final OTA payload generation and snapshot merge behavior have not been build-
  or hardware-tested for the full ROM product.
- AVB signing policy for production LieppOS releases remains a release-level
  decision; stock keys must not be fabricated or redistributed.
