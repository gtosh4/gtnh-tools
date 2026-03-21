use anyhow::Result;
use clap::{Parser, Subcommand, ValueEnum};
use gtnh::{GtRecipe, Recipe, RecipeIoType, Repository, build_db};

// ===== CLI definition =====

#[derive(Parser)]
#[command(name = "gtnh", about = "Query GTNH items and recipes")]
struct Cli {
    /// Path to gtnh.db (created with build-db)
    #[arg(long, default_value = "gtnh.db", global = true)]
    data: String,

    /// Emit JSON instead of human-readable text
    #[arg(long, global = true)]
    json: bool,

    /// Include Canner and Recycler recipes (hidden by default)
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
        #[arg(short, long, default_value = "gtnh.db")]
        output: String,
    },

    /// Search items and fluids by name
    Search {
        query: String,
        #[arg(short, long, default_value = "20")]
        limit: usize,
        /// Also search within item tooltips
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
        Some(n) if n.starts_with("Canner ")
                || n.starts_with("Fluid Canner ")
                || n.starts_with("Recycler ")
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
    recipe.gt_recipe.as_ref()?.metadata.iter().find_map(|m| {
        if m.key == "fuel_value" {
            Some(m.value)
        } else {
            None
        }
    })
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
        let db_id = io.goods_id.as_deref().unwrap_or("?");
        let name = repo.name_of(db_id).unwrap_or_else(|_| db_id.to_string());
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
        let prob = if io.probability < 1.0 {
            format!("  ({:.0}%)", io.probability * 100.0)
        } else {
            String::new()
        };
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
        println!("  Inputs:");
        for io in recipe.inputs() {
            let db_id = io.goods_id.as_deref().unwrap_or("?");
            let label = if io.io_type == RecipeIoType::OreDictInput {
                format!("{} (ore dict)", from_db_id(db_id))
            } else {
                repo.name_of(db_id).unwrap_or_else(|_| db_id.to_string())
            };
            println!("    {:>4}×  {}", io.amount, label);
        }
        println!("  Outputs:");
        for io in recipe.outputs() {
            let db_id = io.goods_id.as_deref().unwrap_or("?");
            let name = repo.name_of(db_id).unwrap_or_else(|_| db_id.to_string());
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

    // build-db doesn't need an existing database
    if let Command::BuildDb { script, output } = &cli.command {
        eprintln!("Building {} from {}...", output, script);
        build_db(script, output, |n| eprintln!("  {} lines processed...", n))?;
        eprintln!("Done.");
        return Ok(());
    }

    eprintln!("Loading {}...", cli.data);
    let repo = Repository::open(&cli.data)?;

    match &cli.command {
        Command::BuildDb { .. } => unreachable!(),

        Command::Search {
            query,
            limit,
            tooltip,
        } => {
            let db_query = to_db_id(query); // pass through; search is text-based not id-based
            let _ = db_query;
            let items = repo.search_items(query, *tooltip, Some(*limit))?;
            let fluids = repo.search_fluids(query, *tooltip, Some(*limit))?;

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
                println!("{}", serde_json::to_string_pretty(&shown)?);
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
                    format!("  ({hidden} canner/recycler hidden, use --all-recipes to show)")
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
                println!("{}", serde_json::to_string_pretty(&shown)?);
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
                    format!("  ({hidden} canner/recycler hidden, use --all-recipes to show)")
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
                println!("{}", serde_json::to_string_pretty(&recipe)?);
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
            print_recipe_list(&repo, &shown, dummy, sort);
        }
    }

    Ok(())
}
