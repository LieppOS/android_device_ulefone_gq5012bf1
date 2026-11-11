#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inspect, normalise and compare GQ5012BF1 DTBO images and overlays.

No third-party dependencies (no libfdt). Subcommands:

  info IMG              Android DTBO table, MediaTek cert blocks, AVB footer
  extract IMG DIR       write every table entry to DIR/entry-NN-id-X-rev-Y.dtbo
  canon DTBO            phandle-independent text form of an overlay: fragment
                        targets and phandle cells are resolved to labels
                        (__fixups__) or overlay-local node paths
                        (__local_fixups__); phandle values are dropped
  effective DTBO        like canon, but fragments that share a target are
                        merged in application order, giving the effective
                        change per target node
  compare A B           canon + effective comparison of two overlays/images
  mtkcert IMG           check the MediaTek cert2 hashes against the image
  labels DTBO BASE      every overlay label resolves in the base __symbols__
  apply BASE A B        fdtoverlay A and B onto BASE, compare merged trees

BASE may be a raw FDT or an Android DT table (vendor_boot dtb section).

An argument that is an Android DTBO image (magic d7b7ab1e) uses entry 0
unless --entry is given.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import os
import struct
import sys

DT_TABLE_MAGIC = 0xD7B7AB1E
FDT_MAGIC = 0xD00DFEED
MTK_CERT_MAGIC = b"\x88\x16\x88\x58"  # 0x58881688 little endian


# --------------------------------------------------------------------------
# Android DTBO table


def parse_table(data: bytes) -> dict:
    (magic, total, hsz, esz, count, eoff, page, ver) = struct.unpack(">8I", data[:32])
    if magic != DT_TABLE_MAGIC:
        raise ValueError("not an Android DTBO table (magic %08x)" % magic)
    entries = []
    for i in range(count):
        o = eoff + i * esz
        size, off, eid, rev, c0, c1, c2, c3 = struct.unpack(">8I", data[o:o + 32])
        entries.append(dict(index=i, size=size, offset=off, id=eid, rev=rev,
                            custom=[c0, c1, c2, c3]))
    return dict(magic=magic, total_size=total, header_size=hsz, entry_size=esz,
                entry_count=count, entries_offset=eoff, page_size=page,
                version=ver, entries=entries)


def avb_footer(data: bytes):
    if len(data) < 64 or data[-64:-60] != b"AVBf":
        return None
    maj, mnr, orig, vboff, vbsz = struct.unpack(">IIQQQ", data[-60:-28])
    return dict(version="%d.%d" % (maj, mnr), original_size=orig,
                vbmeta_offset=vboff, vbmeta_size=vbsz)


def mtk_certs(data: bytes, start: int, end: int) -> list:
    out = []
    i = start
    while True:
        j = data.find(MTK_CERT_MAGIC, i, end)
        if j < 0:
            break
        size = struct.unpack("<I", data[j + 4:j + 8])[0]
        name = data[j + 8:j + 40].split(b"\0")[0].decode("ascii", "replace")
        out.append(dict(offset=j, der_offset=j + 512, der_size=size, name=name))
        i = j + 4
    return out


def load_overlay(path: str, entry: int = 0) -> bytes:
    data = open(path, "rb").read()
    magic = struct.unpack(">I", data[:4])[0]
    if magic == FDT_MAGIC:
        return data[:struct.unpack(">I", data[4:8])[0]]
    if magic == DT_TABLE_MAGIC:
        e = parse_table(data)["entries"][entry]
        return data[e["offset"]:e["offset"] + e["size"]]
    raise ValueError("%s: neither FDT nor DTBO table" % path)


# --------------------------------------------------------------------------
# FDT


class Node:
    def __init__(self, name: str, parent=None):
        self.name = name
        self.parent = parent
        self.props: list[tuple[str, bytes]] = []
        self.children: list[Node] = []

    @property
    def path(self) -> str:
        if self.parent is None:
            return "/"
        pp = self.parent.path
        return (pp if pp != "/" else "") + "/" + self.name

    def child(self, name):
        for c in self.children:
            if c.name == name:
                return c
        return None

    def prop(self, name):
        for n, v in self.props:
            if n == name:
                return v
        return None

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


def parse_fdt(blob: bytes) -> Node:
    (magic, total, off_struct, off_strings, off_rsv, ver, last, boot_cpu,
     sz_strings, sz_struct) = struct.unpack(">10I", blob[:40])
    if magic != FDT_MAGIC:
        raise ValueError("bad FDT magic")
    strings = blob[off_strings:off_strings + sz_strings]
    p = off_struct
    root = None
    cur = None
    while True:
        tok = struct.unpack(">I", blob[p:p + 4])[0]
        p += 4
        if tok == 1:  # BEGIN_NODE
            e = blob.index(b"\0", p)
            name = blob[p:e].decode()
            p = (e + 4) & ~3
            n = Node(name, cur)
            if cur is None:
                root = n
            else:
                cur.children.append(n)
            cur = n
        elif tok == 2:  # END_NODE
            cur = cur.parent
        elif tok == 3:  # PROP
            ln, nameoff = struct.unpack(">II", blob[p:p + 8])
            p += 8
            val = blob[p:p + ln]
            p = (p + ln + 3) & ~3
            name = strings[nameoff:strings.index(b"\0", nameoff)].decode()
            cur.props.append((name, val))
        elif tok == 4:  # NOP
            continue
        elif tok == 9:  # END
            break
        else:
            raise ValueError("bad FDT token %d" % tok)
    return root


def lookup(root: Node, path: str):
    n = root
    for part in [x for x in path.split("/") if x]:
        n = n.child(part)
        if n is None:
            return None
    return n


# --------------------------------------------------------------------------
# Overlay normalisation


def _is_strings(v: bytes) -> bool:
    if not v or v[-1] != 0:
        return False
    for s in v[:-1].split(b"\0"):
        if not s:
            return False
        if any(c < 0x20 or c > 0x7E for c in s):
            return False
    return True


class Overlay:
    def __init__(self, blob: bytes):
        self.root = parse_fdt(blob)
        r = self.root
        self.symbols = {n: v.rstrip(b"\0").decode() for n, v in
                        (r.child("__symbols__").props if r.child("__symbols__") else [])}
        # (path, prop, offset) -> label
        self.ext = {}
        fx = r.child("__fixups__")
        for label, v in (fx.props if fx else []):
            for item in v.rstrip(b"\0").split(b"\0"):
                path, prop, off = item.decode().rsplit(":", 2)
                self.ext[(path, prop, int(off))] = label
        # (path, prop) -> [offsets] for local phandle references
        self.loc = {}
        lf = r.child("__local_fixups__")
        if lf:
            for n in lf.walk():
                rel = n.path[len("/__local_fixups__"):] or "/"
                for prop, v in n.props:
                    self.loc[(rel, prop)] = list(struct.unpack(">%dI" % (len(v) // 4), v))
        self.ph2path = {}
        for n in r.walk():
            if n.path.startswith(("/__symbols__", "/__fixups__", "/__local_fixups__")):
                continue
            for pn in ("phandle", "linux,phandle"):
                v = n.prop(pn)
                if v is not None:
                    self.ph2path[struct.unpack(">I", v)[0]] = n.path

    def fragments(self):
        return [c for c in self.root.children if not c.name.startswith("__")]

    def target_of(self, frag: Node) -> str:
        if (frag.path, "target", 0) in self.ext:
            return "&" + self.ext[(frag.path, "target", 0)]
        tp = frag.prop("target-path")
        if tp is not None:
            return "path:" + tp.rstrip(b"\0").decode()
        t = frag.prop("target")
        if t is not None:
            return "local:%s" % self.ph2path.get(struct.unpack(">I", t)[0], "?")
        return "?"

    def _local_name(self, path: str) -> str:
        """Overlay-local node path with the fragment number replaced by its
        target, so renumbered fragments compare equal."""
        parts = path.split("/")
        if len(parts) > 2 and parts[1].startswith("fragment@"):
            frag = self.root.child(parts[1])
            rest = "/".join(parts[3:])  # drop fragment@N/__overlay__
            return "{%s}/%s" % (self.target_of(frag), rest)
        return path

    def render_value(self, node_path: str, prop: str, v: bytes) -> str:
        refs = {}
        for (p, pr, off), label in self.ext.items():
            if p == node_path and pr == prop:
                refs[off] = "&" + label
        for off in self.loc.get((node_path, prop), []):
            ph = struct.unpack(">I", v[off:off + 4])[0]
            refs[off] = "&{%s}" % self._local_name(self.ph2path.get(ph, "?%x" % ph))
        if refs or (v and len(v) % 4 == 0 and not _is_strings(v)):
            if len(v) % 4:
                return "[%s] refs=%s" % (v.hex(), refs)
            cells = []
            for i in range(0, len(v), 4):
                cells.append(refs.get(i, "0x%x" % struct.unpack(">I", v[i:i + 4])[0]))
            return "<%s>" % " ".join(cells)
        if not v:
            return "<empty>"
        if _is_strings(v):
            return ", ".join('"%s"' % s.decode() for s in v[:-1].split(b"\0"))
        return "[%s]" % v.hex()

    def render_node(self, n: Node, indent: int, out: list):
        pad = "  " * indent
        for prop, v in n.props:
            if prop in ("phandle", "linux,phandle"):
                out.append("%s%s = <PHANDLE>" % (pad, prop))
                continue
            out.append("%s%s = %s" % (pad, prop, self.render_value(n.path, prop, v)))
        for c in n.children:
            out.append("%s%s {" % (pad, c.name))
            self.render_node(c, indent + 1, out)
            out.append("%s}" % pad)

    def canon(self) -> list:
        out = []
        for f in self.fragments():
            out.append("%s -> %s {" % (f.name, self.target_of(f)))
            ov = f.child("__overlay__")
            if ov is not None:
                self.render_node(ov, 1, out)
            extra = [p for p, _ in f.props if p not in ("target", "target-path")]
            if extra:
                out.append("  # extra fragment props: %s" % extra)
            out.append("}")
        out.append("__symbols__ {")
        for label, path in sorted(self.symbols.items()):
            out.append("  %s = %s" % (label, self._local_name(path)))
        out.append("}")
        return out

    def effective(self) -> list:
        """Merge fragments per target in application order."""
        merged: dict[str, dict] = {}
        order: list[str] = []

        def merge(n: Node, d: dict):
            for prop, v in n.props:
                if prop in ("phandle", "linux,phandle"):
                    d.setdefault("__props__", {})[prop] = "<PHANDLE>"
                else:
                    d.setdefault("__props__", {})[prop] = self.render_value(n.path, prop, v)
            for c in n.children:
                merge(c, d.setdefault(c.name, {}))

        for f in self.fragments():
            t = self.target_of(f)
            if t not in merged:
                merged[t] = {}
                order.append(t)
            ov = f.child("__overlay__")
            if ov is not None:
                merge(ov, merged[t])

        out = []

        def emit(d: dict, indent: int):
            pad = "  " * indent
            for prop, val in sorted(d.get("__props__", {}).items()):
                out.append("%s%s = %s" % (pad, prop, val))
            for name in sorted(k for k in d if k != "__props__"):
                out.append("%s%s {" % (pad, name))
                emit(d[name], indent + 1)
                out.append("%s}" % pad)

        for t in sorted(order):
            out.append("%s {" % t)
            emit(merged[t], 1)
            out.append("}")
        return out


# --------------------------------------------------------------------------
# commands


def cmd_info(a):
    data = open(a.image, "rb").read()
    t = parse_table(data)
    print("file: %s (%d bytes) sha256 %s" % (a.image, len(data), hashlib.sha256(data).hexdigest()))
    for k in ("magic", "total_size", "header_size", "entry_size", "entry_count",
              "entries_offset", "page_size", "version"):
        v = t[k]
        print("  %-15s %s" % (k, hex(v) if k == "magic" else v))
    for e in t["entries"]:
        blob = data[e["offset"]:e["offset"] + e["size"]]
        fdt_magic = struct.unpack(">I", blob[:4])[0]
        ov = Overlay(blob)
        frags = ov.fragments()
        root_compat = ov.root.prop("compatible")
        print("  entry %d: offset %d size %d id 0x%x rev 0x%x custom %s" % (
            e["index"], e["offset"], e["size"], e["id"], e["rev"], e["custom"]))
        print("    fdt magic %08x  sha256 %s" % (fdt_magic, hashlib.sha256(blob).hexdigest()))
        print("    root compatible: %s" % (root_compat.rstrip(b"\0").decode() if root_compat else "(none)"))
        print("    fragments: %d  distinct targets: %d  __symbols__: %d  "
              "__fixups__ labels: %d (%d refs)  __local_fixups__ refs: %d" % (
                  len(frags), len({ov.target_of(f) for f in frags}), len(ov.symbols),
                  len({v for v in ov.ext.values()}), len(ov.ext),
                  sum(len(v) for v in ov.loc.values())))
    footer = avb_footer(data)
    end = footer["original_size"] if footer else len(data)
    certs = mtk_certs(data, t["total_size"], end)
    tail = data[t["total_size"]:end]
    print("  bytes after DT table up to %s: %d" % ("AVB original size" if footer else "EOF", len(tail)))
    for c in certs:
        print("    MediaTek cert block '%s' at %d (DER %d bytes at %d)" % (
            c["name"], c["offset"], c["der_size"], c["der_offset"]))
    if footer:
        print("  AVB footer: version %s original_size %d vbmeta_offset %d vbmeta_size %d" % (
            footer["version"], footer["original_size"], footer["vbmeta_offset"], footer["vbmeta_size"]))
    else:
        print("  AVB footer: none")


def cmd_extract(a):
    data = open(a.image, "rb").read()
    t = parse_table(data)
    os.makedirs(a.dir, exist_ok=True)
    for e in t["entries"]:
        name = "entry-%02d-id-%08x-rev-%08x.dtbo" % (e["index"], e["id"], e["rev"])
        with open(os.path.join(a.dir, name), "wb") as f:
            f.write(data[e["offset"]:e["offset"] + e["size"]])
        print(name)


def cmd_canon(a):
    print("\n".join(Overlay(load_overlay(a.dtbo, a.entry)).canon()))


def cmd_effective(a):
    print("\n".join(Overlay(load_overlay(a.dtbo, a.entry)).effective()))


def cmd_compare(a):
    ba, bb = load_overlay(a.a, a.entry), load_overlay(a.b, a.entry)
    oa, ob = Overlay(ba), Overlay(bb)
    rc = 0
    print("binary: %s" % ("IDENTICAL" if ba == bb else "differs (%d vs %d bytes)" % (len(ba), len(bb))))
    for kind in ("canon", "effective"):
        la, lb = getattr(oa, kind)(), getattr(ob, kind)()
        d = list(difflib.unified_diff(la, lb, a.a, a.b, lineterm="", n=2))
        print("%s: %s" % (kind, "IDENTICAL" if not d else "%d diff lines" % len(d)))
        if d:
            rc = 1
            if a.verbose or kind == "effective":
                print("\n".join(d[:a.max_lines]))
    return rc


def cmd_mtkcert(a):
    """cert2 carries sha256(header[0:32]) (OID 2.16.886.2454.2.4) and
    sha256(data[32:cert1]) (OID ...2.1); report whether they match."""
    data = open(a.image, "rb").read()
    t = parse_table(data)
    footer = avb_footer(data)
    end = footer["original_size"] if footer else len(data)
    certs = mtk_certs(data, t["total_size"], end)
    if not certs:
        print("no MediaTek cert blocks")
        return 2
    c2 = [c for c in certs if c["name"] == "cert2"]
    if not c2:
        print("no cert2 block")
        return 2
    der = data[c2[0]["der_offset"]:c2[0]["der_offset"] + c2[0]["der_size"]]
    oid = {b"\x06\x07\x60\x86\x76\x93\x16\x02\x01": "img_hash",
           b"\x06\x07\x60\x86\x76\x93\x16\x02\x04": "hdr_hash"}
    found = {}
    for k, name in oid.items():
        i = der.find(k)
        if i >= 0 and der[i + 9] == 0x03 and der[i + 10] == 0x21:
            found[name] = der[i + 12:i + 44]
    signed_end = certs[0]["offset"]
    calc = {"hdr_hash": hashlib.sha256(data[0:32]).digest(),
            "img_hash": hashlib.sha256(data[32:signed_end]).digest()}
    ok = True
    for name in ("hdr_hash", "img_hash"):
        got = found.get(name)
        m = got == calc[name]
        ok &= m
        print("%s: cert %s computed %s -> %s" % (
            name, got.hex() if got else "missing", calc[name].hex(), "MATCH" if m else "MISMATCH"))
    print("covered bytes: 0..%d" % signed_end)
    return 0 if ok else 1


def load_base(path: str) -> bytes:
    """Base FDT, or the single FDT inside an Android DT table (vendor_boot dtb)."""
    data = open(path, "rb").read()
    if struct.unpack(">I", data[:4])[0] == DT_TABLE_MAGIC:
        e = parse_table(data)["entries"][0]
        return data[e["offset"]:e["offset"] + e["size"]]
    return data[:struct.unpack(">I", data[4:8])[0]]


def cmd_labels(a):
    """Every __fixups__ label must exist in the base __symbols__ and point at
    an existing node; report the base node each fragment lands on."""
    ov = Overlay(load_overlay(a.dtbo, a.entry))
    base = parse_fdt(load_base(a.base))
    sym = base.child("__symbols__")
    bsyms = {n: v.rstrip(b"\0").decode() for n, v in (sym.props if sym else [])}
    missing, dangling = [], []
    for label in sorted(set(ov.ext.values())):
        if label not in bsyms:
            missing.append(label)
        elif lookup(base, bsyms[label]) is None:
            dangling.append(label)
    print("base: %s  __symbols__: %d" % (a.base, len(bsyms)))
    print("overlay labels needed: %d  missing: %d  dangling: %d" % (
        len(set(ov.ext.values())), len(missing), len(dangling)))
    for m in missing:
        print("  MISSING %s" % m)
    for m in dangling:
        print("  DANGLING %s -> %s" % (m, bsyms[m]))
    if a.verbose:
        for f in ov.fragments():
            t = ov.target_of(f)
            print("  %-12s %-26s -> %s" % (f.name, t, bsyms.get(t[1:], "?")))
    return 1 if missing or dangling else 0


def _apply(base_blob: bytes, ov_blob: bytes, workdir: str, tag: str) -> bytes:
    import subprocess
    b = os.path.join(workdir, tag + ".base.dtb")
    o = os.path.join(workdir, tag + ".dtbo")
    m = os.path.join(workdir, tag + ".merged.dtb")
    open(b, "wb").write(base_blob)
    open(o, "wb").write(ov_blob)
    r = subprocess.run(["fdtoverlay", "-i", b, "-o", m, o], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("fdtoverlay failed for %s: %s" % (tag, r.stderr.strip()))
    return open(m, "rb").read()


def _tree_lines(root: Node) -> list:
    out = []
    for n in root.walk():
        out.append(n.path + " {")
        for p, v in n.props:
            out.append("  %s = %s" % (p, v.hex()))
    return out


def cmd_apply(a):
    """fdtoverlay both overlays onto BASE and compare the merged trees."""
    import tempfile
    base = load_base(a.base)
    with tempfile.TemporaryDirectory() as td:
        try:
            ma = _apply(base, load_overlay(a.a, a.entry), td, "a")
            mb = _apply(base, load_overlay(a.b, a.entry), td, "b")
        except RuntimeError as e:
            print("base %s: %s" % (a.base, e))
            return 2
        if a.save:
            open(a.save, "wb").write(mb)
    print("base %s (%d bytes): merged A %d bytes, merged B %d bytes" % (
        a.base, len(base), len(ma), len(mb)))
    if ma == mb:
        print("merged trees: BYTE-IDENTICAL")
        return 0
    d = list(difflib.unified_diff(_tree_lines(parse_fdt(ma)), _tree_lines(parse_fdt(mb)),
                                  lineterm="", n=1))
    print("merged trees: %d diff lines" % len(d))
    print("\n".join(d[:a.max_lines]))
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entry", type=int, default=0)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info"); p.add_argument("image"); p.set_defaults(fn=cmd_info)
    p = sub.add_parser("extract"); p.add_argument("image"); p.add_argument("dir"); p.set_defaults(fn=cmd_extract)
    p = sub.add_parser("canon"); p.add_argument("dtbo"); p.set_defaults(fn=cmd_canon)
    p = sub.add_parser("effective"); p.add_argument("dtbo"); p.set_defaults(fn=cmd_effective)
    p = sub.add_parser("compare"); p.add_argument("a"); p.add_argument("b")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--max-lines", type=int, default=400)
    p.set_defaults(fn=cmd_compare)
    p = sub.add_parser("mtkcert"); p.add_argument("image"); p.set_defaults(fn=cmd_mtkcert)
    p = sub.add_parser("labels"); p.add_argument("dtbo"); p.add_argument("base")
    p.add_argument("-v", "--verbose", action="store_true"); p.set_defaults(fn=cmd_labels)
    p = sub.add_parser("apply"); p.add_argument("base"); p.add_argument("a"); p.add_argument("b")
    p.add_argument("--save"); p.add_argument("--max-lines", type=int, default=200)
    p.set_defaults(fn=cmd_apply)
    a = ap.parse_args()
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
