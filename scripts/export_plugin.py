"""Create a flat ZIP that TRMNL can import as a private plugin."""
from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
DEFAULT_OUTPUT = ROOT / "design-drill-deck-trmnl.zip"
FORBIDDEN_PATTERNS = (
    r"OPENAI_API_KEY",
    r"BEGIN PRIVATE KEY",
    r"AKIA[0-9A-Z]{16}",
)


def _normalize(text: str) -> bytes:
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def validate_sources() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for name in REQUIRED:
        path = SRC / name
        if not path.is_file():
            raise SystemExit(f"Missing TRMNL export file: src/{name}")
        payload = _normalize(path.read_text(encoding="utf-8"))
        if name.endswith(".liquid") and len(payload) > MAX_TEMPLATE_BYTES:
            raise SystemExit(f"Template exceeds TRMNL's 1 MB limit: src/{name}")
        text = payload.decode("utf-8")
        if name.endswith(".liquid") and re.search(r"<style\b|\bstyle\s*=", text, re.IGNORECASE):
            raise SystemExit(f"Use native Framework classes, not embedded or inline CSS: src/{name}")
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text):
                raise SystemExit(f"Refusing to export secrets from src/{name}")
        files[name] = payload

    settings = files["settings.yml"].decode("utf-8")
    for fragment in ("name:", "strategy: polling", "refresh_interval: 60", "daily.json"):
        if fragment not in settings:
            raise SystemExit(f"settings.yml is missing {fragment!r}")
    if "custom_fields:" not in settings:
        raise SystemExit("settings.yml must include the plugin form custom_fields")
    return files


def write_zip(files: dict[str, bytes], output: Path) -> dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in REQUIRED:
            info = zipfile.ZipInfo(filename=name)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3  # Unix; avoids Windows path-separator surprises
            info.external_attr = 0o644 << 16
            archive.writestr(info, files[name])
        names = archive.namelist()
        if names != list(REQUIRED):
            raise SystemExit(f"Unexpected ZIP contents: {names}")
        if any("/" in name or "\\" in name for name in names):
            raise SystemExit("TRMNL import requires a flat ZIP with no folders")
        if "settings.yml" not in names:
            raise SystemExit("The ZIP file does not contain settings.yml")
    output.write_bytes(buffer.getvalue())
    return {"output": str(output), "files": list(REQUIRED), "bytes": output.stat().st_size}


def export(output: Path, rebuild: bool = True) -> dict[str, object]:
    if rebuild:
        from scripts.build_layouts import build

        build()
    return write_zip(validate_sources(), output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate the six export files without writing a ZIP",
    )
    args = parser.parse_args()
    if args.check_only:
        validate_sources()
        print("TRMNL export files are valid")
        return 0
    print(export(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
