"""Example: small cottage with a stair gable roof, an ArchitectureCraft hip-roofed porch, and a
Carpenter's slope ramp. Run: python -m gtnhbuild run builds/example_cottage.py"""
from gtnhbuild import Build

build = b = Build("example_cottage")

stone = b.block("minecraft:stonebrick")
planks = b.block("minecraft:planks:1")          # spruce
log = b.pillar("minecraft:log:1", "y")          # spruce log, vertical

# footprint x 0..8, z 0..6; floor at y=0, walls y=1..4
b.fill((0, 0, 0), (8, 0, 6), stone)
b.walls((0, 1, 0), (8, 4, 6), planks)
for x, z in ((0, 0), (8, 0), (0, 6), (8, 6)):
    b.fill((x, 1, z), (x, 4, z), log)
b.fill((1, 4, 0), (7, 4, 0), b.pillar("minecraft:log:1", "x"))   # beams along x
b.fill((1, 4, 6), (7, 4, 6), b.pillar("minecraft:log:1", "x"))

# windows and door (north side faces the porch)
for x in (2, 6):
    b.fill((x, 2, 0), (x, 3, 0), "minecraft:glass_pane")
    b.fill((x, 2, 6), (x, 3, 6), "minecraft:glass_pane")
b.clear((4, 1, 0), (4, 2, 0))

# stair gable roof, ridge east-west, spruce stairs, gable ends filled with planks
b.gable_roof((0, 5, 0), (8, 5, 6), "minecraft:spruce_stairs", fill=planks, ridge_axis="x",
             slab="minecraft:wooden_slab:1")

# porch: 3x3 stone slab floor north of the door, ArchitectureCraft hip roof on fence posts
b.fill((3, 0, -3), (5, 0, -1), stone)
for x, z in ((3, -3), (5, -3)):
    b.fill((x, 1, z), (x, 3, z), "minecraft:fence")
roof = b.block("minecraft:planks:5")              # dark oak
y = 4
b.set(4, y, -3, b.ac("Roof Tile", roof, front="n"))
b.set(3, y, -3, b.ac("Roof Outer Corner", roof, front="w"))   # slopes west + north
b.set(5, y, -3, b.ac("Roof Outer Corner", roof, front="n"))   # slopes north + east
b.set(3, y, -2, b.ac("Roof Tile", roof, front="w"))
b.set(5, y, -2, b.ac("Roof Tile", roof, front="e"))
b.set(4, y, -2, b.ac("Hip Roof Ridge", roof))
b.set(3, y, -1, b.ac("Roof Tile", roof, front="w"))
b.set(5, y, -1, b.ac("Roof Tile", roof, front="e"))
b.set(4, y, -1, roof)

# Carpenter's slope ramp up to the door from the west, covered in stone bricks
b.set(2, 0, -2, b.cb_slope(stone, faces="w"))

# Forge Multipart microblocks: stone-brick sills (2/8 edge) under the north windows, against the wall
for x in (2, 6):
    b.add_micro(x, 1, -1, b.mb("edge", stone, "us", 2))

# Lighting with microblocks: a glowstone cover on the ceiling and two white Lapis Caelestis panels
# (Extra Utilities, light 15, full-bright) on the north/south walls inside; an Anti Block-capped
# glow ArchitectureCraft slab marks the porch (glow shapes emit 15).
b.add_micro(4, 4, 3, b.mb("face", "minecraft:glowstone", "up", 1))
b.add_micro(4, 3, 1, b.mb("face", "ExtraUtilities:greenscreen:0", "n", 2))
b.add_micro(4, 3, 5, b.mb("face", "ExtraUtilities:greenscreen:0", "s", 2))
b.set(4, 3, -2, b.ac("Slab", "chisel:antiBlock:0", up="d", glow=True))
