"""Threshold base, stage 2: the rooms north of the atrium (palette V1, see threshold_lib.py).

y80 (floors at y80, walk at y81):
- steam hall (39 x 30, 10 tall) behind the atrium's north wall, entered through the old y80 knock-out
  and seen from the atrium through two glazed bays. Marked pads (black-granite footprint, copper line
  on the aisle side; a one-block gap between different machines, back rows against the wall):
  smeltery with a casting strip, Purifier, Presser, Blender in the back row; Squasher, Fuser, Hearth
  at the west end of the front row and the ore line (Grinder, Grinder, Separator, one block apart)
  at the east end; a single-block bench on a grate trench along the east wall. Planters under the
  windows.
- service spine: the stage-1 tunnel continued north between the steam and power halls, with doors
  into both. Cables and steam pipes run in its trench.
- power hall (33 x 30, 12 tall): steam side with four touching coke ovens and two large boilers
  against the north wall, an infinite-water pool and single-block steam turbines on the west wall;
  oil side with a 9 x 9 refinery bay, two fuel tanks beside it, two generator rows a few blocks on,
  and two Large Combustion Engine pads reserved for EV.
Floor lamps sit only in the aisles, on a regular grid (threshold_lib.aisle_lights).

y100 (floors at y100):
- north corridor from the atrium's y100 knock-out, glazed into the halls on both sides, with
  shrubs at the piers and a knock-out at its far end for the multiblock hall (stage 3).
- LV hall and MV hall west of the corridor: machine rows on grate trenches along both long walls
  and a back-to-back island row down the middle.
- storage room east of the corridor, left empty for drawers, compartments and the crafting station.

Labels: Nuclear Control info panels over the doors (permanent); standing signs on every machine pad
(temporary, removed when the machine goes in).

The box overlaps stage 1 (the atrium's north wall and the service tunnel). If stage 1 isn't in the
server world yet, its result is laid in first so the overlap carries both stages. Paste stage 1
first, then this: stage 1's box would revert this stage's changes in the overlap. Same paste spot as
stage 1: the notch on top of the meteorite, feet in (-558, 130, -229).
"""
import sys
from pathlib import Path

from gtnhbuild import terrain

sys.path.insert(0, str(Path(__file__).resolve().parent))
from threshold_lib import (  # noqa: E402
    COPPER, GLASS, GRAN, GRANB, GRASS, LEAVES, PLANTS, STAGES, WATER, Space, aisle_lights, carve,
    clean_ores, doorway, h, hanging_vine, info_panel, knockout, lay_stages, pad as lay_pad, sign, trench,
    trench_run,
)

BOX = STAGES["industry"].box
ANCHOR = (-558, 130, -229)

terrain.sync(*BOX)
W = terrain.open_world()
build = b = W.load(*BOX, name="threshold-industry")
b.anchor = ANCHOR
lay_stages(b, W, BOX, ["gate_atrium"])

# ---- rooms ------------------------------------------------------------------------------------------
STEAM = ((-624, 81, -299), (-586, 90, -270))
SPINE = ((-583, 81, -300), (-581, 83, -287))
POWER = ((-579, 81, -305), (-547, 92, -276))
CORR = ((-595, 101, -300), (-591, 105, -270))
LV = ((-622, 101, -284), (-597, 106, -271))
MV = ((-622, 101, -300), (-597, 106, -287))
STORE = ((-589, 101, -284), (-578, 105, -271))
SPACES = {
    "steam": Space([STEAM], ceiling="flush", sconces=(80, 84)),
    "spine": Space([SPINE], kind="service", ceiling="flush"),
    "power": Space([POWER], ceiling="flush", sconces=(80, 84, 88)),
    "corridor": Space([CORR], ceiling="pendant", floor=100, sconces=(100,)),
    "lv": Space([LV], ceiling="pendant", floor=100, sconces=(100,)),
    "mv": Space([MV], ceiling="pendant", floor=100, sconces=(100,)),
    "store": Space([STORE], ceiling="pendant", floor=100, sconces=(100,)),
}
interior, zone = carve(b, SPACES)

# doors (copper-framed); the atrium ones reuse the stage-1 knock-out frames
doorway(b, "n", -594, -592, 81, 84, (-269,))        # atrium floor -> steam hall
doorway(b, "n", -594, -592, 101, 104, (-269,))      # atrium y100 gallery -> corridor
doorway(b, "e", -282, -280, 81, 83, (-585, -584))   # steam hall -> spine
doorway(b, "e", -282, -280, 81, 83, (-580,))        # spine -> power hall
doorway(b, "w", -279, -277, 101, 103, (-596,))      # corridor -> LV hall
doorway(b, "w", -295, -293, 101, 103, (-596,))      # corridor -> MV hall
doorway(b, "e", -279, -277, 101, 103, (-590,))      # corridor -> storage
DOOR_Z = {-596: [(-280, -276), (-296, -292)], -590: [(-280, -276)]}   # door spans incl. frames

# ---- windows ------------------------------------------------------------------------------------------
for xs in (range(-599, -596), range(-589, -586)):    # two bays in the atrium's north wall onto the steam hall
    xs = list(xs)
    for x in range(xs[0] - 1, xs[-1] + 2):
        for y in range(82, 90):
            frame = x in (xs[0] - 1, xs[-1] + 1) or y == 89
            b.set(x, y, -269, COPPER if frame else GLASS)
        b.set(x, 81, -269, GRANB)                    # sill
        for y in range(81, 90):                      # vines on the atrium side lose their wall here;
            v = b.get(x, y, -268)                    # strands above get a new glow-lichen cap on the
            if v is not None and v.name in ("minecraft:vine", "etfuturum:glow_lichen"):   # frame top
                b.set(x, y, -268, None)
        above = b.get(x, 90, -268)
        if above is not None and above.name == "minecraft:vine":
            b.set(x, 90, -268, None)
            hanging_vine(b, x, -268, 91, 91, "n")   # re-caps the strand at y90 against the frame
for wx in (-596, -590):                              # corridor walls glazed between pilasters
    for z in range(CORR[0][2], CORR[1][2] + 1):
        if z % 4 == 0 or any(a <= z <= c for a, c in DOOR_Z[wx]):
            continue
        if (wx - 1, 102, z) in interior and (wx + 1, 102, z) in interior:
            for y in range(102, 105):
                b.set(wx, y, z, GLASS)

# ---- machine pads (threshold_lib.pad) ---------------------------------------------------------------------
# Only the ore line keeps a one-block gap between machines for pipes and conveyors.
reserved: dict[str, set] = {"steam": set(), "power": set()}


def pad(room: str, x0: int, z0: int, w: int, d: int, front: str, y: int = 80) -> None:
    lay_pad(b, reserved[room], x0, z0, w, d, front, y)


def run(room: str, cells, y: int = 80, work: str | None = None) -> None:
    trench_run(b, reserved[room], cells, y, work)


# steam hall, back row against the north wall. Different machines keep a one-block gap for hatches,
# buses and pipes; identical ones may share a wall (here only the coke ovens and boilers do).
pad("steam", -624, -299, 5, 5, "s")                 # Tinkers' smeltery (up to 5 x 5 outside)
for x in (-623, -622, -621):                         # casting strip: table, basin, table
    b.set(x, 80, -293, GRANB)
    reserved["steam"].add((x, -293))
pad("steam", -618, -299, 9, 5, "s")                 # Purifier
pad("steam", -608, -299, 5, 7, "s")                 # Presser
pad("steam", -602, -299, 5, 5, "s")                 # Blender
# front row: Squasher, Fuser, Hearth at the west end; the ore line (Grinder -> Grinder -> Separator,
# one block apart) at the east end next to the spine door; room for more in between
pad("steam", -624, -287, 3, 7, "n")                 # Squasher
pad("steam", -620, -287, 3, 3, "n")                 # Fuser
pad("steam", -616, -287, 3, 3, "n")                 # Hearth
pad("steam", -602, -287, 3, 3, "n")                 # ore line 1: Grinder
pad("steam", -598, -287, 3, 3, "n")                 # ore line 2: Grinder
pad("steam", -594, -287, 5, 5, "n")                 # ore line 3: Separator
run("steam", [(x, -290) for x in range(-624, -586)])
run("steam", [(x, -279) for x in range(-624, -586)])
run("steam", [(-586, z) for z in range(-299, -283)], work="w")    # single-block bench, east wall
run("steam", [(-586, -281), (-585, -281), (-584, -281), (-583, -281), (-582, -281)])   # to the spine
run("steam", [(-593, -270), (-593, -269)])         # to the atrium floor ring
for x in range(-623, -586):                          # planters under the windows
    if -595 <= x <= -591:
        continue
    b.set(x, 80, -270, GRASS)
    b.set(x, 81, -270, LEAVES[0] if h(x, "steam") % 4 == 0 else PLANTS[h(x) % len(PLANTS)])
    reserved["steam"].add((x, -270))
# temporary signs on the pad front lines (they go when the machines go in)
for x, z, face, lines in (
        (-622, -294, "s", ("Smeltery", "casting below")), (-614, -294, "s", ("Purifier", "ore washer")),
        (-606, -292, "s", ("Presser", "forge hammer")), (-600, -294, "s", ("Blender", "mixer")),
        (-623, -288, "n", ("Squasher", "compressor")), (-619, -288, "n", ("Fuser", "alloy smelter")),
        (-615, -288, "n", ("Hearth", "furnace")), (-601, -288, "n", ("ORE LINE 1", "Grinder")),
        (-597, -288, "n", ("ORE LINE 2", "Grinder")), (-592, -288, "n", ("ORE LINE 3", "Separator")),
        (-587, -292, "w", ("Single blocks", "on the grate", "extractor etc"))):
    sign(b, x, 81, z, face, *lines)

# ---- spine and power hall --------------------------------------------------------------------------------
# steam side (west): coke ovens and large boilers against the walls, single-block steam turbines on the
# west wall. Oil side (east): refinery bay -> fuel tanks -> two generator rows, each a few blocks from
# the next; two Large Combustion Engine pads reserved for later.
run("power", [(-581, z) for z in range(-300, -286)])
run("power", [(-580, -281), (-579, -281)])
for k in range(4):                                  # coke ovens, touching, against the north wall
    pad("power", -579 + 3 * k, -305, 3, 3, "s")
pad("power", -579, -299, 3, 3, "s")                 # large boilers, touching
pad("power", -576, -299, 3, 3, "s")
for x in range(-572, -568):                         # infinite water: 4 x 2 source pool by the boilers
    for z in (-299, -298):
        b.set(x, 80, z, WATER)
        b.set(x, 79, z, GRAN)
        reserved["power"].add((x, z))
pad("power", -563, -305, 3, 4, "s")                 # Large Combustion Engines (EV), later
pad("power", -560, -305, 3, 4, "s")
for x in range(-566, -557):                         # refinery bay outline: distillery, mixers, reactors
    for z in range(-295, -286):
        if x in (-566, -558) or z in (-295, -287):
            b.set(x, 80, z, COPPER)
        reserved["power"].add((x, z))
pad("power", -556, -295, 3, 3, "w")                 # fuel tanks, touching, facing the refinery
pad("power", -556, -292, 3, 3, "w")
run("power", [(-579, z) for z in range(-294, -276) if not -283 <= z <= -279], work="e")   # steam turbines
run("power", [(-551, z) for z in range(-298, -277)], work="w")      # generator island row
run("power", [(-547, z) for z in range(-304, -276)], work="w")      # generator wall row
run("power", [(x, -277) for x in range(-578, -547)])
for x, z, face, lines in (
        (-578, -302, "s", ("Coke oven",)), (-575, -302, "s", ("Coke oven",)), (-572, -302, "s", ("Coke oven",)),
        (-569, -302, "s", ("Coke oven",)), (-578, -296, "s", ("Large boiler",)), (-575, -296, "s", ("Large boiler",)),
        (-562, -301, "s", ("Large combustion", "engine (EV)")), (-559, -301, "s", ("Large combustion", "engine (EV)")),
        (-578, -290, "e", ("Steam turbines", "on the grate")), (-557, -293, "w", ("Fuel tanks",)),
        (-562, -286, "s", ("Refinery bay",)), (-550, -289, "e", ("Generators", "on the grate"))):
    sign(b, x, 81, z, face, *lines)
for room, ((x0, y0, z0), (x1, _, z1)) in (("steam", STEAM), ("power", POWER)):
    aisle_lights(b, (x0, y0, z0), (x1, y0, z1), 80, reserved[room])

# ---- y100: corridor, LV, MV, storage ---------------------------------------------------------------------
knockout(b, "n", -594, -592, 101, 104, CORR[0][2] - 1)   # far end: multiblock hall (threshold_works.py)
trench(b, [(-595, z) for z in range(-300, -268)], 100)
for z in range(CORR[0][2], CORR[1][2] + 1):          # shrubs at the piers
    if z % 4 == 0:
        b.set(-591, 100, z, GRASS)
        b.set(-591, 101, z, LEAVES[h(z) % 2])
for (x0, _, z0), (x1, _, z1) in (LV, MV):
    trench(b, [(x, z) for x in range(x0, x1 + 1) for z in (z0, z1)]
           + [(x, z) for x in range(x0 + 1, x1 - 2) for z in ((z0 + z1) // 2, (z0 + z1) // 2 + 1)], 100)

# storage is left empty: drawers, compartments and the crafting station go in by hand

# ---- labels: low-profile Nuclear Control panels over the copper lintels -------------------------------
# Each sits in the open row just in front of a doorway's lintel (frame width), fixed to the wall, with a
# transparent background so the copper shows through. Text colour by zone.
info_panel(b, (-595, 85, -268), (-591, 85, -268), "n", "STEAM HALL", text="orange")      # atrium y80
info_panel(b, (-595, 105, -268), (-591, 105, -268), "n", "LV  MV  STORAGE")             # atrium y100
info_panel(b, (-586, 84, -283), (-586, 84, -279), "e", "POWER HALL", text="yellow")      # steam hall
info_panel(b, (-579, 84, -283), (-579, 84, -279), "w", "STEAM HALL", text="orange")      # power hall
info_panel(b, (-595, 104, -280), (-595, 104, -276), "w", "LV HALL", text="green", background="black")  # corridor
info_panel(b, (-595, 104, -296), (-595, 104, -292), "w", "MV HALL", text="light_blue")
info_panel(b, (-591, 104, -280), (-591, 104, -276), "e", "STORAGE", text="light_gray")

clean_ores(b)
