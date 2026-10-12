"""Download and install the pinned English-to-Portuguese OPUS model package."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

MODEL_URL = "https://argos-net.com/v1/translate-en_pt-1_9.argosmodel"
MODEL_SHA256 = "0c5350a2fa5b923de1346edc0d42e08e38bab2e33cede3a0b9a48eb4281ad8a9"
MAX_PACKAGE_BYTES = 100_000_000
PACKAGE_ROOT = "translate-en_pt-1_9/"
FILES = {
    "metadata.json": "metadata.json",
    "sentencepiece.model": "sentencepiece.model",
    "model/config.json": "model/config.json",
    "model/model.bin": "model/model.bin",
    "model/shared_vocabulary.json": "model/shared_vocabulary.json",
}


def download_package(destination: Path) -> None:
    request = urllib.request.Request(
        MODEL_URL, headers={"User-Agent": "GW2-PTBR-Local-Translator"}
    )
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as out:
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_PACKAGE_BYTES:
                raise ValueError(f"model package exceeds {MAX_PACKAGE_BYTES} bytes")
            digest.update(chunk)
            out.write(chunk)
    if digest.hexdigest() != MODEL_SHA256:
        raise ValueError("model package checksum does not match the pinned release")


def install_model(output: Path) -> None:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="prepare-ptbr-model-", dir=output.parent) as temp:
        temp_dir = Path(temp)
        archive = temp_dir / "model.argosmodel"
        extracted = temp_dir / "extracted"
        extracted.mkdir()
        download_package(archive)

        with zipfile.ZipFile(archive) as package:
            metadata_path = PACKAGE_ROOT + "metadata.json"
            metadata = json.loads(package.read(metadata_path))
            if (metadata.get("from_code"), metadata.get("to_code")) != ("en", "pt"):
                raise ValueError("downloaded model is not English-to-Portuguese")
            for relative, target in FILES.items():
                member = PACKAGE_ROOT + relative
                info = package.getinfo(member)
                if info.file_size > MAX_PACKAGE_BYTES:
                    raise ValueError(f"model package member is too large: {member}")
                staged = extracted / target
                staged.parent.mkdir(parents=True, exist_ok=True)
                with package.open(info) as source, staged.open("wb") as destination:
                    shutil.copyfileobj(source, destination)

        for relative in FILES.values():
            source = extracted / relative
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, destination)

    print(f"Installed English-to-Portuguese model under {output}")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    default_model_dir = (project_root / "nexus_build" / "addons" / "text_translator" /
                         "modules" / "local_translator_ptbr_perf" / "PT_BR" / "model")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=default_model_dir,
        help="model package directory (default: inside the Nexus build output)",
    )
    args = parser.parse_args()
    install_model(args.output)


if __name__ == "__main__":
    main()
