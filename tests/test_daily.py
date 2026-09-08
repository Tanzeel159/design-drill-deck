from __future__ import annotations

import unittest
from datetime import date, timedelta
from pathlib import Path

from scripts.generate_daily import (
    ANCHOR_DATE,
    ANCHOR_PROMPT_ID,
    DEFAULT_SOURCE,
    DIFFICULTY_LEVELS,
    MAX_PRIMARY_USER_LENGTH,
    build_payload,
    build_pick,
    build_pools,
    load_prompts,
    source_digest,
)


class DailyFeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prompts = load_prompts()
        cls.pools = build_pools(cls.prompts)

    def ids_for(self, scope: str) -> list[str]:
        return [prompt["id"] for prompt in self.pools[scope]]

    def test_anchor_matches_shipped_paper_design(self) -> None:
        pick = build_pick(self.ids_for("all"), "all", ANCHOR_DATE, "smart_shuffle")
        self.assertEqual(pick["prompt_id"], ANCHOR_PROMPT_ID)

    def test_smart_shuffle_is_deterministic(self) -> None:
        ids = self.ids_for("all")
        first = build_pick(ids, "all", date(2027, 2, 8), "smart_shuffle")
        second = build_pick(ids, "all", date(2027, 2, 8), "smart_shuffle")
        self.assertEqual(first, second)

    def test_every_prompt_appears_once_per_smart_shuffle_cycle(self) -> None:
        for scope in self.pools:
            ids = self.ids_for(scope)
            observed = {
                build_pick(
                    ids,
                    scope,
                    ANCHOR_DATE + timedelta(days=offset),
                    "smart_shuffle",
                )["prompt_id"]
                for offset in range(len(ids))
            }
            self.assertEqual(observed, set(ids), scope)

    def test_smart_shuffle_avoids_cycle_boundary_repeats(self) -> None:
        for scope in self.pools:
            ids = self.ids_for(scope)
            if len(ids) < 2:
                continue
            for cycle in range(-3, 6):
                boundary = (cycle + 1) * len(ids)
                last = build_pick(
                    ids,
                    scope,
                    ANCHOR_DATE + timedelta(days=boundary - 1),
                    "smart_shuffle",
                )["prompt_id"]
                next_first = build_pick(
                    ids,
                    scope,
                    ANCHOR_DATE + timedelta(days=boundary),
                    "smart_shuffle",
                )["prompt_id"]
                self.assertNotEqual(last, next_first, f"{scope}, cycle {cycle}")

    def test_sequence_does_not_reset_at_new_year(self) -> None:
        ids = self.ids_for("all")
        dec_31 = build_pick(ids, "all", date(2027, 12, 31), "smart_shuffle")
        jan_1 = build_pick(ids, "all", date(2028, 1, 1), "smart_shuffle")
        self.assertNotEqual(dec_31["prompt_id"], jan_1["prompt_id"])

    def test_sequential_mode_follows_source_order_from_anchor(self) -> None:
        ids = self.ids_for("all")
        anchor_index = ids.index(ANCHOR_PROMPT_ID)
        tomorrow = build_pick(
            ids, "all", ANCHOR_DATE + timedelta(days=1), "sequential"
        )
        self.assertEqual(tomorrow["prompt_id"], ids[(anchor_index + 1) % len(ids)])

    def test_payload_contains_every_scope_and_mode(self) -> None:
        payload = build_payload(
            self.prompts,
            ANCHOR_DATE,
            source_digest(DEFAULT_SOURCE),
        )
        expected_scopes = set(self.pools)
        self.assertEqual(set(payload["daily_picks"]["smart_shuffle"]), expected_scopes)
        self.assertEqual(set(payload["daily_picks"]["sequential"]), expected_scopes)
        self.assertEqual(payload["rotation_date"], "2026-07-20")
        self.assertEqual(payload["display_date"], "2026-07-20T12:00:00")
        expected_levels = {level["key"] for level in DIFFICULTY_LEVELS}
        for mode in ("smart_shuffle", "sequential"):
            for scope in expected_scopes:
                self.assertEqual(
                    set(payload["daily_picks"][mode][scope]), expected_levels
                )

    def test_difficulty_profiles_increase_scope_without_timing(self) -> None:
        pattern_limits = [level["pattern_limit"] for level in DIFFICULTY_LEVELS]
        self.assertEqual(pattern_limits, sorted(pattern_limits))
        self.assertTrue(
            all("timebox_minutes" not in level for level in DIFFICULTY_LEVELS)
        )
        self.assertEqual(
            {level["key"] for level in DIFFICULTY_LEVELS},
            {"beginner", "intermediate", "advanced"},
        )

    def test_bank_has_balanced_category_coverage(self) -> None:
        self.assertEqual(len(self.prompts), 54)
        category_sizes = {
            scope: len(prompts)
            for scope, prompts in self.pools.items()
            if scope != "all"
        }
        self.assertEqual(set(category_sizes.values()), {6})
        self.assertTrue(
            all(
                len(prompt["primary_user"]) <= MAX_PRIMARY_USER_LENGTH
                for prompt in self.prompts
            )
        )

    def test_information_architecture_is_a_rotating_scope(self) -> None:
        ids = self.ids_for("information_architecture")
        self.assertEqual(len(ids), 6)
        payload = build_payload(
            self.prompts,
            ANCHOR_DATE,
            source_digest(DEFAULT_SOURCE),
        )
        self.assertEqual(
            payload["daily_picks"]["smart_shuffle"]["information_architecture"]
            ["beginner"]["pool_size"],
            6,
        )


class TemplateQualityTests(unittest.TestCase):
    layouts = ("full", "half_horizontal", "half_vertical", "quadrant")
    source_dir = Path(__file__).resolve().parents[1] / "src"

    def test_templates_use_framework_classes_only(self) -> None:
        for layout in self.layouts:
            source = (self.source_dir / f"{layout}.liquid").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("style=", source, layout)

    def test_every_layout_adapts_to_large_and_portrait_screens(self) -> None:
        for layout in self.layouts:
            source = (self.source_dir / f"{layout}.liquid").read_text(
                encoding="utf-8"
            )
            self.assertIn("lg:", source, layout)
            self.assertIn("portrait:", source, layout)


if __name__ == "__main__":
    unittest.main()
