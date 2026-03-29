# Non-Matrix

Sparse-grid cellular intelligence sandbox for emergent computation, information foraging, and deterministic exploration experiments.

## What Non-Matrix is (current state)

Non-Matrix is a coordinate-only cellular simulation where growth happens in an unbounded sparse world (bounded by an adaptive radius), not a fixed 2D matrix.

The engine supports:

- mutation-local rule behavior
- inherited lineage and growth vectors
- food/outpost information foraging
- structural memory and ghost reactivation
- deterministic smell/path-memory exploration (replayable after clear/reseed)
- live runtime tuning through an in-app settings panel

This is an active prototype focused on emergent behavior and rapid experimentation.

## Current feature set

### 1) Core simulation

- Coordinate-only alive storage and frontier stepping
- Rule-based local birth/survival with mutation types
- Energy/tax pressure, crowding pressure, and heat dumping
- Structural promotion and old-growth visualization

### 2) Information-driven growth

- **Adaptive wall radius** (coherence-driven expand/contract)
- **Noise-filtered coherence** (active-pixel shape quality)
- **Food clusters** spawning far from center
- **Outpost anchors** when food is captured
- **Outpost lock area** to stabilize captured regions

### 3) Deterministic exploration model

Movement decisions now use deterministic scoring instead of random movement gates.

Scoring factors include:

- smell attraction
- growth-vector alignment
- path-memory revisit penalty
- crowding penalty

This enables more reproducible path formation and directional searching.

### 4) Visual + UI system

- Three-panel runtime UI:
  - **Left:** Settings (live controls)
  - **Center:** World render
  - **Right:** Simulation info + legend + hovered-setting help
- Faint world-space background grid for spatial orientation
- Structural pulse/ghost rendering and heat overlay
- Expanded legend including line links, ghosts, mutation swatches, and outpost-star semantics

## Runtime UI usage

### Settings panel interactions

- Click row to select a setting
- Click `+` / `-` to adjust
- Arrow keys navigate and edit selected setting
- Mouse wheel over the left panel scrolls long setting lists
- Hovering a setting shows details in the right info panel (non-blocking)

### Global runtime controls

- `F1` Toggle Play/Pause
- `F2` Manual Step
- `F3` Reset/Nuke
- Arrow keys pan the world viewport
- Mouse wheel over world zooms
- Click in render area seeds a single root
- Type text and press `Enter` to seed UTF-8 bit-pattern text

## Tuning categories available in-app

- Smell field dynamics
- Path-memory dynamics
- Deterministic score weights
- Coherence/radius adaptation
- Food/outpost ecology
- Structural/crowding/vector-bias controls

## Default adaptive policy (current)

- Radius range: `300..1200`
- Expand by `+50` when coherence >= `70%` for `10` consecutive checks
- Contract by `-50` when coherence <= `35%` for `20` consecutive checks
- Food spawn default: every `150` ticks, `3..6` clusters, min distance ratio `0.65`

## Validation status

- Test suite currently passing: `42` tests
- Includes deterministic replay and deterministic smell/path-memory behavior checks

## Quick start (uv)

```bash
uv sync --extra dev
uv run pytest
uv run non-matrix
```

## Quick start (python)

```bash
python -m pytest
python -m non_matrix.app
```

