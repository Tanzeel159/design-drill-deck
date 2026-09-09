/**
 * Optional serverless transform for the Design Drill Deck polling feed.
 *
 * polling_url already returns Liquid-ready JSON. This pass keeps that contract
 * explicit: prompts, daily_picks, difficulty_levels, and display_date are the
 * merge variables the layouts read. Enable it by setting serverless_language
 * to node; leave it unused if the raw daily.json payload is merged as-is.
 */
function run(input) {
  const feed =
    input && Array.isArray(input.prompts)
      ? input
      : (input && input.data) || input || {};
  return {
    prompts: feed.prompts || [],
    daily_picks: feed.daily_picks || {},
    difficulty_levels: feed.difficulty_levels || [],
    display_date: feed.display_date || feed.rotation_date,
    rotation_date: feed.rotation_date,
    default_difficulty: feed.default_difficulty || "intermediate",
    default_rotation_mode: feed.default_rotation_mode || "smart_shuffle",
    scopes: feed.scopes || [],
    timezone: feed.timezone,
    schema_version: feed.schema_version,
    trmnl: input && input.trmnl,
  };
}

function transform(input) {
  return run(input);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { run, transform };
}
