# AXIOM-60

**Quantitative Margin-Volatility Engine — 2026 Tournament Edition**

A production-ready pipeline for processing high-variance time-series data to identify efficiency margins and predictive stress points.

-----

## Overview

AXIOM-60 is a quantitative filtering engine that evaluates structured matchup data against spread-adjusted efficiency differentials. It ingests **dual-source** paired statistical profiles, computes averaged margin gaps, and classifies each entry through a deterministic filter chain — outputting actionable signal tiers with zero ambiguity.

The engine is designed for speed, clarity, and repeatability. No discretionary overrides. No manual adjustments. Every output traces directly to the filter logic.

-----

## Core Metrics

|Metric      |Definition                                                                              |
|------------|----------------------------------------------------------------------------------------|
|`BA_Gap`    |`((FavKP − DogKP) + (FavTV − DogTV)) / 2` — averaged efficiency margin from two sources|
|`Abs_Edge`  |`\|BA_Gap − \|Spread\|\|` — spread-adjusted efficiency delta                           |
|`Strength`  |`min(99.9, Abs_Edge × 12.5 + (148.0 − O/U))` — confidence index for BET signals (0–99.9)|

-----

## Filter Chain

AXIOM-60 applies a fixed three-gate filter sequence. Each entry is evaluated top-down — first match exits.

```
1. O/U > 148          → PASS (TEMPO_OVERFLOW)
2. Abs_Edge ≥ 1.5      → BET
3. Abs_Edge ≥ 1.0
   AND BA_Gap < |Spread| → BET (LIVE_DOG)
4. else                → PASS
```

No SpreadCap gate. No discretionary overrides.

-----

## Output Classification

|Signal            |Color Code|Meaning                              |
|------------------|----------|-------------------------------------|
|`BET`             |Green     |Efficiency edge meets threshold      |
|`BET (LIVE_DOG)`  |Purple    |Moderate edge with underdog alignment|
|`PASS (TEMPO_OVERFLOW)`|Orange|Filtered out — pace/environment flag |
|`PASS`            |Gray      |No actionable edge detected          |

-----

## Styling Spec

|Element                  |Value                      |
|-------------------------|---------------------------|
|Font                     |Arial                      |
|Headers                  |Navy background, white text|
|Row shading              |Alternating light/white    |
|BET rows                 |Green fill                 |
|LIVE_DOG rows            |Purple fill                |
|TEMPO_OVERFLOW PASS rows |Orange fill                |
|Standard PASS rows       |Gray fill                  |

-----

## Architecture

```
┌──────────────────────────────────┐
│         Raw Input Data           │
│  (Dual efficiency profiles +     │
│   spread + O/U)                  │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│       Metric Computation         │
│  BA_Gap = avg(KP_diff, TV_diff)  │
│  Abs_Edge = |BA_Gap − |Spread||  │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│     Deterministic Filter Chain   │
│  3-gate sequential evaluation    │
│  First match exits               │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│       Classified Output          │
│  Signal + Strength + Metrics     │
│  + AUDIT_SEAL                    │
│  → Excel / HTML                  │
└──────────────────────────────────┘
```

-----

## Usage

AXIOM-60 requires manually sourced efficiency data (AdjEM values are paywalled). The engine does not fetch data — it processes what you provide.

**Input requirements per entry:**

- Favorite and Dog team identifiers
- `FavKP` and `DogKP` (KenPom adjusted efficiency margin)
- `FavTV` and `DogTV` (secondary efficiency metric, e.g. TeamRankings)
- `Spread` (posted line)
- `O/U` (over/under total)

**Output:**

- `signal` — `BET`, `BET (LIVE_DOG)`, or `PASS`
- `strength` — confidence index 0–99.9 (non-zero for BET signals only)
- `audit_seal` — `AXIOM_VERIFIED_2026`
- Formatted Excel workbook with signal classification and color coding
- Optional HTML bracket or dashboard visualization

-----

## Design Principles

- **Deterministic** — same input always produces same output
- **Transparent** — every signal traces to a specific filter gate
- **No discretion** — the chain decides, not the operator
- **Units kept separate** — AXIOM-60 classifies; bankroll management is external

-----

## Version

**AXIOM-60** — 2026 Tournament Edition. No forks.

-----

## License

Private use. Not licensed for redistribution.