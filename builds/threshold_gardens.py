"""Threshold base, stage 5: the crop hall at y100, south of the atrium (palette V1, see threshold_lib.py).

Built around Basic (LV) Crop Managers (CropsNH, GTNH 2.9): a manager works an 11 x 11 area centred on
itself, two blocks up and down. The hall (25 x 28, 9 tall) holds four 11 x 11 fields in a 2 x 2 grid
with one-wide paths round them and a four-row aisle at the door. Each field is one layer:

- y101 crop sticks; y100 soil (laid as dirt: swap for farmland, fertilized dirt, stone, sand... per
  crop); y99 the "block below" some crops need (laid as granite bricks, swap per crop).
- The centre cell is the manager's spot: the soil and subsoil under it are left open as a chase, so
  power and fluid come up from below.
- Lamps hang on chains over every field (light 9+ at the crops; take some out for crops that want 10
  or less, such as oreberries).

Under the fields a service basement (floor y95, 3 tall) has the subsoil layer as its ceiling, so the
"block below" can be swapped from underneath without lifting crops, and carries the managers' cables
and pipes. A stair down from the door aisle, railed at the floor opening.

A one-wide service link leaves the cellar's north-east corner for the cable riser
(threshold_crop_link.py, its own schematic): crops out to storage and power, power and fluids in for
the managers. Grate trenches run from it along the cellar's north wall and under each manager chase.

Sky access only adds 2 nutrients (about +10% growth) once the managers supply water and fertilizer, so
the hall stays underground. Label: a Nuclear Control panel over the door on the atrium side. The box
overlaps stage 1 (the atrium's south wall), which is laid in first if it isn't in the server world yet.
Paste stage 1 first, then relog once pasted (panels).
"""
import sys
from pathlib import Path

from gtnhbuild import terrain

sys.path.insert(0, str(Path(__file__).resolve().parent))
from threshold_lib import (  # noqa: E402
    CHAIN, GRANB, LAMP, SMOOTH, STAGES, Space, aisle_lights, carve, clean_ores, doorway, info_panel,
    lay_stages, sign, trench,
)

BOX = STAGES["gardens"].box
ANCHOR = (-558, 130, -229)
FLOOR = 100                                         # hall floor = soil layer
BASE = 95                                           # basement floor; walk y96..98, subsoil ceiling y99

terrain.sync(*BOX)
W = terrain.open_world()
build = b = W.load(*BOX, name="threshold-gardens")
b.anchor = ANCHOR
lay_stages(b, W, BOX, ["gate_atrium"])

HALL = ((-605, 101, -252), (-581, 109, -225))
CELLAR = ((-605, BASE + 1, -252), (-581, FLOOR - 2, -225))
LINK_X = -584                                       # service link to the riser (threshold_crop_link.py)
LINK = ((LINK_X, BASE + 1, -254), (LINK_X, BASE + 3, -253))
carve(b, {"crops": Space([HALL], sconces=(FLOOR, 104)),
          "cellar": Space([CELLAR], kind="service"),
          "link": Space([LINK], kind="service")})
doorway(b, "s", -598, -596, 101, 104, (-253,))      # through stage 1's knock-out frame

(x0, _, z0), (x1, y1, z1) = HALL
FIELD = 11
FIELDS = [(fx, fz) for fx in (x0 + 1, x0 + 2 + FIELD) for fz in (z0 + 4, z0 + 5 + FIELD)]   # NW corners
DIRT = b.block("minecraft:dirt")
for fx, fz in FIELDS:
    cx, cz = fx + FIELD // 2, fz + FIELD // 2
    for x in range(fx, fx + FIELD):
        for z in range(fz, fz + FIELD):
            if (x, z) == (cx, cz):                  # manager chase: open down to the cellar
                b.set(x, FLOOR, z, None)
                b.set(x, FLOOR - 1, z, None)
            else:
                b.set(x, FLOOR, z, DIRT)
                b.set(x, FLOOR - 1, z, GRANB)
    for x in range(fx + 1, fx + FIELD, 4):          # lamps low over the field, every fourth cell
        for z in range(fz + 1, fz + FIELD, 4):
            for y in range(FLOOR + 4, y1 + 1):
                b.set(x, y, z, CHAIN)
            b.set(x, FLOOR + 3, z, LAMP)
    sign(b, cx, FLOOR + 1, fz, "n", "Crop manager", "(LV) at centre", "11x11, +-2 up", "cables below")

# Stair to the cellar along the north wall at the west end of the door aisle, descending west; the
# floor opening is railed on its aisle side and open at the top (east).
STAIR_X, STAIR_Z = range(x0 + 4, x0 - 1, -1), (z0, z0 + 1)
for i, x in enumerate(STAIR_X):
    for z in STAIR_Z:
        b.set(x, FLOOR, z, None)
        b.set(x, FLOOR - 1, z, None)
        b.set(x, FLOOR - 1 - i, z, b.stairs("minecraft:stone_brick_stairs", "e"))
hole = {(x, z) for x in STAIR_X for z in STAIR_Z}
rails = {(x, z0 + 2) for x in STAIR_X}
for x, z in rails:
    b.set(x, FLOOR + 1, z, b.ac("BalustradePlain", SMOOTH, front="s"))

# Cellar service trenches: from the link along the north wall, then down past each manager chase.
centres = [(fx + FIELD // 2, fz + FIELD // 2) for fx, fz in FIELDS]
runs = [(LINK_X, z) for z in (-254, -253)] + [(x, z0) for x in range(x0 + 6, LINK_X + 1)]
runs += [(cx, z) for cx in sorted({c[0] for c in centres}) for z in range(z0 + 1, z1)]
trench(b, runs, BASE)

fields = {(x, z) for fx, fz in FIELDS for x in range(fx, fx + FIELD) for z in range(fz, fz + FIELD)}
aisle_lights(b, (x0, FLOOR, z0), (x1, FLOOR, z1), FLOOR, fields | hole | rails)
aisle_lights(b, (x0, BASE, z0), (x1, BASE, z1), BASE, hole | set(runs) | set(centres))

info_panel(b, (-599, 105, -254), (-595, 105, -254), "s", "CROP HALL", text="lime")    # atrium y100 gallery

clean_ores(b)
