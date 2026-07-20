#!/usr/bin/env python3
"""Validate source data, generated feed, TRMNL settings, and templates."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yaml
except ImportError:  # pragma: no cover - CI installs requirements-dev.txt
    yaml = None

from scripts.generate_daily import (
    ROOT,
    build_pools,
    build_payload,
    load_prompts,
    source_digest,
)


LAYOUTS = ("full", "half_horizontal", "half_vertical", "quadrant")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_daily_feed() -> None:
    source_path = ROOT / "data" / "prompts.json"
    daily_path = ROOT / "data" / "daily.json"
    prompts = load_prompts(source_path)
    actual = json.loads(daily_path.read_text(encoding="utf-8"))
    rotation_date = date.fromisoformat(actual["rotation_date"])
    expected = build_payload(prompts, rotation_date, source_digest(source_path))
    require(actual == expected, "data/daily.json does not match the generator")


def validate_settings() -> None:
    settings_path = ROOT / "src" / "settings.yml"
    source = settings_path.read_text(encoding="utf-8")
    if yaml is None:
        required_fragments = (
            "refresh_interval: 60",
            "daily.json",
            "keyname: focus_area",
            "keyname: difficulty",
            "keyname: rotation_mode",
            "default: smart_shuffle",
        )
        for fragment in required_fragments:
            require(fragment in source, f"settings.yml is missing {fragment!r}")
        print("warning: PyYAML unavailable; settings.yml received structural checks only")
        return

    settings = yaml.safe_load(source)
    require(settings["strategy"] == "polling", "strategy must be polling")
    require(settings["refresh_interval"] == 60, "refresh_interval must be 60 minutes")
    require(settings["polling_url"].endswith("/daily.json"), "polling_url must use daily.json")
    fields = {
        field["keyname"]: field
        for field in settings.get("custom_fields", [])
        if field.get("field_type") != "author_bio"
    }
    require("focus_area" in fields, "focus_area control is missing")
    require("difficulty" in fields, "difficulty control is missing")
    require("rotation_mode" in fields, "rotation_mode control is missing")
    require(
        fields["difficulty"].get("default") == "intermediate",
        "intermediate must be the default difficulty",
    )
    require(
        fields["rotation_mode"].get("default") == "smart_shuffle",
        "smart shuffle must be the default rotation mode",
    )
    configured_scopes = {
        next(iter(option.values()))
        for option in fields["focus_area"].get("options", [])
        if isinstance(option, dict) and option
    }
    expected_scopes = set(build_pools(load_prompts()))
    require(
        configured_scopes == expected_scopes,
        "focus-area options must match the categories in prompts.json",
    )


def validate_templates() -> None:
    required_fragments = (
        "trmnl.plugin_settings.custom_fields_values",
        "focus_area",
        "difficulty",
        "rotation_mode",
        "daily_picks",
        "rotation_date",
    )
    for layout in LAYOUTS:
        path = ROOT / "src" / f"{layout}.liquid"
        require(path.exists(), f"Missing layout: {path.name}")
        source = path.read_text(encoding="utf-8")
        for fragment in required_fragments:
            require(fragment in source, f"{path.name} is missing {fragment!r}")
        require(
            "timebox_minutes" not in source,
            f"{path.name} must not expose exercise timing",
        )

    preview = (ROOT / "preview" / "index.html").read_text(encoding="utf-8")
    require("../data/daily.json" in preview, "Preview must load the generated daily feed")
    require(
        "timebox_minutes" not in preview,
        "Preview must not expose exercise timing",
    )


def validate_workflows() -> None:
    for name in ("ci.yml", "publish-daily.yml"):
        require((ROOT / ".github" / "workflows" / name).exists(), f"Missing {name}")


def main() -> int:
    try:
        validate_daily_feed()
        validate_settings()
        validate_templates()
        validate_workflows()
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"validation failed: {error}", file=sys.stderr)
        return 1
    print("Project validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
