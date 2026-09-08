#!/usr/bin/env python3
"""Generate the date-stamped JSON feed consumed by the TRMNL plugin."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo
try:
    from scripts.cards import validate_card
except ModuleNotFoundError:
    from cards import validate_card


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "prompts.json"
DEFAULT_OUTPUT = ROOT / "data" / "daily.json"
TIME_ZONE = "America/Chicago"
ANCHOR_DATE = date(2026, 7, 20)
ANCHOR_PROMPT_ID = "ddd-004"
SHUFFLE_SEED = "design-drill-deck-smart-shuffle-v1"
DEFAULT_DIFFICULTY = "intermediate"
MAX_PRIMARY_USER_LENGTH = 56
DIFFICULTY_LEVELS = (
    {
        "key": "beginner",
        "label": "Beginner",
        "pattern_limit": 3,
        "compact_pattern_limit": 3,
        "scope_note": "Solve one primary happy path, one key screen, and one recovery state.",
    },
    {
        "key": "intermediate",
        "label": "Intermediate",
        "pattern_limit": 4,
        "compact_pattern_limit": 4,
        "scope_note": "Cover the main flow, two meaningful edge cases, and one success metric.",
    },
    {
        "key": "advanced",
        "label": "Advanced",
        "pattern_limit": 6,
        "compact_pattern_limit": 4,
        "scope_note": "Address system states, risk, accessibility, tradeoffs, and measurement.",
    },
)
REQUIRED_PROMPT_FIELDS = {
    "id",
    "mode",
    "industry",
    "primary_user",
    "business_goal",
    "constraint",
    "problem",
    "ai_capability",
    "watch_for",
    "required_patterns",
    "deliverables",
    "interview_focus",
}


def slugify(value: str) -> str:
    """Convert a display label to the stable key used by TRMNL controls."""
    key = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    if not key:
        raise ValueError(f"Cannot create a scope key from {value!r}")
    return key


def source_digest(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_prompts(path: Path = DEFAULT_SOURCE) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    prompts = payload.get("prompts")
    if not isinstance(prompts, list) or not prompts:
        raise ValueError("prompts.json must contain a non-empty 'prompts' array")

    seen_ids: set[str] = set()
    for position, prompt in enumerate(prompts, start=1):
        if not isinstance(prompt, dict):
            raise ValueError(f"Prompt {position} must be an object")
        missing = REQUIRED_PROMPT_FIELDS - prompt.keys()
        if missing:
            raise ValueError(
                f"Prompt {position} is missing: {', '.join(sorted(missing))}"
            )
        prompt_id = prompt["id"]
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ValueError(f"Prompt {position} has an invalid id")
        if prompt_id in seen_ids:
            raise ValueError(f"Duplicate prompt id: {prompt_id}")
        seen_ids.add(prompt_id)
        validate_card(prompt)
        if not isinstance(prompt["required_patterns"], list):
            raise ValueError(f"Prompt {prompt_id} required_patterns must be an array")
        if len(prompt["primary_user"]) > MAX_PRIMARY_USER_LENGTH:
            raise ValueError(
                f"Prompt {prompt_id} primary_user exceeds "
                f"{MAX_PRIMARY_USER_LENGTH} characters"
            )

    if ANCHOR_PROMPT_ID not in seen_ids:
        raise ValueError(f"Anchor prompt {ANCHOR_PROMPT_ID} is missing")

    category_counts: dict[str, int] = {}
    for prompt in prompts:
        category_counts[prompt["mode"]] = category_counts.get(prompt["mode"], 0) + 1
    undersized = {
        category: count for category, count in category_counts.items() if count < 3
    }
    if undersized:
        details = ", ".join(
            f"{category} ({count})" for category, count in sorted(undersized.items())
        )
        raise ValueError(f"Every category needs at least 3 prompts: {details}")
    return prompts


def build_pools(
    prompts: Iterable[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    prompt_list = list(prompts)
    pools: dict[str, list[dict[str, Any]]] = {"all": prompt_list}
    for prompt in prompt_list:
        key = slugify(prompt["mode"])
        pools.setdefault(key, []).append(prompt)
    return pools


def _hash_order(ids: tuple[str, ...], scope: str, cycle: int) -> list[str]:
    def score(prompt_id: str) -> str:
        value = f"{SHUFFLE_SEED}|{scope}|{cycle}|{prompt_id}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    order = sorted(ids, key=score)
    if cycle == 0 and ANCHOR_PROMPT_ID in order:
        anchor_index = order.index(ANCHOR_PROMPT_ID)
        order = order[anchor_index:] + order[:anchor_index]
    return order


def smart_shuffle_order(ids: list[str], scope: str, cycle: int) -> list[str]:
    """Return a stable shuffled cycle with no repeat at cycle boundaries."""
    if len(ids) < 2:
        return ids.copy()

    frozen_ids = tuple(ids)
    current = _hash_order(frozen_ids, scope, 0)
    if cycle > 0:
        for cycle_number in range(1, cycle + 1):
            next_order = _hash_order(frozen_ids, scope, cycle_number)
            if next_order[0] == current[-1]:
                next_order[0], next_order[1] = next_order[1], next_order[0]
            current = next_order
    elif cycle < 0:
        for cycle_number in range(-1, cycle - 1, -1):
            previous_order = _hash_order(frozen_ids, scope, cycle_number)
            if previous_order[-1] == current[0]:
                previous_order[-1], previous_order[-2] = (
                    previous_order[-2],
                    previous_order[-1],
                )
            current = previous_order
    return current


def sequential_order(ids: list[str]) -> list[str]:
    order = ids.copy()
    if ANCHOR_PROMPT_ID in order:
        anchor_index = order.index(ANCHOR_PROMPT_ID)
        return order[anchor_index:] + order[:anchor_index]
    return order


def build_pick(
    ids: list[str], scope: str, rotation_date: date, mode: str
) -> dict[str, Any]:
    if not ids:
        raise ValueError(f"Prompt pool {scope!r} is empty")

    day_offset = (rotation_date - ANCHOR_DATE).days
    cycle, position = divmod(day_offset, len(ids))
    if mode == "smart_shuffle":
        order = smart_shuffle_order(ids, scope, cycle)
    elif mode == "sequential":
        order = sequential_order(ids)
    else:
        raise ValueError(f"Unknown rotation mode: {mode}")

    prompt_id = order[position]
    return {
        "prompt_id": prompt_id,
        "drill_number": ids.index(prompt_id) + 1,
        "position": position + 1,
        "pool_size": len(ids),
        "cycle": cycle,
    }


def build_payload(
    prompts: list[dict[str, Any]], rotation_date: date, digest: str
) -> dict[str, Any]:
    pools = build_pools(prompts)
    picks: dict[str, dict[str, dict[str, dict[str, Any]]]] = {
        "smart_shuffle": {},
        "sequential": {},
    }
    scopes: list[dict[str, Any]] = []

    for scope, scoped_prompts in pools.items():
        ids = [prompt["id"] for prompt in scoped_prompts]
        label = "All categories" if scope == "all" else scoped_prompts[0]["mode"]
        scopes.append({"key": scope, "label": label, "count": len(ids)})
        for mode in picks:
            picks[mode][scope] = {}
            for level in DIFFICULTY_LEVELS:
                level_key = level["key"]
                picks[mode][scope][level_key] = build_pick(
                    ids,
                    f"{scope}:{level_key}",
                    rotation_date,
                    mode,
                )

    return {
        "schema_version": 1,
        "rotation_date": rotation_date.isoformat(),
        # Noon keeps date-only labels stable when LiquidJS previews run west of UTC.
        "display_date": f"{rotation_date.isoformat()}T12:00:00",
        "timezone": TIME_ZONE,
        "anchor_date": ANCHOR_DATE.isoformat(),
        "source_sha256": digest,
        "default_rotation_mode": "smart_shuffle",
        "default_difficulty": DEFAULT_DIFFICULTY,
        "difficulty_levels": [dict(level) for level in DIFFICULTY_LEVELS],
        "scopes": scopes,
        "daily_picks": picks,
        "prompts": prompts,
    }


def resolve_date(raw_date: str | None) -> date:
    if raw_date:
        return date.fromisoformat(raw_date)
    return datetime.now(ZoneInfo(TIME_ZONE)).date()


def serialize(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default="", help="Override date in YYYY-MM-DD format")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero instead of writing when the output is not current",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        prompts = load_prompts(args.source)
        rotation_date = resolve_date(args.date)
        payload = build_payload(prompts, rotation_date, source_digest(args.source))
        rendered = serialize(payload)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    existing = args.output.read_text(encoding="utf-8") if args.output.exists() else None
    if args.check:
        if existing != rendered:
            print(f"{args.output} is not generated for {rotation_date}", file=sys.stderr)
            return 1
        print(f"{args.output} is current for {rotation_date}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if existing == rendered:
        print(f"{args.output} already current for {rotation_date}")
    else:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"Generated {args.output} for {rotation_date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
