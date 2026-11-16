---
name: power-gen-update
description: Update the Quick Reference table in power-gen.md with computed EU costs, tiers, and fuel costs using the gtnh CLI.
---

Update the "Quick Reference: Generator Tiers by EU/t" table in `power-gen.md` with accurate values computed from `nesql.db`. Fill in missing (`—`) Setup EU, Fuel EU, and Tier columns. Remove or correct anything wrong.

## Table columns

| Column | Meaning |
|--------|---------|
| **EU/t** | Rated output of the generator or system |
| **Tier** | Read from the `[TIER]` shown on the "Best:" line of `./gtnh eu-cost <id>` (peak tier is now included by default). Run on the controller and each major component; take the max. This is the build tier — highest GT recipe tier anywhere in the craft chain. |
| **Setup EU** | One-time EU to build all controllers + multiblock components + turbines + fuel processors + startup charges. Use `./gtnh eu-cost <id>` for each piece, sum them. |
| **Fuel EU** | Ongoing cost per unit of fuel. `./gtnh eu-cost <fuel-id>` per mL or per item. Write `free (source)` when inputs come entirely from infinite sources (PGS, EEC, solar, wind, ambient). |

## Workflow for a missing entry

1. **Find the item ID**: `./gtnh search "<name>"` — get the `i:` or `f:` id.
   - Use `--regex` / `-r` for multi-term searches: `./gtnh search "RTG|pellet|americium" -r`
2. **Compute setup cost and tier**: `./gtnh eu-cost "<id>"` for the controller and each required multiblock component (chambers, paired machines, turbines). The "Best:" line now shows both cost and peak tier, e.g. `Best: 626.88M EU/unit  [ZPM]`. Sum costs; take the max tier across all pieces.
3. **Compute fuel cost**: `./gtnh eu-cost "<fuel-id>"` per mL or per item. Check `./gtnh recipes-for "<fuel-id>"` to see if inputs are from infinite sources.
4. **Check for blockers**: if `eu-cost` finds no path it auto-diagnoses at depth 1. Pass `--why` for depth-3 diagnosis. If blocked, write `—` with a parenthetical reason.

## Setup EU conventions

- Include: controller, paired machines (e.g. SSASS with SLAM), fuel-processing multiblocks (e.g. Fusion Mk I for plasma), startup charges (fusion `fusion_threshold` metadata).
- Exclude: rotors (maintenance/consumable), structure casings unless they have a special named recipe cost.
- For fusion reactors, find `fusion_threshold` via `./gtnh recipe "<recipe-id>"` — that is the startup EU per dedicated reactor.
- Write setup as a sum with breakdown when complex: `2.45G EU (27.99M Fusion Mk I + 2.38G XLPT + 40M startup)`.
- Use `>X EU` when structure is partially blocked.

## What to include / exclude

**Include**: net power generators — combustion, gas turbines, solar, geothermal, LFTR, LNR, fusion + turbines, plasma generators, lightning rods, kinetic generators, compressed solar, SLAM, Dyson Swarm, RTGs, HTGR, magic absorbers.

**Exclude**: energy storage systems. The Hydro Turbine system (Hydro Pump → Hydro Dam → Hydro Turbine) is **storage only** — Pump uses EU to pressurize water; Turbine converts it back at ~91.2% round-trip. Do not add it.

## Fuel sources

Infinite sources (write `free (source)`):
- Planetary Gas Siphon: Deuterium (Uranus), Helium-3 (Uranus), Tritium (varies), other gases
- EEC (Extreme Entity Crusher): mob drops
- Solar, wind, ambient magic, lightning: free by nature
- Reservoir Hatch: water — but water by itself is only a fuel in steam setups, not hydro

Non-free fuels that look free:
- Helium Plasma from D+He3 fusion: inputs free via PGS, but reactor recipe costs ~245 EU/mL; note as `~245 EU/mL recipe cost, inputs free (PGS)`
- Helium Plasma from D+T fusion: inputs free via PGS, recipe costs ~524 EU/mL

## Common blockers (write `—` with note)

| Item | Blocker |
|------|---------|
| IC2 Wind Mill (`i:IC2:blockGenerator:4`) | Recipe needs `o:craftingGenerator` → `i:IC2:blockGenerator:0`, which has no recipe in DB |
| IC2 Geothermal Generator (`i:IC2:blockGenerator:1`) | Not craftable — exclude from table entirely |
| Field Restriction Casing | → Prismatic Naquadah Composite Slurry → Molten Prismatic Naquadah → Prismatic Naquadah (ore/mining only; `Crushed Prismatic Naquadah Ore` has 0 recipes) |
| Antimatter Annihilation Matrix / Semi-Stable Antimatter | → Superdense Hot Proto-Halkonite Steel Plate → Molten Proto-Halkonite Steel Base (Alloy Blast Smelter UEV) → **Tartarite dust** — same root blocker as Molten Tartarite |
| Molten Tartarite | Tartarite from Eye of Harmony T8 star recipes only; inputs are `0×` in DB (star fuel not in crafting graph) — blocks CT plasma fuel cost for UV Fusion rows |
| Advanced Compact Fusion Coil (`compactFusionCoil:2`) | → Hi-Computation Station MK-IV Prototype → Engraved Energy Chip → `o:batteryAdvanced` → GalacticraftAmunRa Advanced Battery (no recipe in DB) |
| Compact Fusion Coil MK-II Prototype (`compactFusionCoil:3`) | Needs Hi-Computation Station MK-V Finaltype + Advanced Fusion Coil — both unresolved |


## Fusion reactor startup

Find `fusion_threshold` in the recipe metadata — this is startup EU per reactor.

| Reactor | Recipe type | Controller ID |
|---------|-------------|--------------|
| Fusion Mk I (D+He3 → He plasma) | Fusion Reactor (EV) | `i:gregtech:gt.blockmachines:1193` |
| Fusion Mk I (D+T → He plasma) | Fusion Reactor (IV) | same |
| FusionTech MK IV (→ CT plasma) | Fusion Reactor (UV) | `i:gregtech:gt.blockmachines:965` |

Startup EU comes from the `fusion_threshold` metadata field on the specific recipe — always read it fresh with `./gtnh recipe "<recipe-id>"`.

## Key machine IDs

| Machine | ID |
|---------|-----|
| Fusion Control Computer Mk I | `i:gregtech:gt.blockmachines:1193` |
| FusionTech MK IV | `i:gregtech:gt.blockmachines:965` |
| Large Plasma Turbine (LPT) | `i:gregtech:gt.blockmachines:1153` |
| XL Turbo Plasma Turbine (XLPT) | `i:gregtech:gt.blockmachines:31074` |
| XL Turbo Steam Turbine (XLST) | `i:gregtech:gt.blockmachines:865` |
| Extreme Heat Exchanger (EHE) | `i:gregtech:gt.blockmachines:32017` |
| Plasma Generator Mk I | `i:gregtech:gt.blockmachines:1196` |
| Plasma Generator Mk II | `i:gregtech:gt.blockmachines:1197` |
| Plasma Generator Mk III | `i:gregtech:gt.blockmachines:1198` |
| Plasma Generator Mk IV | `i:gregtech:gt.blockmachines:10752` |
| SLAM controller | `i:gregtech:gt.blockmachines:32028` |
| SSASS controller | `i:gregtech:gt.blockmachines:32027` |
| HTGR | `i:gregtech:gt.blockmachines:12733` |
| UCFE | `i:gregtech:gt.blockmachines:32001` |

## Voltage tier reference

```
0=ULV 1=LV 2=MV 3=HV 4=EV 5=IV 6=LuV 7=ZPM 8=UV 9=UHV 10=UEV 11=UIV 12=UMV 13=UXV
```

## Number formatting

Use SI suffixes: `k` = 10³, `M` = 10⁶, `G` = 10⁹, `T` = 10¹², `P` = 10¹⁵. Examples: `27.99M EU`, `2.45G EU`, `8.20T EU`. For estimated/lower-bound values prefix with `>` or `~`.
