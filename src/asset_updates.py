"""Versioned, opt-in updates for local translation data."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Callable

import PTBR_server as lt
import plurale_pt_br as plural
from patch_db import CachePatch

log = logging.getLogger("lt")

DEFAULT_UPDATE_SETTING = (
    "# Atualizações automáticas do GitHub para patch, glossário e plural.\n"
    "# Altere o valor abaixo para \"on\" para verificar atualizações ao iniciar o jogo.\n"
    "# Use \"off\" para manter somente os dados locais/compilados.\n"
    "off\n"
)
REPOSITORY = "DracanX/ProjetoTyria"
BRANCH = "main"
MANIFEST_PATH = "updates/manifest.json"
BASE_URL = f"https://raw.githubusercontent.com/{REPOSITORY}/{BRANCH}"
MAX_MANIFEST_BYTES = 1_000_000
MAX_ASSET_BYTES = lt.MAX_PATCH_FILE_BYTES
HASH_RE = re.compile(r"[0-9a-f]{64}")
ASSET_PATHS = {
    "glossary": "glossary/glossary_pt_br.json",
    "plural": "plural/plural_pt_br.json",
    "patch": "patch/pt_br/index.json",
}


def _fetch(url: str, limit: int = MAX_ASSET_BYTES) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "ProjetoTyria-Local-Translator"})
    with urllib.request.urlopen(request, timeout=10) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"download exceeds {limit} bytes")
    return data


def _read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return data


def _version(path: Path, kind: str) -> int:
    try:
        data = _read_json(path)
    except FileNotFoundError:
        return 0
    field = "_version" if kind == "glossary" else "version"
    value = data.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{path} has an invalid {field}")
    return value


def _updates_enabled(settings: Path) -> bool:
    try:
        lines = settings.read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        log.info("automatic updates off (no %s; default is off)", settings.name)
        return False
    except OSError:
        log.exception("cannot read automatic update setting %s", settings)
        return False
    values = [line.strip().lower() for line in lines
              if line.strip() and not line.lstrip().startswith(("#", ";"))]
    if values and values[0] in ("on", "off"):
        if len(values) > 1:
            log.warning("%s: ignoring content after the on/off setting", settings.name)
        return values[0] == "on"
    log.warning("%s must contain 'on' or 'off'; automatic updates remain off", settings)
    return False


def _ensure_setting(lang_dir: Path) -> Path:
    settings = lang_dir / "auto_updates.txt"
    if not settings.exists() and getattr(sys, "frozen", False):
        _atomic_write(settings, DEFAULT_UPDATE_SETTING.encode("utf-8"))
    return settings


def _manifest(fetch: Callable[[str], bytes]) -> dict:
    url = f"{BASE_URL}/{MANIFEST_PATH}"
    data = json.loads(fetch(url, MAX_MANIFEST_BYTES).decode("utf-8"))
    if not isinstance(data, dict) or data.get("format") != 1:
        raise ValueError("unsupported automatic update manifest")
    assets = data.get("assets")
    if not isinstance(assets, dict):
        raise ValueError("update manifest has no assets object")
    for name, expected_path in ASSET_PATHS.items():
        item = assets.get(name)
        if not isinstance(item, dict):
            raise ValueError(f"update manifest has no {name!r} asset")
        version, path, sha = item.get("version"), item.get("path"), item.get("sha256")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise ValueError(f"update manifest has invalid {name!r} version")
        if path != expected_path:
            raise ValueError(f"update manifest has unexpected {name!r} path")
        if not isinstance(sha, str) or not HASH_RE.fullmatch(sha):
            raise ValueError(f"update manifest has invalid {name!r} SHA-256")
    return assets


def _verified_asset(fetch: Callable[[str], bytes], path: str, expected_hash: str) -> bytes:
    data = fetch(f"{BASE_URL}/{path}")
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError(f"SHA-256 mismatch for {path}")
    return data


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _validate_glossary(data: bytes, expected_version: int) -> None:
    decoded = json.loads(data.decode("utf-8"))
    if not isinstance(decoded, dict) or decoded.get("_version") != expected_version:
        raise ValueError("glossary version does not match the update manifest")
    glossary = lt.Glossary()
    glossary.load_dict(decoded)


def _validate_plural(data: bytes, expected_version: int) -> None:
    decoded = json.loads(data.decode("utf-8"))
    if not isinstance(decoded, dict) or decoded.get("version") != expected_version:
        raise ValueError("plural rules version does not match the update manifest")
    plural.validate_rules(decoded)


def _validate_patch(directory: Path, expected_version: int) -> dict:
    raw = _read_json(directory / "index.json")
    index = lt.parse_index(raw)
    if index["version"] != expected_version:
        raise ValueError("patch version does not match the update manifest")
    seen: set[int] = set()
    for name, (number, expected_hash, size) in index["pieces"].items():
        body = (directory / name).read_bytes()
        if len(body) != size or hashlib.sha256(body).hexdigest() != expected_hash:
            raise ValueError(f"patch piece {name} does not match index.json")
        data = json.loads(body.decode("utf-8"))
        strings, auto, drop, hashes = lt.parse_piece(data, number, index["width"])
        versions = lt.parse_piece_versions(data)
        keys = set(strings) | set(auto) | drop
        if seen & keys:
            raise ValueError(f"patch contains duplicate IDs in {name}")
        if not set(hashes) <= keys or not set(versions) <= keys:
            raise ValueError(f"patch piece {name} has metadata for missing IDs")
        seen.update(keys)
    return index


def _replace_directory(staging: Path, target: Path) -> None:
    backup = target.with_name(f"{target.name}.previous_{int(time.time())}")
    suffix = 1
    while backup.exists():
        backup = target.with_name(f"{target.name}.previous_{int(time.time())}_{suffix}")
        suffix += 1
    moved_old = False
    if target.exists():
        target.rename(backup)
        moved_old = True
    try:
        os.replace(staging, target)
    except Exception:
        if moved_old and backup.exists():
            backup.rename(target)
        raise


def _download_patch(fetch: Callable[[str], bytes], item: dict, target: Path) -> None:
    index_body = _verified_asset(fetch, ASSET_PATHS["patch"], item["sha256"])
    index_data = json.loads(index_body.decode("utf-8"))
    index = lt.parse_index(index_data)
    if index["version"] != item["version"]:
        raise ValueError("patch version does not match the update manifest")

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".pt_br-update-", dir=target.parent))
    try:
        (staging / "index.json").write_bytes(index_body)
        for name, (_, expected_hash, _) in index["pieces"].items():
            relative_path = f"patch/pt_br/{name}"
            body = _verified_asset(fetch, relative_path, expected_hash)
            (staging / name).write_bytes(body)
        _validate_patch(staging, item["version"])
        _replace_directory(staging, target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def sync_updates(lang_dir: Path, bundle_dir: Path, patch: CachePatch,
                 fetch: Callable[[str, int], bytes] = _fetch) -> bool:
    """Check GitHub once at startup and cache only assets newer than local project data."""
    settings = _ensure_setting(lang_dir)
    if not _updates_enabled(settings):
        log.info("automatic updates off")
        return False
    log.info("checking GitHub for newer local translation data")
    try:
        assets = _manifest(fetch)
    except Exception:
        log.exception("automatic update check failed; keeping local translation data")
        return False

    update_dir = lang_dir / "updates"
    glossary_source = bundle_dir / "glossary_pt_br.json"
    glossary_target = update_dir / "glossary_pt_br.json"
    plural_source = bundle_dir / "plural" / "plural_pt_br.json"
    plural_target = update_dir / "plural_pt_br.json"

    for kind, source, target, validator in (
        ("glossary", glossary_source, glossary_target, _validate_glossary),
        ("plural", plural_source, plural_target, _validate_plural),
    ):
        try:
            local_version = max(_version(source, kind), _version(target, kind))
            item = assets[kind]
            if item["version"] <= local_version:
                log.info("%s is current locally (v%d; GitHub v%d)", kind, local_version,
                         item["version"])
                continue
            body = _verified_asset(fetch, item["path"], item["sha256"])
            validator(body, item["version"])
            _atomic_write(target, body)
            log.info("%s updated from GitHub: v%d -> v%d", kind, local_version,
                     item["version"])
        except Exception:
            log.exception("could not update %s; keeping the local copy", kind)

    try:
        patch_source = bundle_dir / "patch" / "pt_br"
        manual_patch = lang_dir / "patch" / "pt_br"
        cached_patch = update_dir / "patch" / "pt_br"
        local_version = max(
            _version(patch_source / "index.json", "patch"),
            _version(manual_patch / "index.json", "patch"),
            _version(cached_patch / "index.json", "patch"),
            patch.version,
        )
        item = assets["patch"]
        if item["version"] > local_version:
            _download_patch(fetch, item, cached_patch)
            log.info("patch updated from GitHub: v%d -> v%d", local_version, item["version"])
        else:
            log.info("patch is current locally (v%d; GitHub v%d)", local_version,
                     item["version"])
    except Exception:
        log.exception("could not update patch; keeping the local copy")
    return True


def active_glossary(bundle_file: Path, update_file: Path) -> Path:
    """Choose cached remote data only when it is strictly newer than bundled local source."""
    try:
        base_version = _version(bundle_file, "glossary")
        update_version = _version(update_file, "glossary")
        if update_version > base_version:
            _validate_glossary(update_file.read_bytes(), update_version)
            return update_file
    except FileNotFoundError:
        pass
    except Exception:
        log.exception("invalid cached glossary update; using bundled glossary")
    return bundle_file


def active_plural(bundle_file: Path, update_file: Path) -> Path:
    """Choose cached remote rules only when they are strictly newer than bundled local source."""
    try:
        base_version = _version(bundle_file, "plural")
        update_version = _version(update_file, "plural")
        if update_version > base_version:
            _validate_plural(update_file.read_bytes(), update_version)
            return update_file
    except FileNotFoundError:
        pass
    except Exception:
        log.exception("invalid cached plural update; using bundled rules")
    return bundle_file
