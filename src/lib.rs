use std::collections::HashMap;

use anyhow::{bail, Result};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};

const DATA_VERSION: i32 = 5;

// ===== Raw binary reader =====

struct RawReader {
    bytes: Vec<u8>,
}

impl RawReader {
    fn new(bytes: Vec<u8>) -> Self {
        Self { bytes }
    }

    /// Read i32 (little-endian) at word offset `n`, i.e. byte offset `n*4`.
    fn i32_at(&self, word_offset: usize) -> i32 {
        let b = word_offset * 4;
        i32::from_le_bytes(
            self.bytes
                .get(b..b + 4)
                .and_then(|s| s.try_into().ok())
                .unwrap_or([0u8; 4]),
        )
    }

    /// Read f64 (little-endian) at word offset `n`, i.e. byte offset `n*4`.
    /// Occupies 8 bytes (2 word slots).
    fn f64_at(&self, word_offset: usize) -> f64 {
        let b = word_offset * 4;
        f64::from_le_bytes(
            self.bytes
                .get(b..b + 8)
                .and_then(|s| s.try_into().ok())
                .unwrap_or([0u8; 8]),
        )
    }

    /// Read a length-prefixed UTF-8 string at word pointer `pointer`.
    ///
    /// Format: `elements[pointer]` = byte length, then bytes follow at
    /// `pointer*4 + 4` (i.e. immediately after the length word).
    fn str_at(&self, pointer: i32) -> Option<String> {
        if pointer <= 0 {
            return None;
        }
        let p = pointer as usize;
        let len = self.i32_at(p) as usize;
        if len == 0 {
            return Some(String::new());
        }
        let begin = p * 4 + 4;
        let end = begin + len;
        if end > self.bytes.len() {
            return None;
        }
        Some(String::from_utf8_lossy(&self.bytes[begin..end]).into_owned())
    }

    /// Read a length-prefixed slice of i32 values at word pointer `pointer`.
    ///
    /// Format: `elements[pointer]` = count, then `count` i32 values follow.
    fn slice_at(&self, pointer: i32) -> Vec<i32> {
        if pointer <= 0 {
            return Vec::new();
        }
        let p = pointer as usize;
        let len = self.i32_at(p) as usize;
        (0..len).map(|i| self.i32_at(p + 1 + i)).collect()
    }

    /// Indirect string: read `elements[base + field]` as a string pointer,
    /// then read the string at that pointer.
    fn str_indirect(&self, base: usize, field: usize) -> Option<String> {
        self.str_at(self.i32_at(base + field))
    }

    /// Indirect slice: read `elements[base + field]` as a slice pointer,
    /// then read the slice at that pointer.
    fn slice_indirect(&self, base: usize, field: usize) -> Vec<i32> {
        self.slice_at(self.i32_at(base + field))
    }

    /// Read the id string of a `SearchableObject` at word pointer `pointer`.
    /// The id is stored at `elements[pointer + 4]` (a string pointer).
    fn id_at(&self, pointer: i32) -> Option<String> {
        if pointer <= 0 {
            return None;
        }
        self.str_indirect(pointer as usize, 4)
    }

    // ===== Object parsers =====

    /// Parse common fields shared by `Item` and `Fluid` (the `Goods` class).
    ///
    /// Returns `(name, mod_name, internal_name, icon_id, tooltip,
    ///           unlocalized_name, nbt, production_ids, consumption_ids)`.
    fn parse_goods_common(
        &self,
        base: usize,
    ) -> (
        Option<String>,
        Option<String>,
        Option<String>,
        i32,
        Option<String>,
        Option<String>,
        Option<String>,
        Vec<String>,
        Vec<String>,
    ) {
        let name = self.str_indirect(base, 5);
        let mod_name = self.str_indirect(base, 6);
        let internal_name = self.str_indirect(base, 7);
        let icon_id = self.i32_at(base + 9);
        let tooltip = self.str_indirect(base, 10);
        let unlocalized_name = self.str_indirect(base, 11);
        let nbt = self.str_indirect(base, 12);
        // production / consumption are slices of recipe pointers; resolve to ids
        let production = self
            .slice_indirect(base, 13)
            .into_iter()
            .filter_map(|p| self.id_at(p))
            .collect();
        let consumption = self
            .slice_indirect(base, 14)
            .into_iter()
            .filter_map(|p| self.id_at(p))
            .collect();
        (
            name,
            mod_name,
            internal_name,
            icon_id,
            tooltip,
            unlocalized_name,
            nbt,
            production,
            consumption,
        )
    }

    fn parse_item(&self, base: usize) -> Item {
        let id = self.str_indirect(base, 4).unwrap_or_default();
        let (name, mod_name, internal_name, icon_id, tooltip, unlocalized_name, nbt, production, consumption) =
            self.parse_goods_common(base);
        let stack_size = self.i32_at(base + 15);
        let damage = self.i32_at(base + 16);
        let container_ptr = self.i32_at(base + 17);
        let container = if container_ptr <= 0 {
            None
        } else {
            let fc = container_ptr as usize;
            let fluid_ptr = self.i32_at(fc);
            let amount = self.i32_at(fc + 1);
            let empty_ptr = self.i32_at(fc + 2);
            Some(FluidContainerInfo {
                fluid_id: self.id_at(fluid_ptr),
                amount,
                empty_item_id: self.id_at(empty_ptr),
            })
        };
        Item {
            id,
            name,
            mod_name,
            internal_name,
            icon_id,
            tooltip,
            unlocalized_name,
            nbt,
            stack_size,
            damage,
            container,
            production_recipe_ids: production,
            consumption_recipe_ids: consumption,
        }
    }

    fn parse_fluid(&self, base: usize) -> Fluid {
        let id = self.str_indirect(base, 4).unwrap_or_default();
        let (name, mod_name, internal_name, icon_id, tooltip, unlocalized_name, nbt, production, consumption) =
            self.parse_goods_common(base);
        let is_gas = self.i32_at(base + 15) == 1;
        Fluid {
            id,
            name,
            mod_name,
            internal_name,
            icon_id,
            tooltip,
            unlocalized_name,
            nbt,
            is_gas,
            production_recipe_ids: production,
            consumption_recipe_ids: consumption,
        }
    }

    fn parse_ore_dict(&self, base: usize) -> OreDict {
        let id = self.str_indirect(base, 4).unwrap_or_default();
        let item_ids = self
            .slice_indirect(base, 5)
            .into_iter()
            .filter_map(|p| self.id_at(p))
            .collect();
        OreDict { id, item_ids }
    }

    fn parse_recipe_type(&self, base: usize) -> RecipeType {
        let name = self.str_indirect(base, 0);
        let category = self.str_indirect(base, 1);
        let dimensions = self.slice_indirect(base, 2);
        let shapeless = self.i32_at(base + 4) == 1;
        let singleblock_item_ids = self
            .slice_indirect(base, 5)
            .into_iter()
            .filter_map(|p| self.id_at(p))
            .collect();
        let multiblock_item_ids = self
            .slice_indirect(base, 3)
            .into_iter()
            .filter_map(|p| self.id_at(p))
            .collect();
        let default_crafter_ptr = self.i32_at(base + 6);
        let default_crafter_id = self.id_at(default_crafter_ptr);
        RecipeType {
            name,
            category,
            dimensions,
            shapeless,
            singleblock_item_ids,
            multiblock_item_ids,
            default_crafter_id,
        }
    }

    fn parse_gt_recipe(&self, base: usize) -> GtRecipe {
        let voltage = self.i32_at(base);
        let duration_ticks = self.i32_at(base + 1);
        let amperage = self.i32_at(base + 2);
        let voltage_tier = self.i32_at(base + 3);
        let circuit_conflicts = self.i32_at(base + 5);
        let special_value = self.i32_at(base + 6);
        let metadata = self
            .slice_indirect(base, 4)
            .into_iter()
            .map(|p| {
                let mb = p as usize;
                GtRecipeMetadata {
                    key: self.str_indirect(mb, 0),
                    value: self.f64_at(mb + 1),
                }
            })
            .collect();
        GtRecipe {
            voltage,
            duration_ticks,
            amperage,
            voltage_tier,
            metadata,
            circuit_conflicts,
            special_value,
        }
    }

    fn parse_recipe(&self, base: usize) -> Recipe {
        let id = self.str_indirect(base, 4).unwrap_or_default();

        // IO items: 5 i32s each — [io_type, goods_ptr, slot, amount, probability*100]
        let io_raw = self.slice_indirect(base, 5);
        let io_count = io_raw.len() / 5;
        let mut io = Vec::with_capacity(io_count);
        for i in 0..io_count {
            let type_raw = io_raw[i * 5];
            let goods_ptr = io_raw[i * 5 + 1];
            let slot = io_raw[i * 5 + 2];
            let amount = io_raw[i * 5 + 3];
            let probability_raw = io_raw[i * 5 + 4];
            io.push(RecipeIo {
                io_type: RecipeIoType::from_i32(type_raw),
                goods_id: self.id_at(goods_ptr),
                slot,
                amount,
                probability: probability_raw as f32 / 100.0,
            });
        }

        let recipe_type_ptr = self.i32_at(base + 6);
        let recipe_type_name = if recipe_type_ptr <= 0 {
            None
        } else {
            self.str_indirect(recipe_type_ptr as usize, 0)
        };

        let gt_recipe_ptr = self.i32_at(base + 7);
        let gt_recipe = if gt_recipe_ptr <= 0 {
            None
        } else {
            Some(self.parse_gt_recipe(gt_recipe_ptr as usize))
        };

        Recipe {
            id,
            recipe_type_name,
            gt_recipe,
            io,
        }
    }
}

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
    pub icon_id: i32,
    pub tooltip: Option<String>,
    pub unlocalized_name: Option<String>,
    pub nbt: Option<String>,
    pub stack_size: i32,
    pub damage: i32,
    pub container: Option<FluidContainerInfo>,
    pub production_recipe_ids: Vec<String>,
    pub consumption_recipe_ids: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Fluid {
    pub id: String,
    pub name: Option<String>,
    pub mod_name: Option<String>,
    pub internal_name: Option<String>,
    pub icon_id: i32,
    pub tooltip: Option<String>,
    pub unlocalized_name: Option<String>,
    pub nbt: Option<String>,
    pub is_gas: bool,
    pub production_recipe_ids: Vec<String>,
    pub consumption_recipe_ids: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OreDict {
    pub id: String,
    pub item_ids: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecipeType {
    pub name: Option<String>,
    pub category: Option<String>,
    pub dimensions: Vec<i32>,
    pub shapeless: bool,
    pub singleblock_item_ids: Vec<String>,
    pub multiblock_item_ids: Vec<String>,
    pub default_crafter_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GtRecipeMetadata {
    pub key: Option<String>,
    pub value: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GtRecipe {
    pub voltage: i32,
    pub duration_ticks: i32,
    pub amperage: i32,
    pub voltage_tier: i32,
    pub circuit_conflicts: i32,
    pub special_value: i32,
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
    Unknown,
}

impl RecipeIoType {
    fn from_i32(v: i32) -> Self {
        match v {
            0 => Self::ItemInput,
            1 => Self::OreDictInput,
            2 => Self::FluidInput,
            3 => Self::ItemOutput,
            4 => Self::FluidOutput,
            _ => Self::Unknown,
        }
    }

    pub fn is_input(self) -> bool {
        matches!(self, Self::ItemInput | Self::OreDictInput | Self::FluidInput)
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
    pub items: Vec<Item>,
    pub fluids: Vec<Fluid>,
    pub ore_dicts: Vec<OreDict>,
    pub recipe_types: Vec<RecipeType>,
    pub recipes: Vec<Recipe>,

    item_by_id: HashMap<String, usize>,
    fluid_by_id: HashMap<String, usize>,
    ore_dict_by_id: HashMap<String, usize>,
    recipe_by_id: HashMap<String, usize>,
}

impl Repository {
    pub fn from_file(path: &str) -> Result<Self> {
        use flate2::read::GzDecoder;
        use std::io::Read;

        let compressed = std::fs::read(path)?;
        let mut decoder = GzDecoder::new(&compressed[..]);
        let mut bytes = Vec::new();
        decoder.read_to_end(&mut bytes)?;
        Self::from_bytes(bytes)
    }

    pub fn from_bytes(bytes: Vec<u8>) -> Result<Self> {
        let r = RawReader::new(bytes);

        let version = r.i32_at(0);
        if version != DATA_VERSION {
            bail!(
                "Unsupported data version: {} (required: {})",
                version,
                DATA_VERSION
            );
        }

        // Header: word offsets 1-7 are pointers to top-level slices
        let item_ptrs = r.slice_at(r.i32_at(1));
        let fluid_ptrs = r.slice_at(r.i32_at(2));
        let ore_dict_ptrs = r.slice_at(r.i32_at(3));
        let recipe_type_ptrs = r.slice_at(r.i32_at(4));
        let recipe_ptrs = r.slice_at(r.i32_at(5));
        // offset 6 = service slice (not used here)
        let remap_ptrs = r.slice_at(r.i32_at(7));

        let items: Vec<Item> = item_ptrs.iter().map(|&p| r.parse_item(p as usize)).collect();
        let fluids: Vec<Fluid> = fluid_ptrs
            .iter()
            .map(|&p| r.parse_fluid(p as usize))
            .collect();
        let ore_dicts: Vec<OreDict> = ore_dict_ptrs
            .iter()
            .map(|&p| r.parse_ore_dict(p as usize))
            .collect();
        let recipe_types: Vec<RecipeType> = recipe_type_ptrs
            .iter()
            .map(|&p| r.parse_recipe_type(p as usize))
            .collect();
        let recipes: Vec<Recipe> = recipe_ptrs
            .iter()
            .map(|&p| r.parse_recipe(p as usize))
            .collect();

        // Primary id → index maps
        let item_by_id: HashMap<String, usize> = items
            .iter()
            .enumerate()
            .map(|(i, x)| (x.id.clone(), i))
            .collect();
        let fluid_by_id: HashMap<String, usize> = fluids
            .iter()
            .enumerate()
            .map(|(i, x)| (x.id.clone(), i))
            .collect();
        let ore_dict_by_id: HashMap<String, usize> = ore_dicts
            .iter()
            .enumerate()
            .map(|(i, x)| (x.id.clone(), i))
            .collect();
        let mut recipe_by_id: HashMap<String, usize> = recipes
            .iter()
            .enumerate()
            .map(|(i, x)| (x.id.clone(), i))
            .collect();

        // Remap: additional aliases — each entry is (id_string_ptr, target_recipe_ptr)
        for &remap_pos in &remap_ptrs {
            let id_str_ptr = r.i32_at(remap_pos as usize);
            let target_ptr = r.i32_at(remap_pos as usize + 1);
            if let Some(id) = r.str_at(id_str_ptr) {
                if let Some(idx) = recipe_ptrs.iter().position(|&p| p == target_ptr) {
                    recipe_by_id.entry(id).or_insert(idx);
                }
            }
        }

        Ok(Repository {
            items,
            fluids,
            ore_dicts,
            recipe_types,
            recipes,
            item_by_id,
            fluid_by_id,
            ore_dict_by_id,
            recipe_by_id,
        })
    }

    // ===== Lookups by id =====

    pub fn get_item(&self, id: &str) -> Option<&Item> {
        self.item_by_id.get(id).map(|&i| &self.items[i])
    }

    pub fn get_fluid(&self, id: &str) -> Option<&Fluid> {
        self.fluid_by_id.get(id).map(|&i| &self.fluids[i])
    }

    pub fn get_ore_dict(&self, id: &str) -> Option<&OreDict> {
        self.ore_dict_by_id.get(id).map(|&i| &self.ore_dicts[i])
    }

    pub fn get_recipe(&self, id: &str) -> Option<&Recipe> {
        self.recipe_by_id.get(id).map(|&i| &self.recipes[i])
    }

    // ===== Search =====

    /// Find items whose name, id, or internal name contains `query` (case-insensitive).
    /// If `tooltip` is true, also searches the tooltip field.
    pub fn search_items<'a>(&'a self, query: &str, tooltip: bool) -> Vec<&'a Item> {
        let q = query.to_lowercase();
        self.items
            .par_iter()
            .filter(|item| {
                item.id.to_lowercase().contains(&q)
                    || item.name.as_deref().is_some_and(|n| n.to_lowercase().contains(&q))
                    || item
                        .internal_name
                        .as_deref()
                        .is_some_and(|n| n.to_lowercase().contains(&q))
                    || (tooltip
                        && item
                            .tooltip
                            .as_deref()
                            .is_some_and(|n| n.to_lowercase().contains(&q)))
            })
            .collect()
    }

    /// Find fluids whose name, id, or internal name contains `query` (case-insensitive).
    /// If `tooltip` is true, also searches the tooltip field.
    pub fn search_fluids<'a>(&'a self, query: &str, tooltip: bool) -> Vec<&'a Fluid> {
        let q = query.to_lowercase();
        self.fluids
            .par_iter()
            .filter(|f| {
                f.id.to_lowercase().contains(&q)
                    || f.name.as_deref().is_some_and(|n| n.to_lowercase().contains(&q))
                    || f.internal_name
                        .as_deref()
                        .is_some_and(|n| n.to_lowercase().contains(&q))
                    || (tooltip
                        && f.tooltip
                            .as_deref()
                            .is_some_and(|n| n.to_lowercase().contains(&q)))
            })
            .collect()
    }

    /// All recipes that output the given item or fluid id.
    pub fn recipes_producing<'a>(&'a self, goods_id: &str) -> Vec<&'a Recipe> {
        self.recipes
            .iter()
            .filter(|r| {
                r.io.iter().any(|io| {
                    io.io_type.is_output() && io.goods_id.as_deref() == Some(goods_id)
                })
            })
            .collect()
    }

    /// All recipes that consume the given item, fluid, or ore dict id as input.
    pub fn recipes_consuming<'a>(&'a self, goods_id: &str) -> Vec<&'a Recipe> {
        self.recipes
            .iter()
            .filter(|r| {
                r.io.iter().any(|io| {
                    io.io_type.is_input() && io.goods_id.as_deref() == Some(goods_id)
                })
            })
            .collect()
    }

    /// All recipes of a given recipe type name.
    pub fn recipes_by_type<'a>(&'a self, type_name: &str) -> Vec<&'a Recipe> {
        self.recipes
            .iter()
            .filter(|r| r.recipe_type_name.as_deref() == Some(type_name))
            .collect()
    }

    /// Resolve any goods id (item / fluid / ore dict) to its human-readable name.
    pub fn name_of<'a>(&'a self, id: &'a str) -> &'a str {
        if let Some(item) = self.get_item(id) {
            return item.name.as_deref().unwrap_or(id);
        }
        if let Some(fluid) = self.get_fluid(id) {
            return fluid.name.as_deref().unwrap_or(id);
        }
        id
    }

    /// Resolve any goods id to its mod name.
    pub fn mod_of<'a>(&'a self, id: &'a str) -> Option<&'a str> {
        if let Some(item) = self.get_item(id) {
            return item.mod_name.as_deref();
        }
        if let Some(fluid) = self.get_fluid(id) {
            return fluid.mod_name.as_deref();
        }
        None
    }

    pub fn summary(&self) -> String {
        format!(
            "items={} fluids={} ore_dicts={} recipe_types={} recipes={}",
            self.items.len(),
            self.fluids.len(),
            self.ore_dicts.len(),
            self.recipe_types.len(),
            self.recipes.len(),
        )
    }
}
