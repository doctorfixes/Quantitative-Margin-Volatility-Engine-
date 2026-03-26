# AXIOM-60

**Quantitative Margin-Volatility Engine**

A production-ready pipeline for processing high-variance time-series data to identify efficiency margins and predictive stress points.

-----

## Overview

AXIOM-60 is a quantitative filtering engine that evaluates structured matchup data against spread-adjusted efficiency differentials. It ingests paired statistical profiles, computes margin gaps, and classifies each entry through a deterministic filter chain — outputting actionable signal tiers with zero ambiguity.

The engine is designed for speed, clarity, and repeatability. No discretionary overrides. No manual adjustments. Every output traces directly to the filter logic.

-----

## Core Metrics

|Metric    |Definition                                                                   |
|----------|-----------------------------------------------------------------------------|
|`BA_Gap`  |`FavAdjEM − DogAdjEM` — raw adjusted efficiency margin between paired entries|
|`Abs_Edge`|`                                                                            |

-----

## Filter Chain

AXIOM-60 applies a fixed five-gate filter sequence. Each entry is evaluated top-down — first match exits.

```
1. O/U > 148          → PASS (Tempo)
2. |Spread| > 24.5     → PASS (SpreadCap)
3. Abs_Edge ≥ 1.5      → BET
4. Abs_Edge ≥ 1.0
   AND BA_Gap < |Spread| → BET (LIVE DOG)
5. else                → PASS
```

No PK zone. No Conflict gate. No Auto-DOG. No Dead Zone. No star tiers. No discretionary overrides.

-----

## Output Classification

|Signal            |Color Code|Meaning                              |
|------------------|----------|-------------------------------------|
|`BET`             |Green     |Efficiency edge meets threshold      |
|`LIVE DOG`        |Purple    |Moderate edge with underdog alignment|
|`PASS (Tempo)`    |Orange    |Filtered out — pace/environment flag |
|`PASS (SpreadCap)`|Orange    |Filtered out — spread exceeds cap    |
|`PASS`            |Gray      |No actionable edge detected          |

-----

## Styling Spec

|Element           |Value                      |
|------------------|---------------------------|
|Font              |Arial                      |
|Headers           |Navy background, white text|
|Row shading       |Alternating light/white    |
|BET rows          |Green fill                 |
|LIVE DOG rows     |Purple fill                |
|Filter PASS rows  |Orange fill                |
|Standard PASS rows|Gray fill                  |

-----

## Architecture

```
┌──────────────────────────────────┐
│         Raw Input Data           │
│  (Paired efficiency profiles +   │
│   spread + O/U)                  │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│       Metric Computation         │
│  BA_Gap = FavAdjEM − DogAdjEM    │
│  Abs_Edge = |BA_Gap − |Spread||  │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│     Deterministic Filter Chain   │
│  5-gate sequential evaluation    │
│  First match exits               │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│       Classified Output          │
│  Signal + Color Code + Metrics   │
│  → Excel / HTML                  │
└──────────────────────────────────┘
```

-----

## Usage

AXIOM-60 requires manually sourced efficiency data (AdjEM values are paywalled). The engine does not fetch data — it processes what you provide.

**Input requirements per entry:**

- Favorite and Dog team identifiers
- `FavAdjEM` and `DogAdjEM` (adjusted efficiency margin)
- `Spread` (posted line)
- `O/U` (over/under total)

**Output:**

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

**AXIOM-60** — current and locked. No version suffix. No forks.

-----

## License

Private use. Not licensed for redistribution.