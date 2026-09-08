"""Create a flat ZIP that can be imported as a TRMNL private plugin."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
REQUIRED = (
    "settings.yml",
    "shared.liquid",
    "full.liquid",
    "half_horizontal.liquid",
    "half_vertical.liquid",
    "quadrant.liquid",
)
MAX_TEMPLATE_BYTES = 1_000_000


def validate_sources() -> list[Path]:
    files = []
    for name in REQUIRED:
        path = SRC / name
        if not path.is_file():
            raise SystemExit(f"Missing TRMNL export file: src/{name}")
        if name.endswith(".liquid") and path.stat().st_size > MAX_TEMPLATE_BYTES:
            raise SystemExit(f"Template exceeds TRMNL's 1 MB limit: src/{name}")
        if name.endswith(".liquid"):
            markup = path.read_text(encoding="utf-8")
            if re.search(r'<style\b|\bstyle\s*=', markup, re.IGNORECASE):
                raise SystemExit(f"Use native Framework classes, not embedded or inline CSS: src/{name}")
        files.append(path)
    return files


def export(output: Path) -> dict[str, object]:
    files = validate_sources()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            # Arc names are deliberately flat; TRMNL expects these at the ZIP root.
            archive.write(path, arcname=path.name)
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        if names != list(REQUIRED):
            raise SystemExit(f"Unexpected ZIP contents: {names}")
    return {"output": str(output), "files": list(REQUIRED), "bytes": output.stat().st_size}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "design-drill-deck-trmnl.zip")
    parser.add_argument("--check-only", action="store_true", help="Validate the six export files without writing a ZIP")
    args = parser.parse_args()
    if not args.check_only:
        from build_layouts import build
        build()
    validate_sources()
    if args.check_only:
        print("TRMNL export files are valid")
    else:
        print(export(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
