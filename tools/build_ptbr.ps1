param(
    [switch]$SkipDependencyInstall,
    [switch]$SkipModelDownload
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not $SkipDependencyInstall) {
    py -3.12 -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install build dependencies."
    }
}

$modelPath = Join-Path $projectRoot "PT_BR\model\model\model.bin"
if (-not (Test-Path -LiteralPath $modelPath)) {
    if ($SkipModelDownload) {
        throw "Model is missing. Run tools\prepare_ptbr_model.py or omit -SkipModelDownload."
    }
    py -3.12 tools\prepare_ptbr_model.py
    if ($LASTEXITCODE -ne 0) {
        throw "Could not download and verify the translation model."
    }
}

py -3.12 -m PyInstaller --noconfirm --clean --noconsole --onedir `
    --name Local_Translator_PTBR `
    --paths src `
    --add-data "src\glossary_pt-br.default.json;." `
    --hidden-import ctranslate2 `
    --collect-all ctranslate2 `
    --collect-all sentencepiece `
    src\lt_module.py
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller could not build the module."
}

Write-Output "Build complete: dist\Local_Translator_PTBR"
