#!/usr/bin/env bash
# turbine-table.sh
# Generates a turbine blade comparison table (XLST / XLSCT / XLPT) from DB tooltips.
# Tooltip rule: SH Steam (XLST) and SC Steam (XLSCT) are both 2× the base Steam value
# at the same optimal flow. Plasma values are read directly.
#
# Usage: ./turbine-table.sh [> output.md]
#   Progress is written to stderr; the markdown table to stdout.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

TMPDATA=$(mktemp)
RESULT=$(mktemp)
trap 'rm -f "$TMPDATA" "$RESULT"' EXIT

# ── 1. Fetch and parse tooltips ──────────────────────────────────────────────

printf 'Fetching huge turbine items...\n' >&2

./gtnh --json search "huge turbine" --limit 200 2>/dev/null \
| jq -r '.items[] | select(.tooltip != null) | [.id, .tooltip] | @tsv' \
| while IFS=$'\t' read -r raw_id tooltip; do
    id=$(echo "$raw_id" | tr '~' ':')

    # jq @tsv escapes newlines to literal \n — restore them for grep
    tt=$(printf '%s' "$tooltip" | sed 's/\\n/\n/g')

    # Material name: "§7<Name>:§e Tier N§7"
    material=$(printf '%s' "$tt" | grep -oP '§7\K[^§:]+(?=:§e Tier)')
    [[ -z "$material" ]] && continue

    # Base efficiency
    eff=$(printf '%s' "$tt" | grep -oP 'Base Efficiency: §9\K[0-9]+')

    # Steam line: "§f  Steam §7 | §6<flow>§7 L/t > §2<eu>§7 EU/t | §9<eff>%§7"
    steam_line=$(printf '%s' "$tt" | grep '§f  Steam §7 |' || true)
    [[ -z "$steam_line" ]] && continue
    steam_flow=$(printf '%s' "$steam_line" | grep -oP '§6\K[0-9,]+(?=§7 L/t)'  | tr -d ',')
    steam_eu=$(  printf '%s' "$steam_line" | grep -oP '> §2\K[0-9,]+(?=§7 EU/t)' | tr -d ',')

    # Plasma line: "§d  Plasma§7 | §6<flow>§7 EU/t > §2<eu>§7 EU/t | §9<eff>%§7"
    plasma_line=$(printf '%s' "$tt" | grep '§d  Plasma§7 |' || true)
    [[ -z "$plasma_line" ]] && continue
    plasma_flow=$(printf '%s' "$plasma_line" | grep -oP '§6\K[0-9,]+(?=§7 EU/t > )' | tr -d ',')
    plasma_eu=$(  printf '%s' "$plasma_line" | grep -oP '> §2\K[0-9,]+(?=§7 EU/t)'  | tr -d ',')

    [[ -z "${steam_flow}${steam_eu}${plasma_flow}${plasma_eu}" ]] && continue

    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$id" "$material" "$eff" "$steam_flow" "$steam_eu" "$plasma_flow" "$plasma_eu"

# Deduplicate: keep one entry per material name (first seen)
done | sort -t$'\t' -k2,2 -u > "$TMPDATA"

N=$(wc -l < "$TMPDATA")
printf 'Found %d unique blade materials. Looking up tiers...\n' "$N" >&2

# ── 2. Tier helpers ──────────────────────────────────────────────────────────

TIER_ORDER=(ULV LV MV HV EV IV LuV ZPM UV UHV UEV UIV UMV UXV MAX)

tier_rank() {
    local t="$1" i
    for i in "${!TIER_ORDER[@]}"; do
        [[ "${TIER_ORDER[$i]}" == "$t" ]] && printf '%d' "$i" && return
    done
    printf '99'
}

# ── 3. EU-cost tier lookup ───────────────────────────────────────────────────

i=0
while IFS=$'\t' read -r id material eff steam_flow steam_eu plasma_flow plasma_eu; do
    i=$((i + 1))
    printf '  [%d/%d] %-45s' "$i" "$N" "$material..." >&2
    tier=$(./gtnh eu-cost --min-tier "$id" 2>/dev/null \
           | grep -oP 'Best:.*\[\K[^\]]+' || printf '?')
    rank=$(tier_rank "$tier")
    xlst_eu=$steam_eu               # XLST = regular steam, base value
    xlsct_eu=$((steam_eu * 2))      # XLSCT = supercritical steam = 2× base
    printf '%02d\t%s\t%s\t%d\t%d\t%d\t%d\t%d\t%s\n' \
        "$rank" "$tier" "$material" \
        "$steam_flow" "$xlst_eu" "$xlsct_eu" \
        "$plasma_flow" "$plasma_eu" \
        "$eff" >> "$RESULT"
    printf ' %s\n' "$tier" >&2
done < "$TMPDATA"

# ── 4. Format as markdown table ──────────────────────────────────────────────

fmt() { printf '%d' "$1" | sed ':a;s/\B[0-9]\{3\}\>/,&/;ta'; }

printf '\nDone. Writing table...\n\n' >&2

echo "| Material | Tier | Opt Flow (L/t) | XLST EU/t | XLSCT EU/t | XLPT Opt Flow (EU/t) | XLPT EU/t | Efficiency |"
echo "|----------|:----:|---------------:|----------:|-----------:|---------------------:|----------:|:----------:|"

# Sort: by tier rank asc, then by XLSCT EU/t desc within tier
sort -t$'\t' -k1,1n -k6,6rn "$RESULT" \
| while IFS=$'\t' read -r rank tier material steam_flow xlst_eu xlsct_eu plasma_flow plasma_eu eff; do
    printf '| %s | %s | %s | %s | %s | %s | %s | %s%% |\n' \
        "$material" "$tier" \
        "$(fmt "$steam_flow")" \
        "$(fmt "$xlst_eu")" \
        "$(fmt "$xlsct_eu")" \
        "$(fmt "$plasma_flow")" \
        "$(fmt "$plasma_eu")" \
        "$eff"
done
