use anyhow::Result;
use clap::{Parser, Subcommand, ValueEnum};
use gtnh::{
    CROPS_RECIPE_TYPE, EuGraph, EuGraphEdge, EuGraphNode, GtRecipe, Recipe, RecipeIo, RecipeIoType,
    Repository, build_db, merge_db, tier_rank_u8,
};
use petgraph::Direction;
use petgraph::graph::NodeIndex;
use petgraph::visit::EdgeRef;
use serde::{Deserialize, Serialize};
use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap, HashSet};

// ===== CLI definition =====

#[derive(Parser)]
#[command(name = "gtnh", about = "Query GTNH items and recipes")]
struct Cli {
    /// Path to nesql.db
    #[arg(long, default_value = "nesql.db", global = true)]
    data: String,

    /// Emit JSON instead of human-readable text
    #[arg(long, global = true)]
    json: bool,

    /// Emit Graphviz DOT format (for eu-cost and uu-cost)
    #[arg(long, global = true)]
    dot: bool,

    /// Include Recycler recipes (hidden by default)
    #[arg(long, global = true)]
    all_recipes: bool,

    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Build gtnh.db from nesql-db.script
    BuildDb {
        /// Path to the HSQLDB script file
        #[arg(default_value = "nesql-db.script")]
        script: String,
        /// Output database path
        #[arg(short, long, default_value = "nesql.db")]
        output: String,
    },

    /// Merge another NESQL export into the database (e.g. a `/nesqlcrops` repository's
    /// nesql.db); rows the database already has are skipped
    MergeDb {
        /// Path to the export to merge in
        src: String,
    },

    /// Search items and fluids by name
    Search {
        query: String,
        #[arg(short, long, default_value = "20")]
        limit: usize,
        /// Also search within item tooltips
        #[arg(short, long)]
        tooltip: bool,
        /// Treat query as a case-insensitive regex (supports | for OR, .* for wildcards, etc.)
        #[arg(short, long)]
        regex: bool,
    },

    /// Show details for an item by id
    Item { id: String },

    /// Show details for a fluid by id
    Fluid { id: String },

    /// Show all recipe types (optionally filtered)
    RecipeTypes {
        #[arg(short, long, help = "Filter by name substring")]
        filter: Option<String>,
    },

    /// Show recipes that produce an item or fluid
    RecipesFor {
        id: String,
        #[arg(short, long, help = "Max results (default: all)")]
        limit: Option<usize>,
        #[arg(long, value_enum, default_value = "eu")]
        sort: SortBy,
    },

    /// Show recipes that consume an item, fluid, or ore dict
    RecipesUsing {
        id: String,
        #[arg(short, long, help = "Max results (default: all)")]
        limit: Option<usize>,
        #[arg(long, value_enum, default_value = "eu")]
        sort: SortBy,
    },

    /// Show full details for a single recipe
    Recipe { id: String },

    /// List recipes of a given type
    RecipesOfType {
        name: String,
        #[arg(short, long, default_value = "20")]
        limit: usize,
        #[arg(long, value_enum, default_value = "eu")]
        sort: SortBy,
    },

    /// Compute the minimum UU-Matter cost to produce an item by tracing recipes to replicable inputs
    UuCost {
        id: String,
        /// Number of recipe levels to expand in the output
        #[arg(short, long, default_value = "3")]
        depth: usize,
    },

    /// Compute the minimum total EU cost to produce an item by tracing the full recipe chain
    EuCost {
        id: String,
        /// Number of recipe levels to expand in the output
        #[arg(short, long, default_value = "3")]
        depth: usize,
        /// When no path is found, show why each recipe is blocked (which inputs are unsettled)
        #[arg(long)]
        why: bool,
        /// Find the path with minimum peak voltage tier (break ties with minimum EU cost)
        #[arg(long)]
        min_tier: bool,
        /// Find the minimum EU cost path using only recipes at or below this tier
        /// (e.g. IV, LuV, ZPM). Incompatible with --min-tier.
        #[arg(long, value_name = "TIER")]
        max_tier: Option<String>,
    },
}

#[derive(Clone, ValueEnum)]
enum SortBy {
    /// EU per unit of target output (ascending) — best efficiency first
    Eu,
    /// Recipe duration in ticks (ascending) — fastest first
    Time,
    /// Number of distinct inputs (ascending) — simplest first
    Inputs,
    /// fuel_value metadata (descending) — highest energy density first
    Fuel,
}

// ===== ID translation =====

/// Convert user-facing id (i:mod:name:dmg, f:..., o:name) to NESQL DB format.
fn to_db_id(id: &str) -> String {
    if id.starts_with("i:") || id.starts_with("f:") {
        id.replace(':', "~")
    } else if let Some(rest) = id.strip_prefix("o:") {
        format!("od~{rest}")
    } else {
        id.to_string()
    }
}

/// Convert NESQL DB id back to user-facing format for display.
fn from_db_id(id: &str) -> String {
    if id.starts_with("i~") || id.starts_with("f~") {
        id.replace('~', ":")
    } else if let Some(rest) = id.strip_prefix("od~") {
        format!("o:{rest}")
    } else if id.starts_with("ig~") {
        id.to_string() // synthetic multi-item group
    } else {
        id.to_string()
    }
}

// ===== Helpers =====

/// Strip Minecraft §X color/formatting codes from a string.
fn strip_mc_fmt(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut chars = s.chars();
    while let Some(c) = chars.next() {
        if c == '§' {
            chars.next(); // skip the format code character
        } else {
            out.push(c);
        }
    }
    out
}

fn fmt_eu(eu: i64) -> String {
    if eu >= 1_000_000_000 {
        format!("{:.2}G EU", eu as f64 / 1e9)
    } else if eu >= 1_000_000 {
        format!("{:.2}M EU", eu as f64 / 1e6)
    } else if eu >= 1_000 {
        format!("{:.1}k EU", eu as f64 / 1e3)
    } else {
        format!("{} EU", eu)
    }
}

fn fmt_duration(ticks: i32) -> String {
    let secs = ticks as f64 / 20.0;
    if secs >= 60.0 {
        format!("{:.1}m", secs / 60.0)
    } else {
        format!("{:.1}s", secs)
    }
}

fn is_canning_or_recycling(recipe: &Recipe) -> bool {
    if matches!(
        recipe.recipe_type_name.as_deref(),
        Some(n) if n.starts_with("Recycler ")
    ) {
        return true;
    }
    recipe
        .gt_recipe
        .as_ref()
        .map(|gt| {
            gt.metadata
                .iter()
                .any(|m| m.key == "recycle" && m.value == 1)
        })
        .unwrap_or(false)
}

fn eu_per_output(gt: &GtRecipe, output_amount: i32) -> i64 {
    gt.eu_total() / output_amount.max(1) as i64
}

fn fuel_value(recipe: &Recipe) -> Option<i64> {
    let gt = recipe.gt_recipe.as_ref()?;
    // Prefer explicit metadata entry (combustion, gas turbine, etc.)
    if let Some(v) = gt.metadata.iter().find_map(|m| {
        if m.key == "fuel_value" { Some(m.value) } else { None }
    }) {
        return Some(v);
    }
    // Rocket Engine Fuel recipes store the value in recipe_special_value (circuit_conflicts)
    // with no metadata entry. The in-game display multiplies by 3000.
    let type_name = recipe.recipe_type_name.as_deref().unwrap_or("");
    if type_name.starts_with("Rocket Engine Fuel") && gt.circuit_conflicts > 0 {
        return Some(gt.circuit_conflicts as i64 * 3000);
    }
    None
}

fn sort_key(recipe: &Recipe, target_id: &str, by: &SortBy) -> i64 {
    match by {
        SortBy::Eu => {
            let amt = recipe
                .outputs()
                .find(|io| io.goods_id.as_deref() == Some(target_id))
                .map(|io| io.amount)
                .unwrap_or(1);
            recipe
                .gt_recipe
                .as_ref()
                .map(|gt| eu_per_output(gt, amt))
                .unwrap_or(i64::MAX)
        }
        SortBy::Time => recipe
            .gt_recipe
            .as_ref()
            .map(|gt| gt.duration_ticks as i64)
            .unwrap_or(i64::MAX),
        SortBy::Inputs => recipe.inputs().count() as i64,
        SortBy::Fuel => -fuel_value(recipe).unwrap_or(0),
    }
}

fn print_gt_recipe(gt: &GtRecipe) {
    let is_fuel = gt.voltage == 0 && gt.duration_ticks == 0;
    if !is_fuel {
        println!(
            "  GT:    {} EU/t × {}A × {}t = {} ({})  [{}]",
            gt.voltage,
            gt.amperage,
            gt.duration_ticks,
            fmt_eu(gt.eu_total()),
            fmt_duration(gt.duration_ticks),
            gt.voltage_tier,
        );
    }
    if !gt.metadata.is_empty() {
        let meta: Vec<_> = gt
            .metadata
            .iter()
            .map(|m| format!("{}={}", m.key, m.value))
            .collect();
        println!("  Meta:  {}", meta.join("  "));
    }
}

/// CropsNH page text for a "Crops" recipe: tier, growth points, drop multiplier, liked biomes and
/// growth requirements (the seed, soils and drops are the recipe's inputs and outputs).
fn print_crop(repo: &Repository, recipe: &Recipe) {
    if recipe.recipe_type_name.as_deref() != Some(CROPS_RECIPE_TYPE) {
        return;
    }
    let Ok(Some(c)) = repo.crop_info(&recipe.id) else {
        return;
    };
    println!(
        "  Crop:  {} [{}]  tier {}  growth {} pts  drop ×{}",
        c.name,
        c.crop_id,
        c.tier,
        c.growth_duration,
        // stored as f32 (0.6983373): round like NEI does
        format!("{:.2}", c.drop_chance).trim_end_matches('0').trim_end_matches('.')
    );
    if !c.liked_biome_tags.is_empty() {
        println!("  Likes: {}", c.liked_biome_tags.join(", "));
    }
    for r in &c.requirements {
        println!("  Needs: {r}");
    }
}

/// Name of an input: ore dict entries by name, multi-item groups (no ore dict, e.g. a crop's
/// soils) as "one of N: a, b, c, …".
fn input_label(repo: &Repository, io: &RecipeIo) -> String {
    let db_id = io.goods_id.as_deref().unwrap_or("?");
    if io.io_type != RecipeIoType::OreDictInput {
        return repo.name_of(db_id).unwrap_or_else(|_| db_id.to_string());
    }
    if !db_id.starts_with("ig~") {
        return format!("{} (ore dict)", from_db_id(db_id));
    }
    // Distinct names: a group often holds several metas of one block (e.g. a block's variants).
    let members = repo.ore_dict_item_ids(db_id).unwrap_or_default();
    let mut names: Vec<String> = Vec::new();
    for m in &members {
        let name = repo.name_of(m).unwrap_or_else(|_| m.clone());
        if !names.contains(&name) {
            if names.len() == 3 {
                names.push("…".to_string());
                break;
            }
            names.push(name);
        }
    }
    format!("one of {}: {}", members.len(), names.join(", "))
}

/// Recipes as JSON, with a `crop` object on CropsNH "Crops" recipes.
fn recipes_json(repo: &Repository, recipes: &[Recipe]) -> Result<serde_json::Value> {
    recipes
        .iter()
        .map(|r| {
            let mut v = serde_json::to_value(r)?;
            if let Some(crop) = repo.crop_info(&r.id)? {
                v["crop"] = serde_json::to_value(crop)?;
            }
            Ok(v)
        })
        .collect::<Result<Vec<_>>>()
        .map(serde_json::Value::Array)
}

/// " (p%)" for chanced outputs: whole percents as is, others to 0.01% (crop drops go that fine).
fn fmt_prob(p: f32) -> String {
    if p >= 1.0 {
        return String::new();
    }
    let pct = p as f64 * 100.0;
    if (pct - pct.round()).abs() < 1e-6 {
        format!("  ({pct:.0}%)")
    } else {
        format!("  ({pct:.2}%)")
    }
}

fn print_recipe(repo: &Repository, recipe: &Recipe) {
    println!(
        "[{}]  type: {}",
        recipe.id,
        recipe.recipe_type_name.as_deref().unwrap_or("?")
    );
    if let Some(gt) = &recipe.gt_recipe {
        print_gt_recipe(gt);
    }
    print_crop(repo, recipe);
    println!("  Inputs:");
    for io in recipe.inputs() {
        let db_id = io.goods_id.as_deref().unwrap_or("?");
        let name = input_label(repo, io);
        println!(
            "    {:>4}×  {:<35}  [{}]",
            io.amount,
            name,
            from_db_id(db_id)
        );
    }
    println!("  Outputs:");
    for io in recipe.outputs() {
        let db_id = io.goods_id.as_deref().unwrap_or("?");
        let name = repo.name_of(db_id).unwrap_or_else(|_| db_id.to_string());
        let prob = fmt_prob(io.probability);
        println!(
            "    {:>4}×  {:<35}  [{}]{}",
            io.amount,
            name,
            from_db_id(db_id),
            prob
        );
    }
}

fn print_recipe_list(repo: &Repository, recipes: &[Recipe], target_id: &str, by: &SortBy) {
    for (i, recipe) in recipes.iter().enumerate() {
        let output_amt = recipe
            .outputs()
            .find(|io| io.goods_id.as_deref() == Some(target_id))
            .map(|io| io.amount)
            .unwrap_or(1);

        let note = recipe.gt_recipe.as_ref().map(|gt| {
            if let Some(fv) = fuel_value(recipe) {
                format!("  →  fuel_value={fv}")
            } else {
                format!(
                    "  →  {}  ({} EU/output)",
                    fmt_eu(gt.eu_total()),
                    fmt_eu(eu_per_output(gt, output_amt))
                )
            }
        });

        println!(
            "\n#{:<3} [{}]  {}{}",
            i + 1,
            recipe.id,
            recipe.recipe_type_name.as_deref().unwrap_or("?"),
            note.as_deref().unwrap_or(""),
        );
        if let Some(gt) = &recipe.gt_recipe {
            print_gt_recipe(gt);
        }
        print_crop(repo, recipe);
        println!("  Inputs:");
        for io in recipe.inputs() {
            println!("    {:>4}×  {}", io.amount, input_label(repo, io));
        }
        println!("  Outputs:");
        for io in recipe.outputs() {
            let db_id = io.goods_id.as_deref().unwrap_or("?");
            let name = repo.name_of(db_id).unwrap_or_else(|_| db_id.to_string());
            let prob = fmt_prob(io.probability);
            println!("    {:>4}×  {}{}", io.amount, name, prob);
        }
        let _ = by;
    }
}

// ===== UU-Matter cost solver =====

/// The DB-format fluid ID for UU-Matter; base cost = 1.0 UU per mB.
const UU_MATTER_ID: &str = "f~IC2~ic2uumatter";

#[derive(Clone, Serialize)]
pub struct UuResult {
    pub uu_per_unit: f64,
    pub path: UuPath,
}

#[derive(Clone, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum UuPath {
    /// This node IS UU-Matter (base case).
    Base,
    /// Cheapest route is via a recipe (including Replicator recipes).
    Recipe {
        recipe_id: String,
        recipe_type: String,
        /// Expected output of the target good per recipe run (amount × probability).
        output_amount: f64,
        inputs: Vec<UuInput>,
    },
}

#[derive(Clone, Serialize)]
pub struct UuInput {
    pub name: String,
    /// Resolved goods_id — for ore dict inputs, the chosen cheapest member.
    pub goods_id: String,
    pub amount: f64,
    pub result: UuResult,
}

/// Recursively find the minimum UU-Matter cost to produce 1 unit of `goods_id`.
///
/// Uses path-based cycle detection: items already being computed in the current
/// call chain are skipped, preventing both infinite loops and the negative-cycle
/// trap (where a cyclic conversion could drive costs to 0). Successes are
/// memoized; failures are tracked in `impossible`. Because a cycle-blocked
/// failure may be a false negative (the item IS reachable via a non-cyclic
/// path), the caller should run multiple passes (clearing `impossible` but
/// keeping successful memos) until the result converges.
fn compute_uu_cost(
    goods_id: &str,
    path: &mut HashSet<String>,
    memo: &mut HashMap<String, UuResult>,
    impossible: &mut HashSet<String>,
    repo: &Repository,
) -> Option<UuResult> {
    if goods_id == UU_MATTER_ID {
        return Some(UuResult {
            uu_per_unit: 1.0,
            path: UuPath::Base,
        });
    }
    if let Some(cached) = memo.get(goods_id) {
        return Some(cached.clone());
    }
    if impossible.contains(goods_id) {
        return None;
    }
    if path.contains(goods_id) {
        return None; // cycle
    }
    path.insert(goods_id.to_string());

    let recipes = repo.recipes_producing(goods_id).unwrap_or_default();
    let mut best: Option<UuResult> = None;

    'recipe: for recipe in &recipes {
        if is_canning_or_recycling(recipe) {
            continue;
        }
        let output_io = recipe
            .outputs()
            .find(|io| io.goods_id.as_deref() == Some(goods_id));
        let Some(output_io) = output_io else { continue };
        if output_io.probability <= 0.0 {
            continue;
        }
        if !recipe.inputs().any(|io| io.amount > 0) {
            continue;
        }
        let output_amount = output_io.amount as f64 * output_io.probability as f64;

        let mut total_uu = 0.0;
        let mut inputs: Vec<UuInput> = Vec::new();

        for input_io in recipe.inputs() {
            let Some(input_id) = &input_io.goods_id else {
                continue;
            };
            let amount = input_io.amount as f64;
            if amount == 0.0 {
                continue;
            }

            let (resolved_id, sub_result) = if input_io.io_type == RecipeIoType::OreDictInput {
                let members = repo.ore_dict_item_ids(input_id).unwrap_or_default();

                // Check already-memoized members first (O(1)), then explore others.
                let mut best_member: Option<(String, UuResult)> = None;
                for mid in &members {
                    if let Some(r) = memo.get(mid.as_str()) {
                        let r = r.clone();
                        if best_member
                            .as_ref()
                            .map_or(true, |(_, br)| r.uu_per_unit < br.uu_per_unit)
                        {
                            best_member = Some((mid.clone(), r));
                        }
                    }
                }
                for mid in &members {
                    if memo.contains_key(mid.as_str()) || impossible.contains(mid.as_str()) {
                        continue;
                    }
                    if let Some(r) = compute_uu_cost(mid, path, memo, impossible, repo) {
                        if best_member
                            .as_ref()
                            .map_or(true, |(_, br)| r.uu_per_unit < br.uu_per_unit)
                        {
                            best_member = Some((mid.clone(), r));
                        }
                    }
                }
                match best_member {
                    None => continue 'recipe,
                    Some(bm) => bm,
                }
            } else {
                match compute_uu_cost(input_id, path, memo, impossible, repo) {
                    None => continue 'recipe,
                    Some(r) => (input_id.clone(), r),
                }
            };

            total_uu += amount * sub_result.uu_per_unit;
            let name = repo
                .name_of(&resolved_id)
                .unwrap_or_else(|_| resolved_id.clone());
            inputs.push(UuInput {
                name,
                goods_id: resolved_id,
                amount,
                result: sub_result,
            });
        }

        let uu_per_unit = total_uu / output_amount;
        if best.as_ref().map_or(true, |b| uu_per_unit < b.uu_per_unit) {
            best = Some(UuResult {
                uu_per_unit,
                path: UuPath::Recipe {
                    recipe_id: recipe.id.clone(),
                    recipe_type: recipe.recipe_type_name.clone().unwrap_or_default(),
                    output_amount,
                    inputs,
                },
            });
        }
    }

    path.remove(goods_id);

    if let Some(ref r) = best {
        memo.insert(goods_id.to_string(), r.clone());
    } else {
        impossible.insert(goods_id.to_string());
    }
    best
}

// ===== EU cost solver =====

#[derive(Clone, Serialize)]
pub struct EuResult {
    pub eu_per_unit: f64,
    pub path: EuPath,
}

#[derive(Clone, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum EuPath {
    /// Item requires no GT recipe — obtained freely (mined, harvested, crafting table, etc.).
    Free,
    /// Cheapest route is via a GT recipe chain.
    Recipe {
        recipe_id: String,
        recipe_type: String,
        /// GT voltage tier string (e.g. "ULV", "EV"). Empty for non-GT recipes.
        voltage_tier: String,
        /// EU consumed by this recipe step alone (before amortising over output).
        recipe_eu: i64,
        output_amount: f64,
        inputs: Vec<EuInput>,
    },
}

#[derive(Clone, Serialize)]
pub struct EuInput {
    pub name: String,
    pub goods_id: String,
    pub amount: f64,
    pub result: EuResult,
}

// f64 total-order wrapper for BinaryHeap (NaN treated as Equal to anything).
#[derive(PartialEq)]
struct OrdF64(f64);
impl Eq for OrdF64 {}
impl PartialOrd for OrdF64 {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}
impl Ord for OrdF64 {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.0
            .partial_cmp(&other.0)
            .unwrap_or(std::cmp::Ordering::Equal)
    }
}

/// Result of the Dijkstra pass over the EU-cost graph.
#[derive(Serialize, Deserialize)]
struct DijkState {
    /// goods_ni → (settled EU cost, Option<recipe_ni that produced it>).
    /// recipe_ni = None means the goods is freely obtainable (no valid producing recipe).
    settled: HashMap<NodeIndex, (f64, Option<NodeIndex>)>,
    /// (recipe_ni, slot_idx) → goods_ni selected for that input slot.
    slot_chosen: HashMap<(NodeIndex, usize), NodeIndex>,
}

// ===== Infinite source seeding =====

/// EU cost per unit for bee combs produced by the GT Industrial Apiary.
///
/// Base consumption: ~37 EU/t × 100 ticks (standard bee tick = 5 s) = 3,700 EU per
/// bee tick. Conservative estimate of 1 comb per bee tick → 3,700 EU/comb.
const BEE_COMB_EU: f64 = 3_700.0;

/// EU cost per unit for EIG (Extreme Industrial Greenhouse) crop outputs.
///
/// Minimum config: EV tier (2048 EU/t) × 100 ticks (5 s) = 204,800 EU per operation.
/// At EV, 1 slot holds 64 seeds; 1 crop drop per seed → 64 drops/op.
/// 204,800 / 64 = 3,200 EU per crop unit.
const EIG_CROP_EU: f64 = 3_200.0;

/// EU cost per unit for EEC (Extreme Entity Crusher) mob drop outputs.
///
/// Base energy: 1,920 EU/t × 20 ticks (minimum recipe time) = 38,400 EU per operation.
/// Treating as ~1 item drop per operation → 38,400 EU per drop.
#[allow(dead_code)]
const EEC_DROP_EU: f64 = 38_400.0;

/// Returns the EU seed cost for a goods node if it is obtainable from a known
/// infinite resource source, or `None` if it cannot be sourced this way.
///
/// The returned cost is the amortised EU per unit from the source machine.
/// Goods seeded here may still have recipe routes; Dijkstra picks the minimum.
fn seed_cost_for(goods_id: &str, name: Option<&str>) -> Option<f64> {
    // 0-EU infinite sources ─────────────────────────────────────────────────
    // water, air, netherair are handled by add_infinite_source_recipes (fake recipe nodes)
    // so they show a named source rather than "[from infinite source]".
    const ZERO_EU: &[&str] = &[
        "i~minecraft~end_stone~0",  // Ender Tree
        "i~minecraft~obsidian~0",   // Ender Tree
        "i~minecraft~netherrack~0", // Nether Tree
        "i~minecraft~quartz~0",     // Nether Tree (nether quartz item)
        "i~minecraft~soul_sand~0",  // Nether Tree
    ];
    if ZERO_EU.contains(&goods_id) {
        return Some(0.0);
    }

    let name = name?.trim();

    // EIG crops (Extreme Industrial Greenhouse, non-IC2) ────────────────────
    // Magical Crops essences/shards and similar crop outputs.
    if name.ends_with(" Essence") || name.ends_with(" Shard") {
        if goods_id.contains("~magicalcrops~")
            || goods_id.contains("~extratic~")
            || goods_id.contains("~MagicalCrops~")
            || goods_id.contains("~ExtraTiC~")
        {
            return Some(EIG_CROP_EU);
        }
    }

    // EEC drops (Extreme Entity Crusher) ────────────────────────────────────
    // Items produced exclusively by mob spawner drops with no recipe route.
    // Identified by being from mob-drop-only sources. We match on mod + known
    // item prefixes rather than trying to enumerate every mob drop.
    // Currently left empty — most EEC drops have alternative recipe routes,
    // so they are naturally reachable from the seeded free sources above.

    None
}

/// Populate `eu_graph.seed_costs` for all goods nodes that are obtainable
/// from an infinite resource source.  Must be called before `run_eu_dijkstra`.
fn populate_seed_costs(eu_graph: &mut EuGraph, repo: &Repository) {
    let mut seeds: HashMap<NodeIndex, f64> = HashMap::new();
    for (goods_id, &ni) in &eu_graph.goods_idx {
        let name = repo.name_of(goods_id).ok();
        if let Some(cost) = seed_cost_for(goods_id, name.as_deref()) {
            seeds.insert(ni, cost);
        }
    }
    eu_graph.seed_costs = seeds;
}

/// Seed all ore vein items into eu_graph.seed_costs (cost 0.0) and populate
/// eu_graph.mining_tiers for space-planet ores.
///
/// Overworld/Nether/End/Twilight ores are seeded at tier 0 (accessible with surface mining).
/// Off-world ores are seeded at the voltage tier of the lowest rocket that reaches them
/// (from ore_vein_dimensions).
/// run_min_tier_dijkstra then uses mining_tiers to assign the correct minimum tier.
fn populate_mining_tiers(eu_graph: &mut EuGraph, repo: &Repository) {
    // Seed ALL ore vein items as free sources (cost 0.0).
    match repo.all_ore_vein_items() {
        Ok(items) => {
            for item_id in items {
                if let Some(&ni) = eu_graph.goods_idx.get(&item_id) {
                    eu_graph.seed_costs.entry(ni).or_insert(0.0);
                }
            }
        }
        Err(e) => eprintln!("Warning: could not load ore vein items: {e}"),
    }
    // For space-planet ores, record the minimum tier required to mine them.
    match repo.ore_mining_tiers() {
        Ok(tiers) => {
            for (item_id, tier) in tiers {
                if let Some(&ni) = eu_graph.goods_idx.get(&item_id) {
                    // Only raise the tier; don't lower it if already set higher.
                    let e = eu_graph.mining_tiers.entry(ni).or_insert(tier);
                    if tier > *e {
                        *e = tier;
                    }
                }
            }
        }
        Err(e) => eprintln!("Warning: could not load ore mining tiers: {e}"),
    }
}

/// Inject synthetic zero-input recipe nodes for infinite sources that have no
/// DB recipe entry.  These fire immediately in the Dijkstra's zero-slot pre-pass
/// and produce their outputs at 0 EU, displaying the machine name in the tree.
fn add_infinite_source_recipes(eu_graph: &mut EuGraph) {
    let sources: &[(&str, &str, &str)] = &[
        // (recipe_type_label, synthetic_recipe_id, output_goods_id)
        (
            "Reservoir Hatch",
            "syn:reservoir_hatch",
            "f~minecraft~water",
        ),
        ("Air Intake Hatch", "syn:air_intake_air", "f~gregtech~air"),
        (
            "Air Intake Hatch",
            "syn:air_intake_netherair",
            "f~gregtech~netherair",
        ),
    ];
    for &(label, syn_id, output_id) in sources {
        // Ensure the goods node exists.
        if !eu_graph.goods_idx.contains_key(output_id) {
            let ni = eu_graph
                .g
                .add_node(EuGraphNode::Goods(output_id.to_string()));
            eu_graph.goods_idx.insert(output_id.to_string(), ni);
        }
        let output_ni = eu_graph.goods_idx[output_id];

        // Add a synthetic Recipe node with no inputs (num_slots = 0).
        let recipe_ni = eu_graph.g.add_node(EuGraphNode::Recipe {
            id: syn_id.to_string(),
            output_goods_id: output_id.to_string(),
            eu: 0,
            output_amount: 1.0,
            num_slots: 0,
            recipe_type: label.to_string(),
            voltage_tier: String::new(),
            metadata_tier: 0,
        });
        eu_graph.recipe_idx.insert(syn_id.to_string(), recipe_ni);
        eu_graph
            .g
            .add_edge(recipe_ni, output_ni, EuGraphEdge::Output);
    }
}

/// Inject synthetic zero-input recipe nodes for every EEC mob drop, one node
/// per (mob_info, item) pair.  EU cost is amortised over the expected output:
///   EU/unit = EEC_DROP_EU / (probability × stack_size)
/// Dijkstra will automatically pick the cheapest mob for each item.
fn add_eec_recipes(eu_graph: &mut EuGraph, repo: &Repository) {
    let drops = match repo.mob_drop_entries() {
        Ok(d) => d,
        Err(_) => return,
    };
    for (mob_info_id, item_id, expected_output) in drops {
        // Ensure the goods node exists.
        if !eu_graph.goods_idx.contains_key(&item_id) {
            let ni = eu_graph.g.add_node(EuGraphNode::Goods(item_id.clone()));
            eu_graph.goods_idx.insert(item_id.clone(), ni);
        }
        let output_ni = eu_graph.goods_idx[&item_id];

        let syn_id = format!("syn:eec:{}:{}", mob_info_id, item_id);
        let recipe_ni = eu_graph.g.add_node(EuGraphNode::Recipe {
            id: syn_id.clone(),
            output_goods_id: item_id.clone(),
            eu: EEC_DROP_EU as i64,
            output_amount: expected_output,
            num_slots: 0,
            recipe_type: "Extreme Entity Crusher".to_string(),
            voltage_tier: String::new(),
            metadata_tier: 0,
        });
        eu_graph.recipe_idx.insert(syn_id, recipe_ni);
        eu_graph
            .g
            .add_edge(recipe_ni, output_ni, EuGraphEdge::Output);
    }
}

/// Modified Dijkstra over the bipartite EU-cost graph.
///
/// Goods nodes listed in `eu_graph.seed_costs` are seeded at their configured
/// EU cost (0 for free infinite sources, non-zero for machine-powered sources).
/// Goods not in `seed_costs` are only reachable via recipe chains from seeded goods.
/// A recipe node becomes "ready" when all its input slots are settled; its cost is
/// then (recipe_eu + sum(input_amount × input_cost)) / output_amount.
/// Since all EU values are ≥ 0, standard Dijkstra correctness applies.
/// For ore-dict slots, the first (cheapest) member to be settled wins.
fn run_eu_dijkstra(eu_graph: &EuGraph) -> DijkState {
    let g = &eu_graph.g;
    let mut settled: HashMap<NodeIndex, (f64, Option<NodeIndex>)> = HashMap::new();
    let mut slot_chosen: HashMap<(NodeIndex, usize), NodeIndex> = HashMap::new();
    let mut remaining_slots: HashMap<NodeIndex, usize> = HashMap::new();
    let mut recipe_input_eu: HashMap<NodeIndex, f64> = HashMap::new();

    // Min-heap: (Reverse(cost), goods_ni, via_recipe_ni).
    let mut pq: BinaryHeap<(Reverse<OrdF64>, NodeIndex, Option<NodeIndex>)> = BinaryHeap::new();

    // Initialise recipe slot counts.
    for ni in g.node_indices() {
        if let EuGraphNode::Recipe { num_slots, .. } = &g[ni] {
            remaining_slots.insert(ni, *num_slots);
        }
    }

    // Seed goods nodes from known infinite sources at their configured EU costs.
    // Goods not listed in seed_costs are treated as unreachable (infinite cost).
    for (&ni, &cost) in &eu_graph.seed_costs {
        pq.push((Reverse(OrdF64(cost)), ni, None));
    }

    // Fire zero-input recipe nodes immediately (Planetary Gas Siphon, Bee Products, …).
    // These have no Input edges so they are never triggered by goods settlement;
    // their output goods are pushed to the PQ at cost = recipe_eu / output_amount.
    for ni in g.node_indices() {
        if let EuGraphNode::Recipe {
            eu, output_amount, ..
        } = &g[ni]
        {
            if remaining_slots.get(&ni).copied().unwrap_or(0) == 0 {
                let recipe_cost = *eu as f64 / *output_amount;
                for out_edge in g.edges_directed(ni, Direction::Outgoing) {
                    if matches!(out_edge.weight(), EuGraphEdge::Output) {
                        pq.push((Reverse(OrdF64(recipe_cost)), out_edge.target(), Some(ni)));
                    }
                }
            }
        }
    }

    while let Some((Reverse(OrdF64(cost)), goods_ni, via_recipe)) = pq.pop() {
        if settled.contains_key(&goods_ni) {
            continue; // stale entry
        }
        settled.insert(goods_ni, (cost, via_recipe));

        // Propagate settlement to every recipe that uses this goods as an input.
        for edge in g.edges_directed(goods_ni, Direction::Outgoing) {
            let recipe_ni = edge.target();
            let EuGraphEdge::Input { slot, amount } = *edge.weight() else {
                continue;
            };

            // For ore-dict slots, only the first (cheapest) member settles the slot.
            if slot_chosen.contains_key(&(recipe_ni, slot)) {
                continue;
            }
            slot_chosen.insert((recipe_ni, slot), goods_ni);
            *recipe_input_eu.entry(recipe_ni).or_insert(0.0) += amount * cost;

            let rem = remaining_slots.entry(recipe_ni).or_insert(0);
            if *rem == 0 {
                continue; // shouldn't happen
            }
            *rem -= 1;

            if *rem == 0 {
                // All slots settled → compute recipe cost and push output goods.
                let EuGraphNode::Recipe {
                    eu, output_amount, ..
                } = &g[recipe_ni]
                else {
                    continue;
                };
                let recipe_cost = (*eu as f64 + recipe_input_eu[&recipe_ni]) / *output_amount;
                for out_edge in g.edges_directed(recipe_ni, Direction::Outgoing) {
                    if matches!(out_edge.weight(), EuGraphEdge::Output) {
                        let output_ni = out_edge.target();
                        if !settled.contains_key(&output_ni) {
                            pq.push((Reverse(OrdF64(recipe_cost)), output_ni, Some(recipe_ni)));
                        }
                    }
                }
            }
        }
    }

    DijkState {
        settled,
        slot_chosen,
    }
}

/// Map a voltage tier string to a rank used for ordering.
/// Empty string (free/synthetic sources) maps to 0.
/// Dijkstra variant that minimises (peak_voltage_tier_rank, eu_cost) lexicographically.
///
/// The "cost" of a goods node is (max tier of any recipe in its production chain, total EU).
/// For a recipe at tier T consuming inputs with costs (t_i, e_i):
///   output_tier = max(T, max(t_i))
///   output_eu   = (recipe_eu + Σ amount_i × e_i) / output_amount
///
/// Returns a DijkState whose `settled` map stores the EU costs of the min-tier paths,
/// allowing all existing build_eu_result / print_eu_tree / peak_voltage_tier code to
/// be reused without modification.
fn run_min_tier_dijkstra(eu_graph: &EuGraph) -> DijkState {
    let g = &eu_graph.g;
    let mut settled: HashMap<NodeIndex, (f64, Option<NodeIndex>)> = HashMap::new();
    let mut slot_chosen: HashMap<(NodeIndex, usize), NodeIndex> = HashMap::new();
    let mut remaining_slots: HashMap<NodeIndex, usize> = HashMap::new();
    let mut recipe_input_eu: HashMap<NodeIndex, f64> = HashMap::new();
    let mut recipe_input_tier: HashMap<NodeIndex, u8> = HashMap::new();

    // Min-heap: (Reverse((tier_rank, eu_cost)), goods_ni, via_recipe_ni).
    let mut pq: BinaryHeap<(Reverse<(u8, OrdF64)>, NodeIndex, Option<NodeIndex>)> =
        BinaryHeap::new();

    for ni in g.node_indices() {
        if let EuGraphNode::Recipe { num_slots, .. } = &g[ni] {
            remaining_slots.insert(ni, *num_slots);
        }
    }

    // Seed infinite sources at tier 0 (or planet mining tier for space ores).
    for (&ni, &cost) in &eu_graph.seed_costs {
        let tier = eu_graph.mining_tiers.get(&ni).copied().unwrap_or(0u8);
        pq.push((Reverse((tier, OrdF64(cost))), ni, None));
    }

    // Fire zero-input recipes immediately.
    for ni in g.node_indices() {
        if let EuGraphNode::Recipe {
            eu, output_amount, voltage_tier, metadata_tier, ..
        } = &g[ni]
        {
            if remaining_slots.get(&ni).copied().unwrap_or(0) == 0 {
                let recipe_cost_eu = *eu as f64 / *output_amount;
                let recipe_tier = tier_rank_u8(voltage_tier).max(*metadata_tier);
                for out_edge in g.edges_directed(ni, Direction::Outgoing) {
                    if matches!(out_edge.weight(), EuGraphEdge::Output) {
                        pq.push((
                            Reverse((recipe_tier, OrdF64(recipe_cost_eu))),
                            out_edge.target(),
                            Some(ni),
                        ));
                    }
                }
            }
        }
    }

    while let Some((Reverse((tier, OrdF64(cost))), goods_ni, via_recipe)) = pq.pop() {
        if settled.contains_key(&goods_ni) {
            continue;
        }
        settled.insert(goods_ni, (cost, via_recipe));

        for edge in g.edges_directed(goods_ni, Direction::Outgoing) {
            let recipe_ni = edge.target();
            let EuGraphEdge::Input { slot, amount } = *edge.weight() else {
                continue;
            };

            if slot_chosen.contains_key(&(recipe_ni, slot)) {
                continue;
            }
            slot_chosen.insert((recipe_ni, slot), goods_ni);
            *recipe_input_eu.entry(recipe_ni).or_insert(0.0) += amount * cost;
            // Track the max tier seen across all settled inputs for this recipe.
            let max_t = recipe_input_tier.entry(recipe_ni).or_insert(0);
            *max_t = (*max_t).max(tier);

            let rem = remaining_slots.entry(recipe_ni).or_insert(0);
            if *rem == 0 {
                continue;
            }
            *rem -= 1;

            if *rem == 0 {
                let EuGraphNode::Recipe {
                    eu, output_amount, voltage_tier, metadata_tier, ..
                } = &g[recipe_ni]
                else {
                    continue;
                };
                let recipe_tier = tier_rank_u8(voltage_tier).max(*metadata_tier);
                let output_tier = recipe_tier.max(recipe_input_tier[&recipe_ni]);
                let output_eu =
                    (*eu as f64 + recipe_input_eu[&recipe_ni]) / *output_amount;
                for out_edge in g.edges_directed(recipe_ni, Direction::Outgoing) {
                    if matches!(out_edge.weight(), EuGraphEdge::Output) {
                        let output_ni = out_edge.target();
                        if !settled.contains_key(&output_ni) {
                            pq.push((
                                Reverse((output_tier, OrdF64(output_eu))),
                                output_ni,
                                Some(recipe_ni),
                            ));
                        }
                    }
                }
            }
        }
    }

    DijkState {
        settled,
        slot_chosen,
    }
}

/// Dijkstra variant that finds minimum EU cost using only recipes at or below `max_tier`.
///
/// Recipes with tier_rank_u8(voltage_tier) > max_tier are simply excluded: they are never
/// added to `remaining_slots`, so their input edges are ignored and they never fire.
/// Everything else is identical to `run_eu_dijkstra`.
fn run_max_tier_dijkstra(eu_graph: &EuGraph, max_tier: u8) -> DijkState {
    let g = &eu_graph.g;
    let mut settled: HashMap<NodeIndex, (f64, Option<NodeIndex>)> = HashMap::new();
    let mut slot_chosen: HashMap<(NodeIndex, usize), NodeIndex> = HashMap::new();
    let mut remaining_slots: HashMap<NodeIndex, usize> = HashMap::new();
    let mut recipe_input_eu: HashMap<NodeIndex, f64> = HashMap::new();

    let mut pq: BinaryHeap<(Reverse<OrdF64>, NodeIndex, Option<NodeIndex>)> = BinaryHeap::new();

    // Initialise slot counts only for recipes within the tier budget.
    // A recipe's effective tier is max(voltage_tier, metadata_tier) — both must be ≤ max_tier.
    for ni in g.node_indices() {
        if let EuGraphNode::Recipe { num_slots, voltage_tier, metadata_tier, .. } = &g[ni] {
            if tier_rank_u8(voltage_tier).max(*metadata_tier) <= max_tier {
                remaining_slots.insert(ni, *num_slots);
            }
        }
    }

    for (&ni, &cost) in &eu_graph.seed_costs {
        pq.push((Reverse(OrdF64(cost)), ni, None));
    }

    // Fire zero-input recipes within tier budget immediately.
    for ni in g.node_indices() {
        if let EuGraphNode::Recipe { eu, output_amount, .. } = &g[ni] {
            if remaining_slots.get(&ni).copied().unwrap_or(1) == 0 {
                let recipe_cost = *eu as f64 / *output_amount;
                for out_edge in g.edges_directed(ni, Direction::Outgoing) {
                    if matches!(out_edge.weight(), EuGraphEdge::Output) {
                        pq.push((Reverse(OrdF64(recipe_cost)), out_edge.target(), Some(ni)));
                    }
                }
            }
        }
    }

    while let Some((Reverse(OrdF64(cost)), goods_ni, via_recipe)) = pq.pop() {
        if settled.contains_key(&goods_ni) {
            continue;
        }
        settled.insert(goods_ni, (cost, via_recipe));

        for edge in g.edges_directed(goods_ni, Direction::Outgoing) {
            let recipe_ni = edge.target();
            let EuGraphEdge::Input { slot, amount } = *edge.weight() else {
                continue;
            };
            // Skip recipes that were excluded (above max_tier).
            if !remaining_slots.contains_key(&recipe_ni) {
                continue;
            }
            if slot_chosen.contains_key(&(recipe_ni, slot)) {
                continue;
            }
            slot_chosen.insert((recipe_ni, slot), goods_ni);
            *recipe_input_eu.entry(recipe_ni).or_insert(0.0) += amount * cost;

            let rem = remaining_slots.entry(recipe_ni).or_insert(0);
            if *rem == 0 {
                continue;
            }
            *rem -= 1;

            if *rem == 0 {
                let EuGraphNode::Recipe { eu, output_amount, .. } = &g[recipe_ni] else {
                    continue;
                };
                let recipe_cost = (*eu as f64 + recipe_input_eu[&recipe_ni]) / *output_amount;
                for out_edge in g.edges_directed(recipe_ni, Direction::Outgoing) {
                    if matches!(out_edge.weight(), EuGraphEdge::Output) {
                        let output_ni = out_edge.target();
                        if !settled.contains_key(&output_ni) {
                            pq.push((Reverse(OrdF64(recipe_cost)), output_ni, Some(recipe_ni)));
                        }
                    }
                }
            }
        }
    }

    DijkState {
        settled,
        slot_chosen,
    }
}

/// Diagnose why a goods node has no EU cost path.
/// Prints which recipe inputs are unsettled and recurses into them.
fn diagnose_no_path(
    goods_id: &str,
    eu_graph: &EuGraph,
    dijk: &DijkState,
    repo: &Repository,
    depth: usize,
    prefix: &str,
) {
    let name = repo.name_of(goods_id).unwrap_or_else(|_| goods_id.to_string());

    let Some(&goods_ni) = eu_graph.goods_idx.get(goods_id) else {
        eprintln!("{prefix}  {name} [{goods_id_fmt}]: NOT IN GRAPH (no production recipe in DB)",
            goods_id_fmt = from_db_id(goods_id));
        return;
    };

    if dijk.settled.contains_key(&goods_ni) {
        eprintln!("{prefix}  {name}: SETTLED (should not be here)");
        return;
    }

    // Find all recipe nodes that produce this goods node.
    let producing_recipes: Vec<NodeIndex> = eu_graph
        .g
        .edges_directed(goods_ni, Direction::Incoming)
        .filter(|e| matches!(e.weight(), EuGraphEdge::Output))
        .map(|e| e.source())
        .collect();

    if producing_recipes.is_empty() {
        eprintln!("{prefix}  {name} [{goods_id_fmt}]: in graph but no recipe nodes produce it",
            goods_id_fmt = from_db_id(goods_id));
        return;
    }

    for recipe_ni in producing_recipes {
        let EuGraphNode::Recipe { id, recipe_type, num_slots, .. } = &eu_graph.g[recipe_ni] else {
            continue;
        };
        eprintln!("{prefix}  Recipe [{id_short}] ({recipe_type}) — {num_slots} input slots:",
            id_short = &id[..id.len().min(12)]);

        // Find which slots are still missing.
        let mut missing_slots: Vec<usize> = (0..*num_slots)
            .filter(|slot| !dijk.slot_chosen.contains_key(&(recipe_ni, *slot)))
            .collect();
        missing_slots.sort_unstable();

        if missing_slots.is_empty() {
            eprintln!("{prefix}    (all slots settled — recipe should have fired; possible bug)");
            continue;
        }

        for slot in missing_slots {
            // Find goods nodes feeding this slot.
            let candidates: Vec<NodeIndex> = eu_graph
                .g
                .edges_directed(recipe_ni, Direction::Incoming)
                .filter(|e| matches!(e.weight(), EuGraphEdge::Input { slot: s, .. } if *s == slot))
                .map(|e| e.source())
                .collect();

            if candidates.is_empty() {
                eprintln!("{prefix}    slot {slot}: no candidates in graph");
                continue;
            }

            let settled_count = candidates.iter().filter(|&&ni| dijk.settled.contains_key(&ni)).count();
            if settled_count > 0 {
                eprintln!("{prefix}    slot {slot}: {settled_count}/{} candidates settled but slot not chosen (ore-dict conflict?)",
                    candidates.len());
                continue;
            }

            eprintln!("{prefix}    slot {slot}: unsettled ({} candidate(s)):", candidates.len());
            if depth > 0 {
                for cand_ni in &candidates {
                    let EuGraphNode::Goods(cand_id) = &eu_graph.g[*cand_ni] else { continue };
                    diagnose_no_path(cand_id, eu_graph, dijk, repo, depth - 1,
                        &format!("{prefix}      "));
                }
            } else {
                for cand_ni in &candidates {
                    let EuGraphNode::Goods(cand_id) = &eu_graph.g[*cand_ni] else { continue };
                    let cand_name = repo.name_of(cand_id).unwrap_or_else(|_| cand_id.clone());
                    eprintln!("{prefix}      {cand_name} [{cand_id_fmt}]",
                        cand_id_fmt = from_db_id(cand_id));
                }
            }
        }
    }
}

/// Walk the full settled subgraph reachable from goods_id and return the
/// highest GT voltage tier found anywhere in the chain.
/// Uses a visited set to avoid re-traversing shared sub-trees — O(nodes) not O(paths).
fn peak_voltage_tier(
    goods_id: &str,
    eu_graph: &EuGraph,
    dijk: &DijkState,
    visited: &mut HashSet<NodeIndex>,
) -> Option<String> {
    const TIER_ORDER: &[&str] = &[
        "ULV", "LV", "MV", "HV", "EV", "IV", "LuV", "ZPM", "UV",
        "UHV", "UEV", "UIV", "UMV", "UXV", "MAX",
    ];
    fn tier_rank(t: &str) -> usize {
        TIER_ORDER.iter().position(|&s| s == t).unwrap_or(0)
    }

    let Some(&goods_ni) = eu_graph.goods_idx.get(goods_id) else {
        return None;
    };
    if !visited.insert(goods_ni) {
        return None; // already processed
    }
    let Some(&(_, via_recipe)) = dijk.settled.get(&goods_ni) else {
        return None;
    };
    let Some(recipe_ni) = via_recipe else {
        return None; // free / infinite source
    };
    if !visited.insert(recipe_ni) {
        return None;
    }

    let EuGraphNode::Recipe { voltage_tier, metadata_tier, num_slots, .. } = &eu_graph.g[recipe_ni] else {
        return None;
    };
    // Start with the higher of the recipe's voltage tier and any metadata-gated tier.
    let effective_tier = if tier_rank_u8(voltage_tier) >= *metadata_tier {
        voltage_tier.clone()
    } else {
        const TIER_NAMES: &[&str] = &[
            "ULV", "LV", "MV", "HV", "EV", "IV", "LuV", "ZPM", "UV",
            "UHV", "UEV", "UIV", "UMV", "UXV", "MAX",
        ];
        TIER_NAMES.get(*metadata_tier as usize).unwrap_or(&"ULV").to_string()
    };
    let mut best = if !effective_tier.is_empty() {
        Some(effective_tier)
    } else {
        None
    };
    let num_slots = *num_slots;

    for slot in 0..num_slots {
        let Some(&chosen_ni) = dijk.slot_chosen.get(&(recipe_ni, slot)) else {
            continue;
        };
        let EuGraphNode::Goods(chosen_id) = &eu_graph.g[chosen_ni] else {
            continue;
        };
        let chosen_id = chosen_id.clone();
        if let Some(sub) = peak_voltage_tier(&chosen_id, eu_graph, dijk, visited) {
            best = Some(match best {
                None => sub,
                Some(ref b) if tier_rank(&sub) > tier_rank(b) => sub,
                Some(b) => b,
            });
        }
    }
    best
}

/// Reconstruct the EuResult display tree from Dijkstra output.
///
/// `max_depth` limits how many recipe levels of sub-inputs are expanded.
/// At max_depth=0 the result contains cost only (no inputs).
/// Returns None only if `goods_id` was not reachable (not in eu_graph or not settled).
fn build_eu_result(
    goods_id: &str,
    dijk: &DijkState,
    eu_graph: &EuGraph,
    repo: &Repository,
    max_depth: usize,
) -> Option<EuResult> {
    let &goods_ni = eu_graph.goods_idx.get(goods_id)?;
    let &(cost, via_recipe) = dijk.settled.get(&goods_ni)?;

    let Some(recipe_ni) = via_recipe else {
        return Some(EuResult {
            eu_per_unit: cost,
            path: EuPath::Free,
        });
    };

    let (recipe_id, recipe_type, voltage_tier, recipe_eu, output_amount, num_slots) =
        if let EuGraphNode::Recipe {
            id,
            recipe_type,
            voltage_tier,
            eu,
            output_amount,
            num_slots,
            ..
        } = &eu_graph.g[recipe_ni]
        {
            (
                id.clone(),
                recipe_type.clone(),
                voltage_tier.clone(),
                *eu,
                *output_amount,
                *num_slots,
            )
        } else {
            return None;
        };

    // At depth 0, return the cost with an empty input list (leaf node in display).
    if max_depth == 0 {
        return Some(EuResult {
            eu_per_unit: cost,
            path: EuPath::Recipe {
                recipe_id,
                recipe_type,
                voltage_tier,
                recipe_eu,
                output_amount,
                inputs: Vec::new(),
            },
        });
    }

    let mut inputs = Vec::new();
    for slot in 0..num_slots {
        let Some(&chosen_ni) = dijk.slot_chosen.get(&(recipe_ni, slot)) else {
            continue;
        };
        let EuGraphNode::Goods(chosen_id) = &eu_graph.g[chosen_ni] else {
            continue;
        };
        let amount = eu_graph
            .slot_amounts
            .get(&(recipe_ni, slot))
            .copied()
            .unwrap_or(0.0);
        let sub = build_eu_result(chosen_id, dijk, eu_graph, repo, max_depth - 1)?;
        let name = repo
            .name_of(chosen_id)
            .unwrap_or_else(|_| chosen_id.clone());
        inputs.push(EuInput {
            name,
            goods_id: chosen_id.clone(),
            amount,
            result: sub,
        });
    }

    Some(EuResult {
        eu_per_unit: cost,
        path: EuPath::Recipe {
            recipe_id,
            recipe_type,
            voltage_tier,
            recipe_eu,
            output_amount,
            inputs,
        },
    })
}

// ===== EU cache =====

/// Returns the mtime (seconds since epoch) of the file at `path`, or 0 on error.
fn file_mtime_secs(path: &str) -> u64 {
    std::fs::metadata(path)
        .and_then(|m| m.modified())
        .map(|t| {
            t.duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs()
        })
        .unwrap_or(0)
}

/// mtime of the running `gtnh` binary: the graph and Dijkstra rules live in code, so a rebuild
/// must invalidate the cache as much as a new DB does.
fn exe_mtime_secs() -> u64 {
    std::env::current_exe()
        .ok()
        .and_then(|p| p.to_str().map(file_mtime_secs))
        .unwrap_or(0)
}

// Separate owned (for deserialize) and borrowed (for serialize) cache types so we
// can serialize without cloning the graph.
#[derive(Deserialize)]
struct EuCache {
    db_mtime_secs: u64,
    exe_mtime_secs: u64,
    eu_graph: EuGraph,
    dijk: DijkState,
}

#[derive(Serialize)]
struct EuCacheRef<'a> {
    db_mtime_secs: u64,
    exe_mtime_secs: u64,
    eu_graph: &'a EuGraph,
    dijk: &'a DijkState,
}

/// Try to load a valid EU cache from `cache_path` for the DB at `db_path`.
/// Returns `None` if the cache is absent, stale (DB or binary newer), or corrupt.
fn load_eu_cache(cache_path: &str, db_path: &str) -> Option<(EuGraph, DijkState)> {
    let bytes = std::fs::read(cache_path).ok()?;
    let cache: EuCache = bincode::deserialize(&bytes).ok()?;
    if cache.db_mtime_secs != file_mtime_secs(db_path) || cache.exe_mtime_secs != exe_mtime_secs() {
        return None;
    }
    Some((cache.eu_graph, cache.dijk))
}

/// Serialize and save the graph + Dijkstra state to `cache_path`.
/// Silently ignores write errors (cache is optional).
fn save_eu_cache(cache_path: &str, db_path: &str, eu_graph: &EuGraph, dijk: &DijkState) {
    let ser = EuCacheRef {
        db_mtime_secs: file_mtime_secs(db_path),
        exe_mtime_secs: exe_mtime_secs(),
        eu_graph,
        dijk,
    };
    if let Ok(bytes) = bincode::serialize(&ser) {
        let _ = std::fs::write(cache_path, bytes);
    }
}

// ===== Graphviz DOT output =====

/// Return a quoted DOT node id like `"g:some~id"`.
fn dot_node_id(prefix: &str, id: &str) -> String {
    let escaped = id.replace('\\', "\\\\").replace('"', "\\\"");
    format!("\"{prefix}:{escaped}\"")
}

/// Return a quoted DOT label string, with `\n` as the DOT newline escape.
fn dot_label(s: &str) -> String {
    let escaped = s.replace('\\', "\\\\").replace('"', "\\\"");
    format!("\"{}\"", escaped)
}

/// Format an amount as "N×" or "N.NNN×".
fn dot_amount(a: f64) -> String {
    if (a - a.round()).abs() < 1e-9 {
        format!("{}×", a as i64)
    } else {
        format!("{:.3}×", a)
    }
}

fn print_eu_dot(result: &EuResult, root_id: &str, root_name: &str) {
    println!("digraph eu_cost {{");
    println!("  rankdir=LR;");
    println!("  node [fontname=\"Helvetica\", fontsize=10];");
    println!("  edge [fontsize=9];");
    let mut vg: HashSet<String> = HashSet::new();
    let mut vr: HashSet<String> = HashSet::new();
    emit_eu_dot(result, root_id, root_name, &mut vg, &mut vr);
    println!("}}");
}

fn emit_eu_dot(
    result: &EuResult,
    goods_id: &str,
    goods_name: &str,
    vg: &mut HashSet<String>,
    vr: &mut HashSet<String>,
) {
    if !vg.insert(goods_id.to_string()) {
        return;
    }
    println!(
        "  {} [label={}, shape=ellipse];",
        dot_node_id("g", goods_id),
        dot_label(&format!(
            "{}\n{}/unit",
            goods_name,
            fmt_eu(result.eu_per_unit as i64)
        ))
    );
    let EuPath::Recipe {
        recipe_id,
        recipe_type,
        voltage_tier,
        recipe_eu,
        output_amount,
        inputs,
    } = &result.path
    else {
        return; // Free node — leaf, no edges
    };

    if vr.insert(recipe_id.clone()) {
        let tier = if voltage_tier.is_empty() {
            String::new()
        } else {
            format!(" [{}]", voltage_tier)
        };
        let eu_line = if *recipe_eu > 0 {
            format!("\n{}", fmt_eu(*recipe_eu))
        } else {
            String::new()
        };
        println!(
            "  {} [label={}, shape=box, style=filled, fillcolor=lightyellow];",
            dot_node_id("r", recipe_id),
            dot_label(&format!("{}{}{}", recipe_type, tier, eu_line))
        );
    }

    // recipe → output goods
    if (*output_amount - 1.0).abs() > 1e-9 {
        println!(
            "  {} -> {} [label=\"{}\"];",
            dot_node_id("r", recipe_id),
            dot_node_id("g", goods_id),
            dot_amount(*output_amount)
        );
    } else {
        println!(
            "  {} -> {};",
            dot_node_id("r", recipe_id),
            dot_node_id("g", goods_id)
        );
    }

    // input goods → recipe (deduplicated by goods_id, amounts summed)
    let mut seen: HashSet<String> = HashSet::new();
    for input in inputs {
        if !seen.insert(input.goods_id.clone()) {
            continue;
        }
        let total: f64 = inputs
            .iter()
            .filter(|i| i.goods_id == input.goods_id)
            .map(|i| i.amount)
            .sum();
        if (total - 1.0).abs() > 1e-9 {
            println!(
                "  {} -> {} [label=\"{}\"];",
                dot_node_id("g", &input.goods_id),
                dot_node_id("r", recipe_id),
                dot_amount(total)
            );
        } else {
            println!(
                "  {} -> {};",
                dot_node_id("g", &input.goods_id),
                dot_node_id("r", recipe_id)
            );
        }
        emit_eu_dot(&input.result, &input.goods_id, &input.name, vg, vr);
    }
}

fn print_uu_dot(result: &UuResult, root_id: &str, root_name: &str) {
    println!("digraph uu_cost {{");
    println!("  rankdir=LR;");
    println!("  node [fontname=\"Helvetica\", fontsize=10];");
    println!("  edge [fontsize=9];");
    let mut vg: HashSet<String> = HashSet::new();
    let mut vr: HashSet<String> = HashSet::new();
    emit_uu_dot(result, root_id, root_name, &mut vg, &mut vr);
    println!("}}");
}

fn emit_uu_dot(
    result: &UuResult,
    goods_id: &str,
    goods_name: &str,
    vg: &mut HashSet<String>,
    vr: &mut HashSet<String>,
) {
    if !vg.insert(goods_id.to_string()) {
        return;
    }
    println!(
        "  {} [label={}, shape=ellipse];",
        dot_node_id("g", goods_id),
        dot_label(&format!(
            "{}\n{}/unit",
            goods_name,
            fmt_uu(result.uu_per_unit)
        ))
    );
    let UuPath::Recipe {
        recipe_id,
        recipe_type,
        output_amount,
        inputs,
    } = &result.path
    else {
        return; // Base (UU-Matter) — leaf, no edges
    };

    if vr.insert(recipe_id.clone()) {
        println!(
            "  {} [label={}, shape=box, style=filled, fillcolor=lightyellow];",
            dot_node_id("r", recipe_id),
            dot_label(recipe_type)
        );
    }

    // recipe → output goods
    if (*output_amount - 1.0).abs() > 1e-9 {
        println!(
            "  {} -> {} [label=\"{}\"];",
            dot_node_id("r", recipe_id),
            dot_node_id("g", goods_id),
            dot_amount(*output_amount)
        );
    } else {
        println!(
            "  {} -> {};",
            dot_node_id("r", recipe_id),
            dot_node_id("g", goods_id)
        );
    }

    // input goods → recipe (deduplicated by goods_id, amounts summed)
    let mut seen: HashSet<String> = HashSet::new();
    for input in inputs {
        if !seen.insert(input.goods_id.clone()) {
            continue;
        }
        let total: f64 = inputs
            .iter()
            .filter(|i| i.goods_id == input.goods_id)
            .map(|i| i.amount)
            .sum();
        if (total - 1.0).abs() > 1e-9 {
            println!(
                "  {} -> {} [label=\"{}\"];",
                dot_node_id("g", &input.goods_id),
                dot_node_id("r", recipe_id),
                dot_amount(total)
            );
        } else {
            println!(
                "  {} -> {};",
                dot_node_id("g", &input.goods_id),
                dot_node_id("r", recipe_id)
            );
        }
        emit_uu_dot(&input.result, &input.goods_id, &input.name, vg, vr);
    }
}

fn print_eu_tree(result: &EuResult, depth: usize, max_depth: usize, pad: &str) {
    match &result.path {
        EuPath::Free => {
            println!("{pad}  [from infinite source]");
        }
        EuPath::Recipe {
            recipe_type,
            recipe_id,
            voltage_tier,
            recipe_eu,
            output_amount,
            inputs,
        } => {
            let output_note = if (*output_amount - output_amount.round()).abs() > 1e-6 {
                format!("  (yields {output_amount:.4}/run)")
            } else {
                format!("  (yields {}×/run)", *output_amount as i64)
            };
            let recipe_note = if *recipe_eu > 0 {
                format!("  recipe: {}", fmt_eu(*recipe_eu))
            } else {
                String::new()
            };
            let tier_note = if voltage_tier.is_empty() {
                String::new()
            } else {
                format!("  [{}]", voltage_tier)
            };
            println!(
                "{pad}  via {recipe_type}  [{recipe_id}]{output_note}{recipe_note}{tier_note}"
            );

            if depth >= max_depth {
                println!("{pad}  … (depth limit; {} inputs)", inputs.len());
                return;
            }

            let mut deduped: Vec<(String, String, f64, &EuResult)> = Vec::new();
            for input in inputs {
                if let Some(entry) = deduped
                    .iter_mut()
                    .find(|(gid, _, _, _)| *gid == input.goods_id)
                {
                    entry.2 += input.amount;
                } else {
                    deduped.push((
                        input.goods_id.clone(),
                        input.name.clone(),
                        input.amount,
                        &input.result,
                    ));
                }
            }

            let child_pad = format!("{pad}    ");
            for (_, name, amount, sub) in &deduped {
                let is_free = matches!(sub.path, EuPath::Free);
                // amount 0: a block the recipe needs in place (a crop's sub-soil), not spent
                let leaf_tag = match (is_free, *amount == 0.0) {
                    (_, true) => "  [placed, not consumed]",
                    (true, false) => "  [free]",
                    (false, false) => "",
                };
                println!(
                    "{pad}    {}×  {}  @  {}  =  {}{}",
                    amount,
                    name,
                    fmt_eu(sub.eu_per_unit as i64),
                    fmt_eu((amount * sub.eu_per_unit) as i64),
                    leaf_tag,
                );
                if !is_free {
                    print_eu_tree(sub, depth + 1, max_depth, &child_pad);
                }
            }
        }
    }
}

fn fmt_uu(uu: f64) -> String {
    if uu == 0.0 {
        return "0".to_string();
    }
    if uu >= 1_000_000.0 {
        format!("{:.3}M UU", uu / 1e6)
    } else if uu >= 1_000.0 {
        format!("{:.2}k UU", uu / 1e3)
    } else if uu >= 1.0 && uu.fract() < 1e-9 {
        format!("{} UU", uu as i64)
    } else {
        format!("{:.4} UU", uu)
    }
}

/// Returns true when the cheapest path for this result is via a Replicator recipe
/// (i.e., the only input is UU-Matter itself).
fn is_replicator_direct(result: &UuResult) -> bool {
    matches!(&result.path, UuPath::Recipe { inputs, .. }
        if inputs.len() == 1 && inputs[0].goods_id == UU_MATTER_ID)
}

fn print_uu_tree(result: &UuResult, depth: usize, max_depth: usize, pad: &str) {
    match &result.path {
        UuPath::Base => {
            println!("{pad}  (UU-Matter)");
        }
        UuPath::Recipe {
            recipe_type,
            recipe_id,
            output_amount,
            inputs,
        } => {
            if is_replicator_direct(result) {
                // Leaf: directly replicated — no need to expand further.
                println!("{pad}  via {recipe_type}");
                return;
            }

            let output_note = if (*output_amount - output_amount.round()).abs() > 1e-6 {
                format!("  (yields {output_amount:.4}/run)")
            } else {
                format!("  (yields {}×/run)", *output_amount as i64)
            };
            println!("{pad}  via {recipe_type}  [{recipe_id}]{output_note}");

            if depth >= max_depth {
                println!("{pad}  … (depth limit; {} inputs)", inputs.len());
                return;
            }

            // Collapse duplicate inputs (same goods_id) into one display entry.
            let mut deduped: Vec<(String, String, f64, &UuResult)> = Vec::new();
            for input in inputs {
                if let Some(entry) = deduped
                    .iter_mut()
                    .find(|(gid, _, _, _)| *gid == input.goods_id)
                {
                    entry.2 += input.amount;
                } else {
                    deduped.push((
                        input.goods_id.clone(),
                        input.name.clone(),
                        input.amount,
                        &input.result,
                    ));
                }
            }

            let child_pad = format!("{pad}    ");
            for (_, name, amount, sub) in &deduped {
                let is_leaf = is_replicator_direct(sub) || matches!(sub.path, UuPath::Base);
                let leaf_tag = if is_leaf { "  [direct]" } else { "" };
                println!(
                    "{pad}    {}×  {}  @  {}  =  {}{}",
                    amount,
                    name,
                    fmt_uu(sub.uu_per_unit),
                    fmt_uu(amount * sub.uu_per_unit),
                    leaf_tag,
                );
                if !is_leaf {
                    print_uu_tree(sub, depth + 1, max_depth, &child_pad);
                }
            }
        }
    }
}

// ===== Main =====

fn main() -> Result<()> {
    let cli = Cli::parse();

    // build-db and merge-db don't read through the repository
    if let Command::BuildDb { script, output } = &cli.command {
        eprintln!("Building {} from {}...", output, script);
        build_db(script, output, |n| eprintln!("  {} lines processed...", n))?;
        eprintln!("Done.");
        return Ok(());
    }
    if let Command::MergeDb { src } = &cli.command {
        eprintln!("Merging {} into {}...", src, cli.data);
        let added = merge_db(&cli.data, src)?;
        if added.is_empty() {
            eprintln!("  nothing new");
        }
        for (table, n) in &added {
            eprintln!("  {table}: +{n}");
        }
        return Ok(());
    }

    eprintln!("Loading {}...", cli.data);
    let repo = Repository::open(&cli.data)?;

    match &cli.command {
        Command::BuildDb { .. } | Command::MergeDb { .. } => unreachable!(),

        Command::Search {
            query,
            limit,
            tooltip,
            regex,
        } => {
            let items = repo.search_items(query, *tooltip, Some(*limit), *regex)?;
            let fluids = repo.search_fluids(query, *tooltip, Some(*limit), *regex)?;

            if cli.json {
                println!(
                    "{}",
                    serde_json::json!({ "items": items, "fluids": fluids })
                );
                return Ok(());
            }

            let trunc_i = items.len() == *limit;
            println!(
                "Items ({} of {}):",
                items.len(),
                if trunc_i {
                    format!("{}+", items.len())
                } else {
                    items.len().to_string()
                }
            );
            for item in &items {
                println!(
                    "  {:<50}  {}  [{}]",
                    item.name.as_deref().unwrap_or("?"),
                    item.mod_name.as_deref().unwrap_or("?"),
                    from_db_id(&item.id)
                );
            }
            if trunc_i {
                println!("  … use --limit to see more");
            }

            let trunc_f = fluids.len() == *limit;
            println!(
                "\nFluids ({} of {}):",
                fluids.len(),
                if trunc_f {
                    format!("{}+", fluids.len())
                } else {
                    fluids.len().to_string()
                }
            );
            for fluid in &fluids {
                println!(
                    "  {:<50}  {}  [{}]",
                    fluid.name.as_deref().unwrap_or("?"),
                    fluid.mod_name.as_deref().unwrap_or("?"),
                    from_db_id(&fluid.id)
                );
            }
            if trunc_f {
                println!("  … use --limit to see more");
            }
        }

        Command::Item { id } => {
            let db_id = to_db_id(id);
            let item = repo
                .get_item(&db_id)?
                .ok_or_else(|| anyhow::anyhow!("Item not found: {id}"))?;
            if cli.json {
                println!("{}", serde_json::to_string_pretty(&item)?);
                return Ok(());
            }
            println!("{}", item.name.as_deref().unwrap_or("?"));
            println!("  id:            {}", from_db_id(&item.id));
            println!(
                "  mod:           {}",
                item.mod_name.as_deref().unwrap_or("?")
            );
            println!(
                "  internal name: {}",
                item.internal_name.as_deref().unwrap_or("?")
            );
            println!("  damage:        {}", item.damage);
            println!("  stack size:    {}", item.stack_size);
            if let Some(nbt) = &item.nbt {
                println!("  nbt:           {}", nbt);
            }
            if let Some(tip) = &item.tooltip {
                let clean = strip_mc_fmt(tip);
                println!("  tooltip:");
                for line in clean.lines() {
                    println!("    {line}");
                }
            }
            if let Some(c) = &item.container {
                let fname = c
                    .fluid_id
                    .as_deref()
                    .map(|fid| repo.name_of(fid).unwrap_or_else(|_| fid.to_string()))
                    .unwrap_or_else(|| "?".to_string());
                println!("  container of:  {}  ({}mB)", fname, c.amount);
            }
        }

        Command::Fluid { id } => {
            let db_id = to_db_id(id);
            let fluid = repo
                .get_fluid(&db_id)?
                .ok_or_else(|| anyhow::anyhow!("Fluid not found: {id}"))?;
            if cli.json {
                println!("{}", serde_json::to_string_pretty(&fluid)?);
                return Ok(());
            }
            println!("{}", fluid.name.as_deref().unwrap_or("?"));
            println!("  id:            {}", from_db_id(&fluid.id));
            println!(
                "  mod:           {}",
                fluid.mod_name.as_deref().unwrap_or("?")
            );
            println!(
                "  internal name: {}",
                fluid.internal_name.as_deref().unwrap_or("?")
            );
            println!("  gas:           {}", fluid.is_gas);
        }

        Command::RecipeTypes { filter } => {
            let types = repo.recipe_types(filter.as_deref())?;
            if cli.json {
                println!("{}", serde_json::to_string_pretty(&types)?);
                return Ok(());
            }
            println!("{} recipe types:", types.len());
            for rt in &types {
                let count = repo.recipe_count_by_type(&rt.id)?;
                println!("  {:<45}  {:>5} recipes  [{}]", rt.name, count, rt.category);
            }
        }

        Command::RecipesFor { id, limit, sort } => {
            let db_id = to_db_id(id);
            let name = repo.name_of(&db_id)?;
            let mut recipes = repo.recipes_producing(&db_id)?;
            let hidden = if !cli.all_recipes {
                let before = recipes.len();
                recipes.retain(|r| !is_canning_or_recycling(r));
                before - recipes.len()
            } else {
                0
            };
            recipes.sort_by_key(|r| sort_key(r, &db_id, sort));
            let total = recipes.len();
            let shown: Vec<_> = recipes
                .into_iter()
                .take(limit.unwrap_or(usize::MAX))
                .collect();

            if cli.json {
                println!("{}", serde_json::to_string_pretty(&recipes_json(&repo, &shown)?)?);
                return Ok(());
            }
            println!(
                "{} recipes producing \"{}\" [{}]{}{}",
                total,
                name,
                from_db_id(&db_id),
                if total > shown.len() {
                    format!("  (showing {})", shown.len())
                } else {
                    String::new()
                },
                if hidden > 0 {
                    format!("  ({hidden} recycler hidden, use --all-recipes to show)")
                } else {
                    String::new()
                },
            );
            print_recipe_list(&repo, &shown, &db_id, sort);
        }

        Command::RecipesUsing { id, limit, sort } => {
            let db_id = to_db_id(id);
            let name = repo.name_of(&db_id)?;
            let mut recipes = repo.recipes_consuming(&db_id)?;
            let hidden = if !cli.all_recipes {
                let before = recipes.len();
                recipes.retain(|r| !is_canning_or_recycling(r));
                before - recipes.len()
            } else {
                0
            };
            recipes.sort_by_key(|r| sort_key(r, &db_id, sort));
            let total = recipes.len();
            let shown: Vec<_> = recipes
                .into_iter()
                .take(limit.unwrap_or(usize::MAX))
                .collect();

            if cli.json {
                println!("{}", serde_json::to_string_pretty(&recipes_json(&repo, &shown)?)?);
                return Ok(());
            }
            println!(
                "{} recipes consuming \"{}\" [{}]{}{}",
                total,
                name,
                from_db_id(&db_id),
                if total > shown.len() {
                    format!("  (showing {})", shown.len())
                } else {
                    String::new()
                },
                if hidden > 0 {
                    format!("  ({hidden} recycler hidden, use --all-recipes to show)")
                } else {
                    String::new()
                },
            );
            print_recipe_list(&repo, &shown, &db_id, sort);
        }

        Command::Recipe { id } => {
            let recipe = repo
                .get_recipe(id)?
                .ok_or_else(|| anyhow::anyhow!("Recipe not found: {id}"))?;
            if cli.json {
                let json = recipes_json(&repo, std::slice::from_ref(&recipe))?;
                println!("{}", serde_json::to_string_pretty(&json[0])?);
                return Ok(());
            }
            print_recipe(&repo, &recipe);
        }

        Command::RecipesOfType { name, limit, sort } => {
            let mut recipes = repo.recipes_by_type(name)?;
            let dummy = "";
            recipes.sort_by_key(|r| sort_key(r, dummy, sort));
            let total = recipes.len();
            let shown: Vec<_> = recipes.into_iter().take(*limit).collect();

            if cli.json {
                println!("{}", serde_json::to_string_pretty(&recipes_json(&repo, &shown)?)?);
                return Ok(());
            }
            println!(
                "{} recipes of type \"{}\"{}",
                total,
                name,
                if total > shown.len() {
                    format!("  (showing {})", shown.len())
                } else {
                    String::new()
                }
            );
            print_recipe_list(&repo, &shown, dummy, sort);
        }

        Command::EuCost { id, depth, why, min_tier, max_tier } => {
            let db_id = to_db_id(id);
            let name = repo.name_of(&db_id)?;

            // Validate --max-tier if supplied.
            let max_tier_rank: Option<u8> = if let Some(t) = max_tier {
                const TIER_ORDER: &[&str] = &[
                    "ULV", "LV", "MV", "HV", "EV", "IV", "LuV", "ZPM", "UV",
                    "UHV", "UEV", "UIV", "UMV", "UXV",
                ];
                match TIER_ORDER.iter().position(|&s| s == t.as_str()) {
                    Some(r) => Some(r as u8),
                    None => anyhow::bail!(
                        "Unknown tier \"{t}\". Valid tiers: {}",
                        TIER_ORDER.join(", ")
                    ),
                }
            } else {
                None
            };

            let cache_path = format!("{}.eucache", cli.data);
            let (eu_graph, dijk) = {
                // Always load/build the EU graph; the cached DijkState is only reused for
                // the default (unconstrained min-EU) mode.
                let (mut g, cached_dijk) =
                    if let Some(cached) = load_eu_cache(&cache_path, &cli.data) {
                        eprintln!("Loaded EU cache.");
                        cached
                    } else {
                        eprintln!("Building EU cost graph...");
                        let mut g = repo.build_eu_graph()?;
                        eprintln!("Seeding infinite sources...");
                        populate_seed_costs(&mut g, &repo);
                        add_infinite_source_recipes(&mut g);
                        add_eec_recipes(&mut g, &repo);
                        eprintln!("Running Dijkstra...");
                        let d = run_eu_dijkstra(&g);
                        save_eu_cache(&cache_path, &cli.data, &g, &d);
                        (g, d)
                    };
                // Always (re-)populate mining tiers: not stored in the cache.
                populate_mining_tiers(&mut g, &repo);
                let d = if *min_tier {
                    eprintln!("Running min-tier Dijkstra...");
                    run_min_tier_dijkstra(&g)
                } else if let Some(rank) = max_tier_rank {
                    eprintln!("Running max-tier Dijkstra...");
                    run_max_tier_dijkstra(&g, rank)
                } else {
                    cached_dijk
                };
                (g, d)
            };
            let result = build_eu_result(&db_id, &dijk, &eu_graph, &repo, *depth);

            if cli.json {
                println!("{}", serde_json::to_string_pretty(&result)?);
                return Ok(());
            }

            match result {
                None => {
                    eprintln!(
                        "No EU cost path found for \"{}\" [{}]",
                        name,
                        from_db_id(&db_id)
                    );
                    let diag_depth = if *why { 3 } else { 1 };
                    eprintln!("Diagnosing:");
                    diagnose_no_path(&db_id, &eu_graph, &dijk, &repo, diag_depth, "");
                }
                Some(ref r) => {
                    if cli.dot {
                        print_eu_dot(r, &db_id, &name);
                    } else {
                        let tier = peak_voltage_tier(
                            &db_id, &eu_graph, &dijk, &mut HashSet::new(),
                        );
                        let tier_str = tier.as_deref().unwrap_or("?");
                        let label = if *min_tier {
                            "EU cost (min-tier)".to_string()
                        } else if let Some(t) = max_tier {
                            format!("EU cost (max-tier: {})", t)
                        } else {
                            "EU cost".to_string()
                        };
                        println!("{} for \"{}\" [{}]", label, name, from_db_id(&db_id));
                        println!("  Best: {}/unit  [{}]", fmt_eu(r.eu_per_unit as i64), tier_str);
                        print_eu_tree(r, 0, *depth, "");
                    }
                }
            }
        }

        Command::UuCost { id, depth } => {
            let db_id = to_db_id(id);
            let name = repo.name_of(&db_id)?;

            eprintln!("Preloading recipe data...");
            repo.preload_recipes_producing()?;

            let mut path: HashSet<String> = HashSet::new();
            let mut memo: HashMap<String, UuResult> = HashMap::new();
            let mut impossible: HashSet<String> = HashSet::new();

            // Iterative passes: each pass clears stale impossibles and evicts the target
            // from memo so it is re-explored using the latest dependency memos.
            // Items that were cycle-blocked in an earlier pass can now resolve.
            // Repeat until the result stops improving.
            let mut result = compute_uu_cost(&db_id, &mut path, &mut memo, &mut impossible, &repo);
            loop {
                impossible.clear();
                path.clear();
                memo.remove(&db_id);
                let new_result =
                    compute_uu_cost(&db_id, &mut path, &mut memo, &mut impossible, &repo);
                let improved = match (&result, &new_result) {
                    (None, Some(_)) => true,
                    (Some(old), Some(new)) => new.uu_per_unit < old.uu_per_unit - 1e-9,
                    _ => false,
                };
                result = new_result;
                if !improved {
                    break;
                }
            }

            if cli.json {
                println!("{}", serde_json::to_string_pretty(&result)?);
                return Ok(());
            }

            match result {
                None => eprintln!(
                    "No UU-Matter path found for \"{}\" [{}]",
                    name,
                    from_db_id(&db_id)
                ),
                Some(ref r) => {
                    if cli.dot {
                        print_uu_dot(r, &db_id, &name);
                    } else {
                        println!("UU-Matter cost for \"{}\" [{}]", name, from_db_id(&db_id));
                        println!("  Best: {}", fmt_uu(r.uu_per_unit));
                        print_uu_tree(r, 0, *depth, "");
                    }
                }
            }
        }
    }

    Ok(())
}
