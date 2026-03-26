# AXIOM HOOPS EDGE — 2026 Tournament Quant Engine

**Quantitative Margin-Volatility Engine**

A production-ready pipeline for processing high-variance time-series data to identify efficiency margins and predictive stress points.

-----

## Overview

AXIOM-60 is a quantitative filtering engine that evaluates structured matchup data against spread-adjusted efficiency differentials. It ingests paired KenPom and TeamRankings statistical profiles, computes averaged margin gaps, and classifies each entry through a deterministic filter chain — outputting actionable signal tiers with zero ambiguity.

The engine is designed for speed, clarity, and repeatability. No discretionary overrides. No manual adjustments. Every output traces directly to the filter logic. All outputs carry the `AXIOM_VERIFIED_2026` audit seal.

-----

## AXIOM_CONFIG

| Constant             | Value               | Purpose                                    |
|----------------------|---------------------|--------------------------------------------|
| `TEMPO_CAP`          | `148.0`             | Safety gate for high-variance games        |
| `EDGE_MIN`           | `1.5`               | Minimum alpha required to trigger BET      |
| `CONFIDENCE_WEIGHT`  | `12.5`              | Multiplier for Strength Index calculation  |
| `AUDIT_SEAL`         | `AXIOM_VERIFIED_2026` | Immutable verification stamp on all outputs |

-----

## Core Metrics

| Metric      | Definition                                                                                           |
|-------------|------------------------------------------------------------------------------------------------------|
| `BA_Gap`    | `((FavKP − DogKP) + (FavTV − DogTV)) / 2` — average efficiency margin across KenPom and TeamRankings |
| `Abs_Edge`  | `|BA_Gap − |Spread||` — spread-adjusted absolute edge                                                |
| `Strength`  | `min(99.9, Abs_Edge × 12.5 + (148.0 − O/U))` — Proprietary Strength Index (BET signals only)        |

-----

## Filter Chain

AXIOM-60 applies a fixed three-gate filter sequence. Each entry is evaluated top-down — first match exits.

```
1. O/U > 148.0          → PASS  (reason: TEMPO_OVERFLOW)
2. Abs_Edge ≥ 1.5        → BET
3. Abs_Edge ≥ 1.0
   AND BA_Gap < |Spread| → LIVE_DOG
4. else                  → PASS
```

No SpreadCap gate. No PK zone. No Conflict gate. No Auto-DOG. No Dead Zone. No star tiers. No discretionary overrides.

-----

## Output Classification

| Signal           | Color Code | Meaning                                    |
|------------------|------------|--------------------------------------------|
| `BET`            | Green      | Efficiency edge meets threshold            |
| `LIVE_DOG`       | Purple     | Moderate edge with underdog alignment      |
| `PASS`           | Gray/Orange| No actionable edge, or Tempo overflow      |

-----

## Output Fields

Every call to `classify()` returns:

| Field        | Type    | Description                                         |
|--------------|---------|-----------------------------------------------------|
| `signal`     | str     | `BET`, `LIVE_DOG`, or `PASS`                        |
| `strength`   | float   | Strength Index 0–99.9 (non-zero for BET only)       |
| `reason`     | str/None| `TEMPO_OVERFLOW` for tempo gate; `None` otherwise   |
| `ba_gap`     | float   | Computed BA_Gap                                     |
| `abs_edge`   | float   | Computed Abs_Edge                                   |
| `spread`     | float   | Input spread                                        |
| `ou`         | float   | Input O/U                                           |
| `audit_seal` | str     | `AXIOM_VERIFIED_2026`                               |

-----

## Styling Spec

| Element            | Value                       |
|--------------------|-----------------------------|
| Font               | Arial                       |
| Headers            | Navy background, white text |
| Row shading        | Alternating light/white     |
| BET rows           | Green fill                  |
| LIVE_DOG rows      | Purple fill                 |
| Filter PASS rows   | Orange fill                 |
| Standard PASS rows | Gray fill                   |

-----

## Architecture

```
┌──────────────────────────────────────┐
│           Raw Input Data             │
│  (KenPom + TeamRankings profiles +   │
│   spread + O/U)                      │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│         Metric Computation           │
│  BA_Gap = avg(KP_gap, TV_gap)        │
│  Abs_Edge = |BA_Gap − |Spread||      │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│     Deterministic Filter Chain       │
│  3-gate sequential evaluation        │
│  First match exits                   │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│         Classified Output            │
│  Signal + Strength + Audit Seal      │
│  → Excel / HTML                      │
└──────────────────────────────────────┘
```

-----

## Usage

AXIOM-60 requires manually sourced efficiency data (AdjEM values are paywalled). The engine does not fetch data — it processes what you provide.

**Input requirements per entry:**

- Favorite and Dog team identifiers
- `FavKP` and `DogKP` — KenPom adjusted efficiency margin
- `FavTV` and `DogTV` — TeamRankings adjusted efficiency margin
- `Spread` (posted line)
- `O/U` (over/under total)

**Output:**

- Formatted Excel workbook with signal classification, strength index, and color coding
- All rows carry the `AXIOM_VERIFIED_2026` audit seal
- Optional HTML bracket or dashboard visualization

-----

## Design Principles

- **Deterministic** — same input always produces same output
- **Transparent** — every signal traces to a specific filter gate
- **No discretion** — the chain decides, not the operator
- **Units kept separate** — AXIOM-60 classifies; bankroll management is external
- **Auditable** — every output stamped with `AXIOM_VERIFIED_2026`

-----

## Version

**AXIOM HOOPS EDGE — 2026 Tournament Quant Engine** (AXIOM-60). Current and locked.

-----

## License

Private use. Not licensed for redistribution.