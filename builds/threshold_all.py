"""Threshold base, every stage in one schematic: a single `//schem load threshold-all` + `//paste -o`
into a world that has none of the stages yet (the server).

The schematic covers the union of the stage boxes. It starts as the live terrain of that box; each
stage in STAGES order is then run and its whole box laid over it, so a later stage wins where boxes
overlap (it already carries the earlier stages' blocks there, see lay_stages). Cells outside every
stage box are the terrain as synced, so paste soon after running it.
"""
import runpy
import sys
from pathlib import Path

from gtnhbuild import terrain

sys.path.insert(0, str(Path(__file__).resolve().parent))
from threshold_lib import STAGES, box  # noqa: E402

ANCHOR = (-558, 130, -229)
LO = tuple(min(st.box[0][i] for st in STAGES.values()) for i in range(3))
HI = tuple(max(st.box[1][i] for st in STAGES.values()) for i in range(3))

terrain.sync(LO, HI)
W = terrain.open_world()
for name, st in STAGES.items():
    m = W.get(*st.marker) if st.marker else None
    if m is not None and (m.name, m.meta) == (st.marker_block.name, st.marker_block.meta):
        raise SystemExit(f"stage {name!r} is already in this world: paste the remaining stages one by one")
build = b = W.load(LO, HI, name="threshold-all")
b.anchor = ANCHOR

for name, st in STAGES.items():
    stage = runpy.run_path(str(Path(__file__).with_name(st.script)), run_name="__gtnhbuild__")["build"]
    for p in box(*st.box):
        blk = stage.blocks.get(p)
        if blk is None:
            b.blocks.pop(p, None)
        else:
            b.blocks[p] = blk
