#!/usr/bin/env python3
import struct, sys, os, hashlib

def pad(x, p): return (x + p - 1) // p * p

def unpack(path, outdir=None):
    d = open(path, 'rb').read()
    assert d[:8] == b'VNDRBOOT', 'not vendor_boot: %s' % path
    (hv, page_size, kaddr, raddr, vrs) = struct.unpack('<5I', d[8:28])
    off = 28 + 2048
    (tags_addr,) = struct.unpack('<I', d[off:off+4]); off += 4
    name = d[off:off+16]; off += 16
    (header_size, dtb_size) = struct.unpack('<2I', d[off:off+8]); off += 8
    (dtb_addr,) = struct.unpack('<Q', d[off:off+8]); off += 8
    res = {'path': path, 'hv': hv, 'page_size': page_size,
           'vendor_ramdisk_size': vrs, 'dtb_size': dtb_size,
           'filesize': len(d)}
    if hv >= 4:
        (tbl_sz, tbl_n, tbl_es, bootcfg) = struct.unpack('<4I', d[off:off+16]); off += 16
        res.update(tbl_size=tbl_sz, tbl_n=tbl_n, tbl_es=tbl_es, bootconfig=bootcfg)

    o = pad(header_size, page_size)
    ramdisk_base = o
    o += pad(vrs, page_size)
    dtb_off = o
    o += pad(dtb_size, page_size)
    tbl_off = o

    entries = []
    if hv >= 4:
        for i in range(tbl_n):
            e = d[tbl_off + i*tbl_es : tbl_off + (i+1)*tbl_es]
            rsz, roff, rtype = struct.unpack('<3I', e[:12])
            rname = e[12:12+32].split(b'\0')[0].decode('utf-8', 'replace')
            blob = d[ramdisk_base + roff : ramdisk_base + roff + rsz]
            entries.append({'idx': i, 'size': rsz, 'offset': roff, 'type': rtype,
                            'name': rname, 'sha256': hashlib.sha256(blob).hexdigest()})
            if outdir:
                os.makedirs(outdir, exist_ok=True)
                fn = os.path.join(outdir, 'ramdisk_%d_%s_type%d.lz4' % (i, rname or 'noname', rtype))
                open(fn, 'wb').write(blob)
                entries[-1]['file'] = fn
    res['entries'] = entries
    res['dtb_sha256'] = hashlib.sha256(d[dtb_off:dtb_off+dtb_size]).hexdigest()
    res['bootconfig'] = d[o + pad(res.get('tbl_size',0), page_size):][:res.get('bootconfig',0)].decode('utf-8','replace') if hv>=4 else ''
    return res

TYPES = {0:'NONE',1:'PLATFORM',2:'RECOVERY',3:'DLKM'}
for p in sys.argv[1:]:
    label = os.path.basename(os.path.dirname(p)) or 'x'
    r = unpack(p, '/tmp/vb-%s' % label)
    print('=== %s' % p)
    print('  hdr_v%d page=%d filesize=%d vendor_ramdisk_size=%d dtb_size=%d dtb_sha256=%s'
          % (r['hv'], r['page_size'], r['filesize'], r['vendor_ramdisk_size'], r['dtb_size'], r['dtb_sha256']))
    for e in r['entries']:
        print('  [%d] %-10s name=%-12s size=%-9d off=%-9d sha256=%s'
              % (e['idx'], TYPES.get(e['type'], e['type']), e['name'], e['size'], e['offset'], e['sha256']))
    if r['bootconfig'].strip():
        print('  bootconfig: %r' % r['bootconfig'][:200])
