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
    load_generated,
    load_prompts,
    source_digest,
)


LAYOUTS = ("full", "half_horizontal", "half_vertical", "quadrant")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_daily_feed() -> None:
    source_path = ROOT / "data" / "prompts.json"
    generated_path = ROOT / "data" / "generated.json"
    daily_path = ROOT / "data" / "daily.json"
    require(generated_path.is_file(), "data/generated.json is required")
    prompts = load_prompts(source_path)
    generated = load_generated(generated_path)
    actual = json.loads(daily_path.read_text(encoding="utf-8"))
    rotation_date = date.fromisoformat(actual["rotation_date"])
    digest_paths = [source_path]
    if generated:
        digest_paths.append(generated_path)
    expected = build_payload(
        prompts, rotation_date, source_digest(*digest_paths), generated
    )
    require(actual == expected, "data/daily.json does not match the generator")


def validate_settings() -> None:
    settings_path = ROOT / "src" / "settings.yml"
    source = settings_path.read_text(encoding="utf-8")
    if yaml is None:
        required_fragments = (
            "refresh_interval: 60",
            "daily.json",
            "polling_url:",
            "prompts, daily_picks, difficulty_levels, display_date",
            "keyname: focus_area",
            "keyname: difficulty",
            "keyname: rotation_mode",
            "default: smart_shuffle",
            "email_address:",
        )
        for fragment in required_fragments:
            require(fragment in source, f"settings.yml is missing {fragment!r}")
        print("warning: PyYAML unavailable; settings.yml received structural checks only")
        return

    settings = yaml.safe_load(source)
    require(settings["strategy"] == "polling", "strategy must be polling")
    require(settings["refresh_interval"] == 60, "refresh_interval must be 60 minutes")
    require(settings["polling_url"].endswith("/daily.json"), "polling_url must use daily.json")
    require(
        "prompts, daily_picks, difficulty_levels, display_date" in source,
        "settings.yml must document the polling JSON keys used by Liquid",
    )
    bios = [
        field
        for field in settings.get("custom_fields", [])
        if field.get("field_type") == "author_bio"
    ]
    require(bios, "author_bio is required so the plugin page can introduce the recipe")
    bio = bios[0]
    require(
        bool(bio.get("email_address") or bio.get("github_url") or bio.get("learn_more_url")),
        "author_bio must include a contact method (email_address, github_url, or learn_more_url)",
    )
    fields = {
        field["keyname"]: field
        for field in settings.get("custom_fields", [])
        if field.get("field_type") != "author_bio"
    }
    require("focus_area" in fields, "focus_area control is missing")
    require("difficulty" in fields, "difficulty control is missing")
    require("rotation_mode" in fields, "rotation_mode control is missing")
    require(
        bool(fields["focus_area"].get("help_text")),
        "focus_area should explain the category list before the dropdown",
    )
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
    configured_scopes = {
        "all" if key == "all_categories" else key for key in configured_scopes
    }
    require(
        fields["focus_area"].get("default") in {"all", "all_categories"},
        "focus_area default must match the All-categories option value",
    )
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
        source = (ROOT / 'src' / 'shared.liquid').read_text(encoding='utf-8') + path.read_text(encoding="utf-8")
        for fragment in required_fragments:
            require(fragment in source, f"{path.name} is missing {fragment!r}")
        require(
            "timebox_minutes" not in source,
            f"{path.name} must not expose exercise timing",
        )
        require(
            "style=" not in source and "<style" not in source.lower(),
            f"{path.name} must use TRMNL framework classes instead of inline styles",
        )
        require(
            "lg:" in source,
            f"{path.name} must include a large-screen adaptation for TRMNL X",
        )
        require(
            "portrait:" in source,
            f"{path.name} must include a portrait adaptation",
        )
        require(
            "font--" not in source,
            f"{path.name} must use title/value/label/description classes, not font-- aliases",
        )
        require(
            "ddd-" not in path.read_text(encoding="utf-8")
            and "data-card-id" not in path.read_text(encoding="utf-8"),
            f"{path.name} must not use custom ddd-* classes or data-card-id",
        )

    selection = (ROOT / "src" / "selection.liquid").read_text(encoding="utf-8")
    require("| downcase" in selection, "Select values must be lowercased before daily_picks lookup")
    require("all_categories" in selection, "focus_area must accept Chef/platform all_categories alias")
    require("prompt_total > 0" in selection, "Modulo fallback must guard against an empty prompt bank")
    require("assign feed_empty" in selection, "Empty decks must set a feed_empty flag for markup")
    require("polling_url" in selection, "Shared markup must document the polling_url data source")
    require(
        '<div class="title_bar">' in (ROOT / "src" / "full.liquid").read_text(encoding="utf-8"),
        "full.liquid must inline a Framework title_bar sibling, not {% render %}",
    )
    transform = (ROOT / "src" / "transform.js").read_text(encoding="utf-8")
    for key in ("prompts", "daily_picks", "difficulty_levels", "display_date"):
        require(key in transform, f"transform.js must map {key!r}")

    preview = (ROOT / "preview" / "index.html").read_text(encoding="utf-8") + (ROOT / 'preview' / 'studio.js').read_text(encoding='utf-8')
    require("../data/daily.json" in preview, "Preview must load the generated daily feed")
    require(
        "timebox_minutes" not in preview,
        "Preview must not expose exercise timing",
    )
    require(
        "screen--lg" in preview and "screen--portrait" in preview,
        "Preview must include TRMNL X landscape and portrait fixtures",
    )


def validate_workflows() -> None:
    for name in ("ci.yml", "publish-daily.yml", "generate-prompts.yml"):
        require((ROOT / ".github" / "workflows" / name).exists(), f"Missing {name}")
    generate = (ROOT / ".github" / "workflows" / "generate-prompts.yml").read_text(
        encoding="utf-8"
    )
    require("OPENAI_API_KEY" in generate, "generation workflow must use OPENAI_API_KEY")
    require("generate_prompts.py" in generate, "generation workflow must run generate_prompts.py")
    require("schedule:" in generate, "generation workflow must run on a weekly schedule")
    require("--live" in generate, "scheduled generation must be able to run live")


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
