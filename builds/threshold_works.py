"""Threshold base, stage 3: the multiblock hall at y100, north of the corridor (palette V1, see
threshold_lib.py).

- The y100 corridor continues through its far-end knock-out (z -301) for six blocks, then a short
  passage east opens into the multiblock hall.
- Multiblock hall (37 x 19, 14 tall; floor y100, above the power hall). Marked pads (black-granite
  footprint, copper line on the aisle side; a one-block gap between different machines, identical
  ones side by side, back rows against the walls): north row EBF, EBF, vacuum freezer, implosion
  compressor, two large chemical reactors, pyrolyse oven and two distillation towers (up to 12 tall
  fits); south row processing array, multi smelter, industrial centrifuge, electrolyzer and oil
  cracking unit, the rest of the row left open.
  A grate trench runs down the central aisle and back to the corridor. Lamps in the ceiling, the
  pilasters and the aisle floor.

Labels: a Nuclear Control panel over the passage on the corridor side; standing signs on the pads
(temporary). The box overlaps stage 2 (the corridor's end), which is laid in first if it isn't in
the server world yet. Paste stages 1 and 2 first, then relog once pasted (panels).
"""
import sys
from pathlib import Path

from gtnhbuild import terrain

sys.path.insert(0, str(Path(__file__).resolve().parent))
from threshold_lib import (  # noqa: E402
    STAGES, Space, aisle_lights, carve, clean_ores, doorway, info_panel, lay_stages, pad, sign, trench_run,
)

BOX = STAGES["works"].box
ANCHOR = (-558, 130, -229)

terrain.sync(*BOX)
W = terrain.open_world()
build = b = W.load(*BOX, name="threshold-works")
b.anchor = ANCHOR
lay_stages(b, W, BOX, ["industry"])

# ---- rooms ------------------------------------------------------------------------------------------
CORR = ((-595, 101, -307), (-591, 105, -302))
LINK = ((-590, 101, -306), (-588, 103, -304))
HALL = ((-587, 101, -321), (-551, 114, -303))
carve(b, {
    "corridor": Space([CORR], ceiling="pendant", floor=100, sconces=(100,)),
    "link": Space([LINK], kind="service"),
    "hall": Space([HALL], ceiling="flush", sconces=(100, 108)),
})
doorway(b, "n", -594, -592, 101, 104, (-301,))      # through stage 2's knock-out frame
doorway(b, "e", -306, -304, 101, 103, (-590,))      # corridor -> passage
doorway(b, "e", -306, -304, 101, 103, (-588,))      # passage -> hall

# ---- pads -----------------------------------------------------------------------------------------------
reserved: set = set()
# Rows run east from their start; different machines keep a one-block gap for hatches, buses and
# pipes, identical ones sit side by side and may share a wall.
NORTH = [  # (width, depth, sign text), back against the north wall
    (3, 3, ("EBF", "3x3, 4 tall")), (3, 3, ("EBF", "3x3, 4 tall")),
    (3, 3, ("Vacuum freezer", "3x3x3")), (3, 3, ("Implosion", "compressor")),
    (3, 3, ("Large chemical", "reactor")), (3, 3, ("Large chemical", "reactor")),
    (5, 5, ("Pyrolyse oven", "5x5, 4 tall")),
    (3, 3, ("Distillation", "tower 3x3", "up to 12 tall")), (3, 3, ("Distillation", "tower 3x3")),
]
SOUTH = [  # back against the south wall; the west end stays clear for the passage
    (3, 3, ("Processing", "array")), (3, 3, ("Multi smelter",)),
    (3, 3, ("Industrial", "centrifuge")), (3, 3, ("Industrial", "electrolyzer")),
    (5, 3, ("Oil cracking", "unit 5x3")),
]


def row(entries, x0: int, z_back: int, front: str) -> None:
    """Pads along a wall; the sign's first line names the machine type."""
    prev = None
    for w, d, text in entries:
        if prev is not None and text[0] != prev:
            x0 += 1                                 # gap between different machines
        z0 = z_back if front == "s" else z_back - d + 1
        pad(b, reserved, x0, z0, w, d, front, 100)
        sign(b, x0 + w // 2, 101, z0 + d if front == "s" else z0 - 1, front, *text)
        x0 += w
        prev = text[0]
    assert x0 - 1 <= HALL[1][0], f"row runs past the hall's east wall: {x0 - 1}"


row(NORTH, HALL[0][0], HALL[0][2], "s")
row(SOUTH, -583, HALL[1][2], "n")

trench_run(b, reserved, [(-595, z) for z in range(-307, -300)] + [(x, -305) for x in range(-594, -587)]
           + [(-587, z) for z in range(-312, -305)] + [(x, -312) for x in range(-587, -550)], 100)
aisle_lights(b, (HALL[0][0], 100, HALL[0][2]), (HALL[1][0], 100, HALL[1][2]), 100, reserved)
aisle_lights(b, (CORR[0][0], 100, CORR[0][2]), (LINK[1][0], 100, CORR[1][2]), 100,
             reserved | {(x, z) for x in range(-590, -587) for z in (-307, -303)}, spacing=3)

# ---- label ----------------------------------------------------------------------------------------------
info_panel(b, (-591, 104, -307), (-591, 104, -303), "e", "MULTIBLOCKS", text="red")

clean_ores(b)
