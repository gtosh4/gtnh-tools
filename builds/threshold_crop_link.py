"""Threshold base, stage 6: the crop hall's service link to the riser (palette V1, see threshold_lib.py).

A one-wide service passage at cellar level (floor y95), behind the atrium's east wall, from the crop
cellar's north-east corner (stage 5 opens the cellar end) north to the cable riser, where it comes out
beside the riser's ladder. A grate trench runs its length for cables and pipes. Down the ladder is the
y80 service tunnel to the power hall; up it the y100 landing and the atrium door to the corridor and
storage. It passes between the atrium and the lift's air tubes without touching either.

A separate schematic because its box has to stay clear of the lift-lobby info panels that a box
reaching from the crop hall to the riser would contain. Paste stage 1 first, then this and stage 5
in any order.
"""
import sys
from pathlib import Path

from gtnhbuild import terrain

sys.path.insert(0, str(Path(__file__).resolve().parent))
from threshold_lib import LAMP, SMOOTH, STAGES, WALL, lay_stages, trench  # noqa: E402

BOX = STAGES["crop_link"].box
ANCHOR = (-558, 130, -229)
X, FLOOR = -584, 95
Z_RISER, Z_END = -266, -255                         # opening into the riser's west wall .. join with stage 5

terrain.sync(*BOX)
W = terrain.open_world()
build = b = W.load(*BOX, name="threshold-crop-link")
b.anchor = ANCHOR
lay_stages(b, W, BOX, ["gate_atrium"])

for z in range(Z_RISER, Z_END + 1):
    for y in range(FLOOR + 1, FLOOR + 4):
        b.set(X, y, z, None)                        # the cell at Z_RISER is the riser's west wall
        if z != Z_RISER:                            # east side: line the rock (the west side is the
            east = LAMP if y == FLOOR + 2 and (z - Z_END) % 4 == 2 else WALL   # atrium's east wall)
            b.set(X + 1, y, z, east)
    b.set(X, FLOOR + 4, z, SMOOTH)
trench(b, [(X, z) for z in range(Z_RISER, Z_END + 1)], FLOOR)
