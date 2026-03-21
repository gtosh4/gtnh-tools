use anyhow::Result;
use clap::{Parser, Subcommand, ValueEnum};
use gtnh::{GtRecipe, Recipe, RecipeIoType, Repository};

// ===== CLI definition =====

#[derive(Parser)]
#[command(name = "gtnh", about = "Query GTNH items and recipes")]
struct Cli {
    /// Path to data.bin
    #[arg(long, default_value = "data.bin", global = true)]
    data: String,

    /// Emit JSON instead of human-readable text
    #[arg(long, global = true)]
    json: bool,

    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Search items and fluids by name
    Search {
        query: String,
        #[arg(short, long, default_value = "20")]
        limit: usize,
        /// Also search within item and fluid tooltips
        #[arg(short, long)]
        tooltip: bool,
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

// ===== Helpers =====

const VOLTAGE_TIERS: &[&str] = &[
    "ULV", "LV", "MV", "HV", "EV", "IV", "LuV", "ZPM", "UV", "UHV", "UEV", "UIV", "UMV", "UXV",
];

fn tier_name(tier: i32) -> &'static str {
    VOLTAGE_TIERS
        .get(tier as usize)
        .copied()
        .unwrap_or("???")
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

/// EU-per-output-unit for a GT recipe producing `output_amount` units. Lower = better.
fn eu_per_output(gt: &GtRecipe, output_amount: i32) -> i64 {
    let amount = output_amount.max(1) as i64;
    gt.eu_total() / amount
}

/// Sort key for a recipe list. Recipes without GT data sort last for EU/time sorts.
fn fuel_value(recipe: &Recipe) -> Option<i64> {
    recipe.gt_recipe.as_ref()?.metadata.iter().find_map(|m| {
        if m.key.as_deref() == Some("fuel_value") {
            Some(m.value as i64)
        } else {
            None
        }
    })
}

fn sort_key(recipe: &Recipe, target_id: &str, by: &SortBy) -> i64 {
    match by {
        SortBy::Eu => {
            let output_amt = recipe
                .outputs()
                .find(|io| io.goods_id.as_deref() == Some(target_id))
                .map(|io| io.amount)
                .unwrap_or(1);
            recipe
                .gt_recipe
                .as_ref()
                .map(|gt| eu_per_output(gt, output_amt))
                .unwrap_or(i64::MAX)
        }
        SortBy::Time => recipe
            .gt_recipe
            .as_ref()
            .map(|gt| gt.duration_ticks as i64)
            .unwrap_or(i64::MAX),
        SortBy::Inputs => recipe.inputs().count() as i64,
        // Negate so highest fuel_value sorts first (ascending key = best first)
        SortBy::Fuel => -fuel_value(recipe).unwrap_or(0),
    }
}

fn print_gt_recipe(gt: &GtRecipe) {
    // Fuel recipes have voltage=0; show fuel_value instead of the useless "0 EU" line
    let is_fuel_recipe = gt.voltage == 0 && gt.duration_ticks == 0;
    if !is_fuel_recipe {
        let total = gt.eu_total();
        println!(
            "  GT:    {} EU/t × {}A × {}t = {} ({})  [{}]",
            gt.voltage,
            gt.amperage,
            gt.duration_ticks,
            fmt_eu(total),
            fmt_duration(gt.duration_ticks),
            tier_name(gt.voltage_tier),
        );
    }
    if !gt.metadata.is_empty() {
        let meta: Vec<_> = gt
            .metadata
            .iter()
            .filter_map(|m| Some(format!("{}={}", m.key.as_deref()?, m.value)))
            .collect();
        if !meta.is_empty() {
            println!("  Meta:  {}", meta.join("  "));
        }
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
    println!("  Inputs:");
    for io in recipe.inputs() {
        let name = io
            .goods_id
            .as_deref()
            .map(|id| repo.name_of(id))
            .unwrap_or("?");
        let id = io.goods_id.as_deref().unwrap_or("?");
        println!("    {:>4}×  {:<35}  [{}]", io.amount, name, id);
    }
    println!("  Outputs:");
    for io in recipe.outputs() {
        let name = io
            .goods_id
            .as_deref()
            .map(|id| repo.name_of(id))
            .unwrap_or("?");
        let id = io.goods_id.as_deref().unwrap_or("?");
        let prob = if io.probability < 1.0 {
            format!("  ({:.0}%)", io.probability * 100.0)
        } else {
            String::new()
        };
        println!("    {:>4}×  {:<35}  [{}]{}", io.amount, name, id, prob);
    }
}

fn print_recipe_list(repo: &Repository, recipes: &[&Recipe], target_id: &str, by: &SortBy) {
    for (i, recipe) in recipes.iter().enumerate() {
        let output_amt = recipe
            .outputs()
            .find(|io| io.goods_id.as_deref() == Some(target_id))
            .map(|io| io.amount)
            .unwrap_or(1);

        let efficiency_note = recipe.gt_recipe.as_ref().map(|gt| {
            if let Some(fv) = fuel_value(recipe) {
                format!("  →  fuel_value={fv}")
            } else {
                let epo = eu_per_output(gt, output_amt);
                format!(
                    "  →  {}  ({} EU/output)",
                    fmt_eu(gt.eu_total()),
                    fmt_eu(epo)
                )
            }
        });

        println!(
            "\n#{:<3} [{}]  {}{}",
            i + 1,
            recipe.id,
            recipe.recipe_type_name.as_deref().unwrap_or("?"),
            efficiency_note.as_deref().unwrap_or(""),
        );
        if let Some(gt) = &recipe.gt_recipe {
            print_gt_recipe(gt);
        }
        println!("  Inputs:");
        for io in recipe.inputs() {
            let name = io
                .goods_id
                .as_deref()
                .map(|id| repo.name_of(id))
                .unwrap_or("?");
            println!(
                "    {:>4}×  {}",
                io.amount,
                if io.io_type == RecipeIoType::OreDictInput {
                    format!("{} (ore dict)", io.goods_id.as_deref().unwrap_or("?"))
                } else {
                    name.to_string()
                }
            );
        }
        println!("  Outputs:");
        for io in recipe.outputs() {
            let name = io
                .goods_id
                .as_deref()
                .map(|id| repo.name_of(id))
                .unwrap_or("?");
            let prob = if io.probability < 1.0 {
                format!("  ({:.0}%)", io.probability * 100.0)
            } else {
                String::new()
            };
            println!("    {:>4}×  {}{}", io.amount, name, prob);
        }
        let _ = by;
    }
}

// ===== Main =====

fn main() -> Result<()> {
    let cli = Cli::parse();

    eprintln!("Loading {}...", cli.data);
    let repo = Repository::from_file(&cli.data)?;

    match &cli.command {
        Command::Search { query, limit, tooltip } => {
            let items = repo.search_items(query, *tooltip);
            let fluids = repo.search_fluids(query, *tooltip);

            if cli.json {
                let shown_items: Vec<_> = items.iter().take(*limit).collect();
                let shown_fluids: Vec<_> = fluids.iter().take(*limit).collect();
                println!(
                    "{}",
                    serde_json::json!({ "items": shown_items, "fluids": shown_fluids })
                );
                return Ok(());
            }

            println!("Items ({} of {}):", items.len().min(*limit), items.len());
            for item in items.iter().take(*limit) {
                println!(
                    "  {:<50}  {}  [{}]",
                    item.name.as_deref().unwrap_or("?"),
                    item.mod_name.as_deref().unwrap_or("?"),
                    item.id,
                );
            }
            if items.len() > *limit {
                println!("  … and {} more", items.len() - limit);
            }

            println!("\nFluids ({} of {}):", fluids.len().min(*limit), fluids.len());
            for fluid in fluids.iter().take(*limit) {
                println!(
                    "  {:<50}  {}  [{}]",
                    fluid.name.as_deref().unwrap_or("?"),
                    fluid.mod_name.as_deref().unwrap_or("?"),
                    fluid.id,
                );
            }
            if fluids.len() > *limit {
                println!("  … and {} more", fluids.len() - limit);
            }
        }

        Command::Item { id } => {
            let item = repo
                .get_item(id)
                .ok_or_else(|| anyhow::anyhow!("Item not found: {id}"))?;
            if cli.json {
                println!("{}", serde_json::to_string_pretty(item)?);
                return Ok(());
            }
            println!("{}", item.name.as_deref().unwrap_or("?"));
            println!("  id:            {}", item.id);
            println!("  mod:           {}", item.mod_name.as_deref().unwrap_or("?"));
            println!(
                "  internal name: {}",
                item.internal_name.as_deref().unwrap_or("?")
            );
            println!("  damage:        {}", item.damage);
            println!("  stack size:    {}", item.stack_size);
            if let Some(nbt) = &item.nbt {
                println!("  nbt:           {}", nbt);
            }
            if let Some(c) = &item.container {
                println!(
                    "  container of:  {}  ({}mB)",
                    c.fluid_id.as_deref().map(|id| repo.name_of(id)).unwrap_or("?"),
                    c.amount
                );
            }
            println!(
                "  produced by {} recipes, consumed by {} recipes",
                item.production_recipe_ids.len(),
                item.consumption_recipe_ids.len(),
            );
        }

        Command::Fluid { id } => {
            let fluid = repo
                .get_fluid(id)
                .ok_or_else(|| anyhow::anyhow!("Fluid not found: {id}"))?;
            if cli.json {
                println!("{}", serde_json::to_string_pretty(fluid)?);
                return Ok(());
            }
            println!("{}", fluid.name.as_deref().unwrap_or("?"));
            println!("  id:            {}", fluid.id);
            println!("  mod:           {}", fluid.mod_name.as_deref().unwrap_or("?"));
            println!(
                "  internal name: {}",
                fluid.internal_name.as_deref().unwrap_or("?")
            );
            println!("  gas:           {}", fluid.is_gas);
            println!(
                "  produced by {} recipes, consumed by {} recipes",
                fluid.production_recipe_ids.len(),
                fluid.consumption_recipe_ids.len(),
            );
        }

        Command::RecipeTypes { filter } => {
            let mut types: Vec<_> = repo.recipe_types.iter().collect();
            if let Some(f) = filter {
                let f = f.to_lowercase();
                types.retain(|rt| {
                    rt.name.as_deref().is_some_and(|n| n.to_lowercase().contains(&f))
                        || rt
                            .category
                            .as_deref()
                            .is_some_and(|c| c.to_lowercase().contains(&f))
                });
            }
            types.sort_by_key(|rt| rt.name.as_deref().unwrap_or(""));

            if cli.json {
                println!("{}", serde_json::to_string_pretty(&types)?);
                return Ok(());
            }

            println!("{} recipe types:", types.len());
            for rt in &types {
                let recipe_count = repo
                    .recipes_by_type(rt.name.as_deref().unwrap_or(""))
                    .len();
                println!(
                    "  {:<45}  {:>5} recipes  [{}]",
                    rt.name.as_deref().unwrap_or("?"),
                    recipe_count,
                    rt.category.as_deref().unwrap_or("?"),
                );
            }
        }

        Command::RecipesFor { id, limit, sort } => {
            let name = repo.name_of(id);
            let mut recipes = repo.recipes_producing(id);
            recipes.sort_by_key(|r| sort_key(r, id, sort));
            let total = recipes.len();
            let shown: Vec<_> = recipes
                .into_iter()
                .take(limit.unwrap_or(usize::MAX))
                .collect();

            if cli.json {
                println!("{}", serde_json::to_string_pretty(&shown)?);
                return Ok(());
            }

            println!(
                "{} recipes producing \"{}\" [{}]{}",
                total,
                name,
                id,
                if total > shown.len() {
                    format!("  (showing {})", shown.len())
                } else {
                    String::new()
                }
            );
            print_recipe_list(&repo, &shown, id, sort);
        }

        Command::RecipesUsing { id, limit, sort } => {
            let name = repo.name_of(id);
            let mut recipes = repo.recipes_consuming(id);
            recipes.sort_by_key(|r| sort_key(r, id, sort));
            let total = recipes.len();
            let shown: Vec<_> = recipes
                .into_iter()
                .take(limit.unwrap_or(usize::MAX))
                .collect();

            if cli.json {
                println!("{}", serde_json::to_string_pretty(&shown)?);
                return Ok(());
            }

            println!(
                "{} recipes consuming \"{}\" [{}]{}",
                total,
                name,
                id,
                if total > shown.len() {
                    format!("  (showing {})", shown.len())
                } else {
                    String::new()
                }
            );
            print_recipe_list(&repo, &shown, id, sort);
        }

        Command::Recipe { id } => {
            let recipe = repo
                .get_recipe(id)
                .ok_or_else(|| anyhow::anyhow!("Recipe not found: {id}"))?;
            if cli.json {
                println!("{}", serde_json::to_string_pretty(recipe)?);
                return Ok(());
            }
            print_recipe(&repo, recipe);
        }

        Command::RecipesOfType { name, limit, sort } => {
            let mut recipes = repo.recipes_by_type(name);
            // For recipes-of-type, use the first output as the target for EU/output calc
            let dummy_target = "";
            recipes.sort_by_key(|r| sort_key(r, dummy_target, sort));
            let total = recipes.len();
            let shown: Vec<_> = recipes.into_iter().take(*limit).collect();

            if cli.json {
                println!("{}", serde_json::to_string_pretty(&shown)?);
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
            print_recipe_list(&repo, &shown, dummy_target, sort);
        }
    }

    Ok(())
}
