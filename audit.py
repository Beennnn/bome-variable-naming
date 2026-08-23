#!/usr/bin/env python3
"""Audit variable usage in a Bome MIDI Translator Pro project (.bmtp).

Read-only. Reports scope violations, cross-preset collisions, and the two
outgoing-action patterns that turn a naming slip into silence on stage.

    python3 audit.py MyProject.bmtp
"""
import re
import sys

LOCALS = {"pp", "qq", "rr", "ss", "tt", "uu", "vv", "ww", "xx"}
GLOBAL_HEADS = set("ghijklmnyz")
# Reserved Channel Mode messages — a stray controller number here silences a rig.
CHANNEL_MODE = {120: "All Sound Off", 121: "Reset All Controllers",
                122: "Local Control", 123: "All Notes Off", 124: "Omni Off",
                125: "Omni On", 126: "Mono On", 127: "Poly On"}
VAR = r"[a-z][a-z0-9]"
OPS = "=(<>+-*/"


def parse(path):
    """-> {preset_id: {'active':bool, 'name':str, 'lines':[...]}} in file order."""
    presets, cur = {}, None
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        m = re.match(r"\[([A-Za-z0-9.]+)\]", line)
        if m:
            cur = m.group(1)
            presets[cur] = {"active": False, "name": cur, "lines": []}
            continue
        if cur is None:
            continue
        presets[cur]["lines"].append(line)
        if line.startswith("Active="):
            presets[cur]["active"] = line.split("=", 1)[1].strip() == "1"
        elif line.startswith("Name="):
            presets[cur]["name"] = line.split("=", 1)[1]
    return {k: v for k, v in presets.items() if k.startswith("Preset.")}


def payload(options_line):
    """Strip the Options header, leaving the concatenated rule text."""
    body = options_line.split("=", 1)[1]
    return re.sub(r"^Actv\d+Stop\d+OutO\d+(StMa[0-9A-F]{8})?", "", body)


def scan(lines):
    """-> (writes, reads) over one preset."""
    writes, reads = set(), set()
    for l in lines:
        if not re.match(r"(Options|Incoming|Outgoing)\d+=", l):
            continue
        if l.startswith("Incoming"):
            writes |= set(re.findall(r'var="(%s)" Type="SetVar"' % VAR, l))
        elif l.startswith("Outgoing"):
            reads |= set(re.findall(r'var="(%s)"' % VAR, l))
        else:
            p = payload(l)
            writes |= set(re.findall(r"(%s)=(?!=)" % VAR, p))
            reads |= set(re.findall(r"[%s](%s)" % (re.escape(OPS), VAR), p))
    return writes, reads


def classify(v):
    if v in LOCALS:
        return "local"
    if v[0] in GLOBAL_HEADS:
        return "global"
    return "UNDOCUMENTED"


def main(path):
    presets = parse(path)
    active = {k: v for k, v in presets.items() if v["active"]}
    print("%s — %d presets, %d active\n" % (path, len(presets), len(active)))

    allvars, writers, readers = set(), {}, {}
    for pid, p in presets.items():
        w, r = scan(p["lines"])
        allvars |= w | r
        for v in w:
            writers.setdefault(v, set()).add(pid)
        for v in r:
            readers.setdefault(v, set()).add(pid)

    print("== scope ==")
    for kind in ("UNDOCUMENTED", "global", "local"):
        names = sorted(v for v in allvars if classify(v) == kind)
        if names:
            print("  %-13s %s" % (kind, " ".join(names)))
    print("  (UNDOCUMENTED = neither one of the nine locals nor a g/h/i/j/k/l/m/n/y/z global)")

    print("\n== collisions: written by more than one ACTIVE preset ==")
    print("  (locals are excluded: pp..xx cannot leak between translators)")
    hits = 0
    for v in sorted(allvars):
        if v in LOCALS:
            continue
        ps = sorted(p for p in writers.get(v, ()) if p in active)
        if len(ps) > 1:
            hits += 1
            print("  %-4s %s" % (v, " · ".join("%s «%s»" % (p, presets[p]["name"]) for p in ps)))
    print("  none" if not hits else "  -> %d" % hits)

    print("\n== de-facto globals: read in a preset that never writes them ==")
    for pid, p in sorted(presets.items()):
        w, r = scan(p["lines"])
        ext = sorted(r - w)
        if ext:
            print("  %-11s %-6s %-28s reads %s"
                  % (pid, "ACTIVE" if p["active"] else "off", p["name"][:28], " ".join(ext)))

    dead = sorted(v for v in allvars if v in readers and v not in writers)
    if dead:
        print("\n== read but NEVER written anywhere (always 0) ==\n  " + " ".join(dead))

    print("\n== outgoing actions with a VARIABLE as controller number ==")
    for pid, p in sorted(presets.items()):
        for l in p["lines"]:
            if not l.startswith("Outgoing"):
                continue
            m = re.search(r'Type="ControlChange".*?<Value1 var="(%s)"' % VAR, l)
            if m:
                print("  %-11s %-6s %-12s controller = %s  [%s]"
                      % (pid, "ACTIVE" if p["active"] else "off", l.split("=")[0],
                         m.group(1), classify(m.group(1))))

    print("\n== early exits that fire the outgoing action ==")
    for pid, p in sorted(presets.items()):
        for l in p["lines"]:
            if not l.startswith("Options"):
                continue
            body = payload(l)
            for m in re.finditer(r"if\([^)]*\)execute", body):
                tail = body[m.end():]
                assigned = set(re.findall(r"(%s)=(?!=)" % VAR, tail))
                if assigned:
                    print("  %-11s %-6s %-10s '%s' fires before %s is assigned"
                          % (pid, "ACTIVE" if p["active"] else "off", l.split("=")[0],
                             m.group(0), "/".join(sorted(assigned))))
    print("\n  ('noexecute' leaves the rules WITHOUT firing — use it when the branch means"
          "\n   'nothing to send'. Reserved Channel Mode targets: %s)"
          % ", ".join("CC%d=%s" % (k, v) for k, v in sorted(CHANNEL_MODE.items())))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
