"""Threshold base, stage 1 (palette V1 "Observatory Verdigris"), carved into the live server terrain:

- east-cliff gate: dressed marble facade, copper-and-glass conservatory with pool, planters and two
  birches, and a checkered plaza opening onto the meteorite courtyard: the AE2 meteorite core (left
  untouched) on an island in a lit moat, copper ring, compass-spoke paving, benches, planters, lamp
  posts and a marble retaining wall;
- gate hall and entrance gallery at y126 into the atrium;
- atrium shaft 15 x 15 from the y80 floor up to a copper-ribbed glass roof laid along the mountain's
  own contour, galleries at y100 / y112 / y126 with balustrades, hedges and hanging leaves, vines on
  the walls, a cascade from the top of the west wall into a pool, a distillation-tower pad;
- lift: a lobby off the atrium's east side on every level with a 3x3 OpenBlocks elevator pad
  (jump = up, sneak = down) linking y80 / 100 / 112 / 126 and a landing on the mountainside;
- services: copper-grate trenches in every floor and gallery, a cable riser (open chase, landings,
  maintenance ladder), a y80 service tunnel to the future power hall, and framed knock-out panels
  where the steam hall, the y100 corridor, the y112 level and the crop hall join (later stages);
- the approach: a three-wide mossy stone-brick path cut into the mountain along its contours, from
  the grass at the eastern foot up the south-east shoulder and along the crater rim, through a cutting
  into the courtyard on its east spoke, lanterns at the bends and every few steps;
- ores left showing on any carved or outdoor face are swapped for the rock around them.

Floors are the block layer at y80 / 100 / 112 / 126 (you walk one above). The whole box is exported
with the terrain it was carved from, so the paste reproduces everything it doesn't change; the script
syncs the server world first. Paste soon after running it.
"""
import math
import sys
from pathlib import Path

from gtnhbuild import terrain

sys.path.insert(0, str(Path(__file__).resolve().parent))
from threshold_lib import (  # noqa: E402
    CHAIN, CHIS, COPPER, DIRS, GLASS, GRAN, GRANB, GRASS, GRATE, LAMP, LEAVES, PLANTS, SMOOTH, SOFT, STAGES,
    STONE, WALL, WATER, OPPOSITE, Space, carve, checker, clean_ores, h, hanging_vine, info_panel,
    knockout, lamp_post, solid_top, trench,
)

BOX = STAGES["gate_atrium"].box
# Paste anchor: stand on the top sky-stone block of the meteorite core (right above the Mysterious
# Cube) -> feet in block (-558, 130, -229).
ANCHOR = (-558, 130, -229)

terrain.sync(*BOX)
W = terrain.open_world()
build = b = W.load(*BOX, name="threshold-gate-atrium")
b.anchor = ANCHOR

# ---- carved rooms: interior air, then a shell lining every face that touches rock ------------------
ATRIUM = ((-600, 81, -268), (-586, 140, -254))
LEVELS = (80, 100, 112, 126)          # floor blocks; galleries at 100/112/126
SPACES = {
    "atrium": Space([ATRIUM], sconces=LEVELS),
    "riser": Space([((-583, 81, -268), (-581, 140, -266))], kind="service", ceiling_block=GRANB),
    "tunnel": Space([((-583, 81, -286), (-581, 83, -269))], kind="service", ceiling="flush"),
    "hall": Space([((-590, 127, -239), (-579, 134, -231))], ceiling="pendant", floor=126, sconces=(126,)),
    "gallery": Space([((-595, 127, -253), (-589, 131, -232))], ceiling="pendant", floor=126, sconces=(126,)),
}
# Lift lobby east of the atrium on every level: 5x5x4 room, door from the atrium, a 3x3 floor of
# OpenBlocks elevator blocks against the back wall, facing the door. Elevators in one column link when
# they share a colour, are at most 20 apart and have at most 4 non-air blocks between them (server
# OpenBlocks.cfg: searchDistance=20, maxPassThrough=4), so each pad column has an air tube from the
# lobby ceiling up to the pad above; the top pad comes out on the mountainside east of the skylight.
LOBBY_X, LOBBY_Z = (-584, -580), (-264, -260)
PADS = [(x, z) for x in range(LOBBY_X[1] - 2, LOBBY_X[1] + 1) for z in range(LOBBY_Z[0] + 1, LOBBY_Z[1])]
for L in LEVELS:
    SPACES[f"lobby{L}"] = Space([((LOBBY_X[0], L + 1, LOBBY_Z[0]), (LOBBY_X[1], L + 4, LOBBY_Z[1]))],
                                sconces=(L,))
DOORS = []                            # through the atrium's east wall: riser, lift lobby
for L in LEVELS:
    DOORS.append(("riser", [(x, y, -267) for x in (-585, -584) for y in (L + 1, L + 2)]))
    DOORS.append((f"lobby{L}", [(-585, y, z) for z in range(-263, -260) for y in range(L + 1, L + 4)]))
interior, zone = carve(b, SPACES, DOORS)

# ---- atrium galleries -------------------------------------------------------------------------------
(ax0, _, az0), (ax1, _, az1) = ATRIUM
CASCADE_Z = (-262, -260)


def wall_side(x: int, z: int) -> str | None:
    """Direction of the atrium wall a cell in the outer 2-wide ring belongs to."""
    if x <= ax0 + 1:
        return "w"
    if x >= ax1 - 1:
        return "e"
    if z <= az0 + 1:
        return "n"
    if z >= az1 - 1:
        return "s"
    return None


def on_wall(x: int, z: int) -> bool:
    return x in (ax0, ax1) or z in (az0, az1)


for L in LEVELS[1:]:
    ledge = {(x, z) for x in range(ax0, ax1 + 1) for z in range(az0, az1 + 1)
             if wall_side(x, z) and not (x <= ax0 + 1 and CASCADE_Z[0] <= z <= CASCADE_Z[1])}
    if L == 100:                                    # distillation tower pad, NW corner
        ledge |= {(x, z) for x in range(ax0, ax0 + 6) for z in range(az0, az0 + 6)}
    for x, z in ledge:
        if on_wall(x, z):
            continue
        b.set(x, L, z, checker(x, z))
        b.set(x, L - 1, z, COPPER)                  # copper band under every gallery edge
    trench(b, [(x, z) for x, z in ledge if on_wall(x, z)], L)
    # balustrades on void edges, newels with lamps on outer corners, hedges every fifth cell
    for x, z in ledge:
        voids = [d for d, (dx, dz) in DIRS.items()
                 if (x + dx, z + dz) not in ledge and ax0 <= x + dx <= ax1 and az0 <= z + dz <= az1]
        if not voids:
            continue
        if len(voids) > 1:
            b.set(x, L + 1, z, SMOOTH)
            b.set(x, L + 2, z, LAMP)
        elif (x + z) % 5 == 0:
            b.set(x, L + 1, z, LEAVES[(x * z) % 2])
        else:
            # the rail is the shape's back (local south): front points away from the drop
            b.set(x, L + 1, z, b.ac("BalustradePlain", SMOOTH, front=OPPOSITE[voids[0]]))
        if not on_wall(x, z):                      # leaves hanging below the gallery edge
            for k in range(h(x, z, L) % 4):
                b.set(x, L - 2 - k, z, LEAVES[(x + z + k) % 2])
    if L == 100:                                    # mark the 3x3 tower footprint
        for x in range(ax0 + 2, ax0 + 5):
            for z in range(az0 + 2, az0 + 5):
                b.set(x, L, z, GRAN if (x, z) == (ax0 + 3, az0 + 3) else COPPER)

# vines down the walls under each gallery, each strand capped by a glow-lichen tuft so it stops there
for L_above, L in zip(LEVELS[1:], LEVELS):
    for x in range(ax0, ax1 + 1):
        for z in range(az0, az1 + 1):
            side = wall_side(x, z) if on_wall(x, z) else None
            if side is None or (side == "w" and CASCADE_Z[0] - 1 <= z <= CASCADE_Z[1] + 1):
                continue
            n = 2 + h(x, z, L_above, "v") % 6
            hanging_vine(b, x, z, L_above - 3, max(L_above - 2 - n, L + 5), side)

# y80 floor: trench ring along the walls, pool under the cascade
trench(b, [(x, z) for x in range(ax0, ax1 + 1) for z in range(az0, az1 + 1)
        if on_wall(x, z) and not (x == ax0 and CASCADE_Z[0] - 1 <= z <= CASCADE_Z[1] + 1)], 80)
for x in range(ax0, ax0 + 3):
    for z in range(CASCADE_Z[0] - 1, CASCADE_Z[1] + 2):
        b.set(x, 80, z, WATER)
        b.set(x, 79, z, GRAN)
for z in range(CASCADE_Z[0] - 2, CASCADE_Z[1] + 3):
    b.set(ax0 + 3, 81, z, CHIS)
for x in range(ax0, ax0 + 3):
    b.set(x, 81, CASCADE_Z[0] - 2, CHIS)
    b.set(x, 81, CASCADE_Z[1] + 2, CHIS)

# ---- skylight: a copper-ribbed glass roof laid along the mountain's own contour ---------------------
# Each column of the shaft is roofed at the slope's height there (3x3 mean of the terrain), each column
# of its wall ring at that column's own height, so the mountain keeps its shape outside with a glass
# window set into it. Steps between columns are glazed down to the lower neighbour; ring walls are
# glazed wherever the slope outside falls below them. Never below 133: clear of the y126 gallery and
# the entrance gallery's ceiling (132).
cx, cz = (ax0 + ax1) // 2, (az0 + az1) // 2
TOPS = {(x, z): solid_top(W, x, z) for x in range(ax0 - 2, ax1 + 3) for z in range(az0 - 2, az1 + 3)}
ROOF = {}
for x in range(ax0 - 1, ax1 + 2):
    for z in range(az0 - 1, az1 + 2):
        ring = not (ax0 <= x <= ax1 and az0 <= z <= az1)
        t = TOPS[x, z] if ring else round(sum(TOPS[x + i, z + k] for i in (-1, 0, 1) for k in (-1, 0, 1)) / 9)
        ROOF[x, z] = max(t, 133)
for (x, z), r in ROOF.items():
    for y in range(r + 1, 166):
        b.set(x, y, z, None)
    if ax0 <= x <= ax1 and az0 <= z <= az1:
        for y in range(141, r):                     # the shaft rises to its roof
            b.set(x, y, z, None)
        low = min(ROOF[x + dx, z + dz] for dx, dz in DIRS.values())
        grid = abs(x - cx) == 3 or abs(z - cz) == 3  # ribs: 4 / 5 / 4 panes inside the copper curb
        pane = LAMP if (x, z) == (cx, cz) else COPPER if grid else GLASS
        for y in range(min(low + 1, r), r + 1):
            b.set(x, y, z, pane)
        continue
    out = [(dx, dz) for dx, dz in DIRS.values() if (x + dx, z + dz) not in ROOF]
    corner = len(out) > 1
    for y in range(81, r + 1):
        if (x, y, z) in interior:
            continue
        exposed = any(b.get(x + dx, y, z + dz) is None and (x + dx, y, z + dz) not in interior for dx, dz in out)
        if y == r or (exposed and corner):
            b.set(x, y, z, COPPER)                  # curb along the roof edge, posts at the corners
        elif exposed:
            b.set(x, y, z, GLASS)                   # a window wherever the slope outside drops away
        elif y > 140:
            b.set(x, y, z, WALL)

# cascade: one source in a niche near the top of the west wall; it steps out one block and falls
nz = (CASCADE_Z[0] + CASCADE_Z[1]) // 2
ny = ROOF[ax0 - 1, nz] - 2
for p in ((ax0 - 2, ny, nz), (ax0 - 1, ny - 1, nz), (ax0 - 1, ny + 1, nz), (ax0 - 1, ny, nz - 1), (ax0 - 1, ny, nz + 1)):
    b.set(*p, COPPER)
b.set(ax0 - 1, ny, nz, WATER)


# ---- riser: landings with a ladder hole, open cable chase on the east side --------------------------
(rx0, _, rz0), (rx1, _, rz1) = SPACES["riser"].boxes[0]
for L in LEVELS[1:]:
    for x in range(rx0, rx1):
        for z in range(rz0, rz1 + 1):
            if (x, z) != (rx0, rz1):
                b.set(x, L, z, GRATE)
for y in range(81, 141):
    b.set(rx0, y, rz1, b.facing("minecraft:ladder", "n"))
for L in LEVELS:                                    # door spurs carry the gallery trenches in
    trench(b, [(-585, -267), (-584, -267)], L)
trench(b, [(rx1, z) for z in range(-286, rz1 + 1)], 80)  # chase + tunnel trench

# ---- lift: a 3x3 elevator pad in every lobby floor and on the mountainside --------------------------
ELEVATOR = b.block("OpenBlocks:elevator", 9)      # cyan; pads only link to the same colour
stops = list(LEVELS) + [141]
pad_c = PADS[len(PADS) // 2]
for L, nxt in zip(stops, stops[1:]):
    for x, z in PADS:
        b.set(x, L, z, ELEVATOR)
        if (x, z) == pad_c:
            b.set(x, L + 5, z, LAMP)                # ceiling light over the pad centre: 1 of the 4 allowed
        for y in range(L + 6, nxt):                 # the rest of the way up is an air tube
            b.set(x, y, z, None)
# top stop: the pad comes out on the mountainside east of the skylight, in a 5x5 landing levelled at 141
for x in range(PADS[0][0] - 1, PADS[-1][0] + 2):
    for z in range(PADS[0][1] - 1, PADS[-1][1] + 2):
        for y in range(solid_top(W, x, z) + 1, 141):
            if (x, z) not in PADS:                  # pad columns are the lift tube
                b.set(x, y, z, STONE)
        b.set(x, 141, z, ELEVATOR if (x, z) in PADS else checker(x, z))
        for y in range(142, 166):
            b.set(x, y, z, None)
for x, z in ((PADS[0][0] - 1, PADS[0][1] - 1), (PADS[-1][0] + 1, PADS[-1][1] + 1)):
    lamp_post(b, x, 141, z)                         # two diagonal corners light the landing
for L in LEVELS:                                    # copper door frame on the atrium side
    for y in range(L + 1, L + 5):
        b.set(-585, y, -264, COPPER)
        b.set(-585, y, -260, COPPER)
    for z in range(-263, -260):
        b.set(-585, L + 4, z, COPPER)

# ---- gate hall, gallery, facade, conservatory, plaza ------------------------------------------------
trench(b, [(-589, z) for z in range(-253, -239)] + [(x, -239) for x in range(-589, -578)], 126)
FX = -578                                           # facade plane
for z in range(-246, -223):
    for y in range(126, 141):
        if y == 126:
            blk = GRANB
        elif z % 4 == 0:
            blk = LAMP if y == 133 else GRANB
        elif y == 127:
            blk = GRANB
        elif y == 138:
            blk = CHIS
        elif y == 139:
            blk = COPPER
        else:
            blk = WALL
        b.set(FX, y, z, blk)
for y in range(127, 132):                           # doorway, copper frame
    for z in range(-237, -232):
        b.set(FX, y, z, None)
    b.set(FX, y, -238, COPPER)
    b.set(FX, y, -232, COPPER)
for z in range(-238, -231):
    b.set(FX, 132, z, COPPER)

PX0, PX1, PZ0, PZ1 = -577, -566, -246, -224        # plaza floor
for x in range(PX0, PX1 + 1):
    for z in range(PZ0, PZ1 + 1):
        for y in range(127, 166):
            b.set(x, y, z, None)
        for y in range(120, 126):
            if b.get(x, y, z) is None:
                b.set(x, y, z, STONE)
        b.set(x, 126, z, COPPER if x in (PX0, PX1) or z in (PZ0, PZ1) else checker(x, z))
for z in (PZ0 - 1, PZ1 + 1):                        # retaining walls where the slope rises
    for x in range(PX0, PX1 + 1):
        top = solid_top(W, x, z)
        for y in range(127, min(top, 140) + 1):
            b.set(x, y, z, WALL)
        if top >= 127:
            b.set(x, min(top, 140) + 1, z, CHIS)
MX, MZ = -558, -229                                 # meteorite core centre (untouched, r < CORE_R)
CORE_R, MOAT_R, RING_R, COURT_R = 4.6, 5.8, 6.6, 13.6


def court_r(x: int, z: int) -> float:
    return math.hypot(x - MX, z - MZ)


def in_court(x: int, z: int) -> bool:
    """Meteorite courtyard cell (the plaza proper keeps its own floor)."""
    return court_r(x, z) < COURT_R and not (x <= PX1 and PZ0 <= z <= PZ1)


for z in range(PZ0 + 1, PZ1):                       # balustrade where the plaza edge doesn't open onto the court
    if not in_court(PX1 + 1, z):
        b.set(PX1, 127, z, b.ac("BalustradePlain", SMOOTH, front="w"))   # rail on the court side
for z in (PZ0, PZ1):
    b.set(PX1, 127, z, GRANB)
    b.set(PX1, 128, z, GRANB)
    b.set(PX1, 129, z, LAMP)

CX0, CX1, CZ0, CZ1, CR = -577, -571, -243, -227, -235   # conservatory, ridge along x at z=CR


def roof_y(z: int) -> int:
    return 133 + (8 - abs(z - CR)) // 2


for x in range(CX0, CX1 + 1):
    for z in range(CZ0, CZ1 + 1):
        wall = x == CX1 or z in (CZ0, CZ1)
        post = (x == CX1 and (z - CZ0) % 4 == 0) or (z in (CZ0, CZ1) and (x - CX0) % 3 == 0)
        if wall:
            for y in range(127, 133):
                b.set(x, y, z, COPPER if post else GLASS)
        ry = roof_y(z)
        out = min(roof_y(z - 1) if z > CZ0 else ry, roof_y(z + 1) if z < CZ1 else ry)
        for y in range(133, ry + 1):
            if x == CX1 or y == ry or y > out:
                rib = y == ry and (x == (CX0 + CX1) // 2 or z == CR or z in (CZ0, CZ1))
                b.set(x, y, z, COPPER if rib or (x == CX1 and y == ry) else GLASS)
for y in range(127, 131):                           # garden door in the east gable
    for z in range(CR - 1, CR + 2):
        b.set(CX1, y, z, None)
    b.set(CX1, y, CR - 2, COPPER)
    b.set(CX1, y, CR + 2, COPPER)
for z in range(CR - 2, CR + 3):
    b.set(CX1, 130, z, COPPER)
for x in range(-575, -572):                         # lily pool
    for z in range(CR - 2, CR + 3):
        b.set(x, 125, z, GRAN)
        b.set(x, 126, z, WATER)
        if h(x, z) % 3 == 0:
            b.set(x, 127, z, "minecraft:waterlily")
for z in (CZ0 + 1, CZ1 - 1):                        # planter beds along the long glass walls
    for x in range(CX0, CX1):
        b.set(x, 126, z, GRASS)
        b.set(x, 127, z, PLANTS[(x + z) % len(PLANTS)])
for tz in (CZ0 + 2, CZ1 - 2):                       # two birches
    tx = CX0 + 1
    b.set(tx, 126, tz, GRASS)
    for y in range(127, 131):
        b.set(tx, y, tz, b.pillar("minecraft:log:2", "y"))
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            for y in (129, 130, 131):
                if (dx, dz) != (0, 0) or y == 131:
                    if b.get(tx + dx, y, tz + dz) is None:
                        b.set(tx + dx, y, tz + dz, LEAVES[1])
for x in (CX0 + 1, CX1 - 2):                        # lamps on chains under the ridge, 4 above the floor
    for y in range(131, roof_y(CR)):
        b.set(x, y, CR, CHAIN)
    b.set(x, 130, CR, LAMP)

# ---- meteorite courtyard ----------------------------------------------------------------------------
# A round court at plaza level (floor y126) opening off the plaza: the core sits on an island inside
# a lit moat ringed in copper, black-granite compass spokes run out to a promenade band, with benches
# facing the meteorite, planters behind them, lamp posts and a marble retaining wall where the crater
# rim is higher. Sky stone is never removed: fragments stay where they lie, inlaid in the paving.
def is_sky(blk) -> bool:
    return blk is not None and "Sky" in blk.name


SPOKES = [math.radians(a) for a in range(0, 360, 45)]
SEATS = [math.radians(a) for a in range(23, 360, 45)]


def angle_off(x: int, z: int, angles) -> float:
    a = math.atan2(z - MZ, x - MX)
    return min(abs((a - t + math.pi) % (2 * math.pi) - math.pi) for t in angles)


for x in range(MX - 15, MX + 16):
    for z in range(MZ - 15, MZ + 16):
        r = court_r(x, z)
        if r < CORE_R:                              # around the core: only plug gaps the moat could leak into
            if r >= CORE_R - 1 and (b.get(x, 126, z) is None or any(s in b.get(x, 126, z).name for s in SOFT)):
                b.set(x, 126, z, GRAN)
                if b.get(x, 125, z) is None:
                    b.set(x, 125, z, STONE)
            continue
        if x <= PX1 and PZ0 - 1 <= z <= PZ1 + 1:
            continue
        if r >= COURT_R:                            # retaining wall ring
            if r < COURT_R + 1:
                top = solid_top(W, x, z)
                cap = max(min(top, 140), 126) + 1
                for y in range(min(top + 1, 126), cap + 1):
                    if not is_sky(b.get(x, y, z)):
                        b.set(x, y, z, CHIS if y == cap else WALL)
            continue
        for y in range(127, 166):
            if not is_sky(b.get(x, y, z)):
                b.set(x, y, z, None)
        for y in range(120, 126):
            if b.get(x, y, z) is None:
                b.set(x, y, z, STONE)
        if is_sky(b.get(x, 126, z)):
            continue                                # fragment inlaid in the paving / rock in the moat
        if r < MOAT_R:
            b.set(x, 126, z, WATER)
            if not is_sky(b.get(x, 125, z)):
                b.set(x, 125, z, LAMP if h(x, z, "moat") % 3 == 0 else GRAN)
        elif r < RING_R:
            b.set(x, 126, z, COPPER)
        elif r >= COURT_R - 1.1:
            b.set(x, 126, z, GRAN)                  # promenade band
        elif 9.5 <= r < 10.5 and angle_off(x, z, SEATS) < math.radians(11):
            b.set(x, 126, z, GRASS)
            if b.get(x, 127, z) is None:
                b.set(x, 127, z, LEAVES[0] if h(x, z) % 3 == 0 else PLANTS[h(x, z, "p") % len(PLANTS)])
        elif r * math.sin(angle_off(x, z, SPOKES)) < 0.5:
            b.set(x, 126, z, GRAN)                  # compass spokes
        else:
            b.set(x, 126, z, SMOOTH)
for a in SEATS:                                     # benches facing the meteorite
    x, z = round(MX + 8 * math.cos(a)), round(MZ + 8 * math.sin(a))
    dx, dz = x - MX, z - MZ
    out = ("e" if dx > 0 else "w") if abs(dx) >= abs(dz) else ("s" if dz > 0 else "n")
    b.set(x, 127, z, b.stairs("minecraft:quartz_stairs", out))
for i in range(12):                                 # lamp posts on the promenade
    a = math.radians(i * 30 + 15)
    x, z = round(MX + 12.8 * math.cos(a)), round(MZ + 12.8 * math.sin(a))
    if in_court(x, z):
        b.set(x, 127, z, GRANB)
        b.set(x, 128, z, GRANB)
        b.set(x, 129, z, LAMP)

# ---- night lighting: lamp posts on the atrium floor and the plaza -----------------------------------
for dx in (-4, 4):
    for dz in (-4, 4):
        lamp_post(b, cx + dx, 80, cz + dz, 1)
for z in (PZ0 + 1, -239, -231, PZ1 - 1):
    lamp_post(b, -568, 126, z)

# ---- the approach: a path cut into the mountain from its eastern foot up to the courtyard -------------
# Three blocks wide, mossy stone-brick paving and steps laid along the live terrain: from the grass at
# the foot it climbs west up the south-east shoulder, turns north along the crater rim, and turns west
# again through a cutting in the rim into the courtyard on the axis of its east spoke, where lamps cap
# the retaining wall either side of the gap. Each section climbs at most one block and follows the
# ground where it can, cut in where the ground runs ahead and banked up on stone where it falls away;
# a mossy-cobble parapet guards drops of two or more. Lanterns on mossy-cobble posts at the bends and
# every few steps (in niches where the path is cut in).
COURT_Y = 126
PAVING = [b.block("minecraft:stonebrick"), b.block("minecraft:stonebrick:1"), b.block("minecraft:stonebrick:2")]
STEPS = ("minecraft:stone_brick_stairs", "etfuturum:mossy_stone_brick_stairs")
POST = b.block("minecraft:cobblestone_wall:1")
LANTERN = b.block("etfuturum:lantern")


def solid(p) -> bool:
    blk = b.get(*p)
    return blk is not None and not any(s in blk.name for s in SOFT)


def top_at(x: int, z: int) -> int:
    y = 165
    while y > 60 and not solid((x, y, z)):
        y -= 1
    return y


def run(d: str, lanes, along) -> list:
    """Sections walking `d` over the positions `along`, one cell per lane."""
    return [([(l, a) if d in "ns" else (a, l) for l in lanes], d) for a in along]


def bend(xs, zs) -> list:
    return [([(x, z) for x in xs for z in zs], None)]          # flat turn


SHOULDER, RIM, AXIS = (-210, -209, -208), (-537, -536, -535), (MZ - 1, MZ, MZ + 1)
ROUTE = (run("w", SHOULDER, range(-472, -535, -1)) + bend(RIM, SHOULDER)
         + run("n", RIM, range(-211, -228, -1)) + bend(RIM, AXIS)
         + run("w", AXIS, range(-538, -545, -1)))           # foot -> courtyard edge (x -544)

# Section heights, foot upwards: never down, up one only on a run (a step), rising when the ground
# ahead is higher or the steps left are needed to arrive level with the courtyard, never above it.
heights = []
y = min(solid_top(W, x, z) for x, z in ROUTE[0][0])
rises_left = sum(d is not None for _, d in ROUTE)
for cells, d in ROUTE:
    rises_left -= d is not None
    ground = min(solid_top(W, x, z) for x, z in cells)
    if d is not None and y < COURT_Y and max(ground, COURT_Y - rises_left) > y:
        y += 1
    assert y >= COURT_Y - rises_left, (cells, y)
    heights.append(y)
assert heights[-1] == COURT_Y, heights

path = {}
prev = heights[0]
for (cells, d), y in zip(ROUTE, heights):
    for x, z in cells:
        for yy in range(y + 1, 166):
            b.set(x, yy, z, None)
        if y > prev:
            b.set(x, y, z, b.stairs(STEPS[h(x, z) % 3 == 0], d))
        else:
            b.set(x, y, z, PAVING[0 if h(x, z) % 4 else 1 + h(x, z, 1) % 2])
        yy = y - 1
        while not solid((x, yy, z)):
            b.set(x, yy, z, STONE)
            yy -= 1
        path[(x, z)] = y
    prev = y


# A rest bench cut into the rim at the first bend, looking back down the shoulder to the valley.
ALCOVE = [(RIM[0] - 1, z) for z in SHOULDER]
for x, z in ALCOVE:
    y = path[(RIM[0], z)]
    b.set(x, y, z, STONE)
    b.set(x, y + 1, z, b.stairs("minecraft:stone_brick_stairs", "w"))
    b.set(x, y + 2, z, None)
    b.set(x, y + 3, z, None)


def beside(n) -> bool:
    """A cell next to the path that the path may build on (not the path, the bench alcove or the
    courtyard ring)."""
    return n not in path and n not in ALCOVE and court_r(*n) >= COURT_R + 1


def lantern(x: int, z: int, y: int) -> None:
    """Mossy-cobble post with a lantern beside the path: banked up on stone where the ground is low,
    in a niche where the path is cut in."""
    yy = y
    while not solid((x, yy, z)):
        b.set(x, yy, z, STONE)
        yy -= 1
    b.set(x, y + 1, z, POST)
    b.set(x, y + 2, z, LANTERN)


for (x, z), y in path.items():                      # parapet over drops of two or more
    for dx, dz in DIRS.values():
        n = (x + dx, z + dz)
        if not beside(n):
            continue
        t = top_at(*n)
        if y - t >= 2:
            for yy in range(t + 1, y + 1):
                b.set(n[0], yy, n[1], STONE)
            b.set(n[0], y + 1, n[1], POST)
lanterns = set()
for i, (cells, d) in enumerate(ROUTE):              # lanterns at the bends and every fourth step,
    if d is not None and i % 4 != 1:                # alternating sides
        continue
    if d is None:
        across = DIRS.values()
    else:
        across = ([(1, 0), (-1, 0)] if d in "ns" else [(0, 1), (0, -1)])[(i // 4) % 2:][:1]
    side = [(x + dx, z + dz) for x, z in cells for dx, dz in across if beside((x + dx, z + dz))]
    if side:
        nx, nz = min(side, key=lambda n: (top_at(*n), n))
        lantern(nx, nz, heights[i])
        lanterns.add((nx, nz))
for z in (SHOULDER[0] - 1, SHOULDER[-1] + 1):      # trailhead: a lantern either side at the foot
    lantern(-472, z, heights[0])
    lanterns.add((-472, z))
for z in (AXIS[0] - 1, AXIS[-1] + 1):               # lamps cap the retaining wall either side of the gap
    b.set(-544, top_at(-544, z), z, LAMP)

# Overgrowth: vines hanging down the deeper cut faces (above head height), grass, ferns and flowers on
# the verges.
for (x, z), y in path.items():
    for side, (dx, dz) in DIRS.items():
        n = (x + dx, z + dz)
        if not beside(n) or n in lanterns:
            continue
        t = top_at(*n)
        if t >= y + 4 and h(x, z, side, "vine") % 5 < 2:
            hanging_vine(b, x, z, t, max(y + 3, t - 1 - h(x, z, side) % 4), side)
        top = b.get(n[0], t, n[1])
        if top is not None and top.name == "minecraft:grass" and b.get(n[0], t + 1, n[1]) is None \
                and h(*n, "verge") % 3 == 0:
            b.set(n[0], t + 1, n[1], PLANTS[h(*n, "plant") % len(PLANTS)])

# ---- knock-out panels for the next stages -----------------------------------------------------------
knockout(b, "n", -594, -592, 81, 84, az0 - 1)      # steam hall (y80)
knockout(b, "n", -594, -592, 101, 104, az0 - 1)    # north corridor -> LV/MV halls, storage, multiblock hall
knockout(b, "n", -590, -588, 113, 116, az0 - 1)    # y112: HV hall, cleanroom bay, AE2 core
knockout(b, "s", -598, -596, 101, 104, az1 + 1)    # south: crop hall (y100)
knockout(b, "n", -583, -581, 81, 83, -287)         # power hall, end of the service tunnel

# ---- labels: low-profile Nuclear Control panels over the copper lintels ---------------------------------
info_panel(b, (FX + 1, 132, -238), (FX + 1, 132, -232), "w", "THRESHOLD")   # gate lintel, conservatory side
for L in LEVELS:                                     # lift lobby lintels (z -264..-260 at L+4), atrium side
    info_panel(b, (ax1, L + 4, -264), (ax1, L + 4, -260), "e", "LIFT")

clean_ores(b)
