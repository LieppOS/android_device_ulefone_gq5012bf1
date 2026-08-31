#!/usr/bin/env python3
"""Build reproducible stock/snapshot inventories for GQ5012BF1.

The tool is intentionally read-only with respect to its inputs. It consumes
extracted partition roots and the two live snapshots, then writes JSON and
Markdown under a caller-selected output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1


def relpath(path: Path, roots: dict[str, Path]) -> tuple[str, str]:
    for partition, root in roots.items():
        try:
            return partition, path.relative_to(root).as_posix()
        except ValueError:
            pass
    return "unknown", path.as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command(args: list[str]) -> str:
    try:
        result = subprocess.run(
            args,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return ""
    return result.stdout if result.returncode == 0 else ""


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def partition_roots(stock_root: Path) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    if not stock_root.is_dir():
        raise FileNotFoundError(f"stock partition root not found: {stock_root}")
    for entry in sorted(stock_root.iterdir()):
        if entry.is_dir():
            roots[entry.name] = entry.resolve()
    return roots


def stock_files(roots: dict[str, Path]) -> Iterable[Path]:
    for root in roots.values():
        yield from (path for path in root.rglob("*") if path.is_file())


def inventory_partitions(roots: dict[str, Path]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, root in roots.items():
        files = [path for path in root.rglob("*") if path.is_file()]
        suffixes = Counter(path.suffix.lower() or "<none>" for path in files)
        result[name] = {
            "root": str(root),
            "file_count": len(files),
            "byte_count": sum(path.stat().st_size for path in files),
            "top_suffixes": dict(suffixes.most_common(20)),
        }
    return result


def strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(node: ET.Element, name: str) -> str | None:
    for child in node:
        if strip_ns(child.tag) == name and child.text:
            return child.text.strip()
    return None


def inventory_vintf(roots: dict[str, Path]) -> dict[str, Any]:
    documents: list[dict[str, Any]] = []
    hals: list[dict[str, Any]] = []
    for partition, root in roots.items():
        for path in sorted(root.rglob("*.xml")):
            relative = path.relative_to(root).as_posix()
            if "/vintf/" not in f"/{relative}" and not relative.startswith("etc/vintf/"):
                continue
            try:
                tree = ET.parse(path)
            except ET.ParseError as exc:
                documents.append({"partition": partition, "path": relative, "parse_error": str(exc)})
                continue
            doc_root = tree.getroot()
            documents.append(
                {
                    "partition": partition,
                    "path": relative,
                    "kind": strip_ns(doc_root.tag),
                    "type": doc_root.attrib.get("type"),
                    "level": doc_root.attrib.get("level"),
                }
            )
            for node in doc_root.iter():
                if strip_ns(node.tag) != "hal":
                    continue
                interfaces: list[dict[str, Any]] = []
                fqnames: list[str] = []
                versions: list[str] = []
                for item in node:
                    tag = strip_ns(item.tag)
                    if tag == "fqname" and item.text:
                        fqnames.append(item.text.strip())
                    elif tag == "version" and item.text:
                        versions.append(item.text.strip())
                    elif tag == "interface":
                        interfaces.append(
                            {
                                "name": child_text(item, "name"),
                                "instances": [
                                    child.text.strip()
                                    for child in item
                                    if strip_ns(child.tag) in {"instance", "regex-instance"} and child.text
                                ],
                            }
                        )
                hals.append(
                    {
                        "partition": partition,
                        "source": relative,
                        "format": node.attrib.get("format", "hidl"),
                        "optional": node.attrib.get("optional"),
                        "name": child_text(node, "name"),
                        "transport": child_text(node, "transport"),
                        "versions": versions,
                        "fqnames": fqnames,
                        "interfaces": interfaces,
                    }
                )
    return {"documents": documents, "hals": hals}


def modinfo(path: Path, field: str) -> list[str]:
    value = command(["modinfo", "-F", field, str(path)]).strip()
    return [line for line in value.splitlines() if line]


def inventory_modules(
    roots: dict[str, Path], vendor_boot: Path | None, snapshots: dict[str, Path]
) -> dict[str, Any]:
    scan_roots = dict(roots)
    if vendor_boot and vendor_boot.is_dir():
        scan_roots["vendor_boot"] = vendor_boot.resolve()
    modules: list[dict[str, Any]] = []
    metadata: list[dict[str, Any]] = []
    for partition, root in scan_roots.items():
        for path in sorted(root.rglob("*.ko")):
            modules.append(
                {
                    "partition": partition,
                    "path": path.relative_to(root).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": sha256(path),
                    "name": (modinfo(path, "name") or [path.stem])[0],
                    "vermagic": (modinfo(path, "vermagic") or [None])[0],
                    "depends": sorted(
                        {
                            dep
                            for line in modinfo(path, "depends")
                            for dep in line.split(",")
                            if dep
                        }
                    ),
                    "aliases": modinfo(path, "alias"),
                    "description": (modinfo(path, "description") or [None])[0],
                }
            )
        for path in sorted(root.rglob("modules.*")):
            if path.is_file():
                metadata.append(
                    {
                        "partition": partition,
                        "path": path.relative_to(root).as_posix(),
                        "lines": [line for line in read_text(path).splitlines() if line.strip()],
                    }
                )
    loaded: dict[str, list[str]] = {}
    for name, snapshot in snapshots.items():
        path = snapshot / "kernel-modules.txt"
        if path.is_file():
            names: list[str] = []
            for line in read_text(path).splitlines():
                if not line.strip() or line.startswith("Module") or line.startswith("==="):
                    continue
                token = line.split()[0]
                if re.fullmatch(r"[A-Za-z0-9_.-]+", token):
                    names.append(token)
            loaded[name] = sorted(set(names))
    return {"modules": modules, "metadata": metadata, "loaded": loaded}


def parse_readelf(path: Path) -> dict[str, Any]:
    output = command(["readelf", "-h", "-d", "-lW", str(path)])
    if not output:
        return {"error": "readelf failed"}
    def one(pattern: str) -> str | None:
        match = re.search(pattern, output, re.MULTILINE)
        return match.group(1).strip() if match else None
    return {
        "class": one(r"^\s*Class:\s*(.+)$"),
        "type": one(r"^\s*Type:\s*(.+)$"),
        "machine": one(r"^\s*Machine:\s*(.+)$"),
        "soname": one(r"\(SONAME\).*?\[(.*?)\]"),
        "needed": sorted(set(re.findall(r"\(NEEDED\).*?\[(.*?)\]", output))),
        "interpreter": one(r"Requesting program interpreter:\s*([^\]]+)"),
    }


def inventory_elf(roots: dict[str, Path]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in stock_files(roots):
        try:
            with path.open("rb") as source:
                magic = source.read(4)
        except OSError:
            continue
        if magic != b"\x7fELF":
            continue
        partition, relative = relpath(path, roots)
        record = {
            "partition": partition,
            "path": relative,
            "size": path.stat().st_size,
            "sha256": sha256(path),
        }
        record.update(parse_readelf(path))
        records.append(record)
    sonames = {item["soname"] for item in records if item.get("soname")}
    basenames = {Path(item["path"]).name for item in records}
    unresolved = Counter(
        needed
        for item in records
        for needed in item.get("needed", [])
        if needed not in sonames and needed not in basenames
    )
    return {"elfs": records, "unresolved_dt_needed": dict(sorted(unresolved.items()))}


def parse_service(lines: list[str], start: int, source: str, partition: str) -> tuple[dict[str, Any], int]:
    header = lines[start].strip()
    try:
        tokens = shlex.split(header)
    except ValueError:
        tokens = header.split()
    service: dict[str, Any] = {
        "partition": partition,
        "source": source,
        "name": tokens[1] if len(tokens) > 1 else None,
        "command": tokens[2:] if len(tokens) > 2 else [],
        "options": defaultdict(list),
    }
    index = start + 1
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if stripped and not raw[:1].isspace():
            break
        if stripped and not stripped.startswith("#"):
            try:
                values = shlex.split(stripped)
            except ValueError:
                values = stripped.split()
            if values:
                service["options"][values[0]].append(values[1:])
        index += 1
    service["options"] = dict(service["options"])
    return service, index


def inventory_init(roots: dict[str, Path]) -> dict[str, Any]:
    services: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    imports: list[dict[str, str]] = []
    documents: list[dict[str, Any]] = []
    for partition, root in roots.items():
        for path in sorted(root.rglob("*.rc")):
            relative = path.relative_to(root).as_posix()
            if "/init/" not in f"/{relative}" and not Path(relative).name.startswith("init"):
                continue
            lines = read_text(path).splitlines()
            documents.append({"partition": partition, "path": relative, "lines": len(lines)})
            index = 0
            while index < len(lines):
                stripped = lines[index].strip()
                if stripped.startswith("service "):
                    service, index = parse_service(lines, index, relative, partition)
                    services.append(service)
                    continue
                if stripped.startswith("import "):
                    imports.append({"partition": partition, "source": relative, "path": stripped[7:].strip()})
                if stripped.startswith("on "):
                    commands: list[str] = []
                    cursor = index + 1
                    while cursor < len(lines):
                        raw = lines[cursor]
                        text = raw.strip()
                        if text and not raw[:1].isspace():
                            break
                        if text and not text.startswith("#"):
                            commands.append(text)
                        cursor += 1
                    actions.append(
                        {"partition": partition, "source": relative, "trigger": stripped[3:], "commands": commands}
                    )
                    index = cursor
                    continue
                index += 1
    return {"documents": documents, "services": services, "actions": actions, "imports": imports}


def parse_properties(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and "]: [" in stripped:
            key, value = stripped.split("]: [", 1)
            result[key[1:]] = value[:-1] if value.endswith("]") else value
        elif "=" in stripped:
            key, value = stripped.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def inventory_properties(roots: dict[str, Path], snapshots: dict[str, Path]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    merged: dict[str, dict[str, str]] = defaultdict(dict)
    for partition, root in roots.items():
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.name not in {"build.prop", "prop.default", "default.prop"} and path.suffix != ".prop":
                continue
            properties = parse_properties(read_text(path))
            if properties:
                relative = path.relative_to(root).as_posix()
                files.append({"partition": partition, "path": relative, "count": len(properties)})
                merged[partition].update(properties)
    snapshot_props: dict[str, dict[str, str]] = {}
    for name, snapshot in snapshots.items():
        path = snapshot / "properties.txt"
        if path.is_file():
            snapshot_props[name] = parse_properties(read_text(path))
    return {"files": files, "by_partition": dict(merged), "snapshots": snapshot_props}


def parse_bus_snapshot(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in read_text(path).splitlines():
        if line.startswith("### "):
            if current:
                records.append(current)
            current = {"node": line[4:].strip()}
        elif current is not None and "=" in line:
            key, value = line.split("=", 1)
            current[key.strip()] = value.strip()
    if current:
        records.append(current)
    return records


def parse_sensors(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    pattern = re.compile(
        r"^(0x[0-9a-f]+)\)\s+(.+?)\s+\|\s+(.+?)\s+\|\s+ver:\s*(\d+)\s+\|\s+"
        r"type:\s*([^()]+)\((\d+)\)\s+\|\s+perm:\s*([^|]+)\|\s+flags:\s*(0x[0-9a-f]+)",
        re.IGNORECASE,
    )
    result: list[dict[str, Any]] = []
    for line in read_text(path).splitlines():
        match = pattern.match(line)
        if match:
            result.append(
                {
                    "handle": match.group(1),
                    "name": match.group(2).strip(),
                    "vendor": match.group(3).strip(),
                    "version": int(match.group(4)),
                    "type": match.group(5).strip(),
                    "type_id": int(match.group(6)),
                    "permission": match.group(7).strip(),
                    "flags": match.group(8),
                }
            )
    return result


def parse_inputs(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    devices: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in read_text(path).splitlines():
        match = re.match(r"add device \d+: (\S+)", line)
        if match:
            if current:
                devices.append(current)
            current = {"node": match.group(1), "events": []}
            continue
        if current is None:
            continue
        name = re.match(r'\s+name:\s+"(.*)"', line)
        if name:
            current["name"] = name.group(1)
        event = re.match(r"\s+(KEY|ABS|SW) \([^)]+\):\s*(.*)", line)
        if event:
            current["events"].append({"type": event.group(1), "values": event.group(2).strip()})
    if current:
        devices.append(current)
    return devices


def parse_power_supplies(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    supplies: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in read_text(path).splitlines():
        match = re.match(r"/sys/class/power_supply/([^ ]+) -> (.+)", line)
        if match:
            if current:
                supplies.append(current)
            current = {"name": match.group(1), "target": match.group(2), "attributes": {}}
            continue
        if current is not None and "=" in line and not line.startswith("POWER_SUPPLY_"):
            key, value = line.split("=", 1)
            current["attributes"][key] = value
        elif current is not None and line.startswith("POWER_SUPPLY_") and "=" in line:
            key, value = line.split("=", 1)
            current["attributes"][key.removeprefix("POWER_SUPPLY_").lower()] = value
    if current:
        supplies.append(current)
    return supplies


def parse_cameras(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"count": None, "ids": []}
    text = read_text(path)
    count_match = re.search(r"Number of camera devices:\s*(\d+)", text)
    ids = sorted(set(re.findall(r"Camera ID:\s*([^\s]+)", text)))
    pixel_arrays = re.findall(r"android\.sensor\.info\.pixelArraySize[^\n]*\n\s*\[\s*(\d+)\s+(\d+)\s*\]", text)
    return {
        "count": int(count_match.group(1)) if count_match else None,
        "ids": ids,
        "pixel_array_sizes": [{"width": int(w), "height": int(h)} for w, h in pixel_arrays],
    }


def inventory_snapshots(snapshots: dict[str, Path]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, root in snapshots.items():
        if not root.is_dir():
            raise FileNotFoundError(f"{name} snapshot not found: {root}")
        files = sorted(path for path in root.iterdir() if path.is_file())
        result[name] = {
            "root": str(root.resolve()),
            "files": {path.name: {"size": path.stat().st_size, "sha256": sha256(path)} for path in files},
            "i2c": parse_bus_snapshot(root / "i2c.txt"),
            "spi": parse_bus_snapshot(root / "spi.txt"),
            "sensors": parse_sensors(root / "sensors-dump.txt"),
            "inputs": parse_inputs(root / "getevent.txt"),
            "power_supplies": parse_power_supplies(root / "power-supply.txt"),
            "cameras": parse_cameras(root / "camera-dump.txt"),
        }
    return result


def proprietary_candidates(roots: dict[str, Path], elfs: dict[str, Any]) -> list[str]:
    candidates: set[str] = set()
    elf_paths = {(item["partition"], item["path"]) for item in elfs["elfs"]}
    preferred_prefixes = (
        "bin/hw/", "lib64/hw/", "lib/hw/", "etc/vintf/", "etc/init/",
        "etc/permissions/", "etc/sysconfig/", "etc/firmware/", "firmware/",
        "app/", "priv-app/", "overlay/", "etc/camera/", "etc/audio/",
        "etc/bluetooth/", "etc/wifi/", "etc/gnss/", "etc/sensors/", "etc/thermal/",
    )
    for partition, root in roots.items():
        if partition not in {"vendor", "odm", "product", "system_ext", "vendor_dlkm", "odm_dlkm"}:
            continue
        for path in (item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(root).as_posix()
            if (partition, relative) in elf_paths or relative.startswith(preferred_prefixes) or path.suffix == ".ko":
                candidates.add(f"{partition}/{relative}")
    return sorted(candidates)


def markdown_summary(
    partitions: dict[str, Any], vintf: dict[str, Any], modules: dict[str, Any],
    elfs: dict[str, Any], init: dict[str, Any], snapshots: dict[str, Any], candidates: list[str]
) -> str:
    stock = snapshots.get("stock", {})
    lines = [
        "# Generated GQ5012BF1 evidence summary",
        "",
        "> Generated by `tools/inventory_device.py`. Do not hand-edit this file.",
        "",
        "## Inventory counts",
        "",
        "| Area | Count |",
        "|---|---:|",
        f"| Stock partitions | {len(partitions)} |",
        f"| VINTF documents | {len(vintf['documents'])} |",
        f"| HAL declarations | {len(vintf['hals'])} |",
        f"| Kernel modules | {len(modules['modules'])} |",
        f"| ELF files | {len(elfs['elfs'])} |",
        f"| Init services | {len(init['services'])} |",
        f"| Proprietary candidates | {len(candidates)} |",
        "",
        "## Live stock hardware",
        "",
        f"- I2C bound/device records: **{len(stock.get('i2c', []))}**",
        f"- SPI bound/device records: **{len(stock.get('spi', []))}**",
        f"- Android sensor records: **{len(stock.get('sensors', []))}**",
        f"- Input devices: **{len(stock.get('inputs', []))}**",
        f"- Power supplies: **{len(stock.get('power_supplies', []))}**",
        f"- Camera devices: **{stock.get('cameras', {}).get('count')}**",
        "",
        "## Physical sensor identities",
        "",
        "| Name | Vendor | Android type |",
        "|---|---|---|",
    ]
    for sensor in stock.get("sensors", []):
        if sensor["vendor"] not in {"mtk", "AOSP"}:
            lines.append(f"| `{sensor['name']}` | `{sensor['vendor']}` | `{sensor['type']}` |")
    lines += ["", "## Bound SPI devices", "", "| Node | Driver | Module |", "|---|---|---|"]
    for item in stock.get("spi", []):
        lines.append(f"| `{item.get('node')}` | `{item.get('driver', 'UNKNOWN')}` | `{item.get('module', 'UNKNOWN')}` |")
    lines += ["", "## Notes", "", "- JSON files are the machine-readable source of truth.", "- `unresolved_dt_needed` includes platform/APEX libraries outside the extracted roots and therefore needs human triage; it is not automatically a missing-blob verdict.", ""]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-root", type=Path, required=True, help="directory containing extracted partition roots")
    parser.add_argument("--stock-snapshot", type=Path, required=True)
    parser.add_argument("--recovery-snapshot", type=Path, required=True)
    parser.add_argument("--vendor-boot", type=Path, help="optional extracted vendor_boot platform ramdisk")
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    roots = partition_roots(args.stock_root.resolve())
    snapshots = {
        "stock": args.stock_snapshot.resolve(),
        "recovery": args.recovery_snapshot.resolve(),
    }
    print(f"inventorying {len(roots)} partitions", file=sys.stderr)
    partitions = inventory_partitions(roots)
    print("inventorying snapshots", file=sys.stderr)
    snapshot_data = inventory_snapshots(snapshots)
    print("inventorying VINTF", file=sys.stderr)
    vintf = inventory_vintf(roots)
    print("inventorying modules", file=sys.stderr)
    modules = inventory_modules(roots, args.vendor_boot, snapshots)
    print("inventorying ELF dependencies", file=sys.stderr)
    elfs = inventory_elf(roots)
    print("inventorying init", file=sys.stderr)
    init = inventory_init(roots)
    print("inventorying properties", file=sys.stderr)
    properties = inventory_properties(roots, snapshots)
    candidates = proprietary_candidates(roots, elfs)

    metadata = {
        "schema_version": SCHEMA_VERSION,
        "inputs": {
            "stock_root": str(args.stock_root.resolve()),
            "stock_snapshot": str(args.stock_snapshot.resolve()),
            "recovery_snapshot": str(args.recovery_snapshot.resolve()),
            "vendor_boot": str(args.vendor_boot.resolve()) if args.vendor_boot else None,
        },
    }
    outputs = {
        "metadata.json": metadata,
        "partitions.json": partitions,
        "snapshots.json": snapshot_data,
        "vintf.json": vintf,
        "modules.json": modules,
        "elf.json": elfs,
        "init.json": init,
        "properties.json": properties,
        "proprietary-candidates.json": candidates,
    }
    for filename, value in outputs.items():
        write_json(args.out / filename, value)
    (args.out / "proprietary-candidates.txt").write_text("\n".join(candidates) + "\n")
    (args.out / "summary.md").write_text(
        markdown_summary(partitions, vintf, modules, elfs, init, snapshot_data, candidates)
    )
    print(
        f"wrote {len(outputs) + 2} outputs: {len(vintf['hals'])} HALs, "
        f"{len(modules['modules'])} modules, {len(elfs['elfs'])} ELFs, "
        f"{len(init['services'])} services, {len(candidates)} candidates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
