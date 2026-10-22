"""Convert the OPUS-MT tc-big English-to-Portuguese checkpoint to CTranslate2 int8."""
from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

MODEL_NAME = "Helsinki-NLP/opus-mt-tc-big-en-pt"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "build" / "opus-mt-tc-big-en-pt-ct2-int8"


def _convert_model(output_dir: Path) -> None:
    from ctranslate2.converters.transformers import TransformersConverter

    converter = TransformersConverter(MODEL_NAME, low_cpu_mem_usage=True)
    converter.convert(str(output_dir), quantization="int8", force=True)


def prepare(output_dir: Path) -> None:
    required = ("model.bin", "source.spm", "target.spm")
    if all((output_dir / name).is_file() for name in required):
        print(f"OPUS-MT tc-big is already prepared in {output_dir}")
        return
    if output_dir.exists():
        raise FileExistsError(
            f"{output_dir} already exists but is incomplete; choose another path with --output-dir"
        )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".opus-convert-", dir=output_dir.parent) as temp:
        converted = Path(temp)
        _convert_model(converted)

        from transformers import MarianTokenizer

        tokenizer = MarianTokenizer.from_pretrained(MODEL_NAME)
        tokenizer.save_pretrained(converted)
        missing = [name for name in required if not (converted / name).is_file()]
        if missing:
            raise RuntimeError(f"converted model is missing required files: {', '.join(missing)}")
        os.replace(converted, output_dir)

    print(f"Prepared int8 OPUS-MT tc-big model in {output_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    prepare(args.output_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
