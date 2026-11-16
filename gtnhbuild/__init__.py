"""GTNH building toolkit: design builds in Python, export .schematic, preview them.

    from gtnhbuild import Build
    b = Build("cottage")
    b.fill((0, 0, 0), (8, 0, 6), "minecraft:stonebrick")
    b.save()                       # -> Threshold/.minecraft/schematics/cottage.schematic
    b.preview("out/cottage")       # iso PNG, slices PNG, BOM, HTML viewer

See .claude/skills/gtnh-build/SKILL.md for the full workflow.
"""
from .build import AIR, Block, Build
from .modblocks import ac_shape, carpenters, cb_block, cb_slope, cb_stairs
from .palette import Palette, default as palette

__all__ = ["AIR", "Block", "Build", "Palette", "palette", "ac_shape", "carpenters", "cb_block", "cb_slope",
           "cb_stairs"]
