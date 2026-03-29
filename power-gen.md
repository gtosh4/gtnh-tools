# Power Generation in GTNH

All generator types in the game, grouped by family, with fuel production branches.
`fuel_value` is the energy density metric stored in recipe data; higher = more EU per unit.
Exact EU/t output depends on machine tier, blade/rotor efficiency, and upgrade bonuses.

---

## 1. Combustion / Diesel

### 1a. Single-block Combustion Generator (LV–EV)
Accepts cells and cans. Burns fuel for EU at fixed machine-tier rate. One item at a time.
Four tiers: Basic (LV, 32 EU/t), Advanced (MV, 128 EU/t), Turbo (HV, 512 EU/t), Turbo Supercharging (EV, 2,048 EU/t).

### 1b. Large Combustion Engine (EV)
Multiblock. Uses fluids. Accepts same fuel list as single-block.

### 1c. Extreme Combustion Engine (IV)
Multiblock. Only accepts the three highest-value combustion fuels.
- Default: **10,900 EU/t** at 100% efficiency (requires 8,000 L/h Lubricant)
- Boosted: **32,700 EU/t** at 150% efficiency (add 40 L/s Liquid Oxygen)

### 1d. Universal Chemical Fuel Engine (UCFE) (LuV)
Multiblock. Built from a Large Combustion Engine + Extreme Combustion Engine + LuV Hull.
Accepts **three fuel categories** + Combustion Promoter:

Efficiency formula: `exp(-C / (promoter_L / fuel_L)) × 1.5`, where:
- **C = 0.04** for Combustion (Diesel) and Gas Turbine fuels
- **C = 0.005** for Rocket Fuels — needs far less Combustion Promoter to hit max efficiency
- At maximum promoter ratio: **150% efficiency** regardless of category

Output scales with fuel volume × efficiency per second; cap determined by Dynamo Hatch tier.
Rocket fuels are the tier-appropriate choice at LuV: C=0.005 means near-150% efficiency is cheap to achieve.

**Combustion Fuels (C=0.04):**

| Fuel | fuel_value | Notes |
|------|-----------|-------|
| High Octane Gasoline | 2,500 | Best combustion fuel |
| Jet Fuel A | 2,248 | |
| Jet Fuel No.3 | 1,824 | Extreme Diesel Engine max |
| Ethanol Gasoline | 1,100 | |
| Cetane-Boosted Diesel | 1,000 | |
| Gasoline | 576 | |
| Ether | 537 | |
| Diesel | 480 | |
| Butanol | 400 | |
| Bio Diesel | 320 | |
| Light Fuel | 305 | |
| Ethanol | 192 | |
| Methanol | 84 | |
| Octane | 80 | |
| Sulfuric Light Fuel | 40 | |
| Oil | 16 | |
| Creosote | 8 | |
| Biomass | 8 | |
| Short Mead | 4 | |
| Fish Oil | 2 | Weakest |

**Gas Turbine Fuels (C=0.04):** All 28 Gas Turbine Fuels (see §2b) also work. Top options:

| Fuel | fuel_value | Notes |
|------|-----------|-------|
| Nitrobenzene | 1,600 | Best gas turbine fuel |
| Nefarious Gas | 1,200 | |
| Naquadah Gas | 1,024 | Late game |
| Toluene | 328 | |
| Benzene | 360 | |
| LPG | 320 | |
| Butane | 296 | |
| Phenol | 288 | |
| Butene | 256 | |
| Rocket Fuel (EnderIO) | 250 | |

**Rocket Engine Fuels (C=0.005):** GT++ rocket fuels. Values are ~1,000–5,000× larger than combustion fuels, making them by far the best UCFE fuel despite C=0.005 needing proportionally less promoter.

| Fuel | fuel_value | Rocket Engine tier limit | Notes |
|------|-----------|--------------------------|-------|
| H8N4C2O4 Rocket Fuel | 12,588,000 | all tiers | Best UCFE rocket fuel |
| CN3H7O3 Rocket Fuel | 6,144,000 | up to tier 6 | |
| Dense Hydrazine Fuel Mixture | 3,072,000 | up to tier 4 | |
| Rp-1 Rocket Fuel | 1,536,000 | up to tier 2 | Refined kerosene-based |

**Fuel production branches:**

**Oil refinery track** (main route):
- Crude Oil (Reservoir Hatch or Nether petroleum deposits) → Distillation Tower
  - Light Fuel (305), Naphtha, Refinery Gas, Diesel, Heavy Fuel
- Light Fuel → Chemical Reactor → Gasoline (576)
- Gasoline + additives → Cetane-Boosted Diesel (1000)
- Cetane-Boosted Diesel → further refining → Jet Fuel A/No.3 (2248/1824)
- Jet Fuel A → catalytic cracking → High Octane Gasoline (2500)

**Bio track:**
- Sugar Cane / Sugar Beets (EIG) → Fermentation → Ethanol (192) or Bio Diesel (320)
- Wood → Pyrolysis → Creosote (8) → Wood Gas (gas turbine)
- Manure / Animal Waste → Semifluid gen directly or ferment → Biogas
- Forestry bees → Biomass (8)

**Coal chemistry track:**
- Coal → Coke Oven → Creosote (8), Coal Coke
- Coal → Coal Gas (gas turbine), Coal Tar Oil (semifluid)

---

## 2. Gas Turbines

### 2a. Single-block Gas Turbine (LV–IV)
Five tiers: Basic (LV, 32 EU/t, 95% eff), Advanced (MV, 128 EU/t), Turbo (HV, 512 EU/t), Turbo II (EV, 2,048 EU/t), Turbo III (IV, 8,192 EU/t).

### 2b. Large Gas Turbine (EV)
Multiblock. Requires turbine rotor; efficiency depends on rotor material (up to ~100% with Tungstenate or HSS-S rotors). Accepts all fluids listed.

| Fuel | fuel_value | Notes |
|------|-----------|-------|
| Nitrobenzene | 1,600 | Best GT fuel |
| Nefarious Gas | 1,200 | |
| Naquadah Gas | 1,024 | Late game |
| Ether | 537 | |
| Benzene | 360 | |
| Toluene | 328 | |
| LPG | 320 | |
| Butane | 296 | |
| Phenol | 288 | |
| Butene | 256 | |
| Rocket Fuel | 250 | |
| Propane | 232 | |
| Naphtha | 220 | |
| Butadiene | 206 | |
| Propene | 192 | |
| Ethane | 168 | |
| Refinery Gas | 160 | Direct oil byproduct |
| Ethylene | 128 | |
| Methane | 104 | Easiest infinite source |
| Coal Gas | 96 | Coal chemistry |
| Cyclopentadiene | 70 | |
| Biogas | 40 | Fermentation |
| Sulfuric Naphtha | 40 | |
| Sulfuric Gas | 25 | |
| Wood Gas | 24 | Wood pyrolysis |
| Carbon Monoxide | 24 | |
| Hydrogen | 20 | Electrolysis/cracking |
| Natural Gas | 20 | Planetary Gas Siphon |

**Fuel production branches:**

**Natural Gas / Methane track** (infinite via Planetary Gas Siphon):
- Gas Siphon outputs Natural Gas (20) or Methane (104) depending on planet
- Methane → Steam Cracker → Ethylene (128), Ethane (168), Propene (192), Propane (232)
- Refinery Gas → cracking → Ethane, Ethylene, LPG

**Benzene/Toluene/Nitrobenzene track** (highest value):
- Coal tar → distillation → Benzene (360) + Toluene (328)
- Benzene + Nitric Acid → Nitrobenzene (1600) — best GT fuel
- Phenol from coal tar chemistry → Phenol (288)

**Hydrogen track:**
- Electrolyze Water → Hydrogen (20) [infinite via Reservoir Hatch]
- Also byproduct of most acid production

**Biogas track:**
- EIG fermenter crops or manure → Biogas (40)

---

## 3. Semifluid Generator

Five tiers (LV–IV). Accepts viscous fluid byproducts (1000 mB per event).

| Tier | EU/t | Efficiency |
|------|------|-----------|
| Basic (LV) | 32 | 95% |
| Advanced (MV) | 128 | 90% |
| Turbo (HV) | 512 | 85% |
| Turbo II (EV) | 2,048 | 80% |
| Turbo III (IV) | 8,192 | 75% |

| Fluid | fuel_value/1000mB |
|-------|------------------|
| Nefarious Oil | 572 |
| Heavy Fuel | 360 |
| Glycerol | 328 |
| Naphthenic Acid | 160 |
| Very Heavy Oil | 90 |
| Sulfuric Heavy Fuel | 80 |
| Sulfuric Coal Tar Oil | 64 |
| Heavy Oil / Raw Oil | 60 |
| Creosote Oil | 48 |
| Oil / Light Oil | 40 |
| Coal Tar Oil | 32 |
| Fertile Manure Slurry | 32 |
| Manure Slurry | 24 |
| Biomass | 16 |
| Coal Tar | 16 |
| Raw Animal Waste | 12 |
| Seed Oil / Fish Oil | 4 |

**Sources:** Mostly oil refinery byproducts and animal/bio waste.
Nefarious Oil is a special heavy oil from a specific nether dimension.

---

## 4. Thermal Generator

Single-block. Accepts hot items/cells directly.

| Fuel | fuel_value |
|------|-----------|
| Cryotheum Dust | 62 |
| Pyrotheum Dust | 62 |
| Lava Bucket / 2× Lava Cells | 32 |
| Pahoehoe Lava Cell | 24 |

**Sources:**
- Lava: Thermal Boiler or Nether (infinite via Reservoir Hatch in Nether biome)
- Cryotheum/Pyrotheum: Crafted from Blizz/Blaze powder (Thermal Expansion)

---

## 5. Acid Generator

Single-block (BartWorks). Four tiers. Accepts acid cells (one at a time).

| Tier | EU/t | Efficiency |
|------|------|-----------|
| LV | 32 | 97% |
| MV | 128 | 94% |
| HV | 512 | 91% |
| EV | 2,048 | 88% |

| Acid | fuel_value |
|------|-----------|
| Hydrofluoric Acid | 40 |
| Formic Acid | 40 |
| Phosphoric Acid | 36 |
| Mercury | 32 |
| Hypochlorous Acid | 30 |
| Hydrochloric Acid | 28 |
| Nitric Acid | 24 |
| Sulfuric Acid | 18 |
| Diluted HCl | 14 |
| Acetic Acid | 11 |
| Molten Redstone | 10 |
| Diluted H₂SO₄ | 9 |

**Sources:** Most acids are chemical processing byproducts (sulfuric acid from many ore chains,
HCl from chlorination, HF from fluorite/fluorspar processing).

---

## 6. Plasma Power — Three Routes

Plasma can be converted to EU via three distinct paths. All 127 plasma types work in at
least one route; `fuel_value` from recipe data drives the cell-based routes.

**Plasma sources:**
- Early: Helium Plasma from Fusion Reactor (D+T or D+He3)
- Mid/late: Fusion Reactor element plasmas (many as main or side products)
- Very high tier: Heliothermal Plasma Fabricator (concentrated solar) → Celestial Tungsten
- Byproducts of Transcendent Plasma Mixer processes

---

### 6a. Plasma Generator (single block, cells)

Four tiers. Accepts plasma cells; burns them at rated efficiency.

| Machine | Output tier | Efficiency |
|---------|------------|------------|
| Plasma Generator Mark I | EV (2,048 EU/t) | 50% |
| Plasma Generator Mark II | IV (8,192 EU/t) | 60% |
| Plasma Generator Mark III | LuV (32,768 EU/t) | 70% |
| Plasma Generator Mark IV | ZPM (131,072 EU/t) | 80% |
| Ultimate Pocket Sun | UV (524,288 EU/t) | 90% |

EU output = `fuel_value × efficiency`. Top fuels (127 total):

| Fuel | fuel_value | EU at 80% (MkIV) |
|------|-----------|------------------|
| Celestial Tungsten Plasma | 720,000 | 576,000 |
| Plutonium 239 Plasma | 503,808 | 403,046 |
| Hypogen Plasma | 502,784 | 402,227 |
| Americium Plasma | 501,760 | 401,408 |
| Plutonium 241 Plasma | 497,664 | 398,131 |
| Uranium 238 Plasma | 487,424 | 389,939 |
| Uranium 235 Plasma | 481,280 | 385,024 |
| Thorium Plasma | 471,040 | 376,832 |
| Radon Plasma | 450,560 | 360,448 |
| Bismuth/Lead/Mercury Plasma | ~410–426k | ~328–341k |
| Gold/Platinum/Iridium/Osmium/Tungsten Plasma | ~350–410k | ~280–328k |
| Rare earth plasmas | 50k–380k | varies |

---

### 6b. Large Plasma Turbine (multiblock, fluid)

The **Large Plasma Turbine (LPT)** and **XL Turbo Plasma Turbine (XLPT)** burn plasma
as a fluid directly. Require a turbine rotor placed inside the controller.

XLPT efficiency formula (from tooltip):
```
Efficiency = ((fuel_value / 200,000)^2) / EU_per_turbine
```
Low-grade plasmas (low `fuel_value`) are penalised in high-tier turbines. High-value
plasmas (Celestial Tungsten at 720k) significantly exceed the 200k baseline and achieve
very high efficiency.

XLPT runs as fast as 16 Large Turbines and takes the space of 12.

---

### 6c. Extreme Heat Exchanger → SC Steam → SC Steam Turbine (fluid, cascading)

The **Extreme Heat Exchanger (EHE)** produces two variants of Supercritical Steam depending on input:

**Regular Supercritical Steam** (from non-plasma hot fluids when supplied above the overheating threshold):

| Input | SC Steam / mB input | SH Steam / mB input | Byproduct |
|-------|--------------------:|--------------------:|-----------|
| Lava | 80 | 80 | Pahoehoe Lava |
| Hot Solar Salt | 1,000 | 1,000 | Cold Solar Salt |
| Hot IC2 Coolant | 200 | 200 | IC2 Coolant |

Below the threshold, these inputs produce only SH Steam (Thermal Boiler / sub-threshold EHE mode).
Regular SC Steam is consumed by the **LSCT** or **XLSCT**.

**Dense Supercritical Steam** (from plasma + distilled water — plasma *always* produces Dense SC Steam
regardless of flow rate, no overheating threshold needed):

Regular SC Steam goes into the **LSCT** or **XLSCT** (the SC steam turbines).

Dense SC Steam goes into the **XLST** (regular XL Turbo Steam Turbine, same turbine blades as §8b).
Dense SC is ~1,000× more energy-dense than SH steam per mB, so 1/1000th the SH optimal flow
of Dense SC achieves the same EU/t per turbine. Since the plasma supply fixes the Dense SC flow,
this is always a **steam-limited** setup — pick the highest-efficiency blade (see §8b).

**Dense SC EU/t formula (XLST):**
```
EU/t = Dense_SC_flow_mB_per_t × (efficiency% / 100) × 500
```

Example: 81,000 mB/t Dense SC from UV Fusion CT plasma → Infinity blade (225%): 81,000 × 2.25 × 500 = ~91M EU/t

**Top plasmas for EHE by Dense SC Steam yield per mB of plasma:**

| Plasma | Dense SC Steam / mB | Byproduct |
|--------|--------------------:|-----------|
| Celestial Tungsten | 648.0 | Molten Celestial Tungsten |
| Plutonium 239 | 453.4 | Molten Plutonium |
| Hypogen | 452.5 | Molten Hypogen |
| Americium | 451.6 | Molten Americium |
| Plutonium 241 | 447.9 | Molten Plutonium |
| Uranium 238 | 438.7 | Molten Uranium |
| Uranium 235 | 433.2 | Molten Uranium |
| Thorium | 423.9 | Molten Thorium |
| Radon | 405.5 | — |
| Bismuth | 383.4 | Molten Bismuth |
| Lead | 381.5 | Molten Lead |
| Gold/Platinum/Iridium/Osmium | ~354–361 | Molten [element] |
| Tungsten | 346.3 | Molten Tungsten |
| Most rare earths | 310–345 | Molten [element] |
| Helium | 73.7 | Helium |
| Hydrogen/Deuterium/Tritium | 18–55.3 | — |

The EHE ranking by Dense SC/mB closely mirrors the Plasma Generator's `fuel_value`
ranking, so the best plasmas are the same across all three routes.

---

## 7. Rocket Engines (GT)

Three tiers of multiblock rocket engines + the Rocketdyne F-1A (endgame).

| Machine | Notes |
|---------|-------|
| Basic Rocket Engine | LV–MV tier |
| Advanced Rocket Engine | HV tier |
| Turbo Rocket Engine | EV tier |
| Rocketdyne F-1A Engine | Endgame |

**Fuels** (4 recipe types as "Rocket Engine Fuel"):

| Fuel | Notes |
|------|-------|
| CN3H7O3 Rocket Fuel | |
| Dense Hydrazine Fuel Mixture | |
| H8N4C2O4 Rocket Fuel | |
| Rp-1 Rocket Fuel | RP-1 is refined kerosene |

**Fuel production:**
- Hydrazine from nitrogen chemistry
- Rp-1 from petroleum refining (kerosene fraction)
- Exotic rocket fuels from chemical synthesis chains

---

## 8. Steam Power

### 8a. Large Boiler
Multiblock. Burns fuels to produce steam. Accepts the same fuels as combustion generators
(also solid fuels: coal, charcoal, wood, coke). Steam output scales with fuel_value.

Fuel list overlaps combustion generators (all 55 fuels including solid fuels like coal and charcoal).

### 8b. Steam Turbines
- **Large Steam Turbine (LST)** — holds 1 turbine rotor; HV crafting recipe (HV Machine Hull). Output limited to buffered dynamo hatches.
- **XL Turbo Steam Turbine (XLST)** — 16× an LST; EV Assembler recipe (Incoloy DS). Supports TecTech multi-amp and laser hatches for high-EU/t output.
- **Turbo Steamer** — simple single-block steam conversion (HV, 512 EU/t)

Turbine blade material determines both **optimal flow** and **efficiency**. Two strategies:
- **Flow-unlimited** (you can supply the full optimal flow): pick the highest absolute EU/t → **Chrysotile** dominates
- **Steam-limited** (fixed steam supply): pick the highest efficiency → higher-tier blades return more EU per L

**Turbine blade materials (LST):**

| Material | Opt. Flow (L/t) | EU/t per LST | EU/t per XLST | Efficiency | Blade recipe | Material |
|----------|----------------:|-------------:|--------------:|:-----------:|-------------|---------|
| Nickel-Zinc Ferrite | 150 | 41 | 656 | 55% | MV Forming Press | early ore |
| MAR-Ce-M200 Steel | 7,500 | 3,562 | 56,992 | 96% | LV Forming Press | BW alloy |
| Adamantium Alloy | 9,560 | 5,019 | 80,304 | 105% | LV Forming Press | BW alloy |
| Enriched Naquadah Alloy | 9,000 | 5,175 | 82,800 | 116% | LV Forming Press | BW alloy |
| Precious Metals Alloy | 5,000 | 3,125 | 50,000 | 125% | LV Forming Press | BW alloy |
| Trinium | 6,400 | 4,320 | 69,120 | 135% | MV Forming Press | HV synthesis |
| Alduorite | 9,600 | 3,120 | 49,920 | 65% | MV Forming Press | T3 planet (IV) |
| Awakened Draconium | 2,000 | 1,450 | 23,200 | 145% | MV Forming Press | Draconic Evo. |
| Vulcanite | 64,000 | 24,000 | 384,000 | 75% | MV Forming Press | T4 planet (IV) |
| Infinity Catalyst | 3,200 | 2,480 | 39,680 | 155% | UV Extruder | UV era |
| Duranium | 25,600 | 21,120 | 337,920 | 165% | MV Forming Press | TConstruct alloy |
| Ichorium | 9,600 | 8,400 | 134,400 | 175% | MV Forming Press | Botania Gaia II |
| High Durability Compound Steel | 1,600 | 1,480 | 23,680 | 185% | LV Forming Press | BW alloy |
| Infinity | 12,800 | 14,400 | 230,400 | 225% | UV Extruder | UV era |
| **Chrysotile** | **448,000** | **190,400** | **3,046,400** | 85% | MV Forming Press | T7 planet (UV) |
| Transcendent Metal | 14,500 | 19,937 | 319,000 | 275% | UHV machines | UHV era |
| Metastable Oganesson | 22,176 | 32,709 | 523,000 | 295% | LV Forming Press | endgame fission |
| SpaceTime | 16,000 | 24,400 | 390,400 | 305% | UEV machines | UEV era |
| Shirabon | 32,000 | 50,400 | 806,400 | 315% | LV Forming Press | endgame |

**Key notes:**
- Chrysotile is only on T7 planets (UV era). Alduorite (T3) and Vulcanite (T4) are both IV era.
- Pre-IV best: BW alloys (Enriched Naquadah Alloy 116% / 5,175 EU/t) or Trinium (135% / 4,320 EU/t at HV synthesis).
- At IV, Vulcanite (24,000 EU/t) becomes the best pre-UV option by a wide margin.
- Once UV is reached, Chrysotile (85% efficiency but 448k L/t optimal flow) delivers by far the highest absolute EU/t — 190,400 per LST — beating every higher-efficiency blade because it accepts so much more steam.
- For steam-limited setups, efficiency matters more: Shirabon at 315% converts ~1.58 EU per L; Chrysotile at 85% converts only ~0.43 EU per L.
- Efficiency >100% means the turbine outputs more EU than the "base" steam energy value (2L→1EU). This is not a bug — GT steam turbines can act as EU amplifiers.

### 8c. Thermal Boiler
4 fuels. Burns Pyrotheum/Cryotheum dust or Lava to produce steam.
Useful as a bridge before other power sources.

**Steam production chain:**
```
Fuel → Large Boiler → Superheated Steam → Steam Turbine → EU
```
Efficiency depends heavily on rotor material and boiler size.

---

## 9. Solar Tower

Concentrating solar power track:
```
Solar Tower (heats Solar Salt) → Solar Salt (Hot) → Large Heat Exchanger → Steam → Steam Turbine → EU
```
- Requires sunlight (surface, day cycle)
- Solar Salt (Cold) → Solar Salt (Hot) via Solar Tower
- Hot salt then drives a steam turbine loop
- **Whakawhiti Wera XL** is a related large heat exchanger multiblock

---

## 10. Solar Panels

### 10a. GT Basic Solar Panel
Single-block. Produces EU/t passively in daylight (halved at night/weather).
Very low output per panel; scales by count.

### 10b. Compressed Solar Arrays (miscutils)
Stack multiple solar panels into a single block. Tiers:
- Compressed (8 EU/t, MV recipe), Double-Compressed (64 EU/t, HV recipe), ..., up to much higher tiers
- Fire/Water infused variants (Thaumcraft Crucible): 24-hour uptime regardless of day/night cycle

---

## 11. High Temperature Gas-cooled Reactor (HTGR)

**EU consumer, not a generator.** Multiblock breeder reactor (LuV recipe tier). Consumes 30,720 EU/t to irradiate TRISO pebbles over 72,000 ticks (60 min) per 64 pebbles, producing Burned Out TRISO Balls for reprocessing into fissile material.

| Fuel (input) | Output |
|------|-------|
| TRISO pebble (Thorium) | Burned Out TRISO Ball (Thorium) |
| TRISO pebble (Uranium) | Burned Out TRISO Ball (Uranium) |
| TRISO pebble (Plutonium) | Burned Out TRISO Ball (Plutonium) |

**Role in power chain:** The HTGR is a step in the nuclear fuel cycle (breed/irradiate → reprocess → extract Plutonium/U-233), not a direct power source. Its EU cost must be accounted for in the net energy budget of any reactor chain that uses it.

**TRISO pebble production:**
- Uranium/Thorium ore → enrichment/processing → TRISO pebble
- Plutonium from spent nuclear fuel reprocessing

---

## 12. Liquid Fluoride Thorium Reactor (LFTR)

Multiblock. Molten salt reactor. All three fuels require LFTB (Lithium Tetrafluoroberyllate)
as coolant (200 units per cycle of 2000 ticks).

| Fuel | EU/t output | LFTB consumed |
|------|------------|---------------|
| LFTR Fuel 1 | 8,192 EU/t (EV) | 200 per cycle |
| LFTR Fuel 2 | 32,768 EU/t (LuV) | 200 per cycle |
| LFTR Fuel 3 | 131,072 EU/t (ZPM) | 200 per cycle |

**LFTR fuel production** (via Nuclear Fuel Processing, HV–EV range):
```
LFTR Fuel 1:  U235 (molten) + LiF + BeF2 + ZrF4
LFTR Fuel 2:  LFTR Fuel Base + ZrF4
LFTR Fuel 3:  LFTR Fuel Base + ThF4
```
- LFTR Fuel Base → intermediate precursor produced at EV Centrifuge
- Depleted salts (U Salt, T Salt, TB Salt) are LFTR byproducts; can be reprocessed
- LFTB is synthesized from Lithium and Beryllium fluoride compounds

**LFTR also produces Uranium Hexafluoride** as byproduct → feeds back into fuel processing.

---

## 13. IC2 Vacuum Reactor (Nuclear Fission)

IC2 nuclear reactor built in vacuum-cooled configuration (all-reactor-chamber setup,
no coolant cells). 40 quad fuel rod slots. Output computed by reactor simulation,
not stored in recipe data.

**Fuel rod ladder (EU/t per vacuum reactor):**

| Fuel | EU/t per reactor | First accessible |
|------|-----------------|-----------------|
| Thorium quad rods | 8,720 | Early (ore processing) |
| Uranium quad rods | 43,600 | Early (ore processing) |
| MOX quad rods | 107,979 | MV (Plutonium from irradiated rods) |
| HD Plutonium quad rods | 301,958 | EV (Assembler [EV]) |
| Excited Uranium quad rods | 1,046,400 | IV (Assembler [IV]) |
| The Core (max) | ~4,979,200 | LuV (Assembler [LuV]) |

**The Core:** requires LuV Assembler. Recipe uses 32× Naquadah fuel rods + 192× Long
Tungstensteel Rods + 128× Tiberium Dust. Extremely high output per reactor.

**Fuel production branches:**

**Uranium track:**
- Uranium ore → centrifuge → U-235/U-238 → enrichment → Uranium fuel rods
- Irradiated rods → reprocess → Plutonium

**MOX track:**
- Uranium + Plutonium → MOX fuel fabrication

**HD Plutonium track:**
- Plutonium → HD compression (Assembler [EV]) → High Density Plutonium quad rods

**Excited Uranium track:**
- HD Uranium → Uranium Based Liquid Fuel → Neutron Activator [ULV] (nke_range 5.5M)
  → Excited State liquid fuel → Assembler [IV] → Excited Uranium quad rods
- Alternatively: Fusion Reactor [IV] (threshold 200M) → Excited State liquid fuel

**Naquadah track (The Core):**
- Naquadah ore → processing → Naquadah fuel rods → The Core assembly (LuV Assembler)

**Thorium track:**
- Thorium ore → centrifuge → Thorium fuel rods (lowest output, available earliest)

---

## 14. Naquadah Reactors (Small, MkI–V)

Single-block reactors, one per machine. Each reactor takes one fuel rod at a time.
`fuel_value` = total EU output per rod.

| Machine | Best Fuel | fuel_value |
|---------|-----------|-----------|
| MkI | Enriched Naquadah Bolt | 50,000 |
| MkII | Enriched Naquadah Rod | 250,000 |
| MkIII | Long Enriched Naquadah Rod | 500,000 |
| MkIV | Naquadria Bolt | 250,000 |
| MkV | Naquadria Rod | 1,000,000 |

Also accept Tiberium rods (lower energy density).

**Fuel production:**
- Naquadah ore → Naquadah Bolt/Rod/Long Rod → Enrichment (IV process) → Enriched rods
- Naquadria: processed from extremely unstable Naquadah variants
- Tiberium: synthetic heavy element, produced via dedicated chain

---

## 15. Large Naquadah Reactor (LNR)

Multiblock. Uses liquid fuels consumed over `duration_ticks` per cycle.
`lng_basic_output` in recipe metadata is the **base EU/t** output directly.

**Requirements:** 2,400 L/s Liquid Air (or reactor voids fuel).

### Coolant efficiency multipliers

Optional coolants increase output:

| Coolant | Rate | Efficiency multiplier |
|---------|------|-----------------------|
| IC2 Coolant | 1,000 L/s | 105% (1.05×) |
| Super Coolant | 1,000 L/s | 150% (1.5×) |
| Cryotheum | 1,000 L/s | 275% (2.75×) |
| Tachyon Rich Temporal Fluid | 20 L/s | 500% (5×) |

### Power boosters (excited liquid)

Also increase fuel consumption proportionally:

| Excited liquid | Rate | Power multiplier |
|---------------|------|-----------------|
| Molten Caesium | 180 L/s | 2× |
| Molten Uranium-235 | 180 L/s | 3× |
| Molten Naquadah | 20 L/s | 4× |
| Molten Atomic Separation Catalyst | 20 L/s | 16× |
| Spatially Enlarged Fluid | 20 L/s | 64× |

### Base EU/t by fuel (`lng_basic_output`)

| Fuel | Base EU/t | Cycle duration | First accessible |
|------|-----------|---------------|-----------------|
| Thorium Based Liquid Fuel (Excited) | 2,200 | 500 ticks (25 s) | HV (Mixer [IV] with overclock) |
| Uranium Based Liquid Fuel (Excited) | 12,960 | 100 ticks (5 s) | Early (Neutron Activator [ULV]) |
| Plutonium Based Liquid Fuel (Excited) | 32,400 | 150 ticks (7.5 s) | Early (Neutron Activator [ULV]) |
| Naquadah MkI | 975,000 | 60 ticks (3 s) | ZPM (Fusion Mk II: fusion_threshold 320M > Mk I max ~160M; Mk II controller Assembly Line needs Superdense Europium Plate via HIP [ZPM, compression_tier=1 not tracked by eu-cost]) |
| Naquadah MkII | 2,300,000 | 70 ticks (3.5 s) | UV (LCR [UHV] with overclock) |
| Naquadah MkIII | 9,511,000 | 80 ticks (4 s) | UHV (NFR [UHV], no overclock) |
| Naquadah MkIV | 88,540,000 | 100 ticks (5 s) | UMV (NFR [UMV], no overclock) |
| Naquadah MkV | 399,576,000 | 160 ticks (8 s) | UMV (NFR [UMV], no overclock) |
| Naquadah MkVI | 2,077,795,200 | 240 ticks (12 s) | UXV (NFR [UXV], no overclock) |

Max boosted output (MkVI × 5× coolant × 64× booster): **~664 TU/t**

NFR tooltip: "This machine can run recipes regardless of tier, if given enough energy" — no
overclock benefit applies; recipe voltage tier = required energy hatch tier.

**Early LNR fuels (Excited State) production routes:**
- Thorium excited: base liquid fuel → Multiblock Mixer [IV] with Helium Plasma (accessible at HV via overclock)
- Uranium excited: base liquid fuel → Neutron Activator [ULV] (nke_range 5.5M) — accessible early;
  or Fusion Reactor [IV] (threshold 200M)
- Plutonium excited: base liquid fuel → Neutron Activator [ULV] (nke_range 6.0M) — accessible early;
  or Fusion Reactor [LuV] (threshold 220M)

**Naquadah liquid fuel production chain:**
```
Naquadah ore
  → Light Naquadah Fuel + Heavy Naquadah Fuel   (ore processing)
  → Naquadah Fuel Refinery  →  Naquadah MkIII
  → Naquadah Fuel Refinery (UV+, with exotic inputs)  →  MkIV
  → Naquadah Fuel Refinery (with Radox / Mellion / Creon)  →  MkV
  → Naquadah Fuel Refinery (UMV, with Shirabon / plasma)  →  MkVI
```

**MkIII → MkIV refinement inputs** (one of several recipes):
- Extremely Unstable Naquadah Dust + Nether Star Dust + Awakened Draconium Dust + Orundum + MkIII + Praseodymium (UIV, 8s)
- Or: Extremely Unstable Naquadah + Bedrockium + Awakened Draconium + Hypogen (UIV, 8s)

**MkIV → MkV:**
- Transcendent Metal Dust + Atomic Separation Catalyst + MkIV + Heavy Radox + Mellion + Creon (UMV, 2.5s)
- Or: Infinity Dust + Atomic Separation Catalyst + MkIV + Heavy Radox (UIV, 10s)

**MkV → MkVI:**
- Celestial Tungsten Dust + Tritanium + MkV + Shirabon + Condensed Raw Stellar Plasma (UMV, 3s)
- Or: Astral Titanium + Tritanium + MkV + Shirabon (UMV, 12s, lower yield)

---

## 16. Fusion Reactor

Multiblock. Primarily a production machine but always generates EU as a byproduct of
fusing materials. 65 total fusion recipes.

**Used directly for power (plasma output → Plasma Generator):**

| Reaction | Output | threshold | EU/t consumed |
|----------|--------|-----------|--------------|
| D + T → Helium Plasma | Plasma for gen | 40M | 4,096 EU/t |
| D + He3 → Helium Plasma | Plasma for gen | 60M | 1,920 EU/t |

**Used to activate LNR fuels:**

| Reaction | Output |
|----------|--------|
| Uranium Liquid Fuel + H → Excited Uranium | IV recipe, threshold 200M |
| Plutonium Liquid Fuel + Lutetium → Excited Plutonium | LuV recipe, threshold 220M |

**Material synthesis recipes** (produce plasma/materials as primary outputs):
Produces most of the element plasmas used by the Plasma Generator (Helium, Nitrogen,
Boron, Neon, Sulfur, Zinc, Niobium, Tin, Silver, Bismuth, etc.) as well as exotic
metals (Tungsten, Iridium, Indium, Platinum, Europium, Duranium, Chrome, Iron, Magnesium, etc.)

---

## 17. RTG (Radioisotope Thermoelectric Generator)

Single-block passive generator. Placed in world, no fuel feeding required. Output degrades
over time as isotope decays.

| Fuel | EU/t | Lifetime |
|------|------|----------|
| ²¹⁰Po Pellet | 480 EU/t | 1 day |
| ²³⁸Pu Pellet | 64 EU/t | 87 days |
| ²⁴⁹Am Pellet | 16 EU/t | 216 days |
| ⁹⁰Sr Pellet | 30 EU/t | 29 days |
| RTG Fuel Pellets | 8 EU/t | 2 days |

**Sources:** Radioactive isotopes from nuclear fuel reprocessing and transmutation chains.
Polonium-210 has highest EU/t but shortest lifetime; best for burst or temporary power.
Americium-249 has longest lifetime.

---

## 18. Magic Energy Absorber / Converter

### 18a. Magic Energy Absorber
Four tiers (Novice LV → Grandmaster EV). "Feasts on magic" in the environment.

| Machine | EU/t | Efficiency | Range (default/max) |
|---------|------|-----------|-------------------|
| Novice | 32 (LV) | 90% | 2 / 8 |
| Adept | 128 (MV) | 80% | 4 / 16 |
| Master | 512 (HV) | 70% | 8 / 32 |
| Grandmaster | 2,048 (EV) | 60% | 16 / 64 |

**Sources absorbed in range:**
- Dragon Egg placed on top: permanent, never consumed; hard cap **2,048 EU/t** per Grandmaster
- Ender Crystals: 512 EU per crystal in range
- Energised Node (Thaumcraft): 13/28/60/131 CV/t depending on tier
- Essentia containers: 288/256/224/192 EU per Essentia Aspect-Value
- Enchanted items fed as input: 6,000–10,000 EU per enchant weight × level/max

Scales by number of machines (each needs its own Dragon Egg).

### 18b. Magic Energy Converter
Three tiers (Novice LV → Master HV). Burns consumable magical items (not ambient).

| Machine | EU/t | Efficiency |
|---------|------|-----------|
| Novice | 32 (LV) | 95% |
| Adept | 128 (MV) | 90% |
| Master | 512 (HV) | 85% |

**Top fuels (fuel_value × efficiency = EU per item):**

| Item | fuel_value | EU at 85% (Master) |
|------|-----------|-------------------|
| Infinity Ingot/Plate/Dust | 5,000,000 | 4,250,000 |
| Infinity Catalyst Ingot/Plate | 500,000 | 425,000 |
| Ichorium Ingot/Plate | 250,000 | 212,500 |
| Nether Star | 100,000 | 85,000 |
| Beacon | 100,000 | 85,000 |

Items are consumed per use. Suitable for emergency power or burning surplus exotic materials.

---

## 19. Lightning Rods (GT)

### How it works

The controller block sits on the ground. **Iron Fence blocks placed directly above it**
form the lightning rod. Every 256 ticks the machine checks for a strike using:

```
P(strike) = aRodValue × (aY + aRodValue) / (4 × worldHeight)
           = aRodValue × (aY + aRodValue) / 1024
```

where `aRodValue` = number of consecutive iron fence blocks above the controller,
`aY` = Y coordinate of the controller, worldHeight = 256.

**Strike guaranteed** (probability ≥ 1) when `aRodValue × (aY + aRodValue) ≥ 1024`.

Minimum fences for guaranteed strike at common Y levels:

| Controller Y | Min fences needed | Top of rod reaches |
|-------------|------------------|--------------------|
| Y = 64 | 14 | Y = 78 |
| Y = 128 | 8 | Y = 136 |
| Y = 200 | 5 | Y = 205 |

On each strike: buffer is **filled to 50M EU**. During thunder, one random fence block is
also **destroyed** — requiring periodic maintenance or an auto-placer setup.

### Buffer discharge

The buffer drains two ways each tick:
1. **Decay (waste):** `storedEU / 100 + 1` EU/t is lost regardless of load.
2. **Cable output:** up to `V[tier] × 512A` EU/t drawn by connected machines.

To minimise waste, connect machines that can absorb the full rated output.

### Machines

| Machine | Output voltage | Max cable output | Build cost |
|---------|---------------|-----------------|------------|
| Lightning Rod | HV (512 EU/t) | 262,144 EU/t (512A) | LuV Hull + 4× Elite Battery + 4× Ludicrous Transformer |
| Lightning Rod II | EV (2,048 EU/t) | 1,048,576 EU/t (512A) | ZPM Hull + 4× Master Battery + 4× ZPM Transformer |
| Lightning Rod III | IV (8,192 EU/t) | 4,194,304 EU/t (512A) | UV Hull + 4× Ultimate Battery + 4× Ultimate Transformer |

The **build tier** (LuV/ZPM/UV hull) is far above the **output tier** (HV/EV/IV).

### Average sustainable EU/t (always thundering, guaranteed strikes, max load)

With a strike every 256 ticks (12.8 s) filling the 50M EU buffer, and machines drawing
at full rated amperage, the buffer empties in:

| Rod | Time to drain buffer | EU delivered | EU lost to decay | Avg EU/t |
|-----|---------------------|-------------|-----------------|----------|
| Rod I (HV) | ~107 ticks | 27.8M / 50M | 22.2M (44%) | ~109,000 EU/t |
| Rod II (EV) | ~39 ticks | 40.7M / 50M | 9.3M (19%) | ~159,000 EU/t |
| Rod III (IV) | ~12 ticks | 47.0M / 50M | 3.0M (6%) | ~184,000 EU/t |
| (ideal, no decay) | — | 50.0M / 50M | 0 | ~195,000 EU/t |

All three rods drain their buffer well before the next strike. The **limiting factor is
always strike cadence** (256 ticks), not output rate. The tier differences only affect
how much EU is wasted to the decay term `storedEU/100 + 1` during the drain window —
Rod III loses 6% vs Rod I's 44%. The voltage tier (HV/EV/IV) determines what machines
you can feed directly without transformers, not how much total EU you produce.

**Implication:** for raw EU/t, spam Rod I. One Rod III costs 22× more than one Rod I
(6.73G vs 301M EU) but delivers only 1.7× more average output. 22 Rod I's at the same
cost yield ~2.4M EU/t vs 184k EU/t for one Rod III.

**Practical notes:**
- Always-thundering requires a weather control setup (e.g. Weather Obelisk, commands).
- Each thunder strike destroys one fence — build an auto-placer (Block Placer or similar)
  to replenish the rod, otherwise output degrades within seconds.
- If the rod degrades below the guaranteed-strike threshold, strikes become probabilistic
  and average output drops accordingly.

---

## 20. IC2 Kinetic System

**Conversion ratio: 4 KU = 1 EU.**

IC2's kinetic (KU) pipeline — machines generate rotational energy which flows through
gearboxes to an Electric Kinetic Generator that converts KU → EU.

### KU → EU Conversion
- **Electric Kinetic Generator** (IC2): placed directly behind a KU producer, outputs `KU / 4` EU/t

### KU Infrastructure
- **Kinetic Gearbox** (IC2): routes KU between producers and consumers via shafts
- **Primitive Kinetic Shaftbox** (BartWorks): early-game wooden gearbox (wood planks + iron rings + iron gear)

### Kinetic Wind Generator

KU/t = MCW × Rotor Efficiency. Wind strength peaks at **Y = 160**, drops to zero at Y = 64
and Y = 255.

**Wind formula:** `EU/t = (MCW × Efficiency) / 4`

Example: Energetic Alloy rotor at 55.08 MCW → (55.08 × 44.75) / 4 = **615.5 EU/t**

| Rotor | Min MCW | Max MCW | Efficiency (KU/MCW) | Size | Durability |
|-------|---------|---------|---------------------|------|------------|
| Wood | 10 | 60 | 12.5 | 5×5 | 10,800 (0.125 days) |
| Iron | 14 | 75 | 25 | 7×7 | 86,400 (1 day) |
| Steel | 17 | 90 | 37.25 | 9×9 | 172,800 (2 days) |
| Energetic Alloy | 12 | 80 | 44.75 | 9×9 | 512,000 (~6 days) |
| Carbon | 20 | 110 | 50 | 11×11 | 604,800 (7 days) |
| Tungstensteel | 14 | 120 | 50 | 11×11 | 809,600 (~9 days) |
| Vibrant Alloy | 16 | 160 | 60 | 13×13 | 1,600,000 (~18 days) |
| Iridium (GT++) | 18 | 320 | 75 | 15×15 | Unbreakable |

At max wind (Iridium rotor, 320 MCW): `(320 × 75) / 4 = 6,000 EU/t`

Each wind generator requires a **21×21×161 clear box** (no other kinetic generators inside).

### Kinetic Water Generator / Kinetic Steam Generator / Stirling / Manual

Wiki lacks per-machine KU output tables for these. All convert to EU at 4 KU = 1 EU.
Water generator depends on flowing water blocks adjacent; steam generator consumes steam
like a turbine; Stirling burns solid fuel.

### Compact Kinetic Generators (`compactkineticgenerators` mod)

All-in-one blocks combining KU generation and conversion. Each tier multiplies the base
IC2 output by **4× per tier step**:

| Tier | Multiplier vs. base IC2 | Hull | Wind / Water / Kinetic variants |
|------|------------------------|------|---------------------------------|
| Low (base IC2 × 4) | 4× | EV | Low KWG / Low KWG (water) / Low KG |
| Medium | 16× | IV | Medium KWG / Medium KWG (water) / Medium KG |
| High | 64× | LuV | High KWG / High KWG (water) / High KG |
| Extreme | 256× | ZPM | Extreme KWG / Extreme KWG (water) / Extreme KG |

The third family ("Kinetic Generator") uses the IC2 `Kinetic Generator` (HV hull, HV motors,
stainless steel rotors) as its base — a distinct machine from the wind/water/steam variants.

---

## 21. Antimatter Power Generation

Two paired multiblocks: the **SSASS** produces Semi-Stable Antimatter from protomatter;
the **SLAM** burns that antimatter against a matter catalyst to generate EU.
Both cycle every 1 second (20 ticks). Accessible at UIV (casings/hatches) with UMV
required to fully build the SLAM and SSASS via Assemblyline.

---

### SLAM — Shielded Lagrangian Annihilation Matrix (Generator)

Reacts equal volumes of **Semi-Stable Antimatter** and **Matter** (fluid catalyst).
Consumes all input fluid each cycle; voids any invalid fluid.

**EU/cycle formula:**
```
EU/cycle = Efficiency × 1e12 × Antimatter_L ^ E
```
- **Efficiency** = `min(Antimatter_L / Matter_L, Matter_L / Antimatter_L)` — must be
  equal volumes for efficiency = 1.0; any mismatch cuts output
- **E** (exponent) from matter catalyst:

| Matter catalyst | E |
|----------------|---|
| Molten Copper | 1.00 |
| Molten Superconductor Base UIV | 1.02 |
| Molten Superconductor Base UMV | 1.03 |

E > 1 means output scales **super-linearly** — doubling antimatter more than doubles EU.
Output is capped at `9.22e18` EU/cycle (Long.MAX_VALUE); excess is voided.

**EU/t** = EU/cycle ÷ 20.

Wireless energy output is available with a screwdriver toggle, requiring UMV
Superconductor Base as the matter catalyst.

---

### SSASS — Semi-Stable Antimatter Stabilization Sequencer (Fuel Producer)

Converts protomatter → Semi-Stable Antimatter. 16 Antimatter Hatches store the output.
**Critical:** each cycle the minimum amount across all 16 hatches is found, and every
hatch above that minimum loses half the excess — uneven automation wastes antimatter.
If it runs out of energy or protomatter mid-cycle, **10% of all antimatter is voided**.

**Energy costs (N = total antimatter stored, L):**

| Cost | Formula |
|------|---------|
| Passive (EU/t, every tick) | `10,000,000 + (N × 1000)^(1.5 − M)` |
| Active (EU per 20-tick cycle) | `(N × 10,000)^(1.5 − G)` |

Passive cost decays 0.5%/tick when the machine is idle/empty.

**Antimatter production per cycle:**
```
Per hatch: (1/16) × N^(0.5 + C) × Normal(mean = 0.2 + A, variance = 1)
```
Each hatch draws independently from the normal distribution — the total can be
**negative** (antimatter decreases), especially at low stored amounts or without
Activation stabilization. The system is self-reinforcing once it has enough stored.

**Stabilization fluids** (four independent channels, one fluid active per channel):

| Channel | Modifier | Effect | Fluids (value) |
|---------|----------|--------|----------------|
| **M** agnetic | reduces passive exponent | `1.5 − M` | Molten Purified Tengam (0.1), Tachyon Rich Fluid (0.2), Molten MagMatter (0.3) |
| **G** ravity | reduces active exponent | `1.5 − G` | Molten Spacetime (0.05), Spatially Enlarged Fluid (0.10), Molten Eternity (0.15) |
| **C** ontainment | increases production exponent | `0.5 + C` | Molten Shirabon (0.05), Molten MHDCSM (0.10) |
| **A** ctivation | shifts production mean upward | `0.2 + A` | Depleted Naquadah Fuel Mk V (0.05), Depleted Naquadah Fuel Mk VI (0.10) |

Each stabilization fluid is consumed at `N^x` L/cycle (x varies by channel; see tooltip).

---

### Antimatter Production (bootstrapping)

The SSASS needs an initial antimatter seed to start. External source:
- **UIV Laser Engraver** (cleanroom): 1× Superdense Hot Protohalkonite plate + 100×
  Protomatter → 1 L Semi-Stable Antimatter per run (UIV tier, ~167 min/run). Slow but
  the only recipe-system route.

Once seeded, the SSASS is self-sustaining if kept powered and stabilized.

---

## 22. Dyson Swarm

A space-based solar collector. The **Dyson Swarm Ground Unit** (UIV multiblock) launches
**Dyson Swarm Modules** into orbit around the nearest star. Each module generates EU
passively while in orbit. Modules are slowly consumed by the star over time.

### Output

```
EU/t = 10,000,000 × D × (number of modules in orbit)
```

- **D** = dimension-dependent factor (varies by star; check the quest book for values)
- Max modules: **10,000** → max output = **100,000,000,000 × D EU/t** (100G×D)
- Requires **3,600,000 L/h** (50 L/t) of Gelid Cryotheum as coolant

### Module destruction

Each hour, the following number of modules are destroyed by the star:

```
Destroyed/hour = I × 0.132 / (exp(−0.00005 × (I − 1)) + exp(0.00003 × C))
```

where **I** = current module count, **C** = Computation/s fed to the machine.

At max modules (I = 10,000) with no computation (C = 0):
- ≈ **821 modules/hour** destroyed

At I = 10,000 with C = 100,000 computation/s:
- ≈ **64 modules/hour** destroyed (exp(0.00003×C) dominates denominator)

High enough C makes destruction approach zero. Computation is therefore the key
variable for making the Dyson Swarm low-maintenance.

### Module production cost

Each UHV Assemblyline run (5 s, ~197M EU) produces **64 modules**.
To sustain 10,000 modules at C = 0 requires replenishing ~821/hour ≈ **13 runs/hour**
(one run every ~4.6 min). With C = 100,000 this drops to ~1 run/hour.

### Build tiers

| Component | Build tier |
|-----------|-----------|
| Dyson Swarm Ground Unit (controller) | UIV Assemblyline |
| Dyson Swarm Module | UHV Assemblyline (64/run) |
| Energy Receiver Dish Block (casing) | UEV Assemblyline |
| Other casings/windings | UEV or lower |

Modules can be recovered by right-clicking the controller with a Plunger (sneak to dump
remainder on ground).

---

## 23. GT++ Geothermal Engines

Single-block (GT++). Three tiers, all burning Pahoehoe Lava or Normal Lava. 100 pollution/s each.

| Machine | EU/t | Efficiency | Build tier |
|---------|------|-----------|-----------|
| Basic Geothermal Engine | 2,048 | 72% | EV |
| Turbo Geothermal Engine | 8,192 | 65% | IV |
| Vulcan Geothermal Engine | 32,768 | 58% | LuV |

**Fuel:** Lava from any source (Reservoir Hatch, Nether, Endstone processing). Pahoehoe Lava is a
higher-density variant found in the Nether.

---

## 24. Deep Earth Heating Pump (DEHP)

**Machine type:** Geothermal Heat Pump multiblock (BartWorks / `tooltip.bw.mb_via`)
`i:gregtech:gt.blockmachines:12729`

Converts geothermal heat into Superheated Steam or Hot Coolant. Two modes toggled with a Screwdriver. Consumes **480 EU/t**; cycle time 1 tick. Each maintenance issue reduces output by 10%. **Explodes** if its working fluid (Distilled Water or Coolant) runs dry.

**Build cost:** 2.41G EU [UV regular path] · min-tier **IV** (8.32T EU via all-IV ingredient paths)
**Recipe:** IV Assembler — 1× Fluid Drilling Rig IV + 4,608× Molten HSS-E + 8× Large Ultimate Pipe + 32× Incoloy-903 Gear + 16× Dense PTFE Plate + 1× Field Generator IV

### Direct Steam Mode

Consumes Distilled Water (free from Reservoir Hatch). Produces **512,000 L/s = 25,600 L/t** Superheated Steam.

This exactly matches the optimal flow of a **Duranium XLST** (25,600 L/t → 337,920 EU/t at 165% efficiency).

| | Value |
|---|---|
| XLST gross output | 337,920 EU/t |
| DEHP consumption | −480 EU/t |
| **Net EU/t** | **337,440 EU/t** |
| Net efficiency | 99.86% |

**Full setup cost (one DEHP + one Duranium XLST):**

| Component | EU cost | Peak tier |
|-----------|--------:|:---------:|
| DEHP controller | 2.41G EU | UV |
| XLST controller | 19.52M EU | EV |
| Duranium turbine blade (×16 per rotor) | 241M EU each | UV |
| Duranium Huge Turbine rotor (assembled) | ~3.86G EU | LuV (TConstruct alloy) |

The Duranium alloy (TConstruct) chain is the first-access bottleneck: min-tier **LuV** (3.72G EU path). Rotors are consumable — they degrade over time and must be replaced.

### Coolant Heating Mode

Converts **3,840 L/s = 192 L/t** IC2 Coolant → Hot Coolant. Hot Coolant fed into an **Extreme Heat Exchanger** yields 38,400 L/t Regular SC Steam → XLSCT (blade-dependent EU/t; see §6c and §8b for turbine blade options).

This mode is useful when a SC Steam turbine is already in your power chain, or when you want to avoid a separate Distilled Water supply and can route Coolant instead.

### DEHP vs. GT++ Geothermal Engines

| | DEHP + Duranium XLST | Vulcan Geothermal Engine |
|---|---:|---:|
| EU/t | 337,440 | 32,768 |
| Setup EU | ~6.3G EU (DEHP + XLST + rotor) | ~3.49G EU |
| First-accessible tier | LuV | ZPM |
| Fuel | Distilled Water (free) | Lava (free) |

DEHP delivers ~10× the EU/t of a Vulcan engine for comparable investment and is accessible a full tier earlier.

---

## 25. Non-GT Generators

### IC2 Generators
- **Geothermal Generator**: Lava → EU (IC2 machine)
- **Water Mill**: Water flow → tiny EU/t
- **Wind Mill**: Height-dependent EU/t

### EnderIO
- **Combustion Generator**: Basic RF (converts to EU via transformer)
- **Stirling Generator**: Furnace fuels → RF

### Forestry
- **Biogas Engine** / **Biomass Generator**: Biomass or Biogas → RF

### Draconic Evolution
- **Reactor**: Chaos/Draconic fuel → massive EU; risk of catastrophic explosion if mismanaged

### Botania
- **Mana system**: Not directly EU-producing but powers some machines

### Railcraft
- **Steam Boiler (Solid/Liquid)**: Coal/Creosote → Steam
  - Feeds IC2/GT Steam Turbines

### GalactiCraft
- **Coal Generator**: Starter power for GalactiCraft machines
- **Solar Panel**: Low output, used on space stations

### Advanced Solar Panels / Super Solar Panels
- High-tier solar panels from the ASP mod
- Hybrid/Ultimate/Quantum Solar Panels
- No recipes in data.bin (non-GT machines)

---

## Generation Progression by Family

Each cell shows the EU/t output when that family first becomes viable at that tier (single generator/turbine/reactor unless noted). `—` = not available or no meaningful upgrade at that tier.

| Family | LV | MV | HV | EV | IV | LuV | ZPM | UV | UHV | UEV | UIV+ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Combustion / Diesel (per engine) | 32 | 128 | 512 | 2k | 32k | — | — | — | — | — | — |
| Gas Turbine (per turbine) | 32 | 128 | 512 | 2k | 8k | — | — | — | — | — | — |
| Semifluid Generator (per machine) | 32 | 128 | 512 | 2k | 8k | — | — | — | — | — | — |
| Steam Turbine / XLST (per turbine) | — | — | — | — | 24k | 337k | — | 3M | — | — | — |
| Geothermal (GT++) | — | — | — | 2k | 8k | 32k | — | — | — | — | — |
| LFTR | — | — | — | 8k | — | 32k | 131k | — | — | — | — |
| IC2 Vacuum Reactor | — | 108k | — | — | — | 5M | — | — | — | — | — |
| LNR (per multiblock) | — | — | — | — | — | — | 975k | 2.3M | 9.5M | — | 664B |
| Compressed Solar (per panel, 24h) | — | 8 | 64 | — | 512 | 4k | 32k | 262k | 2M | 16M | — |
| Solar Tower → XLST (max rings) | — | — | — | 40k | — | — | — | 78k | 110k | — | — |
| Fusion → XLPT (per turbine) | — | — | — | — | — | 3.9M | — | — | 13.2M | — | — |
| Fusion → EHE → XLST (per reactor) | — | — | — | — | — | 390k | — | — | 91M | — | — |
| SLAM / Dyson Swarm | — | — | — | — | — | — | — | — | — | — | 50T / 100B |

Notes:
- **Combustion**: single-block LV–EV (32→2k); Large Combustion Engine EV 2k (unboosted); Extreme Combustion Engine IV 32.7k (boosted)
- **Gas Turbine**: single-block LV–IV (32→8k); Large Gas Turbine multiblock EV; UCFE LuV accepts all three fuel categories (combustion, gas turbine, rocket engine)
- **Semifluid**: single-block LV–IV (32→8k), efficiency degrades with tier (95%→75%)
- **Steam / XLST**: Vulcanite blade IV (24k/turbine); DEHP → Duranium XLST LuV (337k net); Chrysotile blade UV (3M/turbine best single turbine); Solar Tower or Plasma via EHE drives the high-end numbers
- **HTGR**: EU *consumer* (30,720 EU/t at LuV), not a generator — part of the nuclear fuel cycle
- **LNR**: ZPM entry = MkI 975k; UV = MkII 2.3M; UHV = MkIII 9.5M; UIV+ = theoretical max MkVI ×boosters ~664B
- **Fusion → EHE → XLST**: D+T reactor at LuV (390k per reactor, Trinium blade); UV Fusion / Heliothermal at UHV (91M per reactor, Infinity blade)
- **SLAM / Dyson Swarm**: SLAM ~50T per structure; Dyson Swarm ~100B after full construction

---

## Quick Reference: Generator Tiers by EU/t

Tier = minimum peak GT voltage tier across all possible production paths (`eu-cost --min-tier`); lower = first-accessible.
Setup/Fuel EU `—` = no recipe-traceable path (IC2/Thaumcraft ingredient blocks chain, or complex multi-machine setup with no single controller).
Tier `—` = tier undetermined (free ambient source or insufficient data).

| Generator / Setup | EU/t | Tier | Setup EU | Fuel EU |
|-------------------|------|------|----------|---------|
| Basic GT Solar Panel | 1 | HV | 881.5k EU | free (solar) |
| Compressed Solar (fire/water infused, 24h) | 8 | MV | 7.81M EU | free (solar) |
| IC2 Wind Mill | 1–8 | ULV | — | free (wind) |
| RTG (²⁴⁹Am) | 16 | IV | 626.88M EU | 2.45G EU/item |
| Single-block Combustion Gen | 32 | MV | 79.7k EU | 99 EU/mL |
| Acid Generator (LV) | 32 | LV | 297.0k EU | 37.8k EU/item |
| Magic Energy Absorber (Novice) | 32 | MV | 2.64M EU | free (ambient magic) |
| Magic Energy Converter (Novice) | 32 | MV | 2.03M EU | 578.68M EU/item |
| RTG (²³⁸Pu) | 64 | IV | 626.88M EU | 15.69G EU/item |
| Double-Compressed Solar (fire/water infused, 24h) | 64 | HV | 68.19M EU | free (solar) |
| Gas Turbine | 128 | LV | 79.8k EU | 125 EU/mL |
| Triple-Compressed Solar (fire/water infused, 24h) | 512 | IV | 667.43M EU | free (solar) |
| Semifluid Generator (Basic, LV) | 32 | MV | — | 12.8k EU/mL |
| Semifluid Generator (Advanced, MV) | 128 | MV | 83.7k EU | 12.8k EU/mL |
| Semifluid Generator (Turbo, HV) | 512 | HV | — | 12.8k EU/mL |
| Semifluid Generator (Turbo II, EV) | 2,048 | HV | — | 12.8k EU/mL |
| Semifluid Generator (Turbo III, IV) | 8,192 | IV | — | 12.8k EU/mL |
| Acid Generator (MV) | 128 | MV | 1.28M EU | 37.8k EU/item |
| Magic Energy Absorber (Adept) | 128 | HV | 17.52M EU | free (ambient magic) |
| Magic Energy Converter (Adept) | 128 | HV | 11.95M EU | 578.68M EU/item |
| Acid Generator (HV) | 512 | HV | 9.62M EU | 37.8k EU/item |
| Magic Energy Absorber (Master) | 512 | EV | 25.97M EU | free (ambient magic) |
| Magic Energy Converter (Master) | 512 | EV | 27.95M EU | 578.68M EU/item |
| Compact Kinetic Generator (Low, wind/water) | ~256 | EV | 134.86M EU | free (wind/water) |
| Solar Tower → SH steam → XLST (ENA 116%, max rings, 340 refl.) | ~40,000 | EV | 110.15M EU | free (solar) |
| Magic Energy Absorber (Grandmaster) | 2,048 | EV | 70.41M EU + 857.1k EU Dragon Egg | free (Dragon Egg on top, not consumed) |
| Large Combustion Engine | 2,048 | EV | 24.11M EU | 99 EU/mL |
| Large Gas Turbine | 2,048 | HV | 19.66M EU | 125 EU/mL |
| Acid Generator (EV) | 2,048 | HV | 17.12M EU | 37.8k EU/item |
| GT++ Basic Geothermal Engine | 2,048 | IV | 97.77M EU | 38 EU/mL |
| Lightning Rod (HV out, ~109k avg) | ~109,000 avg | IV | 301.71M EU | free (lightning) |
| Compact Kinetic Generator (Medium) | ~1,024 | IV | 769.04M EU | free (wind/water) |
| HTGR *(EU consumer, not generator)* | −30,720 EU/t | LuV | 158.95M EU (controller) | 39.21M EU/pebble input (Thorium ore chain); net EU negative — used for fuel breeding, not power |
| Extreme Combustion Engine (ECE) | 10,900 / 32,700 (boosted) | EV | 325.21M EU | 99 EU/mL |
| GT++ Turbo Geothermal Engine | 8,192 | LuV | 870.31M EU | 38 EU/mL |
| Lightning Rod II (EV out, ~160k avg) | ~160,000 avg | LuV | 392.90M EU | free (lightning) |
| Compact Kinetic Generator (High) | ~4,096 | LuV | 3.46G EU | free (wind/water) |
| Quadruple-Compressed Solar (fire/water infused, 24h) | 4,096 | LuV | 5.99G EU | free (solar) |
| GT++ Vulcan Geothermal Engine | 32,768 | ZPM | 3.49G EU | 38 EU/mL |
| UCFE (150% eff, high-octane fuel) | variable, cap = dynamo tier | IV | 552.82M EU (432.38M UCFE + 120.44M LuV Dynamo Hatch) | variable (combustion fuel; see §1d) |
| Lightning Rod III (IV out, ~185k avg) | ~185,000 avg | ZPM | 6.75G EU | free (lightning) |
| DEHP + Duranium XLST (Direct Steam, 25,600 L/t) | 337,440 | LuV | ~6.3G EU (2.41G DEHP + 19.52M XLST + ~3.86G rotor) | free (Distilled Water) |
| Compact Kinetic Generator (Extreme) | ~16,384 | ZPM | 18.92G EU | free (wind/water) |
| Quintuple-Compressed Solar (fire/water infused, 24h) | 32,768 | ZPM | 50.14G EU | free (solar) |
| Sextuple-Compressed Solar (fire/water infused, 24h) | 262,144 | UV | 412.35G EU | free (solar) |
| LFTR (Fuel 1) | 8,192 | ZPM | 285.56M EU | 70.8k EU/mL |
| LFTR (Fuel 2) | 32,768 | ZPM | 285.56M EU | 822.6k EU/mL |
| LFTR (Fuel 3) | 131,072 | ZPM | 285.56M EU | 849.6k EU/mL |
| IC2 Vacuum Reactor (MOX) | 107,979 | ZPM | 110.21M EU | 1.88M EU/quad rod |
| IC2 Vacuum Reactor (The Core) | ~4,979,200 | ZPM | 110.21M EU | 2.03G EU/assembly |
| LNR MkI (base) | 975,000 | ZPM | 655.36M EU | 5.12M EU/mL |
| LNR MkII (base) | 2,300,000 | UV | 655.36M EU | 10.91M EU/mL |
| LNR MkIII (base) | 9,511,000 | UHV | 655.36M EU | 14.99M EU/mL |
| LNR MkIV (base) | 88,540,000 | UMV | 655.36M EU | 158.75M EU/mL |
| LNR MkV (base) | 399,576,000 | UMV | 655.36M EU | 684.94M EU/mL |
| LNR MkVI (base) | 2,077,795,200 | UXV | 655.36M EU | 5.88G EU/mL |
| LNR MkVI (×5 coolant ×64 booster) | ~664,000,000,000 | UXV | 655.36M EU | 5.88G EU/mL |
| Fusion Reactor (D+T) → XLPT (He Plasma, Manyullyn) | 244,125/LPT; ~3.9M/XLPT | UIV | 2.45G EU (27.99M Fusion Mk I + 2.38G XLPT + 40M startup) | free (D+T via PGS) |
| Fusion Reactor (D+T) → EHE (73.7 mB Dense SC/mB He) → XLST (Trinium 135%) | ~390k EU/t per D+T reactor | UIV | 141.58M EU (27.99M Fusion Mk I + 53.30M EHE + 20.29M XLST + 40M startup) | free (D+T via PGS) |
| Fusion Reactor (D+T) → EHE → XLST (Shirabon 315%, endgame) | ~907k EU/t per D+T reactor | UIV | 141.58M EU (same) | free (D+T via PGS) |
| Plasma Generator Mk I (He plasma, D+He3 fusion) | 2,048 | UIV | 202.03M EU (114.04M gen + 27.99M Fusion Mk I + 60M startup) | free (He plasma via D+He3, from PGS) |
| Plasma Generator Mk II (He plasma, D+He3 fusion) | 8,192 | UIV | 238.86M EU (150.87M gen + 27.99M Fusion Mk I + 60M startup) | free (He plasma via D+He3, from PGS) |
| Plasma Generator Mk III (He plasma, D+He3 fusion) | 32,768 | UIV | 756.91M EU (668.92M gen + 27.99M Fusion Mk I + 60M startup) | free (He plasma via D+He3, from PGS) |
| Plasma Generator Mk IV (He plasma, D+He3 fusion) | 131,072 | UMV | 14.97G EU (14.88G gen + 27.99M Fusion Mk I + 60M startup) | free (He plasma via D+He3, from PGS) |
| Ultimate Pocket Sun (Celestial Tungsten plasma, 90%) | 576,000 per cell | UHV | 22.60G EU | 2.13G EU/mL |
| Solar Tower → SH steam → XLST (Infinity 225%, max rings) | ~78,000 | UV | 110.15M EU | free (solar) |
| Septuple-Compressed Solar (fire/water infused, 24h) | 2,097,152 | UHV | 3.36T EU | free (solar) |
| UV Fusion (FusionTech MK IV) → XLPT (CT Plasma, Infinity Catalyst) | 826,560/LPT; ~13.2M/XLPT | UMV | 700.32G EU (697.44G MK IV + 2.38G XLPT + 500M startup) | — (CT plasma: Tartarite input no DB path) |
| UV Fusion (FusionTech MK IV) → EHE (648 mB Dense SC/mB CT) → XLST (Infinity 225%) | ~91M EU/t per UV reactor | UMV | 698.01G EU (697.44G MK IV + 53.30M EHE + 20.29M XLST + 500M startup) | — (CT plasma: Tartarite input no DB path) |
| UV Fusion (FusionTech MK IV) → EHE → XLST (Shirabon 315%, endgame) | ~128M EU/t per UV reactor | UMV | 698.01G EU (same) | — (CT plasma: Tartarite input no DB path) |
| Solar Tower → SH steam → XLST (Shirabon 315%, max rings) | ~110,000 | UHV+ | 110.15M EU | free (solar) |
| Octuple-Compressed Solar (fire/water infused, 24h) | 16,777,216 | UMV | 44.21T EU | free (solar) |
| SLAM (1000 L antimatter, Copper) | 50,000,000,000,000 EU/t | UIV build | >8.20T EU (SLAM 4.10T + SSASS 4.10T; structure blocked by Prismatic Naquadah) | semi-stable antimatter via SSASS (protomatter 79.64M EU/L) |
| SLAM (scales super-linearly with volume) | up to 4.61e17 EU/t | UIV build | same | same |
| Dyson Swarm (10,000 modules, D=1) | 100,000,000,000 EU/t | UIV build | >61.08T EU (Ground Unit; structure counts unknown) + 10k modules @ 3.07M EU each | ~3.07M EU/module maintenance (~821/h at C=0); Gelid Cryotheum no DB path |

---

## Power by Tier

*Each section lists every Quick Reference generator first accessible at that voltage tier. **Spam** = build + fuel cost (★★★★★ cheapest). **ROI** = fuel efficiency (★★★★★ = free/ambient). Scaling columns show EU/t for the natural tier upgrade, or `N*` when no upgrade exists (= 4 units of the current generator at 4× cost). `—` = family caps here.*

---

### LV *(→MV →HV →EV)*

| Generator | EU/t | Spam | ROI | MV | HV | EV |
|-----------|-----:|:---:|:---:|---:|---:|---:|
| Gas Turbine | 128 | ★★★★★ | ★★★★★ | 512* | 2,048 | 8,192* |
| Acid Generator (LV) | 32 | ★★★★☆ | ★★☆☆☆ | 128 | 512 | 2,048 |

**Gas Turbine**: 79.8k EU build; MV = ×4 spam (no single-block MV gas turbine); HV = Large Gas Turbine multiblock (19.66M EU); EV = ×4 LGT spam. **Acid Generator**: scales exactly through MV/HV/EV tiers; byproduct sink only — never produce acid for power (1.03× ROI standalone).

---

### MV *(→HV →EV →IV)*

| Generator | EU/t | Spam | ROI | HV | EV | IV |
|-----------|-----:|:---:|:---:|---:|---:|---:|
| Compressed Solar (1×) | 8 | ★★★☆☆ | ★★★★★ | 64 | 256* | 512 |
| Single-block Combustion Gen | 32 | ★★★★★ | ★★★★☆ | 128* | 2,048 | 32,700 |
| Acid Generator (MV) | 128 | ★★★★☆ | ★★☆☆☆ | 512 | 2,048 | 8,192* |
| Semifluid Gen (Basic, LV) | 32 | ★★★☆☆ | ★★★☆☆ | 512 | 2,048 | 8,192 |
| Semifluid Gen (Advanced, MV) | 128 | ★★★★☆ | ★★★☆☆ | 512 | 2,048 | 8,192 |
| Magic Energy Absorber (Novice) | 32 | ★★★☆☆ | ★★★★★ | 128 | 2,048 | 8,192* |
| Magic Energy Converter (Novice) | 32 | ★★☆☆☆ | ★☆☆☆☆ | 128 | 512 | 2,048* |

**Compressed Solar**: HV = Double-Compressed (64, 8×); EV = ×4 spam (Triple-Compressed needs IV); IV = Triple-Compressed (512). **Single-block Combustion**: HV = ×4 spam; EV = Large Combustion Engine (2,048); IV = ECE boosted (32,700). **Semifluid**: Basic and Advanced share the same upgrade path (Turbo→Turbo II→Turbo III) at 12.8k EU/mL heavy fuel; efficiency degrades per tier. **Magic Absorber Novice→Adept (HV)→Grandmaster (EV, 2,048; Dragon Egg required)**. **Magic Converter**: 578.68M EU/item fuel cost — use only as a Vis sink; terrible ROI.

---

### HV *(→EV →IV →LuV)*

| Generator | EU/t | Spam | ROI | EV | IV | LuV |
|-----------|-----:|:---:|:---:|---:|---:|---:|
| Basic GT Solar Panel | 1 | ★★☆☆☆ | ★★★★★ | 4* | 4* | 4* |
| Double-Compressed Solar | 64 | ★★★☆☆ | ★★★★★ | 256* | 512 | 4,096 |
| Large Gas Turbine | 2,048 | ★★★★☆ | ★★★★★ | 8,192* | 32,768* | 131,072* |
| Acid Generator (HV) | 512 | ★★★☆☆ | ★★☆☆☆ | 2,048 | 8,192* | 32,768* |
| Acid Generator (EV) | 2,048 | ★★★☆☆ | ★★☆☆☆ | 8,192* | 32,768* | 131,072* |
| Semifluid Gen (Turbo, HV) | 512 | ★★★☆☆ | ★★★☆☆ | 2,048 | 8,192 | 32,768* |
| Semifluid Gen (Turbo II, EV) | 2,048 | ★★★☆☆ | ★★★☆☆ | 8,192* | 8,192 | 32,768* |
| Magic Energy Absorber (Adept) | 128 | ★★★☆☆ | ★★★★★ | 2,048 | 8,192* | 32,768* |
| Magic Energy Converter (Adept) | 128 | ★★☆☆☆ | ★☆☆☆☆ | 512 | 2,048* | 8,192* |

**Basic GT Solar**: 881.5k EU build; no tier upgrade — spam only. **Double-Compressed Solar**: EV = ×4 spam; IV = Triple-Compressed (512); LuV = Quad-Compressed (4,096). **Large Gas Turbine**: no gas turbine multiblock upgrade past HV — all ×4 spam; UCFE (IV) is a different family. **Acid Gen EV** is HV min-tier despite EV output. **Semifluid Turbo II** outputs EV power from HV; Turbo III at IV is the upgrade — note EV and IV columns show the same 8,192 (spam at EV vs. upgrade at IV). **Magic Absorber Adept→Grandmaster (EV, 2,048)** skips Master for best EU/t.

---

### EV *(→IV →LuV →ZPM)*

| Generator | EU/t | Spam | ROI | IV | LuV | ZPM |
|-----------|-----:|:---:|:---:|---:|---:|---:|
| Magic Energy Absorber (Master) | 512 | ★★★☆☆ | ★★★★★ | 2,048 | 8,192* | 32,768* |
| Magic Energy Absorber (Grandmaster) | 2,048 | ★★★☆☆ | ★★★★★ | 8,192* | 32,768* | 131,072* |
| Magic Energy Converter (Master) | 512 | ★★☆☆☆ | ★☆☆☆☆ | 2,048* | 8,192* | 32,768* |
| Compact Kinetic Generator (Low) | ~256 | ★★★☆☆ | ★★★★★ | ~1,024 | ~4,096 | ~16,384 |
| Solar Tower → XLST (ENA 116%, max rings) | ~40,000 | ★★☆☆☆ | ★★★★★ | 160,000* | 160,000* | 160,000* |
| Large Combustion Engine | 2,048 | ★★★★☆ | ★★★★☆ | 32,700 | 130,800* | 523,200* |
| Extreme Combustion Engine (ECE) | 10,900 / 32,700 | ★★★☆☆ | ★★★★☆ | 130,800* | 523,200* | 2,092,800* |

**Magic Absorber**: Grandmaster is the final tier; Dragon Egg required on top permanently. **Compact Kinetic Generator**: exact 4× per family step (Low→Medium→High→Extreme) on wind/water; free fuel. **Solar Tower**: ~40k EU/t fixed until UV (Infinity blades, ~78k) and UHV (Shirabon, ~110k) — well outside this window; all ×4 spam here. **LCE→ECE**: both EV min-tier; combustion family peaks at ECE (32,700 boosted); IV and beyond = ×4 spam.

---

### IV *(→LuV →ZPM →UV)*

| Generator | EU/t | Spam | ROI | LuV | ZPM | UV |
|-----------|-----:|:---:|:---:|---:|---:|---:|
| RTG (²⁴⁹Am) | 16 | ★★★☆☆ | ★★☆☆☆ | 64* | 64* | 64* |
| RTG (²³⁸Pu) | 64 | ★★☆☆☆ | ★★☆☆☆ | 256* | 256* | 256* |
| Triple-Compressed Solar | 512 | ★★★☆☆ | ★★★★★ | 4,096 | 32,768 | 262,144 |
| Semifluid Gen (Turbo III, IV) | 8,192 | ★★★☆☆ | ★★★☆☆ | 32,768* | 131,072* | 524,288* |
| GT++ Basic Geothermal Engine | 2,048 | ★★★★☆ | ★★★★★ | 8,192 | 32,768 | — |
| Compact Kinetic Generator (Medium) | ~1,024 | ★★★☆☆ | ★★★★★ | ~4,096 | ~16,384 | 65,536* |
| Lightning Rod I (~109k avg) | ~109,000 | ★★★☆☆ | ★★★★★ | ~160,000 | ~185,000 | — |
| UCFE (150% eff, dynamo-capped) | variable | ★★☆☆☆ | ★★★★☆ | — | — | — |

**RTG**: fixed output, no tier upgrade; use only for small persistent loads. **Triple-Compressed Solar**: 8× per step → Quad (LuV, 4,096) → Quint (ZPM, 32,768) → Sext (UV, 262,144). **Semifluid Turbo III**: final tier; all scaling = ×4 spam. **Geothermal**: exact 4× (Basic→Turbo→Vulcan); Vulcan caps at ZPM; free lava. **CKG Medium→High (LuV)→Extreme (ZPM)**; UV = ×4 spam (no CKG Extreme+). **Lightning Rod**: all three rods share a fixed 256-tick strike cadence — tier upgrades reduce energy-decay loss (44%→6%) but avg EU/t only scales 1.5× per rod; caps at ZPM. **UCFE**: output capped by dynamo hatch tier; accepts combustion (C=0.04), gas turbine (C=0.04), and rocket engine fuels (C=0.005, see §1d). With H8N4C2O4 (12,588,000 fuel_value) it hits the dynamo ceiling instantly; install ZPM dynamo hatch for higher output cap.

---

### LuV *(→ZPM →UV →UHV)*

| Generator | EU/t | Spam | ROI | ZPM | UV | UHV |
|-----------|-----:|:---:|:---:|---:|---:|---:|
| Quadruple-Compressed Solar | 4,096 | ★★☆☆☆ | ★★★★★ | 32,768 | 262,144 | 2,097,152 |
| GT++ Turbo Geothermal Engine | 8,192 | ★★★★☆ | ★★★★★ | 32,768 | — | — |
| Compact Kinetic Generator (High) | ~4,096 | ★★☆☆☆ | ★★★★★ | ~16,384 | 65,536* | 262,144* |
| Lightning Rod II (~160k avg) | ~160,000 | ★★★☆☆ | ★★★★★ | ~185,000 | — | — |
| DEHP + Duranium XLST (Direct Steam) | 337,440 | ★★☆☆☆ | ★★★★★ | 337,440* | 337,440* | 337,440* |

**Quad-Compressed Solar**: 8× per step → Quint (ZPM, 32k) → Sext (UV, 262k) → Sept (UHV, 2M). **Turbo Geothermal**: 4× to Vulcan (ZPM); caps there. **CKG High→Extreme (ZPM)**; UV/UHV = ×4 spam. **Lightning Rod II→III (ZPM)**; both cap at ZPM (no UV rod). **DEHP**: output fixed to Duranium XLST optimal flow (25,600 L/t); upgrade = swap rotor material (see §8b, §24); free Distilled Water.

---

### ZPM *(→UV →UHV →UEV)*

| Generator | EU/t | Spam | ROI | UV | UHV | UEV |
|-----------|-----:|:---:|:---:|---:|---:|---:|
| GT++ Vulcan Geothermal Engine | 32,768 | ★★★★☆ | ★★★★★ | — | — | — |
| Compact Kinetic Generator (Extreme) | ~16,384 | ★★☆☆☆ | ★★★★★ | 65,536* | 262,144* | 1,048,576* |
| Quintuple-Compressed Solar | 32,768 | ★★☆☆☆ | ★★★★★ | 262,144 | 2,097,152 | 8,388,608* |
| Lightning Rod III (~185k avg) | ~185,000 | ★★★☆☆ | ★★★★★ | — | — | — |
| LFTR (Fuel 1) | 8,192 | ★★★☆☆ | ★★★★☆ | 32,768 | 131,072 | 524,288* |
| LFTR (Fuel 2) | 32,768 | ★★★☆☆ | ★★★☆☆ | 131,072 | 524,288* | 524,288* |
| LFTR (Fuel 3) | 131,072 | ★★★☆☆ | ★★★☆☆ | 524,288* | 524,288* | 524,288* |
| IC2 Vacuum Reactor (MOX) | ~108,000 | ★★★☆☆ | ★★★☆☆ | ~4,979,200 | 19,916,800* | 19,916,800* |
| IC2 Vacuum Reactor (The Core) | ~4,979,200 | ★★☆☆☆ | ★★★★☆ | 19,916,800* | 19,916,800* | 19,916,800* |
| LNR MkI | 975,000 | ★★☆☆☆ | ★★★☆☆ | 2,300,000 | 9,511,000 | 38,044,000* |

**Vulcan Geothermal**: caps at ZPM; free lava from Nether. **CKG Extreme**: final CKG tier; all beyond = ×4 spam. **Quintuple-Compressed Solar**: 8× → Sextuple (UV, 262k); UEV = ×4 Septuple (no UEV compressed solar). **Lightning Rod III**: all rods cap at ZPM. **LFTR**: single 285.56M EU controller; fuel swap in same machine gives 8k→32k→131k EU/t with no hardware change. **IC2 Vacuum**: same 110.21M EU controller; MOX→The Core is a rod upgrade, not machine upgrade. **LNR MkI**: ZPM-accessible (Fusion Mk II required: fusion_threshold 320M > Mk I max; Fusion Mk II needs Superdense Europium Plate via HIP [ZPM]); UV upgrade = MkII (2.3M); UHV upgrade = MkIII (9.5M); UEV = ×4 MkIII spam. LFTR and IC2 Vacuum are ZPM's best ROI sources.

---

### UV *(→UHV →UEV →UIV)*

| Generator | EU/t | Spam | ROI | UHV | UEV | UIV |
|-----------|-----:|:---:|:---:|---:|---:|---:|
| Sextuple-Compressed Solar | 262,144 | ★★☆☆☆ | ★★★★★ | 2,097,152 | 8,388,608* | 8,388,608* |
| Solar Tower → XLST (Infinity 225%, max rings) | ~78,000 | ★★☆☆☆ | ★★★★★ | ~110,000 | 440,000* | 440,000* |
| LNR MkII | 2,300,000 | ★★☆☆☆ | ★★★☆☆ | 9,511,000 | 38,044,000* | 38,044,000* |

**Sextuple-Compressed Solar**: 8× to Septuple (UHV, 2M); UEV = ×4 Septuple (Octuple needs UMV). **Solar Tower**: UHV = Shirabon blades (~110k); beyond UHV = ×4 spam. At UV, Chrysotile XLST blades also unlock (~3M EU/t per turbine — see §8b). **LNR MkII**: UV-accessible via LCR with UV energy hatch overclocking the UHV recipe; UHV upgrade = MkIII (9.5M); UEV/UIV = ×4 MkIII spam; MkIV not until UMV.

---

### UHV *(→UEV →UIV →UMV)*

| Generator | EU/t | Spam | ROI | UEV | UIV | UMV |
|-----------|-----:|:---:|:---:|---:|---:|---:|
| LNR MkIII | 9,511,000 | ★★☆☆☆ | ★★★☆☆ | 38,044,000* | 38,044,000* | 88,540,000 |
| Septuple-Compressed Solar | 2,097,152 | ★☆☆☆☆ | ★★★★★ | 8,388,608* | 8,388,608* | 16,777,216 |
| Solar Tower → XLST (Shirabon 315%, max rings) | ~110,000 | ★★☆☆☆ | ★★★★★ | 440,000* | 440,000* | 440,000* |
| Ultimate Pocket Sun | 576,000/cell | ★★☆☆☆ | ★★☆☆☆ | 2,304,000* | 2,304,000* | 2,304,000* |

**LNR MkIII**: UHV-accessible via NFR (no overclock); UEV = ×4 spam (no UEV LNR); UMV = MkIV (88.5M EU/t). **Septuple-Compressed Solar**: UEV = ×4 Sept spam (Octuple needs UMV); UMV = Octuple (16.8M). **Solar Tower Shirabon**: final blade tier — all ×4 spam beyond. **Ultimate Pocket Sun**: Celestial Tungsten plasma fuel (2.13G EU/mL); no tier upgrade — spam only.

---

### UIV *(→UMV →UXV)*

| Generator | EU/t | Spam | ROI | UMV | UXV |
|-----------|-----:|:---:|:---:|---:|---:|
| Fusion (D+T) → XLPT (Manyullyn) | ~3,900,000/XLPT | ★☆☆☆☆ | ★★★★★ | ~13,200,000 | — |
| Fusion (D+T) → EHE → XLST (Trinium) | ~390,000/reactor | ★★☆☆☆ | ★★★★★ | ~128,000,000 | — |
| Fusion (D+T) → EHE → XLST (Shirabon) | ~907,000/reactor | ★★☆☆☆ | ★★★★★ | ~128,000,000 | — |
| Plasma Generator Mk I | 2,048 | ★★☆☆☆ | ★★★★★ | 131,072 | 524,288* |
| Plasma Generator Mk II | 8,192 | ★★☆☆☆ | ★★★★★ | 131,072 | 524,288* |
| Plasma Generator Mk III | 32,768 | ★★☆☆☆ | ★★★★★ | 131,072 | 524,288* |
| SLAM (1,000 L antimatter, Copper) | 50,000,000,000,000+ | ★☆☆☆☆ | ★★★★☆ | super-linear | super-linear |
| Dyson Swarm (10,000 modules) | ~100,000,000,000 | ★☆☆☆☆ | ★★★★★ | scales linearly | scales linearly |

Fusion Mk I (UIV build) is the infrastructure gate: once built, D+T plasma from PGS is free. **Fusion → XLPT**: highest raw EU/t per turbine; UMV = UV Fusion (~13.2M). **Fusion → EHE → XLST**: lower setup cost; Trinium (UIV) → Shirabon blade upgrade in same reactor (UIV-accessible); UMV for both = UV Fusion + Shirabon (~128M). **Plasma Gen Mk I–III**: all UIV min-tier (same fusion prerequisite); Mk IV requires UMV. **SLAM**: output = `Efficiency × 1e12 × Antimatter_L^E` (super-linear with volume); 1,000 L Copper → ~50T EU/t; structure blocked by Prismatic Naquadah. **Dyson Swarm**: linear with module count; ~100B at 10,000 modules.

---

### UMV *(→UXV)*

| Generator | EU/t | Spam | ROI | UXV |
|-----------|-----:|:---:|:---:|---:|
| LNR MkIV | 88,540,000 | ★★☆☆☆ | ★★★☆☆ | 399,576,000 |
| LNR MkV | 399,576,000 | ★★☆☆☆ | ★★★☆☆ | 2,077,795,200 |
| Plasma Generator Mk IV | 131,072 | ★★☆☆☆ | ★★★★★ | 524,288* |
| UV Fusion → XLPT (CT Plasma, Infinity Cat.) | ~13,200,000/XLPT | ★☆☆☆☆ | — | — |
| UV Fusion → EHE → XLST (Infinity 225%) | ~91,000,000/reactor | ★☆☆☆☆ | — | — |
| UV Fusion → EHE → XLST (Shirabon 315%) | ~128,000,000/reactor | ★☆☆☆☆ | — | — |
| Octuple-Compressed Solar | 16,777,216 | ★☆☆☆☆ | ★★★★★ | 67,108,864* |

**LNR MkIV→MkV**: same controller (655M EU), fuel chain only cost; MkV→MkVI at UXV. **Plasma Gen Mk IV**: final plasma gen tier; UXV = ×4 spam. **UV Fusion**: Tartarite input has no DB path — fuel ROI unquantifiable; listed for completeness. **Octuple-Compressed Solar**: 44.21T EU build; UXV = ×4 spam (no UXV compressed solar).

---

### UXV *(terminal)*

| Generator | EU/t | Spam | ROI |
|-----------|-----:|:---:|:---:|
| LNR MkVI (base) | 2,077,795,200 | ★★☆☆☆ | ★★★☆☆ |
| LNR MkVI (×5 coolant loops, ×64 neutron boosters) | ~664,000,000,000 | ★☆☆☆☆ | ★★★☆☆ |

Same 655M EU controller as MkI; MkVI is a fuel-chain upgrade from MkV. Boosted MkVI adds coolant loops and neutron reflectors for ~320× base output (~664B EU/t). No further LNR tier exists.
