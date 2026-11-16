"""Threshold base, stage 4: the y112 level north of the atrium (palette V1, see threshold_lib.py).

- Corridor north from the atrium's y112 gallery through its knock-out, glazed into the HV hall and
  the AE2 room.
- HV hall west of it (30 x 14, 6 tall): machine rows on grate trenches along both long walls and a
  back-to-back island row down the middle, as in the LV and MV halls below.
- Cleanroom bay (11 x 11, 10 tall), empty for the cleanroom multiblock.
- AE2 core room east of it (21 x 21, 14 tall): a 9 x 9 core pad (copper rim, black-granite field)
  for the ME controller, ringed by a grate cable trench, under four pendant lamps; a mezzanine at
  y119 round all four walls, copper-edged and glass-railed, reached by a stair along the west wall.

Labels: Nuclear Control panels over the doors (permanent); standing signs on the core pad and in the
cleanroom bay (temporary). The box overlaps stage 1 (the atrium's north wall) and stage 2's top
layer; whichever isn't in the server world yet is laid in first. Paste stages 1 and 2 first, then
relog once pasted (panels).
"""
import sys
from pathlib import Path

from gtnhbuild import terrain

sys.path.insert(0, str(Path(__file__).resolve().parent))
from threshold_lib import (  # noqa: E402
    CHAIN, COPPER, DIRS, GLASS, LAMP, STAGES, Space, aisle_lights, carve, checker, clean_ores, doorway, info_panel,
    lay_stages, pad, sign, trench,
)

BOX = STAGES["core"].box
ANCHOR = (-558, 130, -229)
FLOOR = 112

terrain.sync(*BOX)
W = terrain.open_world()
build = b = W.load(*BOX, name="threshold-core")
b.anchor = ANCHOR
lay_stages(b, W, BOX, ["gate_atrium", "industry"])

# ---- rooms ------------------------------------------------------------------------------------------
CORR = ((-591, 113, -299), (-587, 117, -270))
HV = ((-622, 113, -284), (-593, 118, -271))
CLEAN = ((-603, 113, -297), (-593, 122, -287))
AE2 = ((-585, 113, -295), (-565, 126, -275))
interior, _ = carve(b, {
    "corridor": Space([CORR], ceiling="pendant", floor=FLOOR, sconces=(FLOOR,)),
    "hv": Space([HV], ceiling="pendant", floor=FLOOR, sconces=(FLOOR,)),
    "clean": Space([CLEAN], ceiling="flush", sconces=(FLOOR, 116)),
    "ae2": Space([AE2], ceiling="flush", sconces=(FLOOR, 119)),
})
doorway(b, "n", -590, -588, 113, 116, (-269,))      # through stage 1's knock-out frame
doorway(b, "w", -279, -277, 113, 115, (-592,))      # corridor -> HV hall
doorway(b, "w", -293, -291, 113, 115, (-592,))      # corridor -> cleanroom bay
doorway(b, "e", -286, -284, 113, 115, (-586,))      # corridor -> AE2 room
DOOR_Z = {-592: [(-280, -276), (-294, -290)], -586: [(-287, -283)]}   # door spans incl. frames


def inside(p, room) -> bool:
    return all(room[0][i] <= p[i] <= room[1][i] for i in range(3))


for wx in (-592, -586):                             # corridor walls glazed between pilasters, into the HV
    for z in range(CORR[0][2], CORR[1][2] + 1):     # hall and the AE2 room (not the cleanroom bay)
        if z % 4 == 0 or any(a <= z <= c for a, c in DOOR_Z[wx]):
            continue
        if inside((wx - 1, 114, z), HV) or inside((wx + 1, 114, z), AE2):
            for y in range(114, 117):
                b.set(wx, y, z, GLASS)

# ---- HV hall: machine rows on trenches along both long walls, a back-to-back island in the middle ------
(x0, _, z0), (x1, _, z1) = HV
mid = (z0 + z1) // 2
trench(b, [(x, z) for x in range(x0, x1 + 1) for z in (z0, z1)]
       + [(x, z) for x in range(x0 + 1, x1 - 2) for z in (mid, mid + 1)], FLOOR)

# ---- cleanroom bay -------------------------------------------------------------------------------------
sign(b, (CLEAN[0][0] + CLEAN[1][0]) // 2, 113, (CLEAN[0][2] + CLEAN[1][2]) // 2, "e",
     "Cleanroom bay", "up to 11x11", "10 tall")

# ---- AE2 core room ---------------------------------------------------------------------------------------
(ax0, _, az0), (ax1, ay1, az1) = AE2
MEZZ = FLOOR + 7                                    # mezzanine floor block; walk at y120
RING = 3
reserved: set = set()
pad(b, reserved, -579, -289, 9, 9, "s", FLOOR)      # core pad 9 x 9 ...
for x in range(-579, -570):                         # ... with a copper rim instead of a front line
    for z in range(-289, -280):
        if x in (-579, -571) or z in (-289, -281):
            b.set(x, FLOOR, z, COPPER)
ring = [(x, z) for x in range(-580, -569) for z in range(-290, -279) if x in (-580, -570) or z in (-290, -280)]
trench(b, ring, FLOOR)                              # covers the pad's front line too
b.set(-575, FLOOR, -285, LAMP)                     # under the controller once it's built
sign(b, -580, 113, -285, "w", "ME controller", "up to 7x7x7")
for x in (-579, -571):                              # pendants over the pad corners, clear of a 7-tall controller
    for z in (-289, -281):
        for y in range(MEZZ + 2, ay1 + 1):
            b.set(x, y, z, CHAIN)
        b.set(x, MEZZ + 1, z, LAMP)

# Mezzanine: a three-wide ring at y119; the stair climbs south along the west wall from the door side,
# its top step level with the mezzanine.
floor = {(x, z) for x in range(ax0, ax1 + 1) for z in range(az0, az1 + 1)
         if x < ax0 + RING or x > ax1 - RING or z < az0 + RING or z > az1 - RING}
STAIR = [(x, -282 + i) for i in range(MEZZ - FLOOR) for x in (ax0, ax0 + 1)]
for x, z in STAIR:
    b.set(x, FLOOR + 1 + (z + 282), z, b.stairs("minecraft:quartz_stairs", "s"))
    floor.discard((x, z))
walk = floor | {(x, z) for x, z in STAIR if FLOOR + 1 + (z + 282) == MEZZ}
edge = {(x, z) for x, z in floor if any((x + dx, z + dz) not in walk and inside((x + dx, 113, z + dz), AE2)
                                        for dx, dz in DIRS.values())}

# floor lamps in the open floor under the mezzanine and round the pad, and in the cleanroom bay
aisle_lights(b, (ax0, FLOOR, az0), (ax1, FLOOR, az1), FLOOR, reserved | set(ring) | set(STAIR) | {(ax0, -285)},
             spacing=4, reach=4)
aisle_lights(b, (CLEAN[0][0], FLOOR, CLEAN[0][2]), (CLEAN[1][0], FLOOR, CLEAN[1][2]), FLOOR,
             {((CLEAN[0][0] + CLEAN[1][0]) // 2, (CLEAN[0][2] + CLEAN[1][2]) // 2)})
for x, z in floor:
    b.set(x, MEZZ, z, COPPER if (x, z) in edge else checker(x, z))
for x, z in edge:
    b.set(x, MEZZ + 1, z, b.block("minecraft:glass_pane"))

# ---- labels -------------------------------------------------------------------------------------------------
info_panel(b, (-591, 117, -268), (-587, 117, -268), "n", "HV  AE2  CLEANROOM")       # atrium y112 gallery
info_panel(b, (-591, 116, -280), (-591, 116, -276), "w", "HV HALL", text="magenta")
info_panel(b, (-591, 116, -294), (-591, 116, -290), "w", "CLEANROOM")
info_panel(b, (-587, 116, -287), (-587, 116, -283), "e", "AE2 CORE", text="cyan")

clean_ores(b)
