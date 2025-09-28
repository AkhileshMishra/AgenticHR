#!/usr/bin/env python3
import json, sys
from pathlib import Path

# very small "merge": copies paths/components; assumes non-conflicting ids
out = {"openapi":"3.0.3","info":{"title":"AgenticHR","version":"0.1.0"},
       "paths":{}, "components":{"schemas":{}}}

for p in sys.argv[1:]:
    try:
        doc = json.loads(Path(p).read_text())
        for k,v in doc.get("paths",{}).items():
            out["paths"][k] = v
        comps = doc.get("components",{}).get("schemas",{})
        out["components"]["schemas"].update(comps)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not process {p}: {e}", file=sys.stderr)
        continue

print(json.dumps(out, indent=2))
