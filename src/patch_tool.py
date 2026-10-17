"""Small Windows GUI for merging reviewed CSV translations into the PT-BR patch."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import PTBR_server as lt


PROJECT_ROOT = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent.parent
)
DEFAULT_PATCH = PROJECT_ROOT / "patch" / "pt_br"
CSV_ENGLISH = "ingles_original"
CSV_CURRENT = "pt_br_atual"
CSV_PATCH = "pt_br_patch"
CSV_TRANSLATION = "nova tradução"
CSV_TRANSLATION_FIELDS = {CSV_CURRENT, CSV_PATCH, CSV_TRANSLATION}
DEFAULT_MODULE_EXE = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Guild Wars 2\addons"
    r"\text_translator\modules\local_translator_pt_br\Local_Translator_PT_BR.exe"
)


def read_review(path: Path) -> dict[int, tuple[str, str, bool]]:
    """Read rows as key -> (translation, English source, reviewed)."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        sample = f.read(8192)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"
        reader = csv.DictReader(f, dialect=dialect)
        fields = set(reader.fieldnames or ())
        missing = {CSV_TRANSLATION, "key"} - fields
        if missing:
            raise ValueError(
                "A planilha precisa ter as colunas 'key' e "
                f"'{CSV_TRANSLATION}'. Colunas ausentes: {', '.join(sorted(missing))}."
            )

        rows: dict[int, tuple[str, str, bool]] = {}
        for line, row in enumerate(reader, start=2):
            reviewed_text = (row.get(CSV_TRANSLATION) or "")
            current_text = (row.get(CSV_CURRENT) or "")
            patch_text = (row.get(CSV_PATCH) or "")
            if reviewed_text.strip() == "-":
                translation, reviewed = reviewed_text, True
            elif reviewed_text.strip():
                translation, reviewed = reviewed_text, True
            elif current_text.strip():
                translation, reviewed = current_text, bool(patch_text.strip())
            else:
                continue
            raw_key = (row.get("key") or "").strip()
            if not raw_key.isdigit():
                raise ValueError(f"ID inválido na linha {line}: {raw_key!r}.")
            key = int(raw_key)
            if key >= 2**32:
                raise ValueError(f"ID fora do limite do jogo na linha {line}: {key}.")
            if key in rows:
                raise ValueError(f"ID duplicado na planilha: {key}.")
            if translation.strip() != "-" and len(translation.encode("utf-8")) > 65535:
                raise ValueError(f"A tradução do ID {key} excede o limite de tamanho.")
            rows[key] = (
                translation,
                (row.get(CSV_ENGLISH) or "").strip(),
                reviewed,
            )
    return rows


def _read_merge_csv(path: Path) -> tuple[list[str], dict[int, dict[str, str]], str]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        sample = stream.read(8192)
        stream.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"
        reader = csv.DictReader(stream, dialect=dialect)
        fields = reader.fieldnames or []
        if "key" not in fields:
            raise ValueError(f"O arquivo {path.name} não tem a coluna obrigatória 'key'.")
        if len(fields) != len(set(fields)):
            raise ValueError(f"O arquivo {path.name} tem nomes de coluna repetidos.")

        rows: dict[int, dict[str, str]] = {}
        for line, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(
                    f"A linha {line} do arquivo {path.name} tem mais colunas do que o cabeçalho.")
            values = {field: row.get(field) or "" for field in fields}
            if not any(value.strip() for value in values.values()):
                continue
            raw_key = values["key"].strip()
            if not raw_key.isdigit():
                raise ValueError(f"ID inválido no arquivo {path.name}, linha {line}: {raw_key!r}.")
            key = int(raw_key)
            if key >= 2**32:
                raise ValueError(f"ID fora do limite no arquivo {path.name}, linha {line}: {key}.")
            if key in rows:
                raise ValueError(f"ID duplicado no arquivo {path.name}: {key}.")
            values["key"] = str(key)
            rows[key] = values
    return fields, rows, dialect.delimiter


def merge_csv_files(base_path: Path, source_paths: list[Path],
                    output_path: Path) -> dict[str, int | Path]:
    """Combine CSV rows by ID, preserving base values and filling only empty cells."""
    base_path = base_path.resolve()
    output_path = output_path.resolve()
    paths = [base_path, *(path.resolve() for path in source_paths)]
    if output_path in paths:
        raise ValueError("Escolha um arquivo de saída diferente dos CSVs originais.")
    if len(set(paths)) != len(paths):
        raise ValueError("O mesmo CSV foi selecionado mais de uma vez.")
    if not output_path.parent.is_dir():
        raise ValueError(f"A pasta de destino não existe: {output_path.parent}")

    fields, rows, delimiter = _read_merge_csv(base_path)
    added_ids = 0
    filled_cells = 0
    conflicts = 0
    for source_path in paths[1:]:
        source_fields, source_rows, _ = _read_merge_csv(source_path)
        for field in source_fields:
            if field not in fields:
                fields.append(field)
        for key, incoming in source_rows.items():
            current = rows.get(key)
            if current is None:
                rows[key] = {field: incoming.get(field, "") for field in fields}
                added_ids += 1
                continue
            has_translation = any(
                current.get(field, "").strip() for field in CSV_TRANSLATION_FIELDS)
            for field in fields:
                candidate = incoming.get(field, "")
                existing = current.get(field, "")
                if not existing.strip() and candidate.strip():
                    if field not in CSV_TRANSLATION_FIELDS or not has_translation:
                        current[field] = candidate
                        filled_cells += 1
                    else:
                        conflicts += 1
                elif field != "key" and candidate.strip() and existing.strip() != candidate.strip():
                    conflicts += 1

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            prefix=f".{output_path.name}-",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            writer = csv.DictWriter(
                stream, fieldnames=fields, delimiter=delimiter, lineterminator="\n")
            writer.writeheader()
            for key in sorted(rows):
                writer.writerow({field: rows[key].get(field, "") for field in fields})
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return {
        "added_ids": added_ids,
        "filled_cells": filled_cells,
        "conflicts": conflicts,
        "rows": len(rows),
        "output": output_path,
    }


def create_empty_patch(patch_dir: Path) -> bool:
    """Initialize an empty patch, or index valid piece files that have no index yet."""
    patch_dir = patch_dir.resolve()
    if patch_dir.exists() and not patch_dir.is_dir():
        raise ValueError(f"O destino não é uma pasta: {patch_dir}")
    patch_dir.mkdir(parents=True, exist_ok=True)
    index_path = patch_dir / "index.json"
    if index_path.is_file():
        load_patch(patch_dir)
        return False

    existing = list(patch_dir.iterdir())
    if existing:
        piece_files = {
            path.name: path.read_bytes()
            for path in existing
            if path.is_file() and lt.piece_number(path.name) is not None
        }
        if len(piece_files) != len(existing):
            raise ValueError(
                "A pasta já contém arquivos que não são partes pNNNN.json válidas. "
                "Nenhum arquivo foi alterado."
            )
        seen: set[int] = set()
        version = 0
        for name, body in piece_files.items():
            number = lt.piece_number(name)
            if number is None:
                raise ValueError(f"Nome inválido para parte do patch: {name}.")
            data = json.loads(body.decode("utf-8"))
            strings, auto, drop, hashes = lt.parse_piece(data, number, lt.PIECE_WIDTH)
            versions = lt.parse_piece_versions(data)
            keys = set(strings) | set(auto) | drop
            if seen & keys or not set(hashes) <= keys or not set(versions) <= keys:
                raise ValueError(f"A parte {name} tem IDs ou metadados inválidos.")
            seen.update(keys)
            version = max([version, *versions.values()])
        index_bytes = lt.index_bytes(version, "", lt.PIECE_WIDTH, piece_files)
        created = False
    else:
        index_bytes = lt.index_bytes(0, "", lt.PIECE_PACKED_WIDTH, {})
        created = True

    temporary = patch_dir / ".index.json.tmp"
    try:
        temporary.write_bytes(index_bytes)
        os.replace(temporary, index_path)
    finally:
        temporary.unlink(missing_ok=True)
    load_patch(patch_dir)
    return created


def load_patch(patch_dir: Path) -> tuple[dict, dict[int, str], dict[int, str],
                                         set[int], dict[int, str]]:
    """Load and verify the published pieces before merging anything."""
    index_path = patch_dir / "index.json"
    try:
        raw_index = json.loads(index_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Não encontrei {index_path}. Selecione a pasta do patch pt-br.") from exc
    index = lt.parse_index(raw_index)
    strings: dict[int, str] = {}
    auto: dict[int, str] = {}
    drop: set[int] = set()
    hashes: dict[int, str] = {}
    seen: set[int] = set()

    for name, (number, expected_hash, expected_size) in index["pieces"].items():
        path = patch_dir / name
        body = path.read_bytes()
        if len(body) != expected_size or hashlib.sha256(body).hexdigest() != expected_hash:
            raise ValueError(f"A parte {name} não corresponde ao index.json. Nenhum arquivo foi alterado.")
        data = json.loads(body.decode("utf-8"))
        piece_strings, piece_auto, piece_drop, piece_hashes = lt.parse_piece(
            data, number, index["width"])
        piece_versions = lt.parse_piece_versions(data)
        keys = set(piece_strings) | set(piece_auto) | piece_drop
        repeated = seen & keys
        if repeated:
            raise ValueError(f"IDs repetidos entre as partes do patch: {sorted(repeated)[:10]}.")
        if not set(piece_hashes) <= keys or not set(piece_versions) <= keys:
            raise ValueError(f"A parte {name} tem metadados para IDs que não existem nela.")
        seen.update(keys)
        strings.update(piece_strings)
        auto.update(piece_auto)
        drop.update(piece_drop)
        hashes.update(piece_hashes)

    return index, strings, auto, drop, hashes


def merge_review(csv_path: Path, patch_dir: Path) -> dict[str, int | bool | Path | None]:
    """Merge a reviewed CSV, regenerate and verify the pieces, and back up the old patch."""
    patch_dir = patch_dir.resolve()
    rows = read_review(csv_path)
    initialized = False
    if not patch_dir.is_dir() or not (patch_dir / "index.json").is_file():
        initialized = create_empty_patch(patch_dir)
    index, strings, auto, drop, hashes = load_patch(patch_dir)
    changed_keys: set[int] = set()
    reviewed_changed = 0
    automatic_changed = 0
    removed = 0

    for key, (translation, english, reviewed) in rows.items():
        if translation.strip() == "-":
            if key in strings:
                strings.pop(key)
                if key not in auto:
                    hashes.pop(key, None)
                removed += 1
            continue

        if english and (reviewed or key not in strings):
            new_hash = lt.english_hash(english)
            if hashes.get(key) != new_hash:
                hashes[key] = new_hash
                changed_keys.add(key)

        if reviewed:
            if strings.get(key) != translation:
                strings[key] = translation
                auto.pop(key, None)
                drop.discard(key)
                changed_keys.add(key)
                reviewed_changed += 1
        elif key not in strings and auto.get(key) != translation:
            auto[key] = translation
            drop.discard(key)
            changed_keys.add(key)
            automatic_changed += 1

    changed = len(changed_keys)
    if not changed and not removed:
        return {"changed": 0, "removed": 0, "backup": None, "pieces": len(index["pieces"]),
                "initialized": initialized, "reviewed_changed": 0, "automatic_changed": 0}

    new_version = index["version"] + 1
    versions = lt.stamp_versions(patch_dir, strings, auto, hashes, new_version)
    width = lt.PIECE_PACKED_WIDTH
    pieces = lt.split_patch(strings, auto, drop, hashes, width, versions)

    staging_root = Path(tempfile.mkdtemp(
        prefix=f".{patch_dir.name}-build-", dir=patch_dir.parent))
    staged_patch = staging_root / patch_dir.name
    staged_patch.mkdir()
    try:
        for name, body in pieces.items():
            (staged_patch / name).write_bytes(body)
        (staged_patch / "index.json").write_bytes(
            lt.index_bytes(new_version, index["glossary"], width, pieces))
        load_patch(staged_patch)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = patch_dir.with_name(f"{patch_dir.name}_backup_{stamp}")
        suffix = 1
        while backup.exists():
            backup = patch_dir.with_name(f"{patch_dir.name}_backup_{stamp}_{suffix}")
            suffix += 1

        patch_dir.rename(backup)
        try:
            os.replace(staged_patch, patch_dir)
        except Exception:
            backup.rename(patch_dir)
            raise
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)

    return {
        "changed": changed,
        "removed": removed,
        "backup": backup,
        "pieces": len(pieces),
        "initialized": initialized,
        "reviewed_changed": reviewed_changed,
        "automatic_changed": automatic_changed,
    }


def export_review(module_exe: Path, output_csv: Path) -> subprocess.CompletedProcess[str]:
    """Run the installed translator's export command without invoking a shell."""
    module_exe = module_exe.resolve()
    output_csv = output_csv.resolve()
    if not module_exe.is_file():
        raise ValueError(f"Não encontrei o executável do módulo: {module_exe}")
    if module_exe.name.lower() != "local_translator_pt_br.exe":
        raise ValueError("Selecione o arquivo Local_Translator_PT_BR.exe do módulo pt-BR.")
    if not output_csv.parent.is_dir():
        raise ValueError(f"A pasta de destino não existe: {output_csv.parent}")

    result = subprocess.run(
        [str(module_exe), "--lang", "pt_br", "--export-review", str(output_csv)],
        cwd=module_exe.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or f"O módulo terminou com código {result.returncode}.")
    if not output_csv.is_file():
        raise RuntimeError("O módulo terminou sem erro, mas não criou o arquivo CSV.")
    return result


class PatchTool(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Mesclador de patch — Português do Brasil")
        self.resizable(False, False)
        self.csv_path = tk.StringVar()
        self.patch_path = tk.StringVar(value=str(DEFAULT_PATCH))
        self.module_exe = tk.StringVar(value=str(DEFAULT_MODULE_EXE))
        self.status = tk.StringVar(value="Escolha a planilha revisada e confira a pasta do patch.")
        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self, padding=16)
        frame.grid(sticky="nsew")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Planilha CSV:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.csv_path, width=68).grid(
            row=0, column=1, sticky="ew", padx=8, pady=5)
        ttk.Button(frame, text="Selecionar…", command=self._choose_csv).grid(
            row=0, column=2, pady=5)

        ttk.Label(frame, text="Pasta patch\\pt_br:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.patch_path, width=68).grid(
            row=1, column=1, sticky="ew", padx=8, pady=5)
        ttk.Button(frame, text="Selecionar…", command=self._choose_patch).grid(
            row=1, column=2, pady=5)

        ttk.Label(frame, text="Executável do módulo:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.module_exe, width=68).grid(
            row=2, column=1, sticky="ew", padx=8, pady=5)
        ttk.Button(frame, text="Selecionar…", command=self._choose_module).grid(
            row=2, column=2, pady=5)

        ttk.Label(
            frame,
            text=("Use a coluna “nova tradução” para correções revisadas. Quando estiver vazia, "
                  "pt_br_atual é importada como tradução automática."),
            wraplength=650,
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 5))
        ttk.Label(
            frame,
            text=("Novas traduções entram como revisadas. Uma cópia de segurança da pasta atual "
                  "será criada antes da atualização."),
            wraplength=650,
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=5)
        ttk.Label(frame, textvariable=self.status, wraplength=650).grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(10, 5))
        self.initialize_button = ttk.Button(
            frame, text="Criar patch vazio", command=self._create_empty_patch)
        self.initialize_button.grid(row=6, column=0, sticky="w", pady=(10, 0))
        self.export_button = ttk.Button(
            frame, text="Exportar textos para revisão", command=self._export_review)
        self.export_button.grid(row=6, column=1, sticky="w", pady=(10, 0))
        self.run_button = ttk.Button(frame, text="Mesclar e gerar partes", command=self._run)
        self.run_button.grid(row=6, column=2, sticky="e", pady=(10, 0))
        self.merge_csv_button = ttk.Button(
            frame, text="Mesclar CSVs de outros usuários na minha base",
            command=self._merge_csvs)
        self.merge_csv_button.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(10, 0))

    def _choose_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecione a planilha revisada",
            filetypes=[("Planilhas CSV", "*.csv"), ("Todos os arquivos", "*.*")],
        )
        if path:
            self.csv_path.set(path)

    def _merge_csvs(self) -> None:
        base_path = Path(self.csv_path.get())
        if not base_path.is_file():
            messagebox.showerror(
                "Planilha base não encontrada",
                "Selecione primeiro, no campo Planilha CSV, o seu arquivo que servirá de base.",
            )
            return

        sources = filedialog.askopenfilenames(
            title="Selecione os CSVs de outros usuários",
            initialdir=str(base_path.parent),
            filetypes=[("Planilhas CSV", "*.csv"), ("Todos os arquivos", "*.*")],
        )
        if not sources:
            return

        output = filedialog.asksaveasfilename(
            title="Salvar a base CSV mesclada",
            initialdir=str(base_path.parent),
            initialfile=f"{base_path.stem}_mesclado.csv",
            defaultextension=".csv",
            filetypes=[("Planilha CSV", "*.csv")],
        )
        if not output:
            return

        self.merge_csv_button.configure(state="disabled")
        self.status.set("Mesclando os CSVs por ID e preservando os dados da sua base…")
        self.update_idletasks()
        try:
            result = merge_csv_files(
                base_path, [Path(path) for path in sources], Path(output))
        except (OSError, ValueError, csv.Error) as exc:
            self.status.set("Não foi possível mesclar os CSVs.")
            messagebox.showerror("Erro ao mesclar CSVs", str(exc))
        else:
            merged_path = Path(result["output"])
            self.csv_path.set(str(merged_path))
            self.status.set(f"Base CSV mesclada: {merged_path}")
            messagebox.showinfo(
                "Mesclagem de CSVs concluída",
                f"IDs na base final: {result['rows']}\n"
                f"IDs novos adicionados: {result['added_ids']}\n"
                f"Campos vazios preenchidos: {result['filled_cells']}\n"
                f"Conflitos mantidos com os dados da base: {result['conflicts']}\n\n"
                f"Arquivo salvo em:\n{merged_path}\n\n"
                "A planilha base original e os CSVs importados foram preservados. "
                "A nova base ficou selecionada para a próxima mesclagem do patch.",
            )
        finally:
            self.merge_csv_button.configure(state="normal")

    def _choose_patch(self) -> None:
        path = filedialog.askdirectory(
            title="Selecione a pasta patch\\pt_br",
            initialdir=self.patch_path.get() if Path(self.patch_path.get()).is_dir()
            else str(PROJECT_ROOT / "patch"),
        )
        if path:
            self.patch_path.set(path)

    def _choose_module(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecione Local_Translator_PT_BR.exe",
            initialdir=str(Path(self.module_exe.get()).parent),
            filetypes=[("Módulo pt-BR", "Local_Translator_PT_BR.exe"), ("Executáveis", "*.exe")],
        )
        if path:
            self.module_exe.set(path)

    def _create_empty_patch(self) -> None:
        current = Path(self.patch_path.get())
        initial = current.parent if current.parent.is_dir() else Path.home()
        selected = filedialog.askdirectory(
            title="Selecione onde criar a pasta pt_br",
            initialdir=str(initial),
        )
        if not selected:
            return
        selected_path = Path(selected)
        target = (
            selected_path
            if selected_path.name.lower() == "pt_br"
            or (selected_path.is_dir() and not any(selected_path.iterdir()))
            else selected_path / "pt_br"
        )
        try:
            created = create_empty_patch(target)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Não foi possível criar o patch", str(exc))
            return

        self.patch_path.set(str(target))
        if created:
            self.status.set(f"Patch vazio criado em: {target}")
            messagebox.showinfo(
                "Patch inicial criado",
                "A pasta agora contém um index.json vazio. Preencha a coluna “nova tradução” no CSV "
                "e clique em “Mesclar e gerar partes” para adicionar as primeiras traduções.",
            )
        else:
            self.status.set(f"Patch existente conferido: {target}")
            messagebox.showinfo("Patch já existe", "O patch foi validado e nenhum arquivo foi alterado.")

    def _export_review(self) -> None:
        module_exe = Path(self.module_exe.get())
        if not module_exe.is_file():
            selected = filedialog.askopenfilename(
                title="Selecione Local_Translator_PT_BR.exe",
                initialdir=str(DEFAULT_MODULE_EXE.parent),
                filetypes=[("Módulo pt-BR", "Local_Translator_PT_BR.exe"), ("Executáveis", "*.exe")],
            )
            if not selected:
                return
            self.module_exe.set(selected)
            module_exe = Path(selected)

        output = filedialog.asksaveasfilename(
            title="Salvar textos exportados",
            initialdir=str(Path.home() / "Desktop"),
            initialfile="revisao.csv",
            defaultextension=".csv",
            filetypes=[("Planilha CSV", "*.csv")],
        )
        if not output:
            return

        self.export_button.configure(state="disabled")
        self.status.set("Exportando os textos do mapa local e do patch…")
        self.update_idletasks()
        try:
            result = export_review(module_exe, Path(output))
        except (OSError, RuntimeError, ValueError) as exc:
            self.status.set("Não foi possível exportar os textos.")
            messagebox.showerror("Erro ao exportar", str(exc))
        else:
            self.status.set(f"Arquivo de revisão criado: {output}")
            messagebox.showinfo(
                "Exportação concluída",
                f"{result.stdout.strip() or 'Os textos foram exportados.'}\n\nArquivo:\n{output}",
            )
        finally:
            self.export_button.configure(state="normal")

    def _run(self) -> None:
        csv_path = Path(self.csv_path.get())
        patch_path = Path(self.patch_path.get())
        if not csv_path.is_file():
            messagebox.showerror("Planilha não encontrada", "Selecione um arquivo CSV existente.")
            return
        self.run_button.configure(state="disabled")
        self.status.set("Validando, mesclando e gerando as partes do patch…")
        self.update_idletasks()
        try:
            result = merge_review(csv_path, patch_path)
        except (ValueError, OSError, ImportError) as exc:
            self.status.set("Não foi possível atualizar o patch.")
            messagebox.showerror("Erro ao mesclar", str(exc))
        else:
            if not result["changed"] and not result["removed"]:
                if result["initialized"]:
                    self.status.set(f"Patch vazio criado em: {patch_path.resolve()}")
                    messagebox.showinfo(
                        "Patch inicial criado",
                        "O patch foi criado, mas o CSV não tem traduções em pt_br_atual "
                        "nem na coluna “nova tradução”. Nenhuma parte é necessária até haver traduções.",
                    )
                else:
                    self.status.set("Nenhuma alteração encontrada; os arquivos foram mantidos.")
                    messagebox.showinfo("Sem alterações", "O patch já contém essas traduções.")
            else:
                self.status.set("Patch atualizado e conferido.")
                messagebox.showinfo(
                    "Patch atualizado",
                    f"Traduções revisadas adicionadas/alteradas: {result['reviewed_changed']}\n"
                    f"Traduções automáticas adicionadas/alteradas: {result['automatic_changed']}\n"
                    f"Traduções revisadas removidas: {result['removed']}\n"
                    f"Partes geradas: {result['pieces']}\n\n"
                    f"Cópia de segurança:\n{result['backup']}",
                )
        finally:
            self.run_button.configure(state="normal")


if __name__ == "__main__":
    PatchTool().mainloop()
