# Cell Settings Deep Dive

This document explains each runtime setting exposed in the control panel, what it does, where it is applied, and how it affects growth behavior.

## 1) Settings pipeline

1. Settings are declared as editable UI controls in `CONTROL_PANEL_ITEMS`.
2. The UI mutates attributes directly on `sim.grid`.
3. Tick-time systems consume those attributes in lifecycle logic:
   - Exploration field update
   - Birth scoring and parent selection
   - Survival/energy drain and structural transitions
   - Radius adaptation and food spawning/capture

## 2) Runtime source of truth

- **Control definitions + ranges + step size**: `src/non_matrix/app.py` (`CONTROL_PANEL_ITEMS`)
- **Human-readable descriptions in UI**: `src/non_matrix/app.py` (`CONTROL_PANEL_HELP`)
- **Default values**: `src/non_matrix/sparse_grid.py` (`SparseGrid.__init__`)
- **Main behavior application**: `src/non_matrix/rules.py` (`step_life`)
- **Exploration fields (smell/path memory)**: `src/non_matrix/sparse_grid.py` (`update_exploration_fields`)

## 3) Complete setting reference

### Exploration fields and deterministic birth scoring

| Setting | Type | Default | Range | What it changes | Used in |
|---|---:|---:|---:|---|---|
| `smell_decay` | float | 0.93 | 0.50..0.999 | Per-tick decay for smell values. Higher retains trails longer. | `update_exploration_fields` |
| `smell_diffusion` | float | 0.22 | 0.0..1.0 | Fraction of decayed smell diffused to Moore neighbors. | `update_exploration_fields` |
| `smell_food_source` | float | 8.0 | 0.0..30.0 | Smell source injected at food cells each tick. | `update_exploration_fields` |
| `smell_outpost_source` | float | 3.0 | 0.0..30.0 | Smell source injected at outpost anchors each tick. | `update_exploration_fields` |
| `path_memory_decay` | float | 0.9 | 0.50..0.999 | Per-tick decay of path-memory field. | `update_exploration_fields` |
| `path_memory_deposit` | float | 1.0 | 0.0..10.0 | Added path-memory by each alive cell per tick. | `update_exploration_fields` |
| `score_smell_weight` | float | 1.0 | 0.0..5.0 | Positive weight for smell in deterministic birth score. | `_deterministic_birth_score` |
| `score_alignment_weight` | float | 0.4 | 0.0..5.0 | Positive weight for directional alignment. | `_deterministic_birth_score` |
| `score_memory_penalty_weight` | float | 0.7 | 0.0..5.0 | Penalty for recently traversed cells. | `_deterministic_birth_score` |
| `score_crowding_penalty_weight` | float | 0.2 | 0.0..5.0 | Penalty for births in crowded locations. | `_deterministic_birth_score` |

Notes:
- Births are filtered by a global threshold (`BIRTH_SCORE_THRESHOLD = -0.25`).
- Structural ghost-node reactivation also uses deterministic score checks.

### Coherence-driven boundary adaptation

| Setting | Type | Default | Range | What it changes | Used in |
|---|---:|---:|---:|---|---|
| `radius_step` | int | 50 | 1..500 | Increment/decrement size when radius adapts. | `adapt_radius_from_coherence` |
| `coherence_high_threshold` | float | 70.0 | 0..100 | Coherence % needed to count toward expansion streak. | `set_coherence_percent` |
| `coherence_low_threshold` | float | 35.0 | 0..100 | Coherence % needed to count toward contraction streak. | `set_coherence_percent` |
| `coherence_expand_ticks` | int | 10 | 1..500 | Consecutive high-coherence ticks needed to expand radius. | `adapt_radius_from_coherence` |
| `coherence_contract_ticks` | int | 20 | 1..500 | Consecutive low-coherence ticks needed to contract radius. | `adapt_radius_from_coherence` |

Notes:
- Coherence is computed from active/structural shape matching elsewhere, then fed into grid radius adaptation.
- Radius bounds are clamped by `min_radius` and `max_radius`.

### Food and outpost economy

| Setting | Type | Default | Range | What it changes | Used in |
|---|---:|---:|---:|---|---|
| `food_spawn_interval` | int | 150 | 0..5000 | Tick interval between food spawn cycles; 0 disables spawn. | `maybe_spawn_food_clusters` |
| `food_cluster_min` | int | 3 | 0..20 | Minimum clusters attempted each spawn cycle. | `maybe_spawn_food_clusters` |
| `food_cluster_max` | int | 6 | 0..30 | Maximum clusters attempted each spawn cycle. | `maybe_spawn_food_clusters` |
| `food_min_distance_ratio` | float | 0.65 | 0.0..1.0 | Minimum radial spawn distance relative to current radius. | `maybe_spawn_food_clusters` |
| `food_energy_bonus` | int | 60 | 0..500 | Bonus energy on successful food capture (captor is structuralized). | `award_food_energy` |
| `outpost_lock_radius` | int | 2 | 0..20 | Chebyshev radius of structural lock around captured outpost. | `_lock_outpost_area` |
| `food_capture_radius` | int | 3 | 1..12 | Chebyshev capture distance for live cells to claim food. | `step_life` capture pass |

Notes:
- Captured food becomes outpost anchor and a locked structural patch.
- Outposts also emit smell (`smell_outpost_source`).

### Metabolic topology, crowding, structural lifecycle

| Setting | Type | Default | Range | What it changes | Used in |
|---|---:|---:|---:|---|---|
| `mycelium_target_neighbors` | int | 2 | 1..8 | “Ideal” neighbor count for line-like vine behavior. | `step_life` tax/multiplier logic + scoring crowding delta |
| `mycelium_zero_tax_enabled` | bool | True | ON/OFF | If ideal neighbor count is met, base tax can be zeroed. | `step_life` |
| `vine_off_target_multiplier` | int | 2 | 1..12 | Drain multiplier when not at ideal neighbor count. | `step_life` |
| `crowding_threshold` | int | 3 | 1..8 | Crowding threshold for suffocation and extra drain. | `step_life` |
| `crowding_multiplier` | int | 4 | 1..12 | Multiplies drain once above crowding threshold. | `step_life` |
| `structural_discount_factor` | float | 0.2 | 0.0..1.0 | Tax discount for non-overcrowded structural cells. | `step_life` |
| `structural_overcrowded_neighbors` | int | 2 | 1..8 | Structural-neighbor threshold to mark calcified/overcrowded. | `step_life` |
| `structural_hibernate_overcrowd_neighbors` | int | 4 | 1..8 | Total-neighbor threshold that increments structural overcrowd ticks. | `step_life` |
| `structural_hibernate_ticks` | int | 5 | 1..120 | Ticks above hibernation threshold before structural status removed. | `step_life` |
| `chemotaxis_outer_ratio` | float | 0.7 | 0.0..1.0 | Start of edge band where outward chemotaxis discount applies. | `step_life` |
| `chemotaxis_discount_factor` | float | 0.5 | 0.0..1.0 | Tax multiplier in outer edge band. | `step_life` |
| `outpost_magnet_radius` | int | 200 | 0..2000 | Radius around outposts for magnet discount. | `step_life` |
| `outpost_magnet_discount_factor` | float | 0.25 | 0.0..1.0 | Tax multiplier within outpost magnet radius. | `step_life` |

Notes:
- Structural cells can be removed (de-structuralized) after sustained local overcrowding.
- Anchor-protected cells bypass normal death pressure and are regularly refueled.

### Directional growth controls

| Setting | Type | Default | Range | What it changes | Used in |
|---|---:|---:|---:|---|---|
| `vector_bias_enabled` | bool | True | ON/OFF | Enables momentum-style directional behavior gate. | `_select_parent_for_birth_deterministic`, `step_life` |
| `vector_bias_forward_chance` | float | 0.75 | 0.0..1.0 | Exposed in UI/help text; currently not consumed in runtime logic. | (currently unused) |
| `vector_bias_side_chance` | float | 0.25 | 0.0..1.0 | Exposed in UI/help text; currently not consumed in runtime logic. | (currently unused) |
| `vector_bias_maturity_ticks` | int | 5 | 0..200 | Required parent age before momentum inheritance can activate. | `_select_parent_for_birth_deterministic`, `step_life` |
| `vector_cone_degrees` | float | 45.0 | 0..180 | Angular cone filter around parent growth vector for birth candidate acceptance. | `_within_cone` + caller checks |
| `lateral_inhibition_enabled` | bool | True | ON/OFF | Prevents side branching from structural line segments under target-neighbor condition. | `_select_parent_for_birth_deterministic`, `step_life` |

Important implementation detail:
- Forward/side probability settings are present in UI and defaults but are not currently applied to random acceptance. Directional behavior is currently deterministic via cone filtering, parent vector, and maturity checks.

## 4) High-impact interactions

### A) Thin, persistent root lines

- Increase `score_alignment_weight`
- Keep `vector_cone_degrees` relatively narrow
- Keep `lateral_inhibition_enabled = ON`
- Keep `mycelium_target_neighbors = 2`
- Keep `mycelium_zero_tax_enabled = ON`

Expected effect: straighter line propagation and lower metabolic pressure on ideal chains.

### B) Dense branching with self-pruning

- Raise `vector_cone_degrees`
- Lower `score_alignment_weight`
- Lower `crowding_threshold`
- Raise `crowding_multiplier`

Expected effect: more exploratory branching followed by aggressive pruning in dense zones.

### C) Edge-seeking expansion

- Lower `chemotaxis_discount_factor`
- Lower `chemotaxis_outer_ratio`
- Increase `coherence_high_threshold` carefully if radius expansion is too easy

Expected effect: stronger metabolic incentive near edges with controlled radius growth pace.

### D) Strong outpost gravity

- Increase `outpost_magnet_radius`
- Lower `outpost_magnet_discount_factor`
- Increase `smell_outpost_source`

Expected effect: growth preferentially consolidates around captured outposts.

## 5) Operational caveats

- Setting changes are applied live to `sim.grid`; there is no separate config staging layer.
- Some penalties/discounts are multiplicative and can compound strongly.
- `vector_bias_forward_chance` and `vector_bias_side_chance` are currently placeholders for future probabilistic steering.

## 6) Suggested next improvement for docs/code alignment

If probabilistic directional bias is intended, implement usage of `vector_bias_forward_chance` and `vector_bias_side_chance` in the birth acceptance path so UI text exactly matches runtime behavior.

