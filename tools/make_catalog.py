#!/usr/bin/env python3
"""Writes catalog.json from the .3dpack files in packs/ (run by .github/workflows/catalog.yml on every push).

The 3DPCS Controller Tool's Pack Manager downloads catalog.json: it lists every pack with a Download button, and a pack
is Official in the app when its exact file hash is in this catalog (current or older version).

- Add a pack:     drop the .3dpack into packs/ and push.
- Update a pack:  replace the file with the new version (higher "version" in its manifest) and push. The old file's
                  hash moves to "older", so copies people already have still count as official and show Update.
- Retire a pack:  delete the file. It stays in the catalog as "retired" (not offered, still trusted); delete its
                  entry from catalog.json by hand to stop trusting it.
Standard library only. Usage: python3 tools/make_catalog.py [--check]
"""
import base64, hashlib, json, sys, zipfile
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
PACKS = ROOT / "packs"
OUT = ROOT / "catalog.json"
RAW = "https://raw.githubusercontent.com/3D-Printed-Controller-Systems/3DPCS-Programmer-Releases/packs/packs/"
MAX_PACK = 2 * 1024 * 1024
MAX_ICON = 24 * 1024
FRETS = ["Green", "Red", "Yellow", "Blue", "Orange"]


def ver(v):
    try: return tuple(int(x) for x in v.split("."))
    except ValueError: sys.exit(f"bad version {v!r}")


def read(path):
    if path.suffix != ".3dpack":
        sys.exit(f"packs/{path.name}: only .3dpack files go in packs/ (rename it to .3dpack if it's a pack)")
    data = path.read_bytes()
    if len(data) > MAX_PACK: sys.exit(f"{path.name}: over 2 MB")
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    if "manifest.json" not in files: sys.exit(f"{path.name}: no manifest.json")
    try: m = json.loads(files["manifest.json"])
    except ValueError as e: sys.exit(f"{path.name}: manifest.json is not valid JSON ({e})")
    if m.get("format") != "3dpcs-pack": sys.exit(f"{path.name}: not a 3DPCS pack")
    c = m.get("contents", {})
    e = {"id": m["id"], "name": m["name"], "version": m["version"], "author": m.get("author", ""),
         "kind": "mod" if c.get("mods") else "colors", "description": m.get("description", ""),
         "boards": m.get("boards", ["*"])}
    for k in ("firmware", "min_app"):
        if m.get(k): e[k] = m[k]
    if c.get("mods"):
        e["mods"] = [{"name": x.get("name", ""), "description": x.get("description", "")} for x in c["mods"]]
    if c.get("color_sets"):
        e["sets"] = []
        for s in c["color_sets"]:
            d = json.loads(files[s])
            e["sets"].append({"name": d.get("name", ""), "idle": [d.get("lights", {}).get(f, {}).get("idle", "") for f in FRETS]})
    icon = files.get(m.get("icon", ""))
    if icon and len(icon) <= MAX_ICON and icon[:8] == b"\x89PNG\r\n\x1a\n":
        e["icon"] = "data:image/png;base64," + base64.b64encode(icon).decode()
    e.update({"url": RAW + quote(path.name), "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
    return e


def main():
    old = {p["id"]: p for p in json.loads(OUT.read_text()).get("packs", [])} if OUT.exists() else {}
    new = {}
    for f in sorted(x for x in PACKS.iterdir() if x.is_file() and not x.name.startswith(".")):
        e = read(f)
        if e["id"] in new: sys.exit(f"{f.name}: id {e['id']} is in packs/ twice (keep only the newest file)")
        prev = old.get(e["id"])
        older = list(prev.get("older", [])) if prev else []
        if prev and prev["sha256"] != e["sha256"]:
            if ver(e["version"]) <= ver(prev["version"]):
                sys.exit(f"{f.name}: the file changed but its version {e['version']} is not higher than {prev['version']}")
            older.append({"version": prev["version"], "sha256": prev["sha256"]})
        if older: e["older"] = older
        new[e["id"]] = e
    for pid, p in old.items():          # file removed: retired, still trusted
        if pid not in new:
            r = {k: v for k, v in p.items() if k not in ("url",)}
            r["retired"] = True
            new[pid] = r
    doc = {"format": "3dpcs-catalog", "version": 1,
           "packs": sorted(new.values(), key=lambda p: (p.get("retired", False), p["kind"] != "mod", p["name"].lower()))}
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        sys.exit(0 if OUT.exists() and OUT.read_text() == text else "catalog.json is out of date: run tools/make_catalog.py")
    OUT.write_text(text)
    print(f"catalog.json: {sum(not p.get('retired') for p in new.values())} packs")


if __name__ == "__main__":
    main()
