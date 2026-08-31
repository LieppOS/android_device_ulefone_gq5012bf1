#!/usr/bin/env python3
"""Rebuild a vendor_boot v4 image, replacing only the RECOVERY ramdisk fragment.
PLATFORM fragment, DTB, bootconfig and all header fields are copied byte-for-byte."""
import struct, sys, hashlib

def pad(x, p): return (x + p - 1) // p * p

def repack(template, new_recovery, out):
    d = bytearray(open(template, 'rb').read())
    new = open(new_recovery, 'rb').read()
    assert d[:8] == b'VNDRBOOT'

    (hv, page, kaddr, raddr, vrs) = struct.unpack('<5I', d[8:28])
    assert hv >= 4, "need vendor_boot v4"
    o = 28 + 2048 + 4 + 16
    (header_size, dtb_size) = struct.unpack('<2I', d[o:o+8]); o += 8
    (dtb_addr,) = struct.unpack('<Q', d[o:o+8]); o += 8
    (tbl_sz, tbl_n, tbl_es, bootcfg) = struct.unpack('<4I', d[o:o+16])
    tbl_field_off = o

    rbase   = pad(header_size, page)
    dtb_off = rbase + pad(vrs, page)
    tbl_off = dtb_off + pad(dtb_size, page)
    bc_off  = tbl_off + pad(tbl_sz, page)

    dtb  = bytes(d[dtb_off:dtb_off+dtb_size])
    bc   = bytes(d[bc_off:bc_off+bootcfg])
    tbl  = bytearray(d[tbl_off:tbl_off+tbl_sz])

    # read table entries
    ents = []
    for i in range(tbl_n):
        e = tbl[i*tbl_es:(i+1)*tbl_es]
        sz, off, ty = struct.unpack('<3I', e[:12])
        nm = e[12:44].split(b'\0')[0].decode()
        ents.append([sz, off, ty, nm, i])

    # rebuild ramdisk section: keep order, swap RECOVERY(type 2) payload
    blobs, cur = [], 0
    for e in ents:
        blob = new if e[2] == 2 else bytes(d[rbase+e[1]:rbase+e[1]+e[0]])
        e[1] = cur          # new offset
        e[0] = len(blob)    # new size
        cur += len(blob)
        blobs.append(blob)
    ramdisk = b''.join(blobs)
    new_vrs = len(ramdisk)

    # write table entries back
    for e in ents:
        i = e[4]
        struct.pack_into('<3I', tbl, i*tbl_es, e[0], e[1], e[2])

    # header: update total vendor_ramdisk_size only
    struct.pack_into('<I', d, 24, new_vrs)

    hdr = bytes(d[:header_size]) + b'\0' * (pad(header_size, page) - header_size)
    img = (hdr
           + ramdisk + b'\0' * (pad(new_vrs, page) - new_vrs)
           + dtb     + b'\0' * (pad(dtb_size, page) - dtb_size)
           + bytes(tbl) + b'\0' * (pad(tbl_sz, page) - tbl_sz)
           + bc      + b'\0' * (pad(bootcfg, page) - bootcfg))
    open(out, 'wb').write(img)

    print("template            : %s" % template)
    print("new recovery frag   : %s (%d bytes, sha256=%s)" % (new_recovery, len(new), hashlib.sha256(new).hexdigest()))
    print("vendor_ramdisk_size : %d -> %d" % (vrs, new_vrs))
    print("output              : %s (%d bytes)" % (out, len(img)))
    for e in ents:
        blob = ramdisk[e[1]:e[1]+e[0]]
        print("  [%d] type=%d name=%-10s size=%-9d off=%-9d sha256=%s"
              % (e[4], e[2], e[3] or '-', e[0], e[1], hashlib.sha256(blob).hexdigest()))
    print("  dtb sha256=%s" % hashlib.sha256(dtb).hexdigest())

if __name__ == '__main__':
    repack(sys.argv[1], sys.argv[2], sys.argv[3])
