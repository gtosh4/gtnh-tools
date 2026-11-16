use anyhow::Result;
use petgraph::graph::{DiGraph, NodeIndex};
use regex::Regex;
use rusqlite::functions::FunctionFlags;
use rusqlite::{Connection, Error as SqlError, OptionalExtension, params};
use serde::{Deserialize, Serialize};
use std::cell::RefCell;
use std::collections::{HashMap, HashSet};

// ===== Public data types =====

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FluidContainerInfo {
    pub fluid_id: Option<String>,
    pub amount: i32,
    pub empty_item_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Item {
    pub id: String,
    pub name: Option<String>,
    pub mod_name: Option<String>,
    pub internal_name: Option<String>,
    pub tooltip: Option<String>,
    pub unlocalized_name: Option<String>,
    pub nbt: Option<String>,
    pub stack_size: i32,
    pub damage: i32,
    pub container: Option<FluidContainerInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Fluid {
    pub id: String,
    pub name: Option<String>,
    pub mod_name: Option<String>,
    pub internal_name: Option<String>,
    pub unlocalized_name: Option<String>,
    pub nbt: Option<String>,
    pub is_gas: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OreDict {
    pub id: String,
    pub name: String,
    pub item_ids: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecipeType {
    pub id: String,
    pub name: String,
    pub category: String,
    pub shapeless: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GtRecipeMetadata {
    pub key: String,
    pub value: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GtRecipe {
    pub voltage: i32,
    pub duration_ticks: i32,
    pub amperage: i32,
    pub voltage_tier: String,
    pub circuit_conflicts: i32,
    pub metadata: Vec<GtRecipeMetadata>,
}

impl GtRecipe {
    pub fn duration_seconds(&self) -> f64 {
        self.duration_ticks as f64 / 20.0
    }
    pub fn eu_total(&self) -> i64 {
        self.voltage as i64 * self.amperage as i64 * self.duration_ticks as i64
    }
}

/// Voltage tier at which a rocket of the given tier is first buildable
/// (T1 = EV … T7 = UEV, T8 and above = UIV).
fn rocket_tier_voltage(rocket_tier: i64) -> &'static str {
    match rocket_tier {
        ..=0 => "",
        1 => "EV",
        2 => "IV",
        3 => "LuV",
        4 => "ZPM",
        5 => "UV",
        6 => "UHV",
        7 => "UEV",
        _ => "UIV",
    }
}

/// Map a voltage-tier string to a sortable rank (0=ULV … 13=UXV).
pub fn tier_rank_u8(t: &str) -> u8 {
    if t.is_empty() {
        return 0; // synthetic free recipes (PGS, EEC) have no voltage tier
    }
    const TIER_ORDER: &[&str] = &[
        "ULV", "LV", "MV", "HV", "EV", "IV", "LuV", "ZPM", "UV",
        "UHV", "UEV", "UIV", "UMV", "UXV", "MAX",
    ];
    TIER_ORDER.iter().position(|&s| s == t).unwrap_or(TIER_ORDER.len()) as u8
}

/// Minimum tier required by metadata constraints that the recipe-voltage tag does not capture.
///
/// Three keys are handled:
///
/// * `fusion_threshold` — the EU a Fusion Reactor must have stored before the reaction starts.
///   The three standard GT Fusion Reactor marks have caps of 160 M, 360 M, and 560 M EU.
///   Recipes with threshold > 160 M require Mk II (ZPM, gated by the HIP unit which makes
///   Superdense Europium Plate, compression_tier=1).  Mk III (> 360 M) requires UV-tier
///   components in its Assembly Line recipe.  Above 560 M the FusionTech reactors apply (UHV+).
///
/// * `compression_tier` — marks that a recipe requires a specialised compressor rather than
///   the standard GT Compressor.  Tier 1 = Hot Isostatic Pressurization (HIP) unit, first
///   accessible at ZPM.  Tier 2 = higher-tier exotic compressor, first accessible at UHV.
///
/// * `algae_pond_tier` (2.9+) — the Algae Pond's recipes are ULV and input-free; each needs a
///   pond built on machine casings of at least that tier (casing meta = voltage tier index).
pub fn metadata_tier_min(gt: &GtRecipe) -> u8 {
    let mut min = 0u8;
    for m in &gt.metadata {
        let extra = match m.key.as_str() {
            "fusion_threshold" => {
                if m.value <= 160_000_000 {
                    0 // Mk I — no additional constraint beyond recipe voltage
                } else if m.value <= 360_000_000 {
                    tier_rank_u8("ZPM") // Mk II
                } else if m.value <= 560_000_000 {
                    tier_rank_u8("UV") // Mk III
                } else {
                    tier_rank_u8("UHV") // FusionTech MK IV+
                }
            }
            "algae_pond_tier" => (m.value.clamp(0, i64::from(tier_rank_u8("MAX")))) as u8,
            "compression_tier" => match m.value {
                1 => tier_rank_u8("ZPM"), // HIP (Hot Isostatic Pressurization)
                2 => tier_rank_u8("UHV"), // ultra-high-pressure exotic compressor
                _ => 0,
            },
            _ => 0,
        };
        min = min.max(extra);
    }
    min
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RecipeIoType {
    ItemInput,
    OreDictInput,
    FluidInput,
    ItemOutput,
    FluidOutput,
}

impl RecipeIoType {
    pub fn is_input(self) -> bool {
        matches!(
            self,
            Self::ItemInput | Self::OreDictInput | Self::FluidInput
        )
    }
    pub fn is_output(self) -> bool {
        matches!(self, Self::ItemOutput | Self::FluidOutput)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecipeIo {
    pub io_type: RecipeIoType,
    pub goods_id: Option<String>,
    pub slot: i32,
    pub amount: i32,
    /// 0.0–1.0 (1.0 = guaranteed)
    pub probability: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Recipe {
    pub id: String,
    pub recipe_type_name: Option<String>,
    pub gt_recipe: Option<GtRecipe>,
    pub io: Vec<RecipeIo>,
}

impl Recipe {
    pub fn inputs(&self) -> impl Iterator<Item = &RecipeIo> {
        self.io.iter().filter(|io| io.io_type.is_input())
    }
    pub fn outputs(&self) -> impl Iterator<Item = &RecipeIo> {
        self.io.iter().filter(|io| io.io_type.is_output())
    }
}

/// CropsNH crop data: the text lines of NEI's "Crops" page, from the `crop` table the
/// NESQL-Exporter `cropsnh` plugin writes (`/nesqlcrops`, merged with `merge-db`). The seed,
/// soils, sub-soils and drops are the recipe's inputs and outputs.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CropInfo {
    pub crop_id: String,
    pub name: String,
    pub tier: i32,
    /// Growth points needed to reach maturity.
    pub growth_duration: i32,
    /// Multiplier on the number of drops.
    pub drop_chance: f32,
    pub liked_biome_tags: Vec<String>,
    /// Growth requirements other than sub-soil (light, weather, ...).
    pub requirements: Vec<String>,
}

/// Recipe type of the CropsNH crop pages (seed + soils → drops).
pub const CROPS_RECIPE_TYPE: &str = "Crops";
/// Input slot of a `Crops` recipe holding the sub-soil blocks (0 = seed, 1 = soils).
pub const CROP_SUBSOIL_SLOT: i32 = 2;

/// Recipe types (name prefixes) that are NEI displays, not processes a machine runs: each shows
/// a multi-step chain or a structure's parts as one 1-EU, 1-tick recipe, which would hand
/// `eu-cost` free products (e.g. the HTGR page turns 2 silver dust into U-235 for 1 EU).
pub const DISPLAY_ONLY_TYPES: &[&str] = &[
    "High Temperature Gas Reactor", // fuel chain, 2.9+
    "Foundry Module Components",    // casings → module casing, 2.9+
    "Godforge Upgrades",            // module unlocks
];

/// Thaumcraft aspect pseudo-items: Thaumcraft NEI Plugin ids (2.8) or AspectRecipeIndex ids (2.9+).
pub fn is_aspect(goods_id: &str) -> bool {
    goods_id.contains("thaumcraftneiplugin~Aspect") || goods_id.starts_with("i~aspectrecipeindex~aspect~")
}

// ===== Repository =====

pub struct Repository {
    conn: Connection,
    /// SQL expression yielding an item's tooltip as one newline-joined string.
    tooltip_expr: &'static str,
    /// The export carries CropsNH crop data (`crop` table).
    has_crops: bool,
    /// Keyed by output goods_id. Populated lazily in bulk on first access.
    producing_cache: RefCell<HashMap<String, Vec<Recipe>>>,
    producing_cache_loaded: RefCell<bool>,
    od_cache: RefCell<HashMap<String, Vec<String>>>,
}

impl Repository {
    pub fn open(path: &str) -> Result<Self> {
        let conn = Connection::open(path)?;
        conn.execute_batch("PRAGMA query_only=ON;")?;
        // Register a REGEXP function so search queries can use regex matching.
        // Uses get_or_create_aux to cache the compiled Regex per SQLite call site.
        conn.create_scalar_function(
            "regexp",
            2,
            FunctionFlags::SQLITE_UTF8 | FunctionFlags::SQLITE_DETERMINISTIC,
            |ctx| {
                let regexp: std::sync::Arc<Regex> =
                    ctx.get_or_create_aux(0, |vr| -> Result<_, Box<dyn std::error::Error + Send + Sync>> {
                        Ok(Regex::new(vr.as_str()?)?)
                    })?;
                let text = ctx.get_raw(1).as_str()
                    .map_err(|e| SqlError::UserFunctionError(e.into()))?;
                Ok(regexp.is_match(text))
            },
        )?;
        // Exports before NESQL-Exporter 0.5.7 store the tooltip as one `item.tooltip` column;
        // newer ones store one row per line in `item_tooltip`.
        let has_tooltip_column: bool = conn.query_row(
            "SELECT EXISTS (SELECT 1 FROM pragma_table_info('item') WHERE name = 'tooltip')",
            [],
            |r| r.get(0),
        )?;
        let tooltip_expr = if has_tooltip_column {
            "item.tooltip"
        } else {
            "COALESCE((SELECT group_concat(t.tooltip, char(10) ORDER BY t.tooltip_order)
                       FROM item_tooltip t WHERE t.item_id = item.id), '')"
        };
        let has_crops: bool = conn.query_row(
            "SELECT EXISTS (SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'crop')",
            [],
            |r| r.get(0),
        )?;
        Ok(Repository {
            conn,
            tooltip_expr,
            has_crops,
            producing_cache: RefCell::new(HashMap::new()),
            producing_cache_loaded: RefCell::new(false),
            od_cache: RefCell::new(HashMap::new()),
        })
    }

    /// CropsNH data for a "Crops" recipe; `None` for other recipes or exports without crops.
    pub fn crop_info(&self, recipe_id: &str) -> Result<Option<CropInfo>> {
        if !self.has_crops {
            return Ok(None);
        }
        let row = self
            .conn
            .query_row(
                "SELECT id, crop_id, localized_name, tier, growth_duration, drop_chance
                 FROM crop WHERE recipe_id = ?",
                params![recipe_id],
                |r| {
                    Ok((
                        r.get::<_, String>(0)?,
                        r.get::<_, String>(1)?,
                        r.get::<_, Option<String>>(2)?,
                        r.get::<_, i32>(3)?,
                        r.get::<_, i32>(4)?,
                        r.get::<_, f32>(5)?,
                    ))
                },
            )
            .optional()?;
        let Some((id, crop_id, name, tier, growth_duration, drop_chance)) = row else {
            return Ok(None);
        };
        let lines = |table: &str, column: &str| -> Result<Vec<String>> {
            let mut stmt = self.conn.prepare_cached(&format!(
                "SELECT {column} FROM {table} WHERE crop_id = ? ORDER BY {column}_order"
            ))?;
            let rows = stmt
                .query_map(params![id], |r| r.get::<_, Option<String>>(0))?
                .collect::<rusqlite::Result<Vec<_>>>()?;
            Ok(rows.into_iter().flatten().collect())
        };
        Ok(Some(CropInfo {
            name: name.unwrap_or_else(|| crop_id.clone()),
            crop_id,
            tier,
            growth_duration,
            drop_chance,
            liked_biome_tags: lines("crop_liked_biome_tags", "liked_biome_tags")?,
            requirements: lines("crop_requirements", "requirements")?,
        }))
    }

    // --- Private helpers ---

    fn fetch_gt_recipe(&self, recipe_id: &str) -> Result<Option<GtRecipe>> {
        let row = self
            .conn
            .query_row(
                "SELECT gtr.id, gtr.voltage, gtr.duration, gtr.amperage, gtr.voltage_tier,
                    gtr.recipe_special_value
             FROM greg_tech_recipe gtr WHERE gtr.recipe_id = ?",
                params![recipe_id],
                |r| {
                    Ok((
                        r.get::<_, String>(0)?,
                        r.get(1)?,
                        r.get(2)?,
                        r.get(3)?,
                        r.get::<_, String>(4)?,
                        r.get(5)?,
                    ))
                },
            )
            .optional()?;

        let Some((gt_id, voltage, duration_ticks, amperage, voltage_tier, circuit_conflicts)) = row
        else {
            return Ok(None);
        };

        let mut stmt = self.conn.prepare_cached(
            "SELECT metadata_key, metadata_value
             FROM greg_tech_recipe_metadata WHERE greg_tech_recipe_id = ?",
        )?;
        let metadata = stmt
            .query_map(params![gt_id], |r| {
                Ok(GtRecipeMetadata {
                    key: r.get(0)?,
                    value: r.get(1)?,
                })
            })?
            .collect::<rusqlite::Result<Vec<_>>>()?;

        Ok(Some(GtRecipe {
            voltage,
            duration_ticks,
            amperage,
            voltage_tier,
            circuit_conflicts,
            metadata,
        }))
    }

    fn fetch_recipe_io(&self, recipe_id: &str) -> Result<Vec<RecipeIo>> {
        let mut io: Vec<RecipeIo> = Vec::new();

        // Item inputs via item_group
        let mut stmt = self.conn.prepare_cached(
            "SELECT rig.item_inputs_key,
                CASE
                    WHEN od.id IS NOT NULL THEN od.id
                    WHEN COUNT(igs.item_stacks_item_id) > 1 THEN MIN(rig.item_inputs_id)
                    ELSE MIN(igs.item_stacks_item_id)
                END,
                CASE WHEN od.id IS NOT NULL OR COUNT(igs.item_stacks_item_id) > 1 THEN 1 ELSE 0 END,
                MIN(igs.item_stacks_stack_size)
             FROM recipe_item_group rig
             JOIN item_group ig ON ig.id = rig.item_inputs_id
             JOIN item_group_item_stacks igs ON igs.item_group_id = rig.item_inputs_id
             LEFT JOIN ore_dictionary od
                ON od.item_group_id = COALESCE(ig.base_item_group_id, ig.id)
             WHERE rig.recipe_id = ?
             GROUP BY rig.item_inputs_key",
        )?;
        for row in stmt.query_map(params![recipe_id], |r| {
            Ok((
                r.get::<_, i32>(0)?,
                r.get::<_, Option<String>>(1)?,
                r.get::<_, i32>(2)? != 0,
                r.get::<_, i32>(3)?,
            ))
        })? {
            let (slot, goods_id, is_ore_dict, amount) = row?;
            io.push(RecipeIo {
                io_type: if is_ore_dict {
                    RecipeIoType::OreDictInput
                } else {
                    RecipeIoType::ItemInput
                },
                goods_id,
                slot,
                amount,
                probability: 1.0,
            });
        }

        // Fluid inputs
        let mut stmt = self.conn.prepare_cached(
            "SELECT rfg.fluid_inputs_key, fgfs.fluid_stacks_fluid_id, fgfs.fluid_stacks_amount
             FROM recipe_fluid_group rfg
             JOIN fluid_group_fluid_stacks fgfs ON fgfs.fluid_group_id = rfg.fluid_inputs_id
             WHERE rfg.recipe_id = ?",
        )?;
        for row in stmt.query_map(params![recipe_id], |r| {
            Ok((
                r.get::<_, i32>(0)?,
                r.get::<_, Option<String>>(1)?,
                r.get::<_, i32>(2)?,
            ))
        })? {
            let (slot, goods_id, amount) = row?;
            io.push(RecipeIo {
                io_type: RecipeIoType::FluidInput,
                goods_id,
                slot,
                amount,
                probability: 1.0,
            });
        }

        // Item outputs
        let mut stmt = self.conn.prepare_cached(
            "SELECT item_outputs_key, item_outputs_value_item_id,
                    item_outputs_value_stack_size, item_outputs_value_probability
             FROM recipe_item_outputs WHERE recipe_id = ?",
        )?;
        for row in stmt.query_map(params![recipe_id], |r| {
            Ok((
                r.get::<_, i32>(0)?,
                r.get::<_, Option<String>>(1)?,
                r.get::<_, i32>(2)?,
                r.get::<_, f64>(3)?,
            ))
        })? {
            let (slot, goods_id, amount, prob) = row?;
            io.push(RecipeIo {
                io_type: RecipeIoType::ItemOutput,
                goods_id,
                slot,
                amount,
                probability: prob as f32,
            });
        }

        // Fluid outputs
        let mut stmt = self.conn.prepare_cached(
            "SELECT fluid_outputs_key, fluid_outputs_value_fluid_id,
                    fluid_outputs_value_amount, fluid_outputs_value_probability
             FROM recipe_fluid_outputs WHERE recipe_id = ?",
        )?;
        for row in stmt.query_map(params![recipe_id], |r| {
            Ok((
                r.get::<_, i32>(0)?,
                r.get::<_, Option<String>>(1)?,
                r.get::<_, i32>(2)?,
                r.get::<_, f64>(3)?,
            ))
        })? {
            let (slot, goods_id, amount, prob) = row?;
            io.push(RecipeIo {
                io_type: RecipeIoType::FluidOutput,
                goods_id,
                slot,
                amount,
                probability: prob as f32,
            });
        }

        // Inputs first, then outputs; within each group sorted by slot
        io.sort_by_key(|e| (e.io_type.is_output() as u8, e.slot));
        Ok(io)
    }

    fn fetch_recipe(&self, id: &str) -> Result<Option<Recipe>> {
        let row = self
            .conn
            .query_row(
                "SELECT r.id, rt.type FROM recipe r
             LEFT JOIN recipe_type rt ON rt.id = r.recipe_type_id
             WHERE r.id = ?",
                params![id],
                |r| Ok((r.get::<_, String>(0)?, r.get::<_, Option<String>>(1)?)),
            )
            .optional()?;

        let Some((recipe_id, recipe_type_name)) = row else {
            return Ok(None);
        };
        let gt_recipe = self.fetch_gt_recipe(&recipe_id)?;
        let io = self.fetch_recipe_io(&recipe_id)?;
        Ok(Some(Recipe {
            id: recipe_id,
            recipe_type_name,
            gt_recipe,
            io,
        }))
    }

    fn fetch_recipes_by_ids(&self, ids: Vec<String>) -> Result<Vec<Recipe>> {
        if ids.is_empty() {
            return Ok(Vec::new());
        }

        // Build a single IN-clause query for each table rather than 5-6 queries per recipe.
        let placeholders = ids.iter().map(|_| "?").collect::<Vec<_>>().join(", ");
        let params_ref: Vec<&dyn rusqlite::types::ToSql> = ids
            .iter()
            .map(|s| s as &dyn rusqlite::types::ToSql)
            .collect();

        // 1. Base recipe + type
        let mut recipes: std::collections::HashMap<String, Recipe> = {
            let sql = format!(
                "SELECT r.id, rt.type FROM recipe r
                 LEFT JOIN recipe_type rt ON rt.id = r.recipe_type_id
                 WHERE r.id IN ({placeholders})"
            );
            let mut stmt = self.conn.prepare(&sql)?;
            let map: Result<std::collections::HashMap<_, _>> = stmt
                .query_map(params_ref.as_slice(), |r| {
                    Ok((r.get::<_, String>(0)?, r.get::<_, Option<String>>(1)?))
                })?
                .map(|row| {
                    let (id, type_name) = row?;
                    Ok((
                        id.clone(),
                        Recipe {
                            id,
                            recipe_type_name: type_name,
                            gt_recipe: None,
                            io: Vec::new(),
                        },
                    ))
                })
                .collect();
            map?
        };

        // 2. GT recipe data
        let gt_data: std::collections::HashMap<String, (String, i32, i32, i32, String, i32)> = {
            let sql = format!(
                "SELECT gtr.recipe_id, gtr.id, gtr.voltage, gtr.duration,
                        gtr.amperage, gtr.voltage_tier, gtr.recipe_special_value
                 FROM greg_tech_recipe gtr WHERE gtr.recipe_id IN ({placeholders})"
            );
            let mut stmt = self.conn.prepare(&sql)?;
            stmt.query_map(params_ref.as_slice(), |r| {
                Ok((
                    r.get::<_, String>(0)?, // recipe_id (FK)
                    r.get::<_, String>(1)?, // gtr.id (PK, for metadata join)
                    r.get::<_, i32>(2)?,
                    r.get::<_, i32>(3)?,
                    r.get::<_, i32>(4)?,
                    r.get::<_, String>(5)?,
                    r.get::<_, i32>(6)?,
                ))
            })?
            .filter_map(|row| {
                row.ok()
                    .map(|(rid, gtr_id, v, d, a, tier, cc)| (rid, (gtr_id, v, d, a, tier, cc)))
            })
            .collect()
        };

        // 3. GT recipe metadata (joined via gtr.id)
        let mut metadata_map: std::collections::HashMap<String, Vec<GtRecipeMetadata>> =
            std::collections::HashMap::new();
        {
            let sql = format!(
                "SELECT gtr.recipe_id, m.metadata_key, m.metadata_value
                 FROM greg_tech_recipe_metadata m
                 JOIN greg_tech_recipe gtr ON gtr.id = m.greg_tech_recipe_id
                 WHERE gtr.recipe_id IN ({placeholders})"
            );
            let mut stmt = self.conn.prepare(&sql)?;
            for row in stmt.query_map(params_ref.as_slice(), |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, String>(1)?,
                    r.get::<_, i64>(2)?,
                ))
            })? {
                let (recipe_id, key, value) = row?;
                metadata_map
                    .entry(recipe_id)
                    .or_default()
                    .push(GtRecipeMetadata { key, value });
            }
        }

        // Assemble GtRecipe entries
        for (
            recipe_id,
            (gtr_id, voltage, duration_ticks, amperage, voltage_tier, circuit_conflicts),
        ) in gt_data
        {
            let _ = gtr_id; // used only for metadata join
            let metadata = metadata_map.remove(&recipe_id).unwrap_or_default();
            if let Some(r) = recipes.get_mut(&recipe_id) {
                r.gt_recipe = Some(GtRecipe {
                    voltage,
                    duration_ticks,
                    amperage,
                    voltage_tier,
                    circuit_conflicts,
                    metadata,
                });
            }
        }

        // 4. Item inputs
        {
            let sql = format!(
                "SELECT rig.recipe_id, rig.item_inputs_key,
                    CASE
                        WHEN od.id IS NOT NULL THEN od.id
                        WHEN COUNT(igs.item_stacks_item_id) > 1 THEN MIN(rig.item_inputs_id)
                        ELSE MIN(igs.item_stacks_item_id)
                    END,
                    CASE WHEN od.id IS NOT NULL OR COUNT(igs.item_stacks_item_id) > 1 THEN 1 ELSE 0 END,
                    MIN(igs.item_stacks_stack_size)
                 FROM recipe_item_group rig
                 JOIN item_group ig ON ig.id = rig.item_inputs_id
                 JOIN item_group_item_stacks igs ON igs.item_group_id = rig.item_inputs_id
                 LEFT JOIN ore_dictionary od
                    ON od.item_group_id = COALESCE(ig.base_item_group_id, ig.id)
                 WHERE rig.recipe_id IN ({placeholders})
                 GROUP BY rig.recipe_id, rig.item_inputs_key"
            );
            let mut stmt = self.conn.prepare(&sql)?;
            for row in stmt.query_map(params_ref.as_slice(), |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, i32>(1)?,
                    r.get::<_, Option<String>>(2)?,
                    r.get::<_, i32>(3)? != 0,
                    r.get::<_, i32>(4)?,
                ))
            })? {
                let (recipe_id, slot, goods_id, is_ore_dict, amount) = row?;
                if let Some(r) = recipes.get_mut(&recipe_id) {
                    r.io.push(RecipeIo {
                        io_type: if is_ore_dict {
                            RecipeIoType::OreDictInput
                        } else {
                            RecipeIoType::ItemInput
                        },
                        goods_id,
                        slot,
                        amount,
                        probability: 1.0,
                    });
                }
            }
        }

        // 5. Fluid inputs
        {
            let sql = format!(
                "SELECT rfg.recipe_id, rfg.fluid_inputs_key,
                        fgfs.fluid_stacks_fluid_id, fgfs.fluid_stacks_amount
                 FROM recipe_fluid_group rfg
                 JOIN fluid_group_fluid_stacks fgfs ON fgfs.fluid_group_id = rfg.fluid_inputs_id
                 WHERE rfg.recipe_id IN ({placeholders})"
            );
            let mut stmt = self.conn.prepare(&sql)?;
            for row in stmt.query_map(params_ref.as_slice(), |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, i32>(1)?,
                    r.get::<_, Option<String>>(2)?,
                    r.get::<_, i32>(3)?,
                ))
            })? {
                let (recipe_id, slot, goods_id, amount) = row?;
                if let Some(r) = recipes.get_mut(&recipe_id) {
                    r.io.push(RecipeIo {
                        io_type: RecipeIoType::FluidInput,
                        goods_id,
                        slot,
                        amount,
                        probability: 1.0,
                    });
                }
            }
        }

        // 6. Item outputs
        {
            let sql = format!(
                "SELECT recipe_id, item_outputs_key, item_outputs_value_item_id,
                        item_outputs_value_stack_size, item_outputs_value_probability
                 FROM recipe_item_outputs WHERE recipe_id IN ({placeholders})"
            );
            let mut stmt = self.conn.prepare(&sql)?;
            for row in stmt.query_map(params_ref.as_slice(), |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, i32>(1)?,
                    r.get::<_, Option<String>>(2)?,
                    r.get::<_, i32>(3)?,
                    r.get::<_, f64>(4)?,
                ))
            })? {
                let (recipe_id, slot, goods_id, amount, prob) = row?;
                if let Some(r) = recipes.get_mut(&recipe_id) {
                    r.io.push(RecipeIo {
                        io_type: RecipeIoType::ItemOutput,
                        goods_id,
                        slot,
                        amount,
                        probability: prob as f32,
                    });
                }
            }
        }

        // 7. Fluid outputs
        {
            let sql = format!(
                "SELECT recipe_id, fluid_outputs_key, fluid_outputs_value_fluid_id,
                        fluid_outputs_value_amount, fluid_outputs_value_probability
                 FROM recipe_fluid_outputs WHERE recipe_id IN ({placeholders})"
            );
            let mut stmt = self.conn.prepare(&sql)?;
            for row in stmt.query_map(params_ref.as_slice(), |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, i32>(1)?,
                    r.get::<_, Option<String>>(2)?,
                    r.get::<_, i32>(3)?,
                    r.get::<_, f64>(4)?,
                ))
            })? {
                let (recipe_id, slot, goods_id, amount, prob) = row?;
                if let Some(r) = recipes.get_mut(&recipe_id) {
                    r.io.push(RecipeIo {
                        io_type: RecipeIoType::FluidOutput,
                        goods_id,
                        slot,
                        amount,
                        probability: prob as f32,
                    });
                }
            }
        }

        // Sort each recipe's IO: inputs first (by slot), then outputs (by slot)
        for r in recipes.values_mut() {
            r.io.sort_by_key(|e| (e.io_type.is_output() as u8, e.slot));
        }

        // Return in the same order as the input ids
        Ok(ids.iter().filter_map(|id| recipes.remove(id)).collect())
    }

    // --- Public query methods ---

    pub fn get_item(&self, id: &str) -> Result<Option<Item>> {
        let tt = self.tooltip_expr;
        let row = self
            .conn
            .query_row(
                &format!(
                    "SELECT id, localized_name, mod_id, internal_name, {tt},
                        unlocalized_name, nbt, max_stack_size, item_damage
                 FROM item WHERE id = ?"
                ),
                params![id],
                |r| {
                    Ok(Item {
                        id: r.get(0)?,
                        name: nonempty(r.get(1)?),
                        mod_name: nonempty(r.get(2)?),
                        internal_name: nonempty(r.get(3)?),
                        tooltip: nonempty(r.get(4)?),
                        unlocalized_name: nonempty(r.get(5)?),
                        nbt: nonempty(r.get(6)?),
                        stack_size: r.get(7)?,
                        damage: r.get(8)?,
                        container: None,
                    })
                },
            )
            .optional()?;

        let Some(mut item) = row else { return Ok(None) };
        item.container = self
            .conn
            .query_row(
                "SELECT fluid_stack_fluid_id, fluid_stack_amount, empty_container_id
             FROM fluid_container WHERE container_id = ?",
                params![id],
                |r| {
                    Ok(FluidContainerInfo {
                        fluid_id: r.get(0)?,
                        amount: r.get(1)?,
                        empty_item_id: r.get(2)?,
                    })
                },
            )
            .optional()?;
        Ok(Some(item))
    }

    pub fn get_fluid(&self, id: &str) -> Result<Option<Fluid>> {
        self.conn
            .query_row(
                "SELECT id, localized_name, mod_id, internal_name, unlocalized_name, nbt, gaseous
             FROM fluid WHERE id = ?",
                params![id],
                |r| {
                    Ok(Fluid {
                        id: r.get(0)?,
                        name: nonempty(r.get(1)?),
                        mod_name: nonempty(r.get(2)?),
                        internal_name: nonempty(r.get(3)?),
                        unlocalized_name: nonempty(r.get(4)?),
                        nbt: nonempty(r.get(5)?),
                        is_gas: r.get::<_, i32>(6)? != 0,
                    })
                },
            )
            .optional()
            .map_err(Into::into)
    }

    pub fn get_ore_dict(&self, id: &str) -> Result<Option<OreDict>> {
        let row = self
            .conn
            .query_row(
                "SELECT id, name, item_group_id FROM ore_dictionary WHERE id = ?",
                params![id],
                |r| {
                    Ok((
                        r.get::<_, String>(0)?,
                        r.get::<_, String>(1)?,
                        r.get::<_, Option<String>>(2)?,
                    ))
                },
            )
            .optional()?;

        let Some((ore_id, name, ig_id)) = row else {
            return Ok(None);
        };
        let item_ids = if let Some(ig) = ig_id {
            let mut stmt = self.conn.prepare_cached(
                "SELECT item_stacks_item_id FROM item_group_item_stacks
                 WHERE item_group_id = ? AND item_stacks_item_id IS NOT NULL",
            )?;
            stmt.query_map(params![ig], |r| r.get(0))?
                .collect::<rusqlite::Result<Vec<String>>>()?
        } else {
            Vec::new()
        };
        Ok(Some(OreDict {
            id: ore_id,
            name,
            item_ids,
        }))
    }

    pub fn get_recipe(&self, id: &str) -> Result<Option<Recipe>> {
        self.fetch_recipe(id)
    }

    pub fn search_items(
        &self,
        query: &str,
        tooltip: bool,
        limit: Option<usize>,
        regex_mode: bool,
    ) -> Result<Vec<Item>> {
        let lim = limit.map(|n| n as i64).unwrap_or(i64::MAX);
        let tt = self.tooltip_expr;
        let select = format!(
            "SELECT id, localized_name, mod_id, internal_name, {tt},
                    unlocalized_name, nbt, max_stack_size, item_damage
             FROM item"
        );
        let filter = match (regex_mode, tooltip) {
            (true, true) => format!(
                "regexp(?1, lower(localized_name)) OR regexp(?1, lower(id))
                 OR regexp(?1, lower(internal_name)) OR regexp(?1, lower({tt}))"
            ),
            (true, false) => "regexp(?1, lower(localized_name)) OR regexp(?1, lower(id))
                 OR regexp(?1, lower(internal_name))"
                .to_string(),
            (false, true) => format!(
                "lower(localized_name) LIKE ?1 OR lower(id) LIKE ?1
                 OR lower(internal_name) LIKE ?1 OR lower({tt}) LIKE ?1"
            ),
            (false, false) => "lower(localized_name) LIKE ?1 OR lower(id) LIKE ?1
                 OR lower(internal_name) LIKE ?1"
                .to_string(),
        };
        let sql = format!("{select} WHERE {filter} LIMIT ?2");
        let q: String = if regex_mode {
            query.to_lowercase()
        } else {
            format!("%{}%", query.to_lowercase())
        };
        let mut stmt = self.conn.prepare_cached(&sql)?;
        stmt.query_map(params![q, lim], |r| {
            Ok(Item {
                id: r.get(0)?,
                name: nonempty(r.get(1)?),
                mod_name: nonempty(r.get(2)?),
                internal_name: nonempty(r.get(3)?),
                tooltip: nonempty(r.get(4)?),
                unlocalized_name: nonempty(r.get(5)?),
                nbt: nonempty(r.get(6)?),
                stack_size: r.get(7)?,
                damage: r.get(8)?,
                container: None,
            })
        })?
        .collect::<rusqlite::Result<Vec<_>>>()
        .map_err(Into::into)
    }

    pub fn search_fluids(
        &self,
        query: &str,
        _tooltip: bool,
        limit: Option<usize>,
        regex_mode: bool,
    ) -> Result<Vec<Fluid>> {
        let lim = limit.map(|n| n as i64).unwrap_or(i64::MAX);
        let (q, sql) = if regex_mode {
            (
                query.to_lowercase(),
                "SELECT id, localized_name, mod_id, internal_name, unlocalized_name, nbt, gaseous
                 FROM fluid
                 WHERE regexp(?1, lower(localized_name)) OR regexp(?1, lower(id))
                    OR regexp(?1, lower(internal_name))
                 LIMIT ?2",
            )
        } else {
            (
                format!("%{}%", query.to_lowercase()),
                "SELECT id, localized_name, mod_id, internal_name, unlocalized_name, nbt, gaseous
                 FROM fluid
                 WHERE lower(localized_name) LIKE ?1 OR lower(id) LIKE ?1
                    OR lower(internal_name) LIKE ?1
                 LIMIT ?2",
            )
        };
        let mut stmt = self.conn.prepare_cached(sql)?;
        stmt.query_map(params![q, lim], |r| {
            Ok(Fluid {
                id: r.get(0)?,
                name: nonempty(r.get(1)?),
                mod_name: nonempty(r.get(2)?),
                internal_name: nonempty(r.get(3)?),
                unlocalized_name: nonempty(r.get(4)?),
                nbt: nonempty(r.get(5)?),
                is_gas: r.get::<_, i32>(6)? != 0,
            })
        })?
        .collect::<rusqlite::Result<Vec<_>>>()
        .map_err(Into::into)
    }

    /// Preload ALL recipes keyed by the goods_id they produce.
    /// Returns a HashMap<goods_id, Vec<Recipe>>. Fetches the entire recipe table
    /// in ~8 queries, avoiding per-item DB round-trips during uu-cost traversal.
    fn preload_producing_recipes(&self) -> Result<std::collections::HashMap<String, Vec<Recipe>>> {
        // Build recipe structs for every recipe in the DB.
        let mut recipes: std::collections::HashMap<String, Recipe> = {
            let mut stmt = self.conn.prepare(
                "SELECT r.id, rt.type FROM recipe r
                 LEFT JOIN recipe_type rt ON rt.id = r.recipe_type_id",
            )?;
            stmt.query_map([], |r| {
                Ok((r.get::<_, String>(0)?, r.get::<_, Option<String>>(1)?))
            })?
            .filter_map(|row| {
                row.ok().map(|(id, type_name)| {
                    (
                        id.clone(),
                        Recipe {
                            id,
                            recipe_type_name: type_name,
                            gt_recipe: None,
                            io: Vec::new(),
                        },
                    )
                })
            })
            .collect()
        };

        // GT recipe data
        {
            let mut stmt = self.conn.prepare(
                "SELECT gtr.recipe_id, gtr.id, gtr.voltage, gtr.duration,
                        gtr.amperage, gtr.voltage_tier, gtr.recipe_special_value
                 FROM greg_tech_recipe gtr",
            )?;
            let rows: Vec<(String, String, i32, i32, i32, String, i32)> = stmt
                .query_map([], |r| {
                    Ok((
                        r.get::<_, String>(0)?,
                        r.get::<_, String>(1)?,
                        r.get::<_, i32>(2)?,
                        r.get::<_, i32>(3)?,
                        r.get::<_, i32>(4)?,
                        r.get::<_, String>(5)?,
                        r.get::<_, i32>(6)?,
                    ))
                })?
                .filter_map(|r| r.ok())
                .collect();

            // Metadata keyed by gtr.id (PK)
            let mut meta_by_gtr_id: std::collections::HashMap<String, Vec<GtRecipeMetadata>> =
                std::collections::HashMap::new();
            {
                let mut mstmt = self.conn.prepare(
                    "SELECT greg_tech_recipe_id, metadata_key, metadata_value
                     FROM greg_tech_recipe_metadata",
                )?;
                for row in mstmt.query_map([], |r| {
                    Ok((
                        r.get::<_, String>(0)?,
                        r.get::<_, String>(1)?,
                        r.get::<_, i64>(2)?,
                    ))
                })? {
                    if let Ok((gtr_id, key, value)) = row {
                        meta_by_gtr_id
                            .entry(gtr_id)
                            .or_default()
                            .push(GtRecipeMetadata { key, value });
                    }
                }
            }

            for (
                recipe_id,
                gtr_id,
                voltage,
                duration_ticks,
                amperage,
                voltage_tier,
                circuit_conflicts,
            ) in rows
            {
                let metadata = meta_by_gtr_id.remove(&gtr_id).unwrap_or_default();
                if let Some(r) = recipes.get_mut(&recipe_id) {
                    r.gt_recipe = Some(GtRecipe {
                        voltage,
                        duration_ticks,
                        amperage,
                        voltage_tier,
                        circuit_conflicts,
                        metadata,
                    });
                }
            }
        }

        // Item inputs (with ore dict detection)
        {
            let mut stmt = self.conn.prepare(
                "SELECT rig.recipe_id, rig.item_inputs_key,
                    CASE
                        WHEN od.id IS NOT NULL THEN od.id
                        WHEN COUNT(igs.item_stacks_item_id) > 1 THEN MIN(rig.item_inputs_id)
                        ELSE MIN(igs.item_stacks_item_id)
                    END,
                    CASE WHEN od.id IS NOT NULL OR COUNT(igs.item_stacks_item_id) > 1 THEN 1 ELSE 0 END,
                    MIN(igs.item_stacks_stack_size)
                 FROM recipe_item_group rig
                 JOIN item_group ig ON ig.id = rig.item_inputs_id
                 JOIN item_group_item_stacks igs ON igs.item_group_id = rig.item_inputs_id
                 LEFT JOIN ore_dictionary od
                    ON od.item_group_id = COALESCE(ig.base_item_group_id, ig.id)
                 GROUP BY rig.recipe_id, rig.item_inputs_key",
            )?;
            for row in stmt.query_map([], |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, i32>(1)?,
                    r.get::<_, Option<String>>(2)?,
                    r.get::<_, i32>(3)? != 0,
                    r.get::<_, i32>(4)?,
                ))
            })? {
                if let Ok((recipe_id, slot, goods_id, is_ore_dict, amount)) = row {
                    if let Some(r) = recipes.get_mut(&recipe_id) {
                        r.io.push(RecipeIo {
                            io_type: if is_ore_dict {
                                RecipeIoType::OreDictInput
                            } else {
                                RecipeIoType::ItemInput
                            },
                            goods_id,
                            slot,
                            amount,
                            probability: 1.0,
                        });
                    }
                }
            }
        }

        // Fluid inputs
        {
            let mut stmt = self.conn.prepare(
                "SELECT rfg.recipe_id, rfg.fluid_inputs_key,
                        fgfs.fluid_stacks_fluid_id, fgfs.fluid_stacks_amount
                 FROM recipe_fluid_group rfg
                 JOIN fluid_group_fluid_stacks fgfs ON fgfs.fluid_group_id = rfg.fluid_inputs_id",
            )?;
            for row in stmt.query_map([], |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, i32>(1)?,
                    r.get::<_, Option<String>>(2)?,
                    r.get::<_, i32>(3)?,
                ))
            })? {
                if let Ok((recipe_id, slot, goods_id, amount)) = row {
                    if let Some(r) = recipes.get_mut(&recipe_id) {
                        r.io.push(RecipeIo {
                            io_type: RecipeIoType::FluidInput,
                            goods_id,
                            slot,
                            amount,
                            probability: 1.0,
                        });
                    }
                }
            }
        }

        // Item outputs
        {
            let mut stmt = self.conn.prepare(
                "SELECT recipe_id, item_outputs_key, item_outputs_value_item_id,
                        item_outputs_value_stack_size, item_outputs_value_probability
                 FROM recipe_item_outputs",
            )?;
            for row in stmt.query_map([], |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, i32>(1)?,
                    r.get::<_, Option<String>>(2)?,
                    r.get::<_, i32>(3)?,
                    r.get::<_, f64>(4)?,
                ))
            })? {
                if let Ok((recipe_id, slot, goods_id, amount, prob)) = row {
                    if let Some(r) = recipes.get_mut(&recipe_id) {
                        r.io.push(RecipeIo {
                            io_type: RecipeIoType::ItemOutput,
                            goods_id,
                            slot,
                            amount,
                            probability: prob as f32,
                        });
                    }
                }
            }
        }

        // Fluid outputs
        {
            let mut stmt = self.conn.prepare(
                "SELECT recipe_id, fluid_outputs_key, fluid_outputs_value_fluid_id,
                        fluid_outputs_value_amount, fluid_outputs_value_probability
                 FROM recipe_fluid_outputs",
            )?;
            for row in stmt.query_map([], |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, i32>(1)?,
                    r.get::<_, Option<String>>(2)?,
                    r.get::<_, i32>(3)?,
                    r.get::<_, f64>(4)?,
                ))
            })? {
                if let Ok((recipe_id, slot, goods_id, amount, prob)) = row {
                    if let Some(r) = recipes.get_mut(&recipe_id) {
                        r.io.push(RecipeIo {
                            io_type: RecipeIoType::FluidOutput,
                            goods_id,
                            slot,
                            amount,
                            probability: prob as f32,
                        });
                    }
                }
            }
        }

        // Sort IOs and group by producing goods_id
        let mut result: std::collections::HashMap<String, Vec<Recipe>> =
            std::collections::HashMap::new();
        for mut recipe in recipes.into_values() {
            recipe
                .io
                .sort_by_key(|e| (e.io_type.is_output() as u8, e.slot));
            // Collect all output item/fluid IDs
            let output_ids: Vec<String> = recipe
                .outputs()
                .filter_map(|io| io.goods_id.clone())
                .collect();
            for gid in output_ids {
                result.entry(gid).or_default().push(recipe.clone());
            }
        }

        Ok(result)
    }

    /// Bulk-load all producing recipes into the cache in one pass.
    /// Call this before uu-cost traversal to avoid per-item DB queries.
    pub fn preload_recipes_producing(&self) -> Result<()> {
        if *self.producing_cache_loaded.borrow() {
            return Ok(());
        }
        *self.producing_cache.borrow_mut() = self.preload_producing_recipes()?;
        *self.producing_cache_loaded.borrow_mut() = true;
        Ok(())
    }

    pub fn recipes_producing(&self, goods_id: &str) -> Result<Vec<Recipe>> {
        if let Some(cached) = self.producing_cache.borrow().get(goods_id) {
            return Ok(cached.clone());
        }
        let mut stmt = self.conn.prepare_cached(
            "SELECT DISTINCT recipe_id FROM recipe_item_outputs
             WHERE item_outputs_value_item_id = ?
             UNION
             SELECT DISTINCT recipe_id FROM recipe_fluid_outputs
             WHERE fluid_outputs_value_fluid_id = ?",
        )?;
        let ids: Vec<String> = stmt
            .query_map(params![goods_id, goods_id], |r| r.get(0))?
            .collect::<rusqlite::Result<_>>()?;
        let recipes = self.fetch_recipes_by_ids(ids)?;
        self.producing_cache
            .borrow_mut()
            .insert(goods_id.to_string(), recipes.clone());
        Ok(recipes)
    }

    pub fn recipes_consuming(&self, goods_id: &str) -> Result<Vec<Recipe>> {
        let ids: Vec<String> = if goods_id.starts_with("od~") {
            let mut stmt = self.conn.prepare_cached(
                "SELECT DISTINCT rig.recipe_id
                 FROM recipe_item_group rig
                 JOIN item_group ig ON ig.id = rig.item_inputs_id
                 JOIN ore_dictionary od
                    ON od.item_group_id = COALESCE(ig.base_item_group_id, ig.id)
                 WHERE od.id = ?",
            )?;
            stmt.query_map(params![goods_id], |r| r.get(0))?
                .collect::<rusqlite::Result<_>>()?
        } else if goods_id.starts_with("f~") {
            let mut stmt = self.conn.prepare_cached(
                "SELECT DISTINCT recipe_id FROM recipe_fluid_inputs_fluids
                 WHERE fluid_inputs_fluids_id = ?",
            )?;
            stmt.query_map(params![goods_id], |r| r.get(0))?
                .collect::<rusqlite::Result<_>>()?
        } else {
            let mut stmt = self.conn.prepare_cached(
                "SELECT DISTINCT recipe_id FROM recipe_item_inputs_items
                 WHERE item_inputs_items_id = ?",
            )?;
            stmt.query_map(params![goods_id], |r| r.get(0))?
                .collect::<rusqlite::Result<_>>()?
        };
        self.fetch_recipes_by_ids(ids)
    }

    pub fn recipes_by_type(&self, type_name: &str) -> Result<Vec<Recipe>> {
        // Match exact name OR "Name (Tier)" variants (e.g. "Scanner" → "Scanner (LV)")
        let like_pattern = format!("{type_name} (%)");
        let mut stmt = self.conn.prepare_cached(
            "SELECT r.id FROM recipe r
             JOIN recipe_type rt ON rt.id = r.recipe_type_id
             WHERE rt.type = ? OR rt.type LIKE ?",
        )?;
        let ids: Vec<String> = stmt
            .query_map(params![type_name, like_pattern], |r| r.get(0))?
            .collect::<rusqlite::Result<_>>()?;
        self.fetch_recipes_by_ids(ids)
    }

    pub fn name_of(&self, id: &str) -> Result<String> {
        if let Some(n) = self
            .conn
            .query_row(
                "SELECT localized_name FROM item WHERE id = ?",
                params![id],
                |r| r.get::<_, String>(0),
            )
            .optional()?
        {
            if !n.is_empty() {
                return Ok(n);
            }
        }

        if let Some(n) = self
            .conn
            .query_row(
                "SELECT localized_name FROM fluid WHERE id = ?",
                params![id],
                |r| r.get::<_, String>(0),
            )
            .optional()?
        {
            if !n.is_empty() {
                return Ok(n);
            }
        }

        if let Some(n) = self
            .conn
            .query_row(
                "SELECT name FROM ore_dictionary WHERE id = ?",
                params![id],
                |r| r.get::<_, String>(0),
            )
            .optional()?
        {
            return Ok(n);
        }

        Ok(id.to_string())
    }

    pub fn mod_of(&self, id: &str) -> Result<Option<String>> {
        if let Some(m) = self
            .conn
            .query_row("SELECT mod_id FROM item WHERE id = ?", params![id], |r| {
                r.get::<_, String>(0)
            })
            .optional()?
        {
            return Ok(Some(m));
        }

        if let Some(m) = self
            .conn
            .query_row("SELECT mod_id FROM fluid WHERE id = ?", params![id], |r| {
                r.get::<_, String>(0)
            })
            .optional()?
        {
            return Ok(Some(m));
        }

        Ok(None)
    }

    pub fn summary(&self) -> Result<String> {
        let items: i64 = self
            .conn
            .query_row("SELECT COUNT(*) FROM item", [], |r| r.get(0))?;
        let fluids: i64 = self
            .conn
            .query_row("SELECT COUNT(*) FROM fluid", [], |r| r.get(0))?;
        let ods: i64 = self
            .conn
            .query_row("SELECT COUNT(*) FROM ore_dictionary", [], |r| r.get(0))?;
        let rts: i64 = self
            .conn
            .query_row("SELECT COUNT(*) FROM recipe_type", [], |r| r.get(0))?;
        let recipes: i64 = self
            .conn
            .query_row("SELECT COUNT(*) FROM recipe", [], |r| r.get(0))?;
        Ok(format!(
            "items={items} fluids={fluids} ore_dicts={ods} recipe_types={rts} recipes={recipes}"
        ))
    }

    pub fn recipe_types(&self, filter: Option<&str>) -> Result<Vec<RecipeType>> {
        let mut stmt = self
            .conn
            .prepare("SELECT id, type, category, shapeless FROM recipe_type ORDER BY type")?;
        let mut types: Vec<RecipeType> = stmt
            .query_map([], |r| {
                Ok(RecipeType {
                    id: r.get(0)?,
                    name: r.get(1)?,
                    category: r.get(2)?,
                    shapeless: r.get::<_, i32>(3)? != 0,
                })
            })?
            .collect::<rusqlite::Result<_>>()?;

        if let Some(f) = filter {
            let f = f.to_lowercase();
            types.retain(|rt| {
                rt.name.to_lowercase().contains(&f) || rt.category.to_lowercase().contains(&f)
            });
        }
        Ok(types)
    }

    pub fn recipe_count_by_type(&self, type_id: &str) -> Result<usize> {
        let n: i64 = self.conn.query_row(
            "SELECT COUNT(*) FROM recipe WHERE recipe_type_id = ?",
            params![type_id],
            |r| r.get(0),
        )?;
        Ok(n as usize)
    }

    /// Returns the item IDs that satisfy an ore dict input (DB format: `od~name`).
    pub fn ore_dict_item_ids(&self, od_id: &str) -> Result<Vec<String>> {
        if let Some(cached) = self.od_cache.borrow().get(od_id) {
            return Ok(cached.clone());
        }
        let mut members = self.ore_dict_item_ids_uncached(od_id)?;
        members.sort_unstable();
        self.od_cache
            .borrow_mut()
            .insert(od_id.to_string(), members.clone());
        Ok(members)
    }

    fn ore_dict_item_ids_uncached(&self, od_id: &str) -> Result<Vec<String>> {
        // item_group_id itself (starts with "ig~") — multi-item input group with no ore dict
        if od_id.starts_with("ig~") {
            let mut stmt = self.conn.prepare_cached(
                "SELECT item_stacks_item_id FROM item_group_item_stacks
                 WHERE item_group_id = ? AND item_stacks_item_id IS NOT NULL",
            )?;
            return stmt
                .query_map(params![od_id], |r| r.get(0))?
                .collect::<rusqlite::Result<Vec<String>>>()
                .map_err(Into::into);
        }
        let ig_id: Option<String> = self
            .conn
            .query_row(
                "SELECT item_group_id FROM ore_dictionary WHERE id = ?",
                params![od_id],
                |r| r.get(0),
            )
            .optional()?;
        let Some(ig) = ig_id else {
            return Ok(Vec::new());
        };
        let mut stmt = self.conn.prepare_cached(
            "SELECT item_stacks_item_id FROM item_group_item_stacks
             WHERE item_group_id = ? AND item_stacks_item_id IS NOT NULL",
        )?;
        stmt.query_map(params![ig], |r| r.get(0))?
            .collect::<rusqlite::Result<Vec<String>>>()
            .map_err(Into::into)
    }

/// Returns (mob_info_id, item_id, expected_output_per_op) for all EEC-producible
    /// mob drops.  expected_output = probability × stack_size.
    /// Entries with zero expected output are excluded.
    pub fn mob_drop_entries(&self) -> Result<Vec<(String, String, f64)>> {
        let mut stmt = self.conn.prepare(
            "SELECT mob_info_id, drops_item_id,
                    CAST(drops_probability AS REAL) * drops_stack_size
             FROM mob_info_drops
             WHERE drops_item_id IS NOT NULL",
        )?;
        let rows = stmt.query_map([], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, String>(1)?,
                r.get::<_, f64>(2)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let entry = row?;
            if entry.2 > 0.0 {
                out.push(entry);
            }
        }
        Ok(out)
    }

    /// Returns a map of ore item ID → minimum voltage tier (u8) needed to mine it,
    /// for ores that only generate off-world.
    ///
    /// Each vein's primary, secondary, between, and sporadic ores take the lowest
    /// rocket tier among the dimensions the vein generates in (`ore_vein_dimensions`,
    /// from the GT NEI ore plugin data); an ore in several veins takes the lowest
    /// across them. Ores reachable at rocket tier 0 (Overworld, Nether, End,
    /// Twilight) are omitted.
    pub fn ore_mining_tiers(&self) -> Result<HashMap<String, u8>> {
        let mut stmt = self.conn.prepare(
            "SELECT ov.primary_id, ov.secondary_id, ov.between_id, ov.sporadic_id,
                    MIN(d.dimensions_rocket_tier)
             FROM ore_vein ov
             JOIN ore_vein_dimensions d ON d.ore_vein_id = ov.id
             GROUP BY ov.id",
        )?;
        let mut rocket_tiers: HashMap<String, i64> = HashMap::new();
        for row in stmt.query_map([], |r| {
            Ok((
                r.get::<_, Option<String>>(0)?,
                r.get::<_, Option<String>>(1)?,
                r.get::<_, Option<String>>(2)?,
                r.get::<_, Option<String>>(3)?,
                r.get::<_, i64>(4)?,
            ))
        })? {
            let (p, s, b, sp, rocket_tier) = row?;
            for id in [p, s, b, sp].into_iter().flatten() {
                let e = rocket_tiers.entry(id).or_insert(rocket_tier);
                if rocket_tier < *e {
                    *e = rocket_tier;
                }
            }
        }
        Ok(rocket_tiers
            .into_iter()
            .filter(|&(_, rocket_tier)| rocket_tier > 0)
            .map(|(id, rocket_tier)| (id, tier_rank_u8(rocket_tier_voltage(rocket_tier))))
            .collect())
    }

    /// Returns the set of all ore block item IDs found in any ore vein
    /// (overworld, Nether, End, or space).  These are free to obtain by mining
    /// and should be seeded as cost-0 sources in the EU cost graph.
    pub fn all_ore_vein_items(&self) -> Result<Vec<String>> {
        let mut stmt = self.conn.prepare(
            "SELECT primary_id, secondary_id, between_id, sporadic_id FROM ore_vein",
        )?;
        let mut out: Vec<String> = Vec::new();
        for row in stmt.query_map([], |r| {
            Ok((
                r.get::<_, Option<String>>(0)?,
                r.get::<_, Option<String>>(1)?,
                r.get::<_, Option<String>>(2)?,
                r.get::<_, Option<String>>(3)?,
            ))
        })? {
            let (p, s, b, sp) = row?;
            out.extend([p, s, b, sp].into_iter().flatten());
        }
        out.sort_unstable();
        out.dedup();
        Ok(out)
    }
}

// ===== EU cost graph =====

/// Node in the bipartite EU-cost graph.
#[derive(Debug, Serialize, Deserialize)]
pub enum EuGraphNode {
    /// A goods node (item, fluid, or ore dict entry).
    Goods(String),
    /// A recipe node representing "use this recipe to produce `output_goods_id`".
    Recipe {
        id: String,
        output_goods_id: String,
        eu: i64,
        output_amount: f64,
        num_slots: usize,
        recipe_type: String,
        /// GT voltage tier string (e.g. "ULV", "EV"). Empty for non-GT recipes.
        voltage_tier: String,
        /// Additional minimum tier imposed by metadata gates (fusion_threshold,
        /// compression_tier) that the voltage tag alone does not capture.
        /// 0 means no additional constraint.  See [`metadata_tier_min`].
        metadata_tier: u8,
    },
}

/// Edge in the bipartite EU-cost graph.
#[derive(Debug, Serialize, Deserialize)]
pub enum EuGraphEdge {
    /// Goods → Recipe: this goods can satisfy the given input slot with the given amount.
    Input { slot: usize, amount: f64 },
    /// Recipe → Goods: this recipe produces the target goods node.
    Output,
}

/// Bipartite hypergraph of goods and recipes for EU-cost Dijkstra.
#[derive(Serialize, Deserialize)]
pub struct EuGraph {
    pub g: DiGraph<EuGraphNode, EuGraphEdge>,
    /// goods_id → NodeIndex for Goods nodes.
    pub goods_idx: HashMap<String, NodeIndex>,
    /// "recipe_id|output_goods_id" → NodeIndex for Recipe nodes.
    pub recipe_idx: HashMap<String, NodeIndex>,
    /// (recipe_node, slot_idx) → amount needed for that slot.
    pub slot_amounts: HashMap<(NodeIndex, usize), f64>,
    /// Goods nodes that are directly sourceable from infinite resource machines.
    /// Maps NodeIndex → EU cost per unit (0.0 for free sources).
    /// Populated after graph construction by the caller via populate_seed_costs().
    pub seed_costs: HashMap<NodeIndex, f64>,
    /// Minimum voltage tier (as u8) required to mine a space-planet ore block.
    /// Populated by populate_mining_tiers().  Used by run_min_tier_dijkstra to
    /// seed ore items at their planet's rocket tier instead of tier 0.
    pub mining_tiers: HashMap<NodeIndex, u8>,
}

impl Repository {
    /// Build the bipartite EU-cost graph from the preloaded recipe cache.
    ///
    /// Each recipe that produces goods G becomes a Recipe node with:
    ///   - Input edges from each required goods (or each ore-dict member) to the recipe node.
    ///   - One Output edge from the recipe node to G.
    ///
    /// Canning and recycling recipes are excluded.  Ore-dict inputs are expanded
    /// to individual member edges sharing the same logical slot index.
    pub fn build_eu_graph(&self) -> Result<EuGraph> {
        self.preload_recipes_producing()?;

        // Precompute ore-dict siblings for every item in bulk (single query).
        // Maps item_id → all other item_ids sharing at least one ore dict with it.
        // Used below to expand item inputs that have no production recipes.
        let ore_dict_sibling_map: HashMap<String, Vec<String>> = {
            let mut stmt = self.conn.prepare(
                "SELECT igs.item_stacks_item_id, igs2.item_stacks_item_id
                 FROM ore_dictionary od
                 JOIN item_group_item_stacks igs  ON igs.item_group_id  = od.item_group_id
                 JOIN item_group_item_stacks igs2 ON igs2.item_group_id = od.item_group_id
                 WHERE igs.item_stacks_item_id IS NOT NULL
                   AND igs2.item_stacks_item_id IS NOT NULL
                   AND igs2.item_stacks_item_id != igs.item_stacks_item_id",
            )?;
            let mut map: HashMap<String, Vec<String>> = HashMap::new();
            for row in stmt.query_map([], |r| {
                Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?))
            })? {
                if let Ok((item_id, sibling_id)) = row {
                    map.entry(item_id).or_default().push(sibling_id);
                }
            }
            map
        };

        let cache = self.producing_cache.borrow();
        let mut g: DiGraph<EuGraphNode, EuGraphEdge> = DiGraph::new();
        let mut goods_idx: HashMap<String, NodeIndex> = HashMap::new();
        let mut recipe_idx: HashMap<String, NodeIndex> = HashMap::new();
        let mut slot_amounts: HashMap<(NodeIndex, usize), f64> = HashMap::new();

        // Get or create a Goods node, returning its NodeIndex.
        // (inline, not a closure, to avoid borrow-checker conflicts with `g`)
        macro_rules! goods_node {
            ($id:expr) => {{
                let id: &str = $id;
                if !goods_idx.contains_key(id) {
                    let ni = g.add_node(EuGraphNode::Goods(id.to_string()));
                    goods_idx.insert(id.to_string(), ni);
                }
                goods_idx[id]
            }};
        }

        for (output_goods_id, recipes) in cache.iter() {
            for recipe in recipes {
                // Filter recycling / recycle-metadata recipes, and NEI pages that only
                // display a process as one 1-EU recipe (DISPLAY_ONLY_TYPES).
                // Canner and Fluid Canner recipes are legitimate crafting steps;
                // cycles (fluid + cell → fluid cell → fluid) are broken naturally
                // by Dijkstra's settled-node check.
                let type_name = recipe.recipe_type_name.as_deref().unwrap_or("");
                let is_utility = type_name.starts_with("Recycler ")
                    || DISPLAY_ONLY_TYPES.iter().any(|t| type_name.starts_with(t))
                    || recipe.gt_recipe.as_ref().map_or(false, |gt| {
                        gt.metadata
                            .iter()
                            .any(|m| m.key == "recycle" && m.value == 1)
                    });
                if is_utility {
                    continue;
                }

                // Find the specific output IO for this output_goods_id.
                let output_io = recipe
                    .outputs()
                    .find(|io| io.goods_id.as_deref() == Some(output_goods_id.as_str()));
                let Some(output_io) = output_io else { continue };
                if output_io.probability <= 0.0 || output_io.amount <= 0 {
                    continue;
                }

                // For "Bee Products" recipes the queen bee is an infinite source,
                // not a consumed input — treat as zero-input so the recipe fires
                // for free. Planetary Gas Siphon recipes are also genuinely
                // zero-input and must not be skipped here.
                let is_free_source = type_name.starts_with("Bee Products");
                // CropsNH "Crops" recipes: the seed is planted, not spent, and the soil is
                // ordinary ground, so neither is an input. The sub-soil block (slot 2, when
                // the crop needs one) must exist under the crop: it stays an input slot with
                // amount 0, so it gates reachability and the recipe's tier (min-tier /
                // peak tier) without adding EU.
                let is_crop = type_name == CROPS_RECIPE_TYPE;
                let inputs: Vec<&RecipeIo> = if is_free_source {
                    vec![]
                } else if is_crop {
                    recipe
                        .inputs()
                        .filter(|io| io.slot == CROP_SUBSOIL_SLOT && io.goods_id.is_some())
                        .collect()
                } else {
                    recipe
                        .inputs()
                        .filter(|io| {
                            io.goods_id.is_some()
                                && io.amount > 0
                                // Thaumcraft Aspects are free ambient resources — treat
                                // them like bee queens (zero-cost, infinite supply).
                                && !is_aspect(io.goods_id.as_deref().unwrap_or(""))
                        })
                        .collect()
                };
                // Zero-input recipes (PGS, Bee Products, crops without a sub-soil) are
                // valid; they fire at zero input-cost and are handled specially in
                // run_eu_dijkstra.
                // Only skip recipes that had non-zero-amount inputs but all were
                // stripped by the filter (e.g. shapeless table with only NBT inputs).
                // That condition is: inputs was non-empty before filter but empty after.
                // We approximate by skipping only if the recipe truly has no recorded
                // inputs AND it is not one of the known zero-input machine types.
                let recipe_has_any_inputs = recipe.inputs().any(|_| true);
                if inputs.is_empty() && recipe_has_any_inputs && !is_free_source && !is_crop {
                    continue;
                }

                let output_amount = output_io.amount as f64 * output_io.probability as f64;
                let recipe_eu = recipe.gt_recipe.as_ref().map_or(0i64, |gt| gt.eu_total());
                let num_slots = inputs.len();
                let recipe_type = recipe.recipe_type_name.clone().unwrap_or_default();
                let voltage_tier = recipe
                    .gt_recipe
                    .as_ref()
                    .map(|gt| gt.voltage_tier.clone())
                    .unwrap_or_default();
                let metadata_tier = recipe
                    .gt_recipe
                    .as_ref()
                    .map(|gt| metadata_tier_min(gt))
                    .unwrap_or(0);

                // Deduplicate: same (recipe_id, output_goods_id) may appear in multiple
                // cache buckets if the recipe has multiple outputs. Skip duplicates.
                let recipe_key = format!("{}|{}", recipe.id, output_goods_id);
                if recipe_idx.contains_key(&recipe_key) {
                    continue;
                }

                // Add Recipe node.
                let recipe_ni = g.add_node(EuGraphNode::Recipe {
                    id: recipe.id.clone(),
                    output_goods_id: output_goods_id.clone(),
                    eu: recipe_eu,
                    output_amount,
                    num_slots,
                    recipe_type,
                    voltage_tier,
                    metadata_tier,
                });
                recipe_idx.insert(recipe_key, recipe_ni);

                // Add Output edge: Recipe → Goods(output_goods_id).
                let output_ni = goods_node!(output_goods_id.as_str());
                g.add_edge(recipe_ni, output_ni, EuGraphEdge::Output);

                // Add Input edges for each logical slot.
                for (slot_idx, input_io) in inputs.iter().enumerate() {
                    let input_id = input_io.goods_id.as_ref().unwrap();
                    let amount = if is_crop { 0.0 } else { input_io.amount as f64 };
                    slot_amounts.insert((recipe_ni, slot_idx), amount);

                    if input_io.io_type == RecipeIoType::OreDictInput {
                        // Drop the od_cache borrow before borrowing producing_cache.
                        // (ore_dict_item_ids uses od_cache, which is a separate RefCell.)
                        let members = self.ore_dict_item_ids(input_id).unwrap_or_default();
                        for member_id in &members {
                            let member_ni = goods_node!(member_id.as_str());
                            g.add_edge(
                                member_ni,
                                recipe_ni,
                                EuGraphEdge::Input {
                                    slot: slot_idx,
                                    amount,
                                },
                            );
                        }
                    } else {
                        // If this specific item has no production recipes, try expanding
                        // to ore-dict siblings (e.g. IC2 Obsidian Plate → GT Obsidian Plate).
                        // This handles cross-mod equivalents recorded as direct item inputs
                        // instead of ore-dict inputs.
                        let siblings: &[String] =
                            if !cache.contains_key(input_id.as_str()) {
                                ore_dict_sibling_map
                                    .get(input_id.as_str())
                                    .map(Vec::as_slice)
                                    .unwrap_or(&[])
                            } else {
                                &[]
                            };
                        if !siblings.is_empty() {
                            // Add an edge from each sibling (ore-dict expansion).
                            for sibling_id in siblings {
                                let sibling_ni = goods_node!(sibling_id.as_str());
                                g.add_edge(
                                    sibling_ni,
                                    recipe_ni,
                                    EuGraphEdge::Input {
                                        slot: slot_idx,
                                        amount,
                                    },
                                );
                            }
                        } else {
                            let input_ni = goods_node!(input_id.as_str());
                            g.add_edge(
                                input_ni,
                                recipe_ni,
                                EuGraphEdge::Input {
                                    slot: slot_idx,
                                    amount,
                                },
                            );
                        }
                    }
                }
            }
        }

        Ok(EuGraph {
            g,
            goods_idx,
            recipe_idx,
            slot_amounts,
            seed_costs: HashMap::new(),
            mining_tiers: HashMap::new(),
        })
    }
}

fn nonempty(s: String) -> Option<String> {
    if s.is_empty() { None } else { Some(s) }
}

// ===== Database merge =====

/// Copy into `dst` every row of `src` (another NESQL export of the same game, e.g. a
/// `/nesqlcrops` repository) that `dst` lacks, creating the tables only `src` has. NESQL keys
/// rows by content hashes, so a row both hold is identical: tables with a primary key take
/// `INSERT OR IGNORE`, the rest (collection tables) only the rows `dst` doesn't already have.
/// `src`'s export `metadata` row is skipped; its plugin names join `dst`'s. Returns the rows
/// added per table, for tables that gained any.
pub fn merge_db(dst: &str, src: &str) -> Result<Vec<(String, usize)>> {
    let mut conn = Connection::open(dst)?;
    conn.execute("ATTACH DATABASE ?1 AS src", params![src])?;
    let tables: Vec<(String, String)> = conn
        .prepare(
            "SELECT name, sql FROM src.sqlite_master
             WHERE type = 'table' AND name NOT LIKE 'sqlite_%' AND name != 'metadata'
             ORDER BY name",
        )?
        .query_map([], |r| Ok((r.get(0)?, r.get(1)?)))?
        .collect::<rusqlite::Result<_>>()?;

    let tx = conn.transaction()?;
    let mut added = Vec::new();
    for (table, create_sql) in tables {
        let exists: bool = tx.query_row(
            "SELECT EXISTS (SELECT 1 FROM main.sqlite_master WHERE type = 'table' AND name = ?1)",
            params![table],
            |r| r.get(0),
        )?;
        if !exists {
            tx.execute_batch(&create_sql)?;
        }
        // Columns both copies have (identical unless the exporter's schema changed).
        let dst_cols: Vec<(String, bool)> = tx
            .prepare(&format!("SELECT name, pk > 0 FROM main.pragma_table_info('{table}')"))?
            .query_map([], |r| Ok((r.get(0)?, r.get(1)?)))?
            .collect::<rusqlite::Result<_>>()?;
        let src_cols: HashSet<String> = tx
            .prepare(&format!("SELECT name FROM src.pragma_table_info('{table}')"))?
            .query_map([], |r| r.get(0))?
            .collect::<rusqlite::Result<_>>()?;
        let cols: Vec<String> = dst_cols
            .iter()
            .filter(|(c, _)| src_cols.contains(c))
            .map(|(c, _)| format!("\"{c}\""))
            .collect();
        let cols = cols.join(", ");
        let has_pk = dst_cols.iter().any(|(_, pk)| *pk);
        let sql = if has_pk {
            format!("INSERT OR IGNORE INTO main.\"{table}\" ({cols}) SELECT {cols} FROM src.\"{table}\"")
        } else {
            format!(
                "INSERT INTO main.\"{table}\" ({cols})
                 SELECT {cols} FROM src.\"{table}\" EXCEPT SELECT {cols} FROM main.\"{table}\""
            )
        };
        let n = tx.execute(&sql, [])?;
        if n > 0 {
            added.push((table, n));
        }
    }
    tx.commit()?;
    conn.execute("DETACH DATABASE src", [])?;
    Ok(added)
}

// ===== Database builder =====

pub fn build_db(script_path: &str, db_path: &str, on_progress: impl Fn(u64)) -> Result<()> {
    use std::io::{BufRead, BufReader};

    let conn = Connection::open(db_path)?;
    conn.execute_batch(
        "PRAGMA synchronous=OFF; PRAGMA journal_mode=OFF; PRAGMA foreign_keys=OFF;",
    )?;

    let file = std::fs::File::open(script_path)?;
    let reader = BufReader::with_capacity(1 << 20, file);

    let mut line_count = 0u64;
    let mut batch = String::with_capacity(512 * 1024);
    let mut batch_len = 0usize;

    for line in reader.lines() {
        let line = line?;
        line_count += 1;
        if line_count % 100_000 == 0 {
            on_progress(line_count);
        }

        if let Some(sql) = transform_line(&line) {
            batch.push_str(&sql);
            batch.push(';');
            batch.push('\n');
            batch_len += 1;
            if batch_len >= 1000 {
                conn.execute_batch(&batch)?;
                batch.clear();
                batch_len = 0;
            }
        }
    }
    if !batch.is_empty() {
        conn.execute_batch(&batch)?;
    }

    // Additional indexes beyond what HSQLDB defined
    conn.execute_batch(
        "CREATE INDEX IF NOT EXISTS idx_recipe_item_out ON recipe_item_outputs(item_outputs_value_item_id);
         CREATE INDEX IF NOT EXISTS idx_recipe_fluid_out ON recipe_fluid_outputs(fluid_outputs_value_fluid_id);
         CREATE INDEX IF NOT EXISTS idx_gtr_recipe ON greg_tech_recipe(recipe_id);
         CREATE INDEX IF NOT EXISTS idx_gtrm_gtr ON greg_tech_recipe_metadata(greg_tech_recipe_id);
         CREATE INDEX IF NOT EXISTS idx_igs_group ON item_group_item_stacks(item_group_id);
         CREATE INDEX IF NOT EXISTS idx_rig_recipe ON recipe_item_group(recipe_id);
         CREATE INDEX IF NOT EXISTS idx_rfg_recipe ON recipe_fluid_group(recipe_id);
         CREATE INDEX IF NOT EXISTS idx_od_group ON ore_dictionary(item_group_id);",
    )?;

    on_progress(line_count);
    Ok(())
}

fn transform_line(line: &str) -> Option<String> {
    let line = line.trim();
    if line.is_empty() {
        return None;
    }
    // Skip HSQLDB-specific non-SQL statements and internal system rows
    if line.starts_with("SET ")
        || line.starts_with("ALTER USER")
        || line.starts_with("CREATE USER")
        || line.starts_with("CREATE SCHEMA")
        || line.starts_with("GRANT ")
        || line.starts_with("ALTER SEQUENCE")
        || line.starts_with("ALTER TABLE")
        || line.starts_with("INSERT INTO BLOCKS ")
    {
        return None;
    }

    let s = if line.starts_with("CREATE MEMORY TABLE PUBLIC.") {
        line.replacen(
            "CREATE MEMORY TABLE PUBLIC.",
            "CREATE TABLE IF NOT EXISTS ",
            1,
        )
    } else if line.starts_with("CREATE INDEX") {
        line.replacen("CREATE INDEX", "CREATE INDEX IF NOT EXISTS", 1)
            .replace(" ON PUBLIC.", " ON ")
    } else if line.starts_with("INSERT INTO PUBLIC.") {
        line.replacen("INSERT INTO PUBLIC.", "INSERT INTO ", 1)
    } else {
        line.to_string()
    };

    // Strip any remaining PUBLIC. references (e.g. in REFERENCES clauses)
    let s = s.replace("PUBLIC.", "");
    Some(decode_unicode_escapes(&s))
}

fn decode_unicode_escapes(s: &str) -> String {
    if !s.contains("\\u") {
        return s.to_string();
    }
    let b = s.as_bytes();
    let mut out = String::with_capacity(s.len());
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'\\'
            && i + 5 <= b.len()
            && b[i + 1] == b'u'
            && b[i + 2..i + 6].iter().all(|x| x.is_ascii_hexdigit())
        {
            let hex = std::str::from_utf8(&b[i + 2..i + 6]).unwrap();
            if let Some(c) = u32::from_str_radix(hex, 16).ok().and_then(char::from_u32) {
                out.push(c);
                i += 6;
                continue;
            }
        }
        // HSQLDB escapes all non-ASCII as \uXXXX, so remaining bytes are ASCII
        out.push(b[i] as char);
        i += 1;
    }
    out
}
