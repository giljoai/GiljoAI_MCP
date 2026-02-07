import json
import os
import re
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path("F:/GiljoAI_MCP")
BS = chr(92)

files_by_layer = {k: [] for k in ["model", "service", "api", "frontend", "test", "config", "docs"]}
path_to_id, id_to_path = {}, {}
dependencies, dependents = defaultdict(set), defaultdict(set)
file_metadata = {}
id_counter = 0


def get_layer(fp):
    p = fp.replace(BS, "/").lower()
    if "/tests/" in p or "__tests__" in p:
        return "test"
    if p.endswith(".spec.js") or p.endswith(".spec.ts"):
        return "test"
    if p.split("/")[-1].startswith("test_"):
        return "test"
    if "/docs/" in p or "/handovers/" in p:
        return "docs"
    if p.endswith(".md") and "/src/" not in p:
        return "docs"
    if "/frontend/src/" in p:
        return "frontend"
    fpo = fp.replace(BS, "/")
    if "src/giljo_mcp/models/" in fpo:
        return "model"
    if "src/giljo_mcp/services/" in fpo:
        return "service"
    if "src/giljo_mcp/repositories/" in fpo:
        return "model"
    if "src/giljo_mcp/config/" in fpo:
        return "config"
    if "/api/" in p:
        return "api"
    if "src/giljo_mcp/" in fpo:
        return "api"
    return "api"


def extract_py_imports(c):
    i = set()
    i.update(re.findall(r"^from\s+([\w.]+)\s+import", c, re.M))
    i.update(re.findall(r"^import\s+([\w.]+)", c, re.M))
    return i


def extract_vue_imports(c):
    pattern = r'import\s+.*?\s+from\s+["\x27]([^"\x27]+)["\x27]'
    return set(re.findall(pattern, c))


def resolve_py(imp):
    cands = []
    if imp.startswith("src.giljo_mcp"):
        cands.append(imp.replace(".", "/") + ".py")
        cands.append(imp.replace(".", "/") + "/__init__.py")
    if imp.startswith("api"):
        cands.append(imp.replace(".", "/") + ".py")
        cands.append(imp.replace(".", "/") + "/__init__.py")
    return cands


def resolve_vue(imp, base):
    cands = []
    if imp.startswith("@/"):
        rel = imp[2:]
        for ext in [".vue", ".js", ".ts", "/index.js", "/index.ts"]:
            cands.append("frontend/src/" + rel + ext)
    elif imp.startswith("./") or imp.startswith("../"):
        bd = str(Path(base).parent)
        res = os.path.normpath(os.path.join(bd, imp)).replace(BS, "/")
        for ext in [".vue", ".js", ".ts", "/index.js"]:
            cands.append(res + ext)
    return cands


def count_m(c):
    d = len(re.findall(r"@deprecated|DEPRECATED", c, re.I))
    t = len(re.findall(r"TODO|FIXME|XXX|HACK", c))
    dc = len(re.findall(r"^#.*def\s+|^#.*class\s+", c, re.M))
    return d, t, dc


def calc_risk(dc, d, t):
    if dc >= 50 or d >= 10:
        return "critical"
    if dc >= 20 or d >= 5:
        return "high"
    if dc >= 5 or d >= 2 or t >= 5:
        return "medium"
    return "low"


print("Collecting files...")
skip = ["venv", "node_modules", "__pycache__", ".git", "htmlcov", ".pytest_cache", ".serena"]

for root, dirs, files in os.walk(BASE_DIR):
    dirs[:] = [d for d in dirs if d not in skip]
    for f in files:
        if f.endswith(".py"):
            fp = Path(root) / f
            rp = str(fp.relative_to(BASE_DIR)).replace(BS, "/")
            layer = get_layer(rp)
            files_by_layer[layer].append(rp)
            path_to_id[rp] = id_counter
            id_to_path[id_counter] = rp
            id_counter += 1

fd = BASE_DIR / "frontend" / "src"
if fd.exists():
    for root, dirs, files in os.walk(fd):
        dirs[:] = [d for d in dirs if d not in ["node_modules", "__pycache__"]]
        for f in files:
            if f.endswith((".vue", ".js", ".ts")):
                fp = Path(root) / f
                rp = str(fp.relative_to(BASE_DIR)).replace(BS, "/")
                layer = "test" if "__tests__" in rp or f.endswith(".spec.js") or f.endswith(".spec.ts") else "frontend"
                files_by_layer[layer].append(rp)
                path_to_id[rp] = id_counter
                id_to_path[id_counter] = rp
                id_counter += 1

for ext in ["*.js", "*.ts"]:
    for f in (BASE_DIR / "frontend").glob(ext):
        rp = str(f.relative_to(BASE_DIR)).replace(BS, "/")
        if rp not in path_to_id:
            layer = "test" if "test" in rp.lower() or "spec" in rp.lower() else "frontend"
            files_by_layer[layer].append(rp)
            path_to_id[rp] = id_counter
            id_to_path[id_counter] = rp
            id_counter += 1

ft = BASE_DIR / "frontend" / "tests"
if ft.exists():
    for root, dirs, files in os.walk(ft):
        dirs[:] = [d for d in dirs if d not in ["node_modules"]]
        for f in files:
            if f.endswith((".js", ".ts", ".vue")):
                fp = Path(root) / f
                rp = str(fp.relative_to(BASE_DIR)).replace(BS, "/")
                if rp not in path_to_id:
                    files_by_layer["test"].append(rp)
                    path_to_id[rp] = id_counter
                    id_to_path[id_counter] = rp
                    id_counter += 1

ft2 = BASE_DIR / "frontend" / "__tests__"
if ft2.exists():
    for root, dirs, files in os.walk(ft2):
        dirs[:] = [d for d in dirs if d not in ["node_modules"]]
        for f in files:
            if f.endswith((".js", ".ts", ".vue")):
                fp = Path(root) / f
                rp = str(fp.relative_to(BASE_DIR)).replace(BS, "/")
                if rp not in path_to_id:
                    files_by_layer["test"].append(rp)
                    path_to_id[rp] = id_counter
                    id_to_path[id_counter] = rp
                    id_counter += 1

dd = BASE_DIR / "docs"
if dd.exists():
    for root, dirs, files in os.walk(dd):
        for f in files:
            if f.endswith(".md"):
                fp = Path(root) / f
                rp = str(fp.relative_to(BASE_DIR)).replace(BS, "/")
                if rp not in path_to_id:
                    files_by_layer["docs"].append(rp)
                    path_to_id[rp] = id_counter
                    id_to_path[id_counter] = rp
                    id_counter += 1

hd = BASE_DIR / "handovers"
if hd.exists():
    for root, dirs, files in os.walk(hd):
        for f in files:
            if f.endswith(".md"):
                fp = Path(root) / f
                rp = str(fp.relative_to(BASE_DIR)).replace(BS, "/")
                if rp not in path_to_id:
                    files_by_layer["docs"].append(rp)
                    path_to_id[rp] = id_counter
                    id_to_path[id_counter] = rp
                    id_counter += 1

for f in BASE_DIR.glob("*.md"):
    rp = str(f.relative_to(BASE_DIR)).replace(BS, "/")
    if rp not in path_to_id:
        files_by_layer["docs"].append(rp)
        path_to_id[rp] = id_counter
        id_to_path[id_counter] = rp
        id_counter += 1

print(f"Collected {id_counter} files")

for layer in files_by_layer:
    files_by_layer[layer] = sorted(list(set(files_by_layer[layer])))

print("Extracting dependencies...")

for fp, fid in path_to_id.items():
    full = BASE_DIR / fp
    if not full.exists():
        continue
    try:
        c = full.read_text(encoding="utf-8", errors="ignore")
    except:
        continue

    d, t, dc = count_m(c)
    file_metadata[fid] = {"deprecations": d, "todos": t, "dead_code": dc}

    if fp.endswith(".py"):
        for imp in extract_py_imports(c):
            for cand in resolve_py(imp):
                if cand in path_to_id:
                    did = path_to_id[cand]
                    if did != fid:
                        dependencies[fid].add(did)
                        dependents[did].add(fid)

    elif fp.endswith((".vue", ".js", ".ts")):
        for imp in extract_vue_imports(c):
            for cand in resolve_vue(imp, fp):
                if cand in path_to_id:
                    did = path_to_id[cand]
                    if did != fid:
                        dependencies[fid].add(did)
                        dependents[did].add(fid)

print("Building output...")

nodes, links = [], []

f2l = {}
for layer, files in files_by_layer.items():
    for f in files:
        f2l[f] = layer

for fp, fid in sorted(path_to_id.items(), key=lambda x: x[1]):
    m = file_metadata.get(fid, {"deprecations": 0, "todos": 0, "dead_code": 0})
    dl = list(dependencies.get(fid, set()))
    dol = list(dependents.get(fid, set()))

    layer = f2l.get(fp, "api")
    risk = calc_risk(len(dol), m["deprecations"], m["todos"])

    node = {
        "id": fid,
        "path": fp,
        "name": fp.split("/")[-1],
        "layer": layer,
        "dependents": dol,
        "dependencies": dl,
        "deprecations": m["deprecations"],
        "todos": m["todos"],
        "dead_code": m["dead_code"],
        "risk": risk,
    }
    nodes.append(node)

    for did in dl:
        links.append({"source": fid, "target": did})

output = {"nodes": nodes, "links": links}

print()
print("Layer Distribution:")
lc = defaultdict(int)
for n in nodes:
    lc[n["layer"]] += 1
for l, c in sorted(lc.items()):
    print(f"  {l}: {c}")

print()
print(f"Total nodes: {len(nodes)}")
print(f"Total links: {len(links)}")

rc = defaultdict(int)
for n in nodes:
    rc[n["risk"]] += 1
print()
print("Risk Distribution:")
for r, c in sorted(rc.items()):
    print(f"  {r}: {c}")

op = BASE_DIR / "docs" / "cleanup" / "dependency_graph.json"
with open(op, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print()
print(f"Output written to: {op}")
