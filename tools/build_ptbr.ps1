param(
    [switch]$SkipDependencyInstall,
    [switch]$SkipModelDownload
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$tempBuild = Join-Path ([System.IO.Path]::GetTempPath()) `
    ("local-translator-ptbr-build-" + [guid]::NewGuid().ToString("N"))
$pyinstallerDist = Join-Path $tempBuild "dist"
$pyinstallerWork = Join-Path $tempBuild "work"
$pyinstallerSpec = Join-Path $tempBuild "spec"
$sourceDir = Join-Path $projectRoot "src"
$entryPoint = Join-Path $sourceDir "lt_module.py"
$glossaryPath = Join-Path $sourceDir "glossary_pt-br.default.json"
$moduleStage = Join-Path $projectRoot `
    "nexus_build\addons\text_translator\modules\local_translator_ptbr_perf"

if (-not $SkipDependencyInstall) {
    py -3.12 -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install build dependencies."
    }
}

$modelPath = Join-Path $moduleStage "PT_BR\model\model\model.bin"
if (-not (Test-Path -LiteralPath $modelPath)) {
    if ($SkipModelDownload) {
        throw "Model is missing from the Nexus package. Omit -SkipModelDownload to download it."
    }
    py -3.12 tools\prepare_ptbr_model.py --output (Join-Path $moduleStage "PT_BR\model")
    if ($LASTEXITCODE -ne 0) {
        throw "Could not download and verify the translation model."
    }
}

try {
    New-Item -ItemType Directory -Force -Path $tempBuild | Out-Null
    py -3.12 -m PyInstaller --noconfirm --clean --noconsole --onedir `
        --distpath $pyinstallerDist `
        --workpath $pyinstallerWork `
        --specpath $pyinstallerSpec `
        --name Local_Translator_PTBR `
        --paths $sourceDir `
        --add-data "${glossaryPath};." `
        --hidden-import ctranslate2 `
        --collect-all ctranslate2 `
        --collect-all sentencepiece `
        $entryPoint
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller could not build the module."
    }

    $runtimeDir = Join-Path $pyinstallerDist "Local_Translator_PTBR"
    if (-not (Test-Path -LiteralPath (Join-Path $runtimeDir "Local_Translator_PTBR.exe"))) {
        throw "PyInstaller output is incomplete: $runtimeDir"
    }

    New-Item -ItemType Directory -Force -Path $moduleStage | Out-Null
    $stagedInternal = Join-Path $moduleStage "_internal"
    if (Test-Path -LiteralPath $stagedInternal) {
        Remove-Item -LiteralPath $stagedInternal -Recurse -Force
    }
    Copy-Item -LiteralPath (Join-Path $runtimeDir "Local_Translator_PTBR.exe") `
        -Destination $moduleStage -Force
    Copy-Item -LiteralPath (Join-Path $runtimeDir "_internal") `
        -Destination $moduleStage -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot "src\text_translator\module.toml") `
        -Destination $moduleStage -Force
    Write-Output "Build complete: $moduleStage"
}
finally {
    if (Test-Path -LiteralPath $tempBuild) {
        $resolvedTemp = (Resolve-Path -LiteralPath $tempBuild).Path
        $tempRoot = [System.IO.Path]::GetTempPath()
        if (-not $resolvedTemp.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove build files outside the temporary directory: $resolvedTemp"
        }
        Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
    }
}
