use anyhow::Result;
use rusqlite::{Connection, OptionalExtension, params};
use serde::{Deserialize, Serialize};

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

// ===== Repository =====

pub struct Repository {
    conn: Connection,
}

impl Repository {
    pub fn open(path: &str) -> Result<Self> {
        let conn = Connection::open(path)?;
        conn.execute_batch("PRAGMA query_only=ON;")?;
        Ok(Repository { conn })
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
                CASE WHEN od.id IS NOT NULL THEN od.id ELSE MIN(igs.item_stacks_item_id) END,
                CASE WHEN od.id IS NOT NULL THEN 1 ELSE 0 END,
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
        let mut out = Vec::with_capacity(ids.len());
        for id in ids {
            if let Some(r) = self.fetch_recipe(&id)? {
                out.push(r);
            }
        }
        Ok(out)
    }

    // --- Public query methods ---

    pub fn get_item(&self, id: &str) -> Result<Option<Item>> {
        let row = self
            .conn
            .query_row(
                "SELECT id, localized_name, mod_id, internal_name, tooltip,
                    unlocalized_name, nbt, max_stack_size, item_damage
             FROM item WHERE id = ?",
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
    ) -> Result<Vec<Item>> {
        let q = format!("%{}%", query.to_lowercase());
        let lim = limit.map(|n| n as i64).unwrap_or(i64::MAX);
        let sql = if tooltip {
            "SELECT id, localized_name, mod_id, internal_name, tooltip,
                    unlocalized_name, nbt, max_stack_size, item_damage
             FROM item
             WHERE lower(localized_name) LIKE ?1 OR lower(id) LIKE ?1
                OR lower(internal_name) LIKE ?1 OR lower(tooltip) LIKE ?1
             LIMIT ?2"
        } else {
            "SELECT id, localized_name, mod_id, internal_name, tooltip,
                    unlocalized_name, nbt, max_stack_size, item_damage
             FROM item
             WHERE lower(localized_name) LIKE ?1 OR lower(id) LIKE ?1
                OR lower(internal_name) LIKE ?1
             LIMIT ?2"
        };
        let mut stmt = self.conn.prepare_cached(sql)?;
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
    ) -> Result<Vec<Fluid>> {
        let q = format!("%{}%", query.to_lowercase());
        let lim = limit.map(|n| n as i64).unwrap_or(i64::MAX);
        let mut stmt = self.conn.prepare_cached(
            "SELECT id, localized_name, mod_id, internal_name, unlocalized_name, nbt, gaseous
             FROM fluid
             WHERE lower(localized_name) LIKE ?1 OR lower(id) LIKE ?1
                OR lower(internal_name) LIKE ?1
             LIMIT ?2",
        )?;
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

    pub fn recipes_producing(&self, goods_id: &str) -> Result<Vec<Recipe>> {
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
        self.fetch_recipes_by_ids(ids)
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
        let mut stmt = self.conn.prepare_cached(
            "SELECT r.id FROM recipe r
             JOIN recipe_type rt ON rt.id = r.recipe_type_id
             WHERE rt.type = ?",
        )?;
        let ids: Vec<String> = stmt
            .query_map(params![type_name], |r| r.get(0))?
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
}

fn nonempty(s: String) -> Option<String> {
    if s.is_empty() { None } else { Some(s) }
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
