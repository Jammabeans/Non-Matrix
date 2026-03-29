# Non-Matrix

Sparse-grid cellular engine prototype for emergent computation experiments.

## Runtime UI panels

The application now uses a three-panel layout:

- **Left panel (Settings):** live-tunable simulation parameters with clickable `+/-` controls.
- **Center panel (Render):** the world simulation view (not obscured by UI overlays).
- **Right panel (Info):** live metrics and a color legend.

### Settings interaction

- **Mouse:** click a setting row to select, click `+` / `-` to adjust.
- **Keyboard:** `Up/Down` selects a setting; `Left/Right` adjusts; `Enter` toggles booleans.
- **Hover help:** hovering a setting shows a detailed explanation tooltip in the left panel.

### Runtime controls

- `F1` Toggle Play/Pause
- `F2` Manual Step
- `F3` Reset/Nuke
- Arrow keys pan the viewport
- Mouse wheel zooms
- Click in render area seeds a root
- Type text and press `Enter` to seed UTF-8 text pattern

## Adaptive growth mechanics

The simulation now includes information-driven expansion and long-range exploration:

- **Variable spatial wall**: active radius is dynamic in the range **300..1200** and adapts to coherence quality.
- **Noise-filtered coherence**: coherence is computed from currently active pixels (not persistent structural ghost pixels).
- **Food clusters**: 3-6 food targets spawn every 150 ticks at >=65% of current radius distance from the center.
- **Outpost creation**: roots that reach food consume it, gain energy, and establish durable outpost anchors.
- **Spatial grid background**: renderer now draws a faint world-space grid to improve orientation while panning and zooming.

### Radius adaptation policy

- Expand by 50 when coherence >=70% for 10 consecutive coherence updates.
- Contract by 50 when coherence <=35% for 20 consecutive coherence updates.
- Radius is always clamped to [300, 1200].

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

