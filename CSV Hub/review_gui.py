"""Graphical export/review/import tool for the PT-BR translation patch."""
from __future__ import annotations

import json
import csv
import os
import shutil
import sys
import tempfile
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

FROZEN = getattr(sys, "frozen", False)
SOURCE_DIR = Path(__file__).resolve().parent
ROOT = Path(sys.executable).resolve().parent if FROZEN else SOURCE_DIR.parent
if not FROZEN:
    sys.path.insert(0, str(ROOT / "src"))

import server  # noqa: E402


def patch_from_pieces(directory: Path) -> dict | None:
    """Rebuild the patch sections needed by review tools from a published pieces directory."""
    index_path = directory / "index.json"
    if not index_path.is_file():
        return None
    index = server.parse_index(json.loads(index_path.read_text(encoding="utf-8")))
    strings: dict[int, str] = {}
    auto: dict[int, str] = {}
    drop: set[int] = set()
    for name, (number, _sha, _size) in index["pieces"].items():
        piece = json.loads((directory / name).read_text(encoding="utf-8"))
        piece_strings, piece_auto, piece_drop, _hashes = server.parse_piece(
            piece, number, index["width"])
        strings.update(piece_strings)
        auto.update({key: value for key, value in piece_auto.items() if key not in strings})
        drop.update(piece_drop)
    data = {
        "version": index["version"],
        "strings": {str(key): strings[key] for key in sorted(strings)},
        "auto": {str(key): auto[key] for key in sorted(auto) if key not in strings},
        "drop": sorted(drop - strings.keys() - auto.keys()),
    }
    if index["glossary"]:
        data["glossary"] = index["glossary"]
    server.Patch().load_dict(data)
    return data


def _patch_data_for_export(master: Path, pieces: Path) -> dict | None:
    if master.is_file():
        data = json.loads(master.read_text(encoding="utf-8"))
        server.Patch().load_dict(data)
        return data
    return patch_from_pieces(pieces)


def export_csv(map_path: Path, master: Path, pieces: Path, csv_path: Path) -> int:
    patch_data = _patch_data_for_export(master, pieces)
    with tempfile.TemporaryDirectory(prefix="lt-review-export-") as temporary:
        patch_path = Path(temporary) / "patch.json"
        if patch_data is not None:
            patch_path.write_text(server.dump_patch(patch_data), encoding="utf-8")
        return server.export_review(map_path, patch_path, csv_path)


def import_csv(review: Path, master: Path, pieces: Path) -> tuple[int, int, Path | None]:
    """Import into a master patch atomically, backing up an existing file before replacement."""
    master.parent.mkdir(parents=True, exist_ok=True)
    initial = _patch_data_for_export(master, pieces)
    if initial is None:
        initial = {"version": 0, "strings": {}, "auto": {}}

    backup = None
    with tempfile.TemporaryDirectory(prefix=".lt-review-", dir=master.parent) as temporary:
        working = Path(temporary) / master.name
        working.write_text(server.dump_patch(initial), encoding="utf-8")
        changed, removed = server.import_review(review, working)
        if not changed and not removed:
            return changed, removed, None

        if master.is_file():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            backup = master.with_name(f"{master.stem}.bak-{stamp}{master.suffix}")
            shutil.copy2(master, backup)
        os.replace(working, master)
    return changed, removed, backup


def merge_csvs(directory: Path, output: Path) -> tuple[int, int, int]:
    """Merge review CSVs by key; the last nonempty cell wins in filename order."""
    if not directory.is_dir():
        raise FileNotFoundError(f"Pasta de CSVs não encontrada: {directory}")
    inputs = sorted(path for path in directory.glob("*.csv")
                    if path.resolve() != output.resolve())
    if not inputs:
        raise ValueError(f"Nenhum arquivo CSV encontrado em {directory}")

    rows: dict[str, dict[str, str]] = {}
    columns = list(server.REVIEW_COLUMNS)
    conflicts = 0
    for path in inputs:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            sample = file.read(8192)
            file.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(file, dialect=dialect)
            if not reader.fieldnames or "chave" not in reader.fieldnames:
                raise ValueError(f"{path.name}: coluna 'chave' não encontrada.")
            if not ({"nova_tradução", "nova_traducao"} & set(reader.fieldnames)):
                raise ValueError(f"{path.name}: coluna 'nova_tradução' não encontrada.")
            for header in reader.fieldnames:
                normalized = "nova_tradução" if header == "nova_traducao" else header
                if normalized not in columns:
                    columns.append(normalized)
            for row in reader:
                key = (row.get("chave") or "").strip()
                if not key:
                    continue
                current = rows.setdefault(key, {})
                for column, value in row.items():
                    if not column:
                        continue
                    normalized = "nova_tradução" if column == "nova_traducao" else column
                    value = (value or "").strip()
                    if value and current.get(normalized) and current[normalized] != value:
                        conflicts += 1
                    if value:
                        current[normalized] = value

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        for key in sorted(rows, key=lambda value: (not value.isdigit(),
                                                   int(value) if value.isdigit() else value)):
            writer.writerow({column: rows[key].get(column, "") for column in columns})
    return len(inputs), len(rows), conflicts


def create_patch_from_csv(review: Path, destination: Path) -> tuple[int, int]:
    """Create a new master patch and split files without overwriting existing paths."""
    if destination.exists():
        raise FileExistsError(
            f"A pasta de destino já existe. Escolha uma pasta nova: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".lt-new-patch-", dir=destination.parent) as work:
        working = Path(work)
        master = working / "patch_pt_br.json"
        master.write_text(
            server.dump_patch({"version": 0, "strings": {}, "auto": {}}), encoding="utf-8")
        server.import_review(review, master)
        patch = server.Patch()
        if not patch.load_file(master) or not patch.strings:
            raise ValueError("O CSV não contém traduções preenchidas em 'nova_tradução'.")

        versions = {key: patch.version for key in patch.strings}
        pieces = server.split_patch(
            patch.strings, patch.auto, patch.drop, {}, 20_000, versions)
        pieces_dir = working / "pt_br"
        pieces_dir.mkdir()
        for name, body in pieces.items():
            (pieces_dir / name).write_bytes(body)
        (pieces_dir / "index.json").write_bytes(
            server.index_bytes(patch.version, patch.glossary_fp, 20_000, pieces))

        result = working / "generated"
        result.mkdir()
        shutil.move(str(master), result / master.name)
        shutil.move(str(pieces_dir), result / "pt_br")
        os.replace(result, destination)
    return len(patch.strings), patch.version


class ReviewApp:
    ACCENT = "#1f6aa5"

    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        root.title("CSV Hub — PT-BR")
        root.geometry("1020x700")
        root.minsize(860, 620)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        self.map_path = tk.StringVar()
        self.master_path = tk.StringVar(value=str(ROOT / "patch_pt_br.json"))
        self.pieces_path = tk.StringVar(value=str(ROOT / "pt_br"))
        self.csv_path = tk.StringVar(value=str(ROOT / "revisao_pt_br.csv"))
        self.merge_folder = tk.StringVar()
        self.merge_output = tk.StringVar(value=str(ROOT / "patch_pt_br_unificado.csv"))
        self.new_destination = tk.StringVar(value=str(ROOT / "patch_pt_br_novo"))
        self.status_text = tk.StringVar(value="Pronto.")
        self.status_indicator: ctk.CTkLabel
        self.buttons: list[ctk.CTkButton] = []
        self.nav_buttons: dict[str, ctk.CTkButton] = {}

        self._build_sidebar()
        self.workspace = ctk.CTkScrollableFrame(
            root, corner_radius=0, fg_color="transparent", scrollbar_button_color="#3a414a")
        self.workspace.grid(row=0, column=1, sticky="nsew")
        self.workspace.grid_columnconfigure(0, weight=1)
        self._build_statusbar()
        self.show_page("export")

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self.root, width=220, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(6, weight=1)
        ctk.CTkLabel(sidebar, text="CSV Hub", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color="white").grid(row=0, column=0, padx=22, pady=(26, 2), sticky="w")
        ctk.CTkLabel(sidebar, text="PT-BR PATCH STUDIO",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#9299a5").grid(row=1, column=0, padx=23, pady=(0, 24), sticky="w")

        for row, (key, text, command) in enumerate((
                ("export", "Exportar CSV", lambda: self.show_page("export")),
                ("merge", "Mesclar CSVs", lambda: self.show_page("merge")),
                ("patch", "Aplicar / criar patch", lambda: self.show_page("patch")),
                ("credits", "Créditos", lambda: self.show_page("credits"))), start=2):
            button = ctk.CTkButton(
                sidebar, text=text, anchor="w", height=42, corner_radius=9,
                fg_color="transparent", text_color=("#313844", "#c9ced6"),
                hover_color=("#dfe7f0", "#30343c"), command=command)
            button.grid(row=row, column=0, padx=14, pady=4, sticky="ew")
            self.nav_buttons[key] = button

        separator = ctk.CTkFrame(sidebar, height=1, fg_color=("#d0d2d6", "#363a42"))
        separator.grid(row=7, column=0, padx=16, pady=(8, 12), sticky="ew")
        ctk.CTkLabel(sidebar, text="Aparência", anchor="w",
                     text_color=("#555b65", "#9299a5"),
                     font=ctk.CTkFont(size=11, weight="bold")).grid(
                         row=8, column=0, padx=20, pady=(0, 5), sticky="w")
        self.appearance = ctk.CTkOptionMenu(
            sidebar, values=["Escuro", "Claro", "Sistema"], command=self._change_appearance,
            height=34, corner_radius=8)
        self.appearance.grid(row=9, column=0, padx=15, pady=(0, 20), sticky="ew")
        self.appearance.set("Escuro")

    def _build_statusbar(self) -> None:
        footer = ctk.CTkFrame(self.root, height=42, corner_radius=0,
                              fg_color=("#e4e7eb", "#202126"))
        footer.grid(row=1, column=0, columnspan=2, sticky="ew")
        footer.grid_columnconfigure(1, weight=1)
        self.status_indicator = ctk.CTkLabel(
            footer, text="●", text_color="#2fa572", font=ctk.CTkFont(size=12))
        self.status_indicator.grid(row=0, column=0, padx=(16, 6), pady=9)
        ctk.CTkLabel(footer, textvariable=self.status_text, anchor="w",
                     text_color=("#4e5661", "#c7cbd1"),
                     font=ctk.CTkFont(size=11)).grid(row=0, column=1, sticky="ew", pady=9)
        ctk.CTkLabel(footer, text="LOCAL • PT-BR", text_color=("#737b86", "#777e89"),
                     font=ctk.CTkFont(size=9, weight="bold")).grid(
                         row=0, column=2, padx=16, pady=9)

    def _change_appearance(self, value: str) -> None:
        ctk.set_appearance_mode({"Escuro": "Dark", "Claro": "Light", "Sistema": "System"}[value])

    def _header(self, title: str, subtitle: str) -> None:
        ctk.CTkLabel(self.workspace, text=title,
                     font=ctk.CTkFont(size=29, weight="bold"),
                     text_color=("#17191d", "#f3f4f6")).grid(
                         row=0, column=0, padx=34, pady=(34, 3), sticky="w")
        ctk.CTkLabel(self.workspace, text=subtitle, anchor="w",
                     font=ctk.CTkFont(size=12),
                     text_color=("#6f7783", "#a0a5ae")).grid(
                         row=1, column=0, padx=36, pady=(0, 24), sticky="w")

    def _build_card(self, row: int = 2) -> ctk.CTkFrame:
        card = ctk.CTkFrame(self.workspace, corner_radius=14,
                            fg_color=("#ffffff", "#27292f"),
                            border_width=1, border_color=("#e1e4e9", "#383b43"))
        card.grid(row=row, column=0, padx=30, pady=6, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        return card

    def _path_field(self, parent, row: int, label: str, variable: tk.StringVar,
                    mode: str, hint: str | None = None) -> None:
        ctk.CTkLabel(parent, text=label, anchor="w",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=("#3f4650", "#d5d8de")).grid(
                         row=row * 2, column=0, padx=16, pady=(14 if row == 0 else 8, 4),
                         sticky="w")
        line = ctk.CTkFrame(parent, fg_color="transparent")
        line.grid(row=row * 2 + 1, column=0, padx=14, pady=(0, 3), sticky="ew")
        line.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(line, textvariable=variable, height=38, corner_radius=8,
                     placeholder_text=hint or "").grid(
                         row=0, column=0, padx=(0, 8), sticky="ew")
        ctk.CTkButton(line, text="Procurar...", width=105, height=38, corner_radius=8,
                      command=lambda: self._browse_for(variable, mode)).grid(
                          row=0, column=1)

    def _primary_button(self, parent, text: str, command) -> None:
        button = ctk.CTkButton(
            parent, text=text, command=command, height=46, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.ACCENT, hover_color="#175282")
        button.grid(row=3, column=0, padx=30, pady=(20, 8), sticky="ew")
        self.buttons.append(button)

    def _note(self, parent, text: str) -> None:
        ctk.CTkLabel(parent, text=text, anchor="w", justify="left", wraplength=670,
                     font=ctk.CTkFont(size=11),
                     text_color=("#727a85", "#989ea8")).grid(
                         row=4, column=0, padx=32, pady=(10, 0), sticky="w")

    def show_page(self, name: str) -> None:
        for child in self.workspace.winfo_children():
            child.destroy()
        for key, button in self.nav_buttons.items():
            button.configure(
                fg_color=self.ACCENT if key == name else "transparent",
                text_color="white" if key == name else ("#313844", "#c9ced6"))
        self.buttons.clear()

        if name == "export":
            self._header("Exportar módulo", "Gere um CSV de revisão a partir dos dados locais PT_BR.")
            card = self._build_card()
            self._path_field(card, 0, "PASTA PT_BR COM map_pt_br.db", self.map_path, "folder")
            self._path_field(card, 1, "PATCH MESTRE JSON (OPCIONAL)", self.master_path, "open-patch")
            self._path_field(card, 2, "PASTA DAS PARTES PUBLICADAS (FALLBACK)",
                             self.pieces_path, "folder")
            self._path_field(card, 3, "CSV DE SAÍDA", self.csv_path, "save-csv")
            self._primary_button(self.workspace, "EXPORTAR CSV", self.export)
            self._note(self.workspace, "O CSV contém texto original em inglês. Mantenha-o privado.")
        elif name == "merge":
            self._header("Mesclar CSVs", "Combine revisões em um único arquivo pronto para importação.")
            card = self._build_card()
            self._path_field(card, 0, "PASTA CONTENDO OS CSVs", self.merge_folder, "folder")
            self._path_field(card, 1, "CSV UNIFICADO DE SAÍDA", self.merge_output, "save-csv")
            self._primary_button(self.workspace, "MESCLAR CSVs", self.merge)
            self._note(self.workspace, "A união usa a coluna 'chave'. Células vazias não substituem "
                         "valores; conflitos são resolvidos pelo último valor não vazio, seguindo "
                         "a ordem alfabética dos arquivos.")
        elif name == "patch":
            self._header("Aplicar patch", "Importe uma revisão ou gere um pacote completo do zero.")
            card = self._build_card()
            self._path_field(card, 0, "CSV REVISADO", self.csv_path, "open-csv")
            self._path_field(card, 1, "PATCH MESTRE JSON", self.master_path, "save-patch")
            self._path_field(card, 2, "PASTA DAS PARTES PUBLICADAS (FALLBACK)",
                             self.pieces_path, "folder")
            self._primary_button(self.workspace, "IMPORTAR CSV PARA O PATCH", self.import_)
            ctk.CTkFrame(self.workspace, height=1, fg_color=("#d8dce2", "#3b3e46")).grid(
                row=4, column=0, padx=30, pady=14, sticky="ew")
            new_card = self._build_card(row=5)
            self._path_field(new_card, 0, "PASTA NOVA PARA GERAR JSON + PARTES",
                             self.new_destination, "new-destination")
            create_button = ctk.CTkButton(
                self.workspace, text="CRIAR PATCH DO ZERO", command=self.create_patch,
                height=46, corner_radius=10, font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="#3b8067", hover_color="#2d6853")
            create_button.grid(row=6, column=0, padx=30, pady=(16, 4), sticky="ew")
            self.buttons.append(create_button)
            self._note(self.workspace, "Criar patch exige uma pasta de destino ainda inexistente. "
                         "Nada é publicado automaticamente.")
        else:
            self._header("Créditos e informações", "CSV Hub — ferramentas locais de patch PT-BR.")
            card = self._build_card()
            ctk.CTkLabel(card, text="DESENVOLVEDOR PRINCIPAL", anchor="w",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=("#69727e", "#a4aab4")).grid(
                             row=0, column=0, padx=22, pady=(22, 4), sticky="w")
            ctk.CTkLabel(card, text="DracanX", anchor="w",
                         font=ctk.CTkFont(size=25, weight="bold"),
                         text_color=self.ACCENT).grid(
                             row=1, column=0, padx=22, pady=(0, 10), sticky="w")
            ctk.CTkLabel(
                card, text="Ferramenta para exportação, revisão, mesclagem e aplicação de patches "
                "CSV em arquivos locais. Desenvolvida com Python e CustomTkinter.",
                anchor="w", justify="left", wraplength=650,
                text_color=("#525a65", "#c2c6cd")).grid(
                    row=2, column=0, padx=22, pady=(0, 22), sticky="w")

    def _browse_for(self, variable: tk.StringVar, mode: str) -> None:
        current = variable.get()
        current_path = Path(current)
        initial = current_path if mode == "folder" and current_path.is_dir() else current_path.parent
        if not initial.is_dir():
            initial = ROOT
        if mode in ("folder", "new-destination"):
            path = filedialog.askdirectory(parent=self.root, initialdir=str(initial))
            if path and mode == "new-destination":
                path = str(Path(path) / "patch_pt_br_novo")
        elif mode == "open-csv":
            path = filedialog.askopenfilename(
                parent=self.root, initialdir=str(initial), filetypes=(("CSV", "*.csv"),))
        elif mode == "save-csv":
            path = filedialog.asksaveasfilename(
                parent=self.root, initialdir=str(initial),
                initialfile=Path(current).name, defaultextension=".csv",
                filetypes=(("CSV", "*.csv"),))
        elif mode == "open-patch":
            path = filedialog.askopenfilename(
                parent=self.root, initialdir=str(initial),
                filetypes=(("Patch JSON", "*.json"),))
        elif mode == "save-patch":
            path = filedialog.asksaveasfilename(
                parent=self.root, initialdir=str(initial),
                initialfile=Path(current).name, defaultextension=".json",
                filetypes=(("Patch JSON", "*.json"),))
        else:
            raise ValueError(f"Modo de seleção inválido: {mode}")
        if path:
            variable.set(path)

    def _run(self, label: str, operation, on_success=None) -> None:
        self.status_text.set(f"{label} em andamento...")
        self.status_indicator.configure(text_color="#e0a43a")
        for button in self.buttons:
            button.configure(state="disabled")

        def work() -> None:
            try:
                result = operation()
            except Exception as exc:
                self.root.after(0, lambda error=exc: self._finished(error=error))
            else:
                self.root.after(
                    0, lambda value=result: self._finished(value=value, on_success=on_success))

        threading.Thread(target=work, daemon=True, name="review-gui-worker").start()

    def _finished(self, value=None, error: Exception | None = None, on_success=None) -> None:
        for button in self.buttons:
            button.configure(state="normal")
        if error is not None:
            self.status_text.set(f"Falha: {error}")
            self.status_indicator.configure(text_color="#d9534f")
            messagebox.showerror("Operação não concluída", str(error), parent=self.root)
        else:
            self.status_text.set(value.splitlines()[0] if value else "Concluído.")
            self.status_indicator.configure(text_color="#2fa572")
            if on_success:
                on_success()
            messagebox.showinfo("Concluído", value, parent=self.root)

    def export(self) -> None:
        map_path = Path(self.map_path.get()) / "map_pt_br.db"
        if not map_path.is_file():
            messagebox.showerror("Mapa não encontrado", "Selecione um map_pt_br.db válido.",
                                 parent=self.root)
            return
        master = Path(self.master_path.get())
        pieces = Path(self.pieces_path.get())
        csv_path = Path(self.csv_path.get())
        if not csv_path.suffix:
            csv_path = csv_path.with_suffix(".csv")
            self.csv_path.set(str(csv_path))
        if csv_path.exists() and not messagebox.askyesno(
                "Substituir CSV?", f"O arquivo já existe:\n{csv_path}\n\nSubstituir?",
                parent=self.root):
            return

        def operation() -> str:
            count = export_csv(map_path, master, pieces, csv_path)
            return f"CSV exportado: {count} linhas\n{csv_path}"

        self._run("Exportação do CSV", operation)

    def import_(self) -> None:
        review = Path(self.csv_path.get())
        if not review.is_file():
            messagebox.showerror("CSV não encontrado", "Selecione um CSV de revisão existente.",
                                 parent=self.root)
            return
        master = Path(self.master_path.get())
        pieces = Path(self.pieces_path.get())
        if not messagebox.askyesno(
                "Confirmar importação",
                "As traduções preenchidas em 'nova_tradução' serão incorporadas ao patch mestre "
                "JSON selecionado. Um backup será criado se o arquivo já existir. "
                "Esta ação não publica as alterações no GitHub. Continuar?",
                parent=self.root):
            return

        def operation() -> str:
            changed, removed, backup = import_csv(review, master, pieces)
            result = (f"Patch atualizado: {changed} traduções adicionadas/alteradas, "
                      f"{removed} removidas.\n{master}")
            if backup:
                result += f"\nBackup: {backup}"
            if not changed and not removed:
                result = "Nenhuma alteração encontrada no CSV; o patch não foi modificado."
            return result

        self._run("Importação do CSV", operation)

    def merge(self) -> None:
        directory = Path(self.merge_folder.get())
        output = Path(self.merge_output.get())
        if not directory.is_dir():
            messagebox.showerror("Pasta não encontrada", "Selecione uma pasta válida de CSVs.",
                                 parent=self.root)
            return
        if output.exists() and not messagebox.askyesno(
                "Substituir CSV?", f"O arquivo já existe:\n{output}\n\nSubstituir?",
                parent=self.root):
            return

        def operation() -> str:
            files, rows, conflicts = merge_csvs(directory, output)
            return (f"CSV unificado: {files} arquivos, {rows} chaves e {conflicts} "
                    f"conflitos resolvidos.\n{output}")

        self._run("Mesclagem dos CSVs", operation,
                  on_success=lambda: self.csv_path.set(str(output)))

    def create_patch(self) -> None:
        review = Path(self.csv_path.get())
        destination = Path(self.new_destination.get())
        if not review.is_file():
            messagebox.showerror("CSV não encontrado", "Selecione um CSV revisado existente.",
                                 parent=self.root)
            return
        if destination.exists():
            messagebox.showerror(
                "Destino já existe",
                "Para evitar sobrescrever arquivos, escolha uma pasta de destino que ainda não exista.",
                parent=self.root)
            return
        if not messagebox.askyesno(
                "Criar patch do zero",
                f"Será criado um novo patch em:\n{destination}\n\nContinuar?",
                parent=self.root):
            return

        def operation() -> str:
            count, version = create_patch_from_csv(review, destination)
            return (f"Patch criado: {count} traduções, versão {version}.\n"
                    f"JSON mestre e partes: {destination}")

        self._run("Criação do patch", operation)

def main() -> None:
    root = ctk.CTk()
    ReviewApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
