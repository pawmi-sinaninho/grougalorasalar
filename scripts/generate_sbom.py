#!/usr/bin/env python3
from __future__ import annotations
import json, uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
lock=json.loads((ROOT/'apps/web/package-lock.json').read_text())
packages=[]
for path,item in sorted(lock.get('packages',{}).items()):
    if not path or 'version' not in item: continue
    name=path.split('node_modules/')[-1]
    packages.append({'SPDXID':f"SPDXRef-npm-{len(packages)+1}",'name':name,'versionInfo':item['version'],'downloadLocation':'NOASSERTION','licenseConcluded':'NOASSERTION','supplier':'NOASSERTION'})
for line in (ROOT/'services/api/requirements.txt').read_text().splitlines():
    line=line.strip()
    if not line or line.startswith('#'): continue
    name=line.split('>')[0].split('<')[0].split('=')[0].strip()
    packages.append({'SPDXID':f"SPDXRef-pypi-{len(packages)+1}",'name':name,'versionInfo':'range in requirements.txt','downloadLocation':'NOASSERTION','licenseConcluded':'NOASSERTION','supplier':'NOASSERTION'})
sbom={'spdxVersion':'SPDX-2.3','dataLicense':'CC0-1.0','SPDXID':'SPDXRef-DOCUMENT','name':'grougalorasalar-solver-v0.9.0','documentNamespace':f"https://example.invalid/grougalorasalar/sbom/{uuid.uuid4()}",'creationInfo':{'created':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'creators':['Tool: scripts/generate_sbom.py']},'packages':packages}
(ROOT/'reports/SBOM.spdx.json').write_text(json.dumps(sbom,indent=2)+"\n")
print(f"generated SBOM with {len(packages)} packages")
