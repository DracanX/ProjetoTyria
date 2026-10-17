# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs

project_dir = Path(SPECPATH).resolve().parent
# Translation data is always compiled from the project-root folders, not from PT_BR runtime data.
datas = [(
    str(project_dir / 'glossary' / 'glossary_pt_br.json'),
    '.',
), (
    str(project_dir / 'plural' / 'plural_pt_br.json'),
    'plural',
)]
patch_dir = project_dir / 'patch' / 'pt_br'
if not patch_dir.joinpath('index.json').is_file():
    raise FileNotFoundError(f'Missing root patch index: {patch_dir / "index.json"}')
datas.extend(
    (str(path), str(Path('patch') / 'pt_br' / path.relative_to(patch_dir).parent))
    for path in patch_dir.rglob('*') if path.is_file()
)
model_dir = project_dir / 'model'
if model_dir.is_dir():
    datas.extend((str(path), str(Path('model') / path.relative_to(model_dir).parent))
                 for path in model_dir.rglob('*') if path.is_file())
binaries = collect_dynamic_libs('ctranslate2')
hiddenimports = []


a = Analysis(
    ['PTBR_module.py'],
    # Prefer the checked-out module sources beside this spec, regardless of the caller's cwd.
    pathex=[str(project_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Local_Translator_PT_BR',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Local_Translator_PT_BR',
)
