"""Match locked Go and frontend packages against OSV; store only public identifiers."""
from pathlib import Path
from urllib.request import Request, urlopen
import json
import re
import sys

root = Path(__file__).resolve().parents[2]
packages = set()
for module in ("go.mod", "relaykit/go.mod", "tokenkit/go.mod"):
    for name, version in re.findall(r"^\s+(\S+)\s+v(\S+)", (root/module).read_text(), re.MULTILINE):
        if name not in {"github.com/QuantumNous/new-api/relaykit", "github.com/QuantumNous/new-api/tokenkit"}:
            packages.add(("Go", name, version))
lock = (root/"web/bun.lock").read_text(encoding="utf-8").split('  "packages": {', 1)[1]
for spec in re.findall(r'^\s*"[^"]+":\s*\["([^"]+)"', lock, re.MULTILINE):
    name, separator, version = spec.rpartition("@")
    if separator and re.match(r"^\d", version):
        packages.add(("npm", name, version))
inventory = sorted(packages)
matches = []
for offset in range(0, len(inventory), 100):
    batch = inventory[offset:offset+100]
    payload = {"queries": [{"package": {"ecosystem": eco, "name": name}, "version": version}
                           for eco, name, version in batch]}
    request = Request("https://api.osv.dev/v1/querybatch", data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=45) as response:
        results = json.load(response)["results"]
    for package, result in zip(batch, results, strict=True):
        if result.get("vulns"):
            matches.append({"package": package, "advisories": [v["id"] for v in result["vulns"]]})
Path(sys.argv[1]).write_text(json.dumps({"inventory": inventory, "matches": matches}, indent=2))
print(f"{len(inventory)} versions checked; {len(matches)} matched packages")
