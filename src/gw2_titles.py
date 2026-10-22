"""Offline catalog of English Guild Wars 2 entity titles from the official API."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import os
import re
import sqlite3
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

log = logging.getLogger("lt")

API_ROOT = "https://api.guildwars2.com/v2"
ENTITY_TYPES = ("items", "skills", "traits", "specializations", "maps")
SKILL_EFFECT_FACT_TYPES = {"Buff", "PrefixedBuff"}
GODS_QUESTION_TITLE = "The Six Gods"
PERSONAL_STORY_SEASON = "My Story"
VALID_MAP_TYPES = {
    "Public", "Pvp", "GvG", "WvW", "Center", "BlueHome", "GreenHome",
    "RedHome", "EdgeOfTheMists", "Dungeon",
}
TOKEN_RE = re.compile(r"<[^<>\n]*>|%[A-Za-z]+\d*%|\[[^\[\]\n]*\]")
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def normalize_title(text: str) -> str:
    """Normalize markup and spelling for exact full-title comparisons, not substring matching."""
    text = html.unescape(unicodedata.normalize("NFKC", text))
    text = TOKEN_RE.sub(" ", text).replace("\u00a0", " ")
    text = text.replace("\u2018", "'").replace("\u2019", "'").casefold()
    text = text.replace("'", "")
    return " ".join(WORD_RE.findall(text))


class TitleCatalog:
    """In-memory exact-name index loaded from the generated SQLite API cache."""

    def __init__(self, db_path: Path | None) -> None:
        self.db_path = Path(db_path) if db_path is not None else None
        self.names: tuple[str, ...] = ()
        self._normalized: frozenset[str] = frozenset()
        self.fingerprint = ""
        self.updated_at = ""
        if self.db_path is None or not self.db_path.is_file():
            return
        try:
            con = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=5)
            try:
                self.names = tuple(row[0] for row in con.execute(
                    "SELECT DISTINCT name FROM titles ORDER BY name COLLATE NOCASE"))
                meta = dict(con.execute("SELECT key, value FROM metadata"))
            finally:
                con.close()
            self._normalized = frozenset(
                normalized for name in self.names if (normalized := normalize_title(name))
            )
            self.fingerprint = meta.get("catalog_sha256", "")
            self.updated_at = meta.get("updated_at", "")
        except sqlite3.Error as exc:
            log.warning("GW2 title catalog %s could not be read: %s", self.db_path, exc)
            self.names = ()
            self._normalized = frozenset()
            self.updated_at = ""

    def __len__(self) -> int:
        return len(self._normalized)

    def contains(self, text: str) -> bool:
        normalized = normalize_title(text)
        return bool(normalized) and normalized in self._normalized


def _fetch_json(url: str) -> object:
    request = urllib.request.Request(
        url, headers={"User-Agent": "GW2-Nexus-Local-Translator/1.0"}
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            retry_after = exc.headers.get("Retry-After")
            if attempt == 4 or (exc.code != 429 and exc.code < 500):
                raise
            delay = min(60.0, float(retry_after)) if retry_after and retry_after.isdigit() \
                else min(30.0, 2.0 ** attempt)
            print(
                f"\nAPI returned HTTP {exc.code}; retrying in {delay:g}s "
                f"(attempt {attempt + 2}/5).",
                file=sys.stderr, flush=True,
            )
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
            delay = min(30.0, 2.0 ** attempt)
            print(
                f"\nAPI request failed ({url}); retrying in {delay:g}s "
                f"(attempt {attempt + 2}/5).",
                file=sys.stderr, flush=True,
            )
            time.sleep(delay)
    raise RuntimeError(f"API request failed after retries: {url}")


def _api_list(value: object, url: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"GW2 API returned an unexpected response for {url}")
    return value


def _title_row(name: object, entity_type: str, entity_id: object) -> tuple | None:
    if not isinstance(name, str) or not normalize_title(name):
        return None
    return normalize_title(name), name, entity_type, str(entity_id)


def _insert_titles(con: sqlite3.Connection, rows: list[tuple]) -> None:
    con.executemany(
        "INSERT OR IGNORE INTO titles (normalized_name, name, entity_type, entity_id) "
        "VALUES (?, ?, ?, ?)", rows
    )


def _elapsed_text(started: float) -> str:
    seconds = int(time.monotonic() - started)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _sync_resource(
    con: sqlite3.Connection, resource: str, fetch_json, batch_size: int,
    allowed_types: set[str] | None = None,
) -> int:
    # The collection endpoint returns IDs directly; the items endpoint rejects ids=all.
    url = f"{API_ROOT}/{resource}"
    print(f"Getting {resource} ID list...", flush=True)
    ids = _api_list(fetch_json(url), url)
    total_batches = (len(ids) + batch_size - 1) // batch_size
    print(f"{resource}: {len(ids):,} IDs in {total_batches:,} requests.", flush=True)
    count = 0
    started = time.monotonic()
    for start in range(0, len(ids), batch_size):
        batch_number = start // batch_size + 1
        batch = ids[start:start + batch_size]
        if not all(isinstance(entity_id, int) and entity_id > 0 for entity_id in batch):
            raise ValueError(f"GW2 API returned an invalid ID in {resource}")
        query = urllib.parse.urlencode({"ids": ",".join(map(str, batch)), "lang": "en"})
        batch_url = f"{API_ROOT}/{resource}?{query}"
        print(
            f"\r{resource}: request {batch_number:,}/{total_batches:,} "
            f"(IDs {start + 1:,}-{start + len(batch):,}/{len(ids):,}, "
            f"elapsed {_elapsed_text(started)})",
            end="", flush=True,
        )
        entities = _api_list(fetch_json(batch_url), batch_url)
        rows = []
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            entity_id, name = entity.get("id"), entity.get("name")
            if allowed_types is not None and entity.get("type") not in allowed_types:
                continue
            row = _title_row(name, resource, entity_id)
            if isinstance(entity_id, int) and row is not None:
                rows.append(row)
            if resource in {"skills", "traits"} and isinstance(entity_id, int):
                facts = entity.get("facts", [])
                if isinstance(facts, list):
                    for index, fact in enumerate(facts):
                        if (not isinstance(fact, dict)
                                or fact.get("type") not in SKILL_EFFECT_FACT_TYPES):
                            continue
                        effect = _title_row(
                            fact.get("status"), "combat_effects",
                            f"{resource}:{entity_id}:{index}",
                        )
                        if effect is not None:
                            rows.append(effect)
        _insert_titles(con, rows)
        con.commit()
        count += len(rows)
    if total_batches:
        print(
            f"\r{resource}: completed {total_batches:,}/{total_batches:,} requests "
            f"({count:,} names, elapsed {_elapsed_text(started)}).",
            flush=True,
        )
    return count


def _sync_professions(con: sqlite3.Connection, fetch_json) -> int:
    url = f"{API_ROOT}/professions?ids=all&lang=en"
    print("Getting professions and training tracks...", flush=True)
    professions = _api_list(fetch_json(url), url)
    rows = []
    for profession in professions:
        if not isinstance(profession, dict):
            continue
        profession_id = profession.get("id")
        if not isinstance(profession_id, str) or not profession_id:
            continue
        row = _title_row(profession.get("name"), "professions", profession_id)
        if row is not None:
            rows.append(row)
        training = profession.get("training", [])
        if isinstance(training, list):
            for index, track in enumerate(training):
                if not isinstance(track, dict):
                    continue
                track_id = track.get("id", index)
                row = _title_row(track.get("name"), "training", f"{profession_id}:{track_id}")
                if row is not None:
                    rows.append(row)
    _insert_titles(con, rows)
    con.commit()
    return len(rows)


def _sync_human_gods(con: sqlite3.Connection, fetch_json, batch_size: int) -> int:
    questions_url = f"{API_ROOT}/backstory/questions?ids=all&lang=en"
    print("Getting human gods from the character-backstory API question...", flush=True)
    questions = _api_list(fetch_json(questions_url), questions_url)
    question = next(
        (entry for entry in questions
         if isinstance(entry, dict)
         and normalize_title(str(entry.get("title", "")))
         == normalize_title(GODS_QUESTION_TITLE)),
        None,
    )
    if question is None:
        raise ValueError(
            f"GW2 API no longer provides the backstory question {GODS_QUESTION_TITLE!r}"
        )
    answer_ids = question.get("answers")
    if not isinstance(answer_ids, list) or not answer_ids:
        raise ValueError(f"GW2 API returned no answers for {GODS_QUESTION_TITLE!r}")

    rows = []
    for start in range(0, len(answer_ids), batch_size):
        batch = answer_ids[start:start + batch_size]
        if not all(isinstance(answer_id, str) and answer_id for answer_id in batch):
            raise ValueError(f"GW2 API returned an invalid answer ID for {GODS_QUESTION_TITLE!r}")
        query = urllib.parse.urlencode({"ids": ",".join(batch), "lang": "en"})
        answers_url = f"{API_ROOT}/backstory/answers?{query}"
        answers = _api_list(fetch_json(answers_url), answers_url)
        returned_ids = set()
        for answer in answers:
            if not isinstance(answer, dict):
                continue
            returned_ids.add(answer.get("id"))
            row = _title_row(answer.get("title"), "gods", answer.get("id"))
            if row is not None:
                rows.append(row)
        if returned_ids != set(batch):
            raise ValueError(
                f"GW2 API did not return every answer for {GODS_QUESTION_TITLE!r}"
            )
    if not rows:
        raise ValueError(f"GW2 API returned no god names for {GODS_QUESTION_TITLE!r}")
    _insert_titles(con, rows)
    con.commit()
    return len(rows)


def _sync_story_seasons(con: sqlite3.Connection, fetch_json) -> int:
    url = f"{API_ROOT}/stories/seasons?ids=all&lang=en"
    print("Getting expansion and Living World names from story seasons...", flush=True)
    seasons = _api_list(fetch_json(url), url)
    rows = []
    for season in seasons:
        if not isinstance(season, dict):
            continue
        name = season.get("name")
        if not isinstance(name, str) or normalize_title(name) == normalize_title(
            PERSONAL_STORY_SEASON
        ):
            continue
        row = _title_row(name, "story_seasons", season.get("id"))
        if row is not None:
            rows.append(row)
    if not rows:
        raise ValueError("GW2 API returned no expansion or Living World story seasons")
    _insert_titles(con, rows)
    con.commit()
    return len(rows)


def sync_catalog(output: Path, fetch_json=_fetch_json, batch_size: int = 200) -> int:
    """Download entity names into a staging SQLite database and atomically replace the cache."""
    output = Path(output).resolve()
    if not 1 <= batch_size <= 200:
        raise ValueError("batch_size must be between 1 and 200")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".gw2-titles-", suffix=".db", dir=output.parent)
    os.close(fd)
    staged = Path(temp_name)
    started = time.monotonic()
    print(f"Starting Guild Wars 2 title catalog sync. Output: {output}", flush=True)
    try:
        con = sqlite3.connect(staged)
        try:
            con.execute("PRAGMA journal_mode=DELETE")
            con.execute("PRAGMA synchronous=NORMAL")
            con.executescript("""
                CREATE TABLE titles (
                    normalized_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    PRIMARY KEY (normalized_name, entity_type, entity_id)
                );
                CREATE INDEX titles_by_name ON titles(normalized_name);
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)
            total = 0
            for resource in ENTITY_TYPES:
                allowed_types = VALID_MAP_TYPES if resource == "maps" else None
                total += _sync_resource(con, resource, fetch_json, batch_size, allowed_types)
            total += _sync_professions(con, fetch_json)
            total += _sync_human_gods(con, fetch_json, batch_size)
            total += _sync_story_seasons(con, fetch_json)
            print("Finalizing catalog database...", flush=True)
            digest = hashlib.sha256()
            for row in con.execute(
                "SELECT normalized_name, entity_type, entity_id FROM titles "
                "ORDER BY normalized_name, entity_type, entity_id"
            ):
                digest.update(f"{row[0]}\0{row[1]}\0{row[2]}\n".encode("utf-8"))
            con.execute(
                "INSERT INTO metadata (key, value) VALUES ('updated_at', CURRENT_TIMESTAMP)"
            )
            con.execute(
                "INSERT INTO metadata (key, value) VALUES ('catalog_sha256', ?)",
                (digest.hexdigest(),),
            )
            con.commit()
        finally:
            con.close()
        os.replace(staged, output)
    except BaseException:
        for suffix in ("", "-journal", "-wal", "-shm"):
            try:
                Path(str(staged) + suffix).unlink()
            except FileNotFoundError:
                pass
        raise
    unique_titles = len(TitleCatalog(output))
    print(
        f"Saved {unique_titles:,} unique titles ({total:,} source entries) to {output} "
        f"in {_elapsed_text(started)}.",
        flush=True,
    )
    return unique_titles


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).resolve().parents[1] / "build" / "gw2_titles.db",
        help="destination SQLite database (default: build/gw2_titles.db)",
    )
    parser.add_argument("--batch-size", type=int, default=200, help="API IDs per request (max 200)")
    args = parser.parse_args()
    sync_catalog(args.output, batch_size=args.batch_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
