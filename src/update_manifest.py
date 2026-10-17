"""Generate the manifest to publish with the GitHub-hosted translation assets."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import PTBR_server as lt
import plurale_pt_br as plural


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS = {
    "glossary": ("glossary/glossary_pt_br.json",
                 "glossary/glossary_pt_br.json", "_version"),
    "plural": ("plural/plural_pt_br.json", "plural/plural_pt_br.json", "version"),
    "patch": ("patch/pt_br/index.json", "patch/pt_br/index.json", "version"),
}


def main() -> int:
    assets = {}
    for name, (relative, local_relative, version_field) in ASSETS.items():
        path = PROJECT_ROOT / local_relative
        body = path.read_bytes()
        data = json.loads(body.decode("utf-8"))
        version = data.get(version_field)
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise ValueError(f"{path} has no valid {version_field}")
        if name == "glossary":
            glossary = lt.Glossary()
            glossary.load_dict(data)
        elif name == "plural":
            plural.validate_rules(data)
        else:
            lt.parse_index(data)
        assets[name] = {
            "version": version,
            "path": relative,
            "sha256": hashlib.sha256(body).hexdigest(),
        }
    manifest = {"format": 1, "assets": assets}
    output = PROJECT_ROOT / "updates" / "manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(f"Manifest generated: {output}")
    for name, item in assets.items():
        print(f"  {name}: v{item['version']} {item['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
