# ZPM-Tier Power Generation — Complete Survey

**Criterion:** the highest recipe tier required to craft the **generator** or produce its
**fuel** from scratch. "Available at ZPM" = that tier is ≤ ZPM (131,072 EU/t).

**64A benchmark:** all "units needed" figures target 64 amps at the named voltage:
- 64A ZPM = 64 × 131,072 = **8,388,608 EU/t** total
- 64A UV  = 64 × 524,288 = **33,554,432 EU/t** total

EU/t values marked † are exact from recipe metadata; values marked ~ are estimated from
community/source knowledge and should be verified in-game.

---

## ☀️ Solar

### Solar Boilers (Simple / Advanced)
- **Machine unlock:** LV (Assembler, ULV recipe)
- **Fuel:** Water (free)
- **Uptime:** ★★★★★ — fully passive, set and forget
- **Output:** ~10 EU/t per boiler via steam turbine; negligible but zero cost
- **64A ZPM:** ~838,000 boilers — never practical; background trickle only
- **Scales to UV+:** ★☆☆☆☆

Make steam, feed to any steam turbine. Provide a background trickle day and night.

---

### Compressed Solar Panels (EMT mod)

| Tier | EU/t (daytime) | Machine unlock | Notes |
|------|---------------|---------------|-------|
| Single | 8 | EV (Solar Factory) | Ignis infused variant gives 24h |
| Double | 16 | EV | Ignis infused variant gives 24h |
| Triple | 512 | EV | Irradiant Reinforced TungstenSteel Plate gating; infused gives 24h |
| Quadruple–Sextuple | up to 32,768 | EV + Thaumcraft Arcane Infusion | Infused (Ignis/elemental) variants give 24h |
| **Septuple** | 65,536 | **ZPM components** | Infused variant gives 24h |
| **Octuple** | 131,072 | **ZPM (Optical Circuit)** | Quantum Core requires `circuitOptical`; day-only only (no infused variant) |

**Infused panels (24h uptime):** Elemental/Fire Infused variants are crafted in the
Thaumcraft **Crucible** using the plain compressed panel + Ignis, Lux, Permutatio, and
Praecantatio aspects (quantities double per tier: 128× for Triple, 512× for Quintuple,
2048× for Septuple). Single through Septuple all have infused variants. The Octuple
(day-only) has no known infused equivalent.

- **Uptime:** ★★★★☆ — infused Single–Septuple run 24h; Octuple is day-only (★★☆☆☆)
- **64A ZPM (Septuple infused, 65,536† EU/t each):** 128 panels
- **64A ZPM (Octuple, 131,072† EU/t each, daytime):** 64 panels daytime / ~128 for 24h average
- **64A UV:** 512 Septuples or 256 Octuples (day) / ~512 (24h avg) — no higher-tier panel exists
- **Scales to UV+:** ★★☆☆☆ — Octuple caps at ZPM voltage; UV power requires large arrays
  with no upgrade path for the panels themselves.

---

### Advanced / Hybrid / Ultimate Hybrid Solar Panels (AdvancedSolarPanel mod)

- **Enriched Sunnarium** (key component): Assembler at **EV** or Autoclave at **LuV**
- Generate EU around the clock (not daytime-only)
- **Machine unlock:** EV–LuV
- **Uptime:** ★★★★☆ — 24h generation
- **64A ZPM / UV:** Many panels; output per panel is mod-capped and no UV tier exists.
  Practical as supplementary power, not as a primary 64A source.
- **Scales to UV+:** ★★☆☆☆

---

## 💨 Wind & Kinetic

### IC2 Wind Mill / Compact Kinetic Wind Generators (Low–High tier)
- **Machine unlock:** LV–EV (crafting table recipes)
- **Uptime:** ★★★★★ — fully passive
- **Output:** Low (hundreds of EU/t per unit)
- **64A ZPM:** Tens of thousands of units — never practical at this scale
- **Scales to UV+:** ★☆☆☆☆ — supplementary only

### Extreme Kinetic Wind Generator
- **Machine unlock:** ZPM — Extreme Crafting (Avaritia table) with **ZPM Motor**, Neutronium
  components, and a Naquadria Battery
- **Uptime:** ★★★★★ — passive wind
- **Output:** Much higher than lower kinetic tiers (exact EU/t depends on installation height
  and biome; typically hundreds of k EU/t in favourable conditions)
- **64A ZPM:** Estimated ~10–40 units in optimal placement
- **64A UV:** ~40–160 units — same machine, more of them
- **Scales to UV+:** ★★★☆☆

### Extreme Kinetic Generator (non-wind)
- Same recipe class and unlock tier as above; pairs with a turbine/shaft source.
- **Machine unlock:** ZPM
- **64A ZPM / UV:** Same profile as wind variant; dependent on shaft power source.
- **Scales to UV+:** ★★★☆☆

---

## ♨️ Steam Turbines

Turbines consume steam; output scales with steam pressure and machine tier.

| Machine | Recipe tier | Notes |
|---------|------------|-------|
| Large Steam Turbine | LV crafting (LuV casings in practice) | |
| Large HP Steam Turbine | LV crafting | Higher-pressure steam |
| Large SC Steam Turbine | MV Assembler | Supercritical steam |
| XL Turbo Steam Turbine | HV Assembler | |
| **XL Turbo SC Steam Turbine** | **LuV Assembler** | Highest pre-UV steam turbine |

Output per turbine depends on steam pressure and configuration; each turbine is a
conversion layer, not a fuel source.

- **64A ZPM:** Achievable with a large enough array of turbines fed by an HTGR or LFTR
  steam loop, but each multiblock outputs far less than a direct-EU generator at the
  same effort.
- **Scales to UV+:** ★★★☆☆ — the turbines themselves top out at LuV construction;
  UV adds a UV-tier turbine. Useful as a conversion layer but not standalone UV power.

**Steam sources:** Solar Boilers (LV) → Large Boilers (EV, many fuels) →
HTGR/LFTR (ZPM, see nuclear section).

---

## 🔥 Combustion & Gas Engines

### Extreme Diesel Engine *(GoodGenerator)*
- **Machine unlock:** LV — shaped crafting using LV Machine Hull, LV Electric Pump,
  Large Bronze Fluid Pipe, Basic Circuit
- **Output:** ~8,192 EU/t per engine ~ (EV-class single block)
- **Fuels** (only 3 valid):

| Fuel | fuel_value† | Production tier |
|------|-----------|----------------|
| High Octane Gasoline | 2,500 | EV (refinery cracking chain) |
| Jet Fuel A | 2,248 | EV |
| Jet Fuel No.3 | 1,824 | EV |

- **Uptime:** ★★★★☆ — with a refinery pipeline or bee oil supply
- **Renewable fuel:** ✓ — bee oil/resin combs → EV refinery chain → infinite supply
- **64A ZPM (~8,192 EU/t each~):** ~1,024 engines — feasible given their trivial
  construction cost; the refinery pipeline is the real bottleneck
- **64A UV:** ~4,096 engines — not practical; use as bridging power only
- **Scales to UV+:** ★★☆☆☆ — fuel chain tops out at EV; no higher-grade diesel exists.
  Good cheap bridging, poor primary UV source.

---

### Large Gas Turbine *(GT multiblock)*
- **Machine unlock:** LuV (Scanner unlock)
- **Output:** Variable; depends on turbine blade material and fuel. With Neutronium
  blades and Naquadah Gas, a single LGT multiblock can reach hundreds of k EU/t.
  Exact figure requires in-game measurement for the blade/fuel combination.
- **Top fuels:**

| Fuel | fuel_value† | Production tier | Notes |
|------|-----------|----------------|-------|
| Nitrobenzene | 1,600 | **MV** Chemical Plant | Benzene + H₂SO₄ |
| Nefarious Gas | 1,200 | EV (GoodGenerator cracking) | |
| Naquadah Gas | 1,024 | EV Oil Cracker + MV Distillery | Byproduct of naquadah refining |

- **Uptime:** ★★★★☆
- Naquadah Gas is effectively **free** — it's a side product of the naquadah chain you
  run anyway. Nitrobenzene requires only benzene (EV coal/oil) and sulfuric acid (LV).
- **64A ZPM:** Approximately 15–85 turbines depending on blade efficiency — run the
  numbers for your specific blade tier before committing. Naquadah Gas supply is the
  natural limit.
- **64A UV:** ~60–340 turbines (same machines, more of them or better blades)
- **Scales to UV+:** ★★★★☆ — machines stack freely, Naquadah Gas remains a free
  byproduct of the UV naquadah chain. Excellent secondary source at any tier.

---

## ⚛️ Nuclear

### IC2 Vacuum Reactor
- **Machine unlock:** HV Assembler
- **Design:** 40 quad fuel rod slots, vacuum cooled (no heat management, no explosion risk);
  see [GTNH wiki — Vacuum Reactor](https://wiki.gtnewhorizons.com/wiki/Vacuum_Reactor)
- **Uptime:** ★★★★☆ fully automated — vacuum cooling eliminates the classic IC2 thermal hazard

The same reactor structure accepts a ladder of fuel rod types with dramatically different outputs.
All EU/t values from the GTNH wiki; fuel production tier is the highest recipe tier in the chain.

| Fuel | EU/t/reactor | Fuel production gate | 64A-ZPM | 64A-UV |
|------|:---:|---|:---:|:---:|
| Quad Thorium | 8,720 | HV (centrifuge chain) | 962 | 3,848 |
| Quad Uranium | 43,600 | HV | 193 | 770 |
| Quad MOX | 107,979 | HV | 78 | 311 |
| Quad HD Plutonium | 301,958 | **HV Assembler** (Wrapped Plutonium Ingot) | 28 | 112 |
| Quad Excited Uranium | 1,046,400 | **IV Mixer** (HD Uranium → Uranium Liquid Fuel → Neutron Activator) | 9 | 33 |
| The Core (25 cells) | 3,200,000 | **IV Assembler** + Tiberium | 3 | 11 |
| **The Core (40 cells)** | **4,979,200** | **IV Assembler** + Tiberium | **2** | **7** |

**Fuel production chains:**
- **Quad HD Plutonium**: Wrapped Plutonium Ingot (HV† Assembler: Pu-oxide-U mixture dust + HSS-S foil)
  → HD Plutonium Nugget (ULV Implosion Compressor + explosives) → rod (LV Canner) → quad (HV† Assembler)
- **Quad Excited Uranium**: HD Uranium Nugget (ULV Implosion Compressor + Wrapped Uranium Ingot) →
  HD Uranium (MV Compressor) → Uranium Based Liquid Fuel (IV Mixer: HD-U + Potassium + Quantium + Radon) →
  Excited State (Neutron Activator, EV† machine) → rod (HV Fluid Canner) → quad (EV† Assembler)
- **The Core**: 32× Naquadah fuel rods + 192× Long Tungstensteel Rods + 128× Tiberium Dust
  → IV Assembler (30,720 EU/t, 5 s). Tiberium is the rare-material gate (meteor impacts or
  GoodGenerator sources); the IV Assembler itself is the recipe tier gate.

† = recipe tier for that step; overall chain gate is the highest tier in the chain.

- **Renewable fuel:** ✓ — bee uranium/plutonium combs feed all rod types indefinitely; Tiberium
  is obtainable via IC2 crops or meteor mining
- **Scales to UV+:** ★★★★☆ — The Core at 40 cells needs only 2 reactors for 64A ZPM and 7 for
  64A UV, both achievable with IV-gated construction. Highest per-reactor output of any IC2
  design; the fuel complexity is the only constraint.

---

### HTGR (High Temperature Gas-cooled Reactor)
- **Machine unlock:** **ZPM** — shaped crafting requires **ZPM Emitter** and
  **ZPM Field Generator** as components
- **Fuel unlock:** ULV — TRISO pebbles from Centrifuge (ULV); trivially available from
  any enriched uranium processing
- **Output: 30,720† EU/t per reactor**, 72,000 ticks (60 min) per 64-pebble load
- **Uptime:** ★★★★★ — 60-minute burn cycles; minimal maintenance
- **64A ZPM (30,720† EU/t each):** **274 reactors**
  - 274 × 64-pebble loads = 17,536 TRISO pebbles per 60-minute cycle.
    With bee uranium this is fully passive but requires a sizeable apiary.
- **64A UV (same reactors, same fuel):** **1,093 reactors**
  - No fuel upgrade path exists; scaling is purely additive.
- **Renewable fuel:** ✓ — bee uranium/thorium/plutonium combs → TRISO → passive supply
- **Scales to UV+:** ★★★☆☆ — strong at ZPM, but 1,093 units for UV is substantial.
  Each unit is a full ZPM-cost multiblock. The trivial fuel cost offsets the build cost
  but this doesn't scale as efficiently as LNR at higher tiers.

---

### LFTR (Liquid Fluoride Thorium Reactor)
- **Machine unlock:** **ZPM** — Assembler at 491,520 EU/t
- **Fuel unlock:** EV — both fuel grades produced via Nuclear Fuel Processing (7,680 EU/t)
  from LFTR Fuel Base (EV Chemical Plant)
- **Cycle:** 2,000 ticks (1.67 min) per 100 fuel + 200 LFTB

| Fuel | Output power† | Production tier |
|------|-------------|----------------|
| LFTR Fuel 1 | 8,192 EU/t (HV) | EV Nuclear Fuel Processing |
| LFTR Fuel 2 | 32,768 EU/t (LuV) | EV Nuclear Fuel Processing |
| LFTR Fuel 3 | **131,072 EU/t (ZPM exact)** | EV Nuclear Fuel Processing (ThF₄ variant) |

- **Uptime:** ★★★★☆ — 100-second cycles; needs a steady fuel trickle
- **64A ZPM with Fuel 3 (131,072† EU/t each):** **64 reactors** (exact — each LFTR
  outputs 1A of ZPM, so 64 directly match the target)
- **64A UV with Fuel 3 (no Fuel 4 exists):** **256 reactors** — same EV-made fuel,
  just more machines
- **Renewable fuel:** ✓ — UF₆ recycled from depleted outputs; thorium/uranium bees at
  EV apiary provide the base feedstock passively
- **Scales to UV+:** ★★★☆☆ — Fuel 3 is the ceiling; no higher fuel grade exists.
  256 reactors for 64A UV is manageable given EV fuel cost, but you're building many
  ZPM-tier multiblocks. LNR becomes more efficient at UV and beyond.

---

### Large Naquadah Reactor (LNR)
- **Machine unlock:** LuV–ZPM (multiblock)
- **Fuel chain** (all EU/t values exact† from recipe `lng_basic_output ÷ duration`):

| Fuel | EU/t† | Production tier | 64A-ZPM units | 64A-UV units |
|------|-------|----------------|:---:|:---:|
| MkI | 16,250 | **IV Fusion Reactor** | 517 | 2,065 |
| MkII | 32,857 | **UV** Large Chemical Reactor | 256 | 1,022 |
| MkIII | 118,887 | **UV** LCR + further processing | 71 | 283 |
| MkIV | 885,400 | UV+ infrastructure | 10 | 38 |
| MkV | 2,497,350 | UV+ infrastructure | 4 | 14 |
| MkVI | 8,657,480 | UV+ infrastructure | **1** | **4** |

- At ZPM tier with MkI fuel (IV Fusion gate): **517 reactors** for 64A ZPM.
  MkII/III require UV power to produce. MkIV–VI require further post-UV infrastructure.
- **MkVI single-reactor performance:** 8,657,480 EU/t — one LNR MkVI covers 64A ZPM
  entirely and four cover 64A UV.
- **Uptime:** ★★★★☆ once the fuel pipeline is established
- **Renewable fuel:** ✓ — bee naquadah combs → EV–LuV cracking chain → MkI fuel;
  higher marks unlock as UV infrastructure comes online
- **Scales to UV+:** ★★★★★ — the defining UV+ power source. Each fuel mark cuts the
  required reactor count dramatically; MkVI drops 64A UV to just 4 reactors. The same
  multiblock structure runs across all fuel marks — you upgrade the fuel, not the machine.

---

### Naquadah Reactors Mk I–V (small, single-block)

All fuel rods share the same upstream gating:
- **Enriched Naquadah** (MkI–III fuel): **LuV Multiblock Dehydrator** (122,880 EU/t)
- **Naquadria** (MkIV bolt, MkV rod): **LuV Autoclave** (122,880 EU/t) from Enriched
  Naquadah + Heavy Radox

Each reactor outputs at its rated voltage tier (estimated~):

| Mark | EU/t~ | Fuel | Duration/rod | 64A-ZPM units | 64A-UV units |
|------|-------|------|:---:|:---:|:---:|
| MkI | ~512 | Enriched Naquadah Bolt | ~50,000 t (41 min) | ~16,384 | ~65,536 |
| MkII | ~2,048 | Enriched Naquadah Rod | ~250,000 t (208 min) | ~4,096 | ~16,384 |
| MkIII | ~8,192 | Long Enriched Naquadah Rod | ~500,000 t (416 min) | ~1,024 | ~4,096 |
| MkIV | ~32,768 | Naquadria Bolt | ~250,000 t (208 min) | ~256 | ~1,024 |
| **MkV** | ~131,072 | Naquadria Rod | ~1,000,000 t (833 min) | **~64** | ~256 |

- **Fuel unlock:** LuV (gating factor for all marks)
- **Uptime:** ★★★★☆ — insert rods, no fluid management; rods last a very long time
- **MkV profile:** ~64 single-block machines for 64A ZPM; ~256 for 64A UV. Same
  LuV-gated fuel for both — the production chain doesn't change as you scale.
- **Renewable fuel:** ✓ — bee naquadah combs → Enriched Naquadah/Naquadria → rods
- **Scales to UV+:** ★★★★☆ — MkV at ~ZPM voltage output, LuV-gated fuel, very long
  rod burn times. Stacks freely. No UV upgrade exists but the fuel is cheap enough
  that ~256 MkVs for UV is genuinely viable as a secondary source.

---

## ⚡ Lightning Rods

| Rod | Hull required | Machine unlock |
|-----|--------------|---------------|
| Lightning Rod I | LuV Machine Hull | LuV |
| Lightning Rod II | ZPM Machine Hull | **ZPM** |
| Lightning Rod III | UV Machine Hull | UV |

- **Fuel:** None — harvests lightning strikes
- **Uptime:** ★☆☆☆☆ weather-dependent, ★★★☆☆ with weather manipulation
- **Output:** Inconsistent; not useful for 64A targets
- **Scales to UV+:** ★★☆☆☆ — Rod III exists at UV; supplementary trickle only

---

## 🧙 Magic Energy Absorber

Consumes items from the Magic Energy Absorber fuel list. Four machine tiers:
Novice (LV hull) → Adept (MV hull) → Master (HV hull) → **Grandmaster (EV hull + IV circuit)**.

- **Output: 2,048 EU/t (1A EV) per Grandmaster machine** — this is the hard cap regardless
  of fuel quality. Fuel choice affects duration, not rate.
- **Free infinite fuel: Dragon Egg** — placed in the fuel slot, it is never consumed and
  runs the machine indefinitely. No fuel automation needed at all.
- **Machine unlock:** Grandmaster at EV (Arcane Infusion); the **Extreme Entity Crusher**
  (EV Hull + HV Robot Arm) is only needed if using Nether Stars instead of a Dragon Egg
- **64A ZPM (2,048 EU/t each):** **4,096 Grandmaster machines**
  - Each machine is cheap (EV hull + Thaumcraft infusion); 4,096 is a large but
    achievable array given the zero fuel cost
- **64A UV:** **16,384 machines** — not practical as a primary UV source
- **Uptime:** ★★★★★ — Dragon Egg never depletes; set and forget
- **Renewable fuel:** ✓ — Dragon Egg is permanent; one egg runs a machine forever
- **Scales to UV+:** ★★★☆☆ — output is hard-capped at 2,048 EU/t per machine; scaling
  to UV purely by adding more MEAs requires 16,384 units. Better used as cheap
  supplementary EV-voltage power alongside a real UV primary source.

---

## 🐝 Infinite Fuel Sources — Cross-Cutting

### Industrial Apiary (GT version)
- **Unlock:** EV (requires EV Robot Arm in recipe)
- Bee strains relevant to power generation:
  - **Radioactive bees** → uranium/plutonium combs → TRISO (HTGR) or IC2 fuel rods
  - **Naquadah bees** → naquadah combs → naquadah reactor fuel chain (LNR / solid Naq
    reactors)
  - **Thorium bees** → thorium combs → LFTR Fuel Base chain
  - **Oil / resin bees** → diesel/gas turbine fuels via refinery chain

Once established, bee apiaries provide a **fully passive, infinite** supply of
high-value materials with no chunk-loading or mining required.

### IC2 Crops
- Uranium, naquadah, and other crop genetics yield trace amounts of high-value materials
- Slow to establish but truly zero-maintenance once running

### Extreme Entity Crusher
- **Unlock:** EV Hull (shaped crafting)
- Automates killing of any mob including Withers → Nether Stars → Magic Energy Absorber
- Blazes → Blaze Rods → thermal fuel chain

---

## Summary

| Source | Machine tier | Fuel tier | EU/t/unit | Renewable? | Uptime | 64A ZPM | 64A UV | Scales UV+ |
|--------|-------------|-----------|-----------|-----------|--------|:-------:|:------:|:----------:|
| Solar Boiler | LV | free | ~10 | ✓ | ★★★★★ | impractical | impractical | ★☆☆☆☆ |
| Solar Septuple (infused) | ZPM | Crucible | 65,536† | ✓ | ★★★★☆ (24h) | 128 | 512 | ★★☆☆☆ |
| Solar Octuple | ZPM | none | 131,072† | ✓ | ★★☆☆☆ (day) | 64–128 | 256–512 | ★★☆☆☆ |
| Adv. Solar Panel (ASP) | EV–LuV | none | varies | ✓ | ★★★★☆ (24h) | many | many | ★★☆☆☆ |
| Extreme Diesel Engine | LV | EV | ~8,192~ | ✓ | ★★★★☆ | ~1,024 | ~4,096 | ★★☆☆☆ |
| Large Gas Turbine | LuV | MV–EV | variable | ✓ | ★★★★☆ | ~15–85 | ~60–340 | ★★★★☆ |
| IC2 Vacuum Reactor (MOX) | HV | HV | 107,979 | ✓ | ★★★★☆ | 78 | 311 | — |
| IC2 Vacuum Reactor (HD Plutonium) | HV | HV | 301,958 | ✓ | ★★★★☆ | 28 | 112 | — |
| IC2 Vacuum Reactor (Excited Uranium) | HV | IV | 1,046,400 | ✓ | ★★★★☆ | 9 | 33 | — |
| **IC2 Vacuum Reactor (The Core)** | HV | **IV** | **4,979,200** | ✓ | ★★★★☆ | **2** | **7** | ★★★★☆ |
| **HTGR** | **ZPM** | ULV | **30,720†** | ✓ | ★★★★★ | **274** | **1,093** | ★★★☆☆ |
| **LFTR Fuel 1** | **ZPM** | EV | **8,192†** | ✓ | ★★★★☆ | 1,024 | 4,096 | — |
| **LFTR Fuel 2** | **ZPM** | EV | **32,768†** | ✓ | ★★★★☆ | 256 | 1,024 | — |
| **LFTR Fuel 3** | **ZPM** | EV | **131,072†** | ✓ | ★★★★☆ | **64** | **256** | ★★★☆☆ |
| LNR MkI | LuV–ZPM | IV | 16,250† | ✓ | ★★★★☆ | 517 | 2,065 | — |
| LNR MkII | LuV–ZPM | **UV** | 32,857† | ✓ | ★★★★☆ | 256 | 1,022 | — |
| LNR MkIII | LuV–ZPM | **UV** | 118,887† | ✓ | ★★★★☆ | 71 | 283 | — |
| LNR MkIV | LuV–ZPM | UV+ | 885,400† | ✓ | ★★★★☆ | **10** | 38 | — |
| LNR MkV | LuV–ZPM | UV+ | 2,497,350† | ✓ | ★★★★☆ | **4** | **14** | — |
| **LNR MkVI** | LuV–ZPM | UV+ | **8,657,480†** | ✓ | ★★★★☆ | **1** | **4** | ★★★★★ |
| Naq Reactor MkIV | LuV | LuV | ~32,768~ | ✓ | ★★★★☆ | ~256 | ~1,024 | ★★★☆☆ |
| **Naq Reactor MkV** | ~ZPM | LuV | ~131,072~ | ✓ | ★★★★☆ | **~64** | **~256** | ★★★★☆ |
| Lightning Rod I | LuV | none | — | ✓ | ★☆☆☆☆ (weather) | — | — | ★★☆☆☆ |
| Lightning Rod II | **ZPM** | none | — | ✓ | ★☆☆☆☆ (weather) | — | — | ★★☆☆☆ |
| Magic Energy Absorber | EV | none (Dragon Egg) | 2,048 | ✓ | ★★★★★ | 4,096 | 16,384 | ★★★☆☆ |
| Extreme Kinetic Generator | **ZPM** | wind | high | ✓ | ★★★★★ | ~10–40 | ~40–160 | ★★★☆☆ |
| XL Turbo SC Steam Turbine | LuV | steam | high | ✓ | ★★★★★ | depends on steam | varies | ★★★☆☆ |

† = exact value from recipe metadata  ~ = estimated; verify in-game

---

### Practical ZPM-era priorities

- **LFTR Fuel 3 + 64 reactors**: clean, exact match — each LFTR outputs 1A of ZPM; 64
  reactors = 64A. EV-made fuel, ZPM machine, closed fuel loop. The clearest path to a
  full 64A ZPM array.
- **IC2 Vacuum Reactor + The Core**: once IV infrastructure is in place, just 2 reactors
  cover 64A ZPM and 7 cover 64A UV. The Tiberium gate is the key blocker; after that the
  reactor itself is HV-tier and trivially cheap.
- **IC2 Vacuum Reactor + Excited Uranium**: 9 reactors for 64A ZPM; IV Mixer is the gate.
  Good stepping stone while working toward Tiberium.
- **HTGR + bee uranium**: easiest fuel supply at ZPM — ULV TRISO, 60-minute burns,
  fully passive. 274 reactors is a big build but no fuel chain to manage.
- **LNR on MkI fuel**: available as soon as IV Fusion is online. 517 reactors at 16k
  EU/t each is a lot, but the same machine body upgrades to MkVI as UV infrastructure
  develops — you're building permanent infrastructure.
- **Large Gas Turbines on Naquadah Gas**: LuV-era machines on a free byproduct. Fewest
  multiblocks to build for 64A ZPM if turbine blades are maximised; no fuel chain
  cost beyond what you're already running.
- **Naquadah Reactor MkV**: ~64 solid-block machines, LuV-gated fuel, rods last 833 min
  each. Lowest operational overhead of any ZPM-tier option.
- **Magic Energy Absorber + Dragon Egg**: single Dragon Egg runs each Grandmaster machine
  forever at 2,048 EU/t. 4,096 machines for 64A ZPM — individually cheap EV builds with
  zero ongoing fuel cost. Best as bulk supplementary EV power, not a primary ZPM source.
- **LNR MkVI (UV+)**: single reactor for 64A ZPM; 4 reactors for 64A UV. The endgame
  power source — but fuel requires deep UV+ infrastructure.
