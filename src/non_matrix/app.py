from __future__ import annotations

import pygame

from .modes import SimMode
from .signal_coherence import coherence_percent_active, skeleton_pulse_alpha
from .simulation import Simulation
from .viewport import Viewport

BACKGROUND = (8, 10, 16)
GRID_COLOR = (22, 28, 40)
CELL_COLOR = (80, 220, 160)
PARENT_LINE_COLOR = (70, 90, 130)
TENSION_HIGH = (255, 70, 70, 220)
TENSION_LOW = (95, 120, 165, 100)
TARGET_LINK_MATCH = (90, 255, 140, 180)
TARGET_LINK_MISMATCH = (120, 120, 120, 90)
HEAT_COLOR = (255, 110, 30)
TEXT_COLOR = (230, 235, 240)
OLD_GROWTH_COLOR = (0, 255, 255)
STRUCTURAL_BLUE = (120, 180, 255)
STRUCTURAL_WHITE = (230, 245, 255)
GHOST_BLUE = (90, 140, 255, 50)
FOOD_COLOR = (255, 210, 90)
OUTPOST_COLOR = (255, 245, 180)
SUCCESS_COLOR = (255, 255, 255)
PAUSED_BORDER_COLOR = (190, 50, 50)
PAUSED_TEXT_COLOR = (255, 170, 170)
CALCIFIED_COLOR = (255, 70, 70)
PANEL_BG = (18, 22, 30)
PANEL_BORDER = (90, 120, 170)
PANEL_TEXT = (220, 230, 245)
PANEL_ACTIVE = (255, 220, 120)
SIDEBAR_WIDTH = 420
INFO_PANEL_WIDTH = 280

ControlItem = tuple[str, str, str, float, float, float]

CONTROL_PANEL_ITEMS: list[ControlItem] = [
    ("Simulation Mode", "mode", "mode", 0.0, 0.0, 1.0),
    ("Target Number", "target_number", "int", 1.0, 1.0, 1000000.0),
    ("Render Every X Ticks", "render_every_x_ticks", "int", 1.0, 1.0, 50.0),
    ("Logic Success Ticks", "logic_success_streak_ticks", "int", 1.0, 1.0, 200.0),
    ("Logic Jolt Threshold", "logic_jolt_threshold_ticks", "int", 1.0, 1.0, 500.0),
    ("Logic Jolt Bias", "logic_jolt_bias", "float", 0.05, 0.0, 1.0),
    ("Logic Hot Flip", "logic_flip_hot_chance", "float", 0.01, 0.0, 1.0),
    ("Logic Cold Flip", "logic_flip_cold_chance", "float", 0.005, 0.0, 0.2),
    ("Logic Gate Hot", "logic_gate_hot_chance", "float", 0.01, 0.0, 1.0),
    ("Logic Gate Cold", "logic_gate_cold_chance", "float", 0.005, 0.0, 0.2),
    ("Smell Decay", "smell_decay", "float", 0.01, 0.5, 0.999),
    ("Smell Diffusion", "smell_diffusion", "float", 0.01, 0.0, 1.0),
    ("Smell Food Source", "smell_food_source", "float", 0.25, 0.0, 30.0),
    ("Smell Outpost Source", "smell_outpost_source", "float", 0.25, 0.0, 30.0),
    ("Path Memory Decay", "path_memory_decay", "float", 0.01, 0.5, 0.999),
    ("Path Memory Deposit", "path_memory_deposit", "float", 0.05, 0.0, 10.0),
    ("Score Smell Weight", "score_smell_weight", "float", 0.05, 0.0, 5.0),
    ("Score Alignment Weight", "score_alignment_weight", "float", 0.05, 0.0, 5.0),
    ("Score Memory Penalty", "score_memory_penalty_weight", "float", 0.05, 0.0, 5.0),
    ("Score Crowding Penalty", "score_crowding_penalty_weight", "float", 0.05, 0.0, 5.0),
    ("Radius Step", "radius_step", "int", 5.0, 1.0, 500.0),
    ("Coherence High Threshold", "coherence_high_threshold", "float", 1.0, 0.0, 100.0),
    ("Coherence Low Threshold", "coherence_low_threshold", "float", 1.0, 0.0, 100.0),
    ("Coherence Expand Ticks", "coherence_expand_ticks", "int", 1.0, 1.0, 500.0),
    ("Coherence Contract Ticks", "coherence_contract_ticks", "int", 1.0, 1.0, 500.0),
    ("Food Spawn Interval", "food_spawn_interval", "int", 5.0, 0.0, 5000.0),
    ("Food Cluster Min", "food_cluster_min", "int", 1.0, 0.0, 20.0),
    ("Food Cluster Max", "food_cluster_max", "int", 1.0, 0.0, 30.0),
    ("Food Min Distance Ratio", "food_min_distance_ratio", "float", 0.05, 0.0, 1.0),
    ("Food Energy Bonus", "food_energy_bonus", "int", 5.0, 0.0, 500.0),
    ("Outpost Lock Radius", "outpost_lock_radius", "int", 1.0, 0.0, 20.0),
    ("Food Capture Radius", "food_capture_radius", "int", 1.0, 1.0, 12.0),
    ("Mycelium Target Neighbors", "mycelium_target_neighbors", "int", 1.0, 1.0, 8.0),
    ("Mycelium Zero Tax", "mycelium_zero_tax_enabled", "bool", 0.0, 0.0, 1.0),
    ("Vine Off-Target Mult", "vine_off_target_multiplier", "int", 1.0, 1.0, 12.0),
    ("Crowding Threshold", "crowding_threshold", "int", 1.0, 1.0, 8.0),
    ("Crowding Multiplier", "crowding_multiplier", "int", 1.0, 1.0, 12.0),
    ("Structural Discount", "structural_discount_factor", "float", 0.05, 0.0, 1.0),
    ("Structural Overcrowded Neigh", "structural_overcrowded_neighbors", "int", 1.0, 1.0, 8.0),
    ("Hibernation Overcrowd Neigh", "structural_hibernate_overcrowd_neighbors", "int", 1.0, 1.0, 8.0),
    ("Hibernation Ticks", "structural_hibernate_ticks", "int", 1.0, 1.0, 120.0),
    ("Chemotaxis Outer Ratio", "chemotaxis_outer_ratio", "float", 0.05, 0.0, 1.0),
    ("Chemotaxis Discount", "chemotaxis_discount_factor", "float", 0.05, 0.0, 1.0),
    ("Outpost Magnet Radius", "outpost_magnet_radius", "int", 10.0, 0.0, 2000.0),
    ("Outpost Magnet Discount", "outpost_magnet_discount_factor", "float", 0.05, 0.0, 1.0),
    ("Vector Bias Enabled", "vector_bias_enabled", "bool", 0.0, 0.0, 1.0),
    ("Vector Bias Forward", "vector_bias_forward_chance", "float", 0.05, 0.0, 1.0),
    ("Vector Bias Side", "vector_bias_side_chance", "float", 0.05, 0.0, 1.0),
    ("Vector Bias Maturity", "vector_bias_maturity_ticks", "int", 1.0, 0.0, 200.0),
    ("Vector Cone Degrees", "vector_cone_degrees", "float", 5.0, 0.0, 180.0),
    ("Lateral Inhibition", "lateral_inhibition_enabled", "bool", 0.0, 0.0, 1.0),
]

CONTROL_PANEL_HELP: dict[str, str] = {
    "mode": "Switches simulation engine mode between mycelium growth and logic-factorizer scaffolding.",
    "target_number": "Desired multiplication target. Click Reset Logic Lattice to rebuild a dynamically sized loom.",
    "render_every_x_ticks": "Only redraw the scene every N simulation ticks. Lower values are more responsive.",
    "logic_success_streak_ticks": "Consecutive fully-correct ticks required before declaring solved and pausing.",
    "logic_jolt_threshold_ticks": "No-change ticks before a thermal jolt is applied.",
    "logic_jolt_bias": "Bias assigned to non-target bits during a thermal jolt.",
    "logic_flip_hot_chance": "Flip chance when a parent bit is in a mismatched (hot) column.",
    "logic_flip_cold_chance": "Flip chance when a parent bit is in a matched (stable) column.",
    "logic_gate_hot_chance": "Flip chance for gate cells in mismatched columns.",
    "logic_gate_cold_chance": "Flip chance for gate cells in matched columns.",
    "smell_decay": "Global decay per tick for smell traces. Higher values retain attractor trails longer.",
    "smell_diffusion": "Fraction of smell that spreads to neighboring tiles each tick.",
    "smell_food_source": "Smell source strength emitted by food clusters.",
    "smell_outpost_source": "Smell source strength emitted by outpost anchors.",
    "path_memory_decay": "Decay rate for path-memory traces. Lower values erase paths faster.",
    "path_memory_deposit": "Path-memory amount deposited by each alive cell per tick.",
    "score_smell_weight": "Weight of smell attraction in deterministic birth scoring.",
    "score_alignment_weight": "Weight of directional alignment with parent growth vector.",
    "score_memory_penalty_weight": "Penalty weight for re-entering recently traversed cells.",
    "score_crowding_penalty_weight": "Penalty weight for births in already crowded neighborhoods.",
    "radius_step": "How much the dynamic wall expands/contracts when coherence streak thresholds are met.",
    "coherence_high_threshold": "Coherence % needed to grow the world radius.",
    "coherence_low_threshold": "Coherence % below which the world radius contracts.",
    "coherence_expand_ticks": "Consecutive high-coherence ticks required before radius expansion.",
    "coherence_contract_ticks": "Consecutive low-coherence ticks required before radius contraction.",
    "food_spawn_interval": "Tick interval between food spawn attempts. Set 0 to disable food spawning.",
    "food_cluster_min": "Minimum number of food clusters spawned per spawn cycle.",
    "food_cluster_max": "Maximum number of food clusters spawned per spawn cycle.",
    "food_min_distance_ratio": "Minimum spawn distance from center as a ratio of current radius.",
    "food_energy_bonus": "Energy gain awarded to the capturing root when food is consumed.",
    "outpost_lock_radius": "Chebyshev radius of structural cells locked around a captured outpost.",
    "food_capture_radius": "Chebyshev distance used to capture food clusters. Higher values let roots claim food from farther away.",
    "mycelium_target_neighbors": "Neighbor count considered the ideal line state. Cells at this count get the vine optimization behavior.",
    "mycelium_zero_tax_enabled": "When enabled, ideal line cells pay zero base metabolic tax, preserving thin root chains.",
    "vine_off_target_multiplier": "Extra drain multiplier when a cell is not at the ideal neighbor count.",
    "crowding_threshold": "Neighbor threshold where crowding penalties start. Lower values prune dense growth earlier.",
    "crowding_multiplier": "How aggressively energy drain increases after crossing the crowding threshold.",
    "structural_discount_factor": "Base tax discount for structural cells when they are not overcrowded.",
    "structural_overcrowded_neighbors": "Structural neighbor count that marks a structural cell as calcified/overcrowded.",
    "structural_hibernate_overcrowd_neighbors": "Total-neighbor threshold that increments structural hibernation-overcrowding ticks.",
    "structural_hibernate_ticks": "Ticks above hibernation-overcrowding threshold required before structural status is removed.",
    "chemotaxis_outer_ratio": "Defines outer-band start as ratio of current radius. Cells beyond this band get chemotaxis discount.",
    "chemotaxis_discount_factor": "Tax multiplier applied in outer chemotaxis band. Smaller value means stronger outward pull.",
    "outpost_magnet_radius": "Distance around outposts where magnet discount applies, pulling growth toward established outposts.",
    "outpost_magnet_discount_factor": "Tax multiplier inside outpost magnet radius. Smaller value means stronger attraction.",
    "vector_bias_enabled": "Enables directional birth bias based on a parent growth vector.",
    "vector_bias_forward_chance": "Birth acceptance probability when candidate direction matches parent growth vector.",
    "vector_bias_side_chance": "Birth acceptance probability for non-forward directions under vector bias.",
    "vector_bias_maturity_ticks": "Parent survival age required before directional momentum bias activates.",
    "vector_cone_degrees": "Hard-lock cone angle around growth vector. Narrower values force straighter root trajectories.",
    "lateral_inhibition_enabled": "Prevents side branching from structural line segments, keeping roots 1-cell thick.",
}


def _format_control_value(value: object, kind: str) -> str:
    if kind == "mode":
        if isinstance(value, SimMode):
            mode = value
        else:
            try:
                mode = SimMode(str(value))
            except ValueError:
                mode = SimMode.MYCELIUM
        return "MYCELIUM" if mode == SimMode.MYCELIUM else "LOGIC_FACTORIZER"
    if kind == "bool":
        return "ON" if bool(value) else "OFF"
    if kind == "int":
        return str(int(value))
    fval = float(value)
    if abs(fval) < 0.1:
        return f"{fval:.4f}"
    return f"{fval:.2f}"


def _adjust_control_value(sim: Simulation, item: ControlItem, direction: int) -> None:
    label, attr, kind, step, min_value, max_value = item
    _ = label
    current = getattr(sim.grid, attr)
    if kind == "mode":
        modes = [SimMode.MYCELIUM, SimMode.LOGIC_FACTORIZER]
        if isinstance(current, SimMode):
            current_mode = current
        else:
            try:
                current_mode = SimMode(str(current))
            except ValueError:
                current_mode = SimMode.MYCELIUM
        idx = modes.index(current_mode)
        delta = 1 if direction >= 0 else -1
        next_mode = modes[(idx + delta) % len(modes)]
        setattr(sim.grid, attr, next_mode)
        if next_mode == SimMode.LOGIC_FACTORIZER and current_mode != SimMode.LOGIC_FACTORIZER:
            sim.grid._init_logic_lattice()
            sim.snapshot = set(sim.grid.alive_coords)
            sim.snapshot_tick = sim.grid.tick
            sim.peak_population = max(sim.peak_population, len(sim.grid.alive_coords))
            sim.config.auto_step = True
        return
    if kind == "bool":
        setattr(sim.grid, attr, not bool(current))
        return

    raw_next = float(current) + (float(direction) * float(step))
    clamped = max(float(min_value), min(float(max_value), raw_next))
    if kind == "int":
        setattr(sim.grid, attr, int(round(clamped)))
    else:
        setattr(sim.grid, attr, float(clamped))


def _apply_direct_control_value(sim: Simulation, item: ControlItem, raw_text: str) -> bool:
    """Apply direct text input to a numeric control item."""
    _, attr, kind, _, min_value, max_value = item
    text = raw_text.strip()
    if kind not in {"int", "float"} or not text:
        return False

    try:
        parsed = float(text)
    except ValueError:
        return False

    clamped = max(float(min_value), min(float(max_value), parsed))
    if kind == "int":
        setattr(sim.grid, attr, int(round(clamped)))
    else:
        setattr(sim.grid, attr, float(clamped))
    return True


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _visible_control_items(sim: Simulation) -> list[ControlItem]:
    if sim.grid.mode == SimMode.LOGIC_FACTORIZER:
        return [
            item
            for item in CONTROL_PANEL_ITEMS
            if item[1]
            in {
                "mode",
                "target_number",
                "render_every_x_ticks",
                "logic_success_streak_ticks",
                "logic_jolt_threshold_ticks",
                "logic_jolt_bias",
                "logic_flip_hot_chance",
                "logic_flip_cold_chance",
                "logic_gate_hot_chance",
                "logic_gate_cold_chance",
            }
        ]
    return list(CONTROL_PANEL_ITEMS)


def _panel_layout(
    viewport: Viewport,
    items: list[ControlItem],
    sidebar_width: int,
    panel_scroll: int = 0,
) -> tuple[pygame.Rect, list[tuple[int, pygame.Rect, pygame.Rect, pygame.Rect]]]:
    panel_rect = pygame.Rect(0, 0, sidebar_width, viewport.height)

    line_h = 22
    max_rows = max(1, (panel_rect.height - 80) // line_h)
    max_start = max(0, len(items) - max_rows)
    start = max(0, min(panel_scroll, max_start))
    end = min(len(items), start + max_rows)

    y = panel_rect.y + 44
    rows: list[tuple[int, pygame.Rect, pygame.Rect, pygame.Rect]] = []
    for idx in range(start, end):
        row_rect = pygame.Rect(panel_rect.x + 10, y, panel_rect.width - 20, line_h)
        minus_rect = pygame.Rect(panel_rect.right - 74, y + 1, 24, line_h - 2)
        plus_rect = pygame.Rect(panel_rect.right - 40, y + 1, 24, line_h - 2)
        rows.append((idx, row_rect, minus_rect, plus_rect))
        y += line_h
    return panel_rect, rows

MUTATION_COLORS: dict[int, tuple[int, int, int]] = {
    0: (80, 220, 160),   # AND/Life-like: green
    1: (175, 110, 255),  # XOR: purple
    2: (90, 190, 255),   # Majority: blue
    3: (255, 180, 80),   # OR: amber
    4: (255, 120, 180),  # XNOR: pink
    5: (255, 90, 90),    # NAND: red
    6: (120, 255, 220),  # Shift-gate: aqua
    7: (245, 245, 130),  # Birth-band: yellow
}

LOGIC_MUTATION_COLORS: dict[int, tuple[int, int, int]] = {
    0: (255, 70, 70),    # vivid red
    1: (255, 165, 40),   # vivid orange
    2: (245, 235, 70),   # vivid yellow
    3: (110, 255, 110),  # vivid lime
    4: (70, 240, 255),   # vivid cyan
    5: (90, 150, 255),   # vivid blue
    6: (190, 110, 255),  # vivid violet
    7: (255, 255, 255),  # white (target lock)
}


def _cell_color(sim: Simulation, coord: tuple[int, int]) -> tuple[int, int, int]:
    if sim.grid.mode == SimMode.LOGIC_FACTORIZER and coord in sim.grid.state:
        if coord in sim.grid.logic_solved_cells:
            return LOGIC_MUTATION_COLORS[7]
        role = sim.grid.logic_role.get(coord, "gate")
        if sim.grid.logic_solved and role in {"input_a", "input_b"}:
            return SUCCESS_COLOR
        base = LOGIC_MUTATION_COLORS[7] if role == "target" else LOGIC_MUTATION_COLORS.get(sim.grid.mutation_type(coord), CELL_COLOR)
        if int(sim.grid.state.get(coord, 0)) == 0:
            return (max(8, base[0] // 4), max(8, base[1] // 4), max(8, base[2] // 4))
        return (min(255, int(base[0] * 1.35)), min(255, int(base[1] * 1.35)), min(255, int(base[2] * 1.35)))
    if sim.is_structural_at(coord):
        return STRUCTURAL_WHITE if ((coord[0] + coord[1]) & 1) == 0 else STRUCTURAL_BLUE
    if sim.is_old_growth_at(coord):
        return OLD_GROWTH_COLOR
    return MUTATION_COLORS.get(sim.grid.mutation_type(coord), CELL_COLOR)


def _hovered_legend_label(
    sim: Simulation,
    coord: tuple[int, int],
    alive_coords: set[tuple[int, int]],
    structural_coords: set[tuple[int, int]],
    food_coords: set[tuple[int, int]],
    outpost_coords: set[tuple[int, int]],
) -> str | None:
    if coord in food_coords:
        return "Food"
    if coord in outpost_coords:
        return "Outpost Anchor (star)"

    if sim.grid.mode == SimMode.LOGIC_FACTORIZER:
        role = sim.grid.logic_role.get(coord)
        if role is None:
            return None
        if role == "target":
            return "Target (Locked)"
        if (
            sim.grid.logic_solved
            and coord in sim.grid.logic_solved_cells
            and role in {"input_a", "input_b"}
        ):
            return "Resolved Inputs"
        state = 1 if int(sim.grid.state.get(coord, 0)) != 0 else 0
        return "Input / Gate ON" if state == 1 else "Input / Gate OFF"

    if coord in structural_coords and coord not in alive_coords:
        return "Structural Ghost"
    if coord in sim.grid.overcrowded_structural_cells:
        return "Calcified/Overcrowded"
    if coord in alive_coords:
        if sim.is_structural_at(coord):
            return "Structural (White)" if ((coord[0] + coord[1]) & 1) == 0 else "Structural (Blue)"
        if sim.is_old_growth_at(coord):
            return "Old Growth"
        return f"Mutation M{sim.grid.mutation_type(coord)}"
    return None


def _seed_template_coords(text: str) -> set[tuple[int, int]]:
    coords: set[tuple[int, int]] = set()
    for row_index, byte in enumerate(text.encode("utf-8")):
        for bit_index in range(8):
            if byte & (1 << (7 - bit_index)):
                coords.add((bit_index, row_index))
    return coords


def _norm_shape(coords: set[tuple[int, int]]) -> set[tuple[int, int]]:
    if not coords:
        return set()
    min_x = min(x for x, _ in coords)
    min_y = min(y for _, y in coords)
    return {(x - min_x, y - min_y) for x, y in coords}


def _guess_seed_from_blob(alive_coords: set[tuple[int, int]]) -> str:
    if not alive_coords:
        return "none"

    norm = _norm_shape(alive_coords)
    candidates = ["Hi", "Hello", "World", "Hello World"]
    best = ("unknown", -1.0)
    for candidate in candidates:
        templ = _norm_shape(_seed_template_coords(candidate))
        inter = len(norm & templ)
        union = max(1, len(norm | templ))
        score = inter / union
        if score > best[1]:
            best = (candidate, score)
    return best[0] if best[1] >= 0.08 else "unknown"


def _guess_seed_from_centroid(
    structural_coords: set[tuple[int, int]],
    seed_history: list[tuple[str, tuple[int, int]]],
) -> str:
    if not structural_coords or not seed_history:
        return "unknown"
    cx = sum(x for x, _ in structural_coords) / len(structural_coords)
    cy = sum(y for _, y in structural_coords) / len(structural_coords)

    best_word = "unknown"
    best_dist = float("inf")
    for word, origin in seed_history:
        dx = cx - origin[0]
        dy = cy - origin[1]
        dist = (dx * dx) + (dy * dy)
        if dist < best_dist:
            best_dist = dist
            best_word = word
    return best_word if best_dist <= 400.0 else "unknown"


def _draw(
    sim: Simulation,
    viewport: Viewport,
    screen: pygame.Surface,
    font: pygame.font.Font,
    panel_font: pygame.font.Font,
    input_text: str,
    alive_coords: set[tuple[int, int]],
    structural_coords: set[tuple[int, int]],
    food_coords: set[tuple[int, int]],
    outpost_coords: set[tuple[int, int]],
    seed_history: list[tuple[str, tuple[int, int]]],
    snapshot_tick: int,
    panel_index: int,
    panel_scroll: int,
    sidebar_width: int,
    editing_attr: str | None = None,
    editing_text: str = "",
    render_stride: int = 1,
) -> None:
    root_screen = screen
    root_screen.fill(PANEL_BG)
    world_rect = pygame.Rect(sidebar_width, 0, viewport.width, viewport.height)
    info_rect = pygame.Rect(sidebar_width + viewport.width, 0, INFO_PANEL_WIDTH, viewport.height)
    screen = root_screen.subsurface(world_rect)
    now_tick = snapshot_tick
    size = max(1, int(viewport.cell_size))
    mouse_pos = pygame.mouse.get_pos()

    hovered_legend_label: str | None = None
    if world_rect.collidepoint(mouse_pos):
        wx, wy = viewport.screen_to_world(mouse_pos[0] - sidebar_width, mouse_pos[1])
        hovered_legend_label = _hovered_legend_label(
            sim,
            (wx, wy),
            alive_coords=alive_coords,
            structural_coords=structural_coords,
            food_coords=food_coords,
            outpost_coords=outpost_coords,
        )

    # Faint spatial grid to improve orientation while panning/zooming.
    if size >= 4:
        center_sx = int(viewport.width / 2 + viewport.offset_x)
        center_sy = int(viewport.height / 2 + viewport.offset_y)
        start_x = center_sx % size
        start_y = center_sy % size
        for x in range(start_x, viewport.width, size):
            pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, viewport.height), 1)
        for y in range(start_y, viewport.height, size):
            pygame.draw.line(screen, GRID_COLOR, (0, y), (viewport.width, y), 1)

    visible_cells: list[tuple[int, int]] = []
    for coord in alive_coords:
        sx, sy = viewport.world_to_screen(coord[0], coord[1])
        if sx + size < 0 or sy + size < 0 or sx >= viewport.width or sy >= viewport.height:
            continue
        visible_cells.append(coord)

    stride = max(1, int(render_stride))
    sampled_cells = visible_cells[::stride]
    structural_only_visible = [
        coord
        for coord in structural_coords
        if coord not in alive_coords
        and (
            lambda sx_sy: not (
                sx_sy[0] + size < 0
                or sx_sy[1] + size < 0
                or sx_sy[0] >= viewport.width
                or sx_sy[1] >= viewport.height
            )
        )(viewport.world_to_screen(coord[0], coord[1]))
    ]
    visible_food = [
        coord
        for coord in food_coords
        if (
            lambda sx_sy: not (
                sx_sy[0] + size < 0
                or sx_sy[1] + size < 0
                or sx_sy[0] >= viewport.width
                or sx_sy[1] >= viewport.height
            )
        )(viewport.world_to_screen(coord[0], coord[1]))
    ]
    visible_outposts = [
        coord
        for coord in outpost_coords
        if (
            lambda sx_sy: not (
                sx_sy[0] + size < 0
                or sx_sy[1] + size < 0
                or sx_sy[0] >= viewport.width
                or sx_sy[1] >= viewport.height
            )
        )(viewport.world_to_screen(coord[0], coord[1]))
    ]

    def _draw_star(surface: pygame.Surface, center: tuple[int, int], radius: int, color: tuple[int, int, int]) -> None:
        cx, cy = center
        points: list[tuple[int, int]] = []
        outer = max(2, radius)
        inner = max(1, int(outer * 0.45))
        for i in range(10):
            angle = (-3.14159265 / 2.0) + (i * (3.14159265 / 5.0))
            r = outer if (i % 2) == 0 else inner
            x = int(cx + (r * pygame.math.Vector2(1, 0).rotate_rad(angle).x))
            y = int(cy + (r * pygame.math.Vector2(1, 0).rotate_rad(angle).y))
            points.append((x, y))
        if len(points) >= 3:
            pygame.draw.polygon(surface, color, points, width=1)

    if sim.grid.mode == SimMode.LOGIC_FACTORIZER:
        tension_surface = pygame.Surface((viewport.width, viewport.height), pygame.SRCALPHA)
        input_a_coords = {coord for coord, role in sim.grid.logic_role.items() if role == "input_a"}
        input_b_coords = {coord for coord, role in sim.grid.logic_role.items() if role == "input_b"}
        gate_coords = [coord for coord, role in sim.grid.logic_role.items() if role == "gate"]
        target_coords_le = sorted(
            [coord for coord, role in sim.grid.logic_role.items() if role == "target"],
            key=lambda c: c[0],
            reverse=True,
        )
        target_bits_le = [1 if int(sim.grid.state.get(coord, 0)) != 0 else 0 for coord in target_coords_le]

        # Column match state for gate->target links with carry propagation.
        gate_cols = sorted({gx for gx, _ in gate_coords}, reverse=True)
        col_index_by_x = {gx: idx for idx, gx in enumerate(gate_cols)}
        carry_in = 0
        column_match: dict[int, bool] = {}
        extra_carry_match: dict[int, bool] = {}
        for col_idx, gx in enumerate(gate_cols):
            col = [coord for coord in gate_coords if coord[0] == gx]
            active = sum(1 for coord in col if int(sim.grid.state.get(coord, 0)) != 0)
            column_sum = active + carry_in
            sum_bit = column_sum & 1
            carry_out = column_sum >> 1
            tbit = target_bits_le[col_idx] if col_idx < len(target_bits_le) else 0
            column_match[gx] = sum_bit == tbit
            carry_in = carry_out

        for bit_idx in range(len(gate_cols), len(target_bits_le)):
            bit = carry_in & 1
            carry_in >>= 1
            extra_carry_match[bit_idx] = bit == target_bits_le[bit_idx]

        def _jitter(seed: int) -> tuple[int, int]:
            dx = ((seed * 17) % 5) - 2
            dy = ((seed * 31) % 5) - 2
            return dx, dy

        def _loop_line(
            surface: pygame.Surface,
            start: tuple[int, int],
            end: tuple[int, int],
            color: tuple[int, int, int, int],
            width: int,
            direction: int,
            magnitude: float = 16.0,
        ) -> None:
            sx, sy = start
            ex, ey = end
            mx = (sx + ex) / 2.0
            my = (sy + ey) / 2.0
            dx = ex - sx
            dy = ey - sy
            norm = max(1.0, (dx * dx + dy * dy) ** 0.5)
            # Perpendicular offset for an outward loop-like arc.
            ox = (-dy / norm) * magnitude * (1 if direction >= 0 else -1)
            oy = (dx / norm) * magnitude * (1 if direction >= 0 else -1)
            c1 = (int((sx * 0.6) + (mx * 0.4) + ox), int((sy * 0.6) + (my * 0.4) + oy))
            c2 = (int((sx * 0.4) + (mx * 0.6) + ox), int((sy * 0.4) + (my * 0.6) + oy))
            points = [start, c1, c2, end]
            pygame.draw.lines(surface, color, False, points, width)

        for gate in gate_coords:
            gx, gy = gate
            a_parent = (10, gy)
            b_parent = (gx, 10)
            if a_parent not in input_a_coords or b_parent not in input_b_coords:
                continue

            a_bit = 1 if int(sim.grid.state.get(a_parent, 0)) != 0 else 0
            b_bit = 1 if int(sim.grid.state.get(b_parent, 0)) != 0 else 0
            g_bit = 1 if int(sim.grid.state.get(gate, 0)) != 0 else 0
            satisfied = g_bit == (a_bit & b_bit)

            gsx, gsy = viewport.world_to_screen(gx, gy)
            asx, asy = viewport.world_to_screen(a_parent[0], a_parent[1])
            bsx, bsy = viewport.world_to_screen(b_parent[0], b_parent[1])
            gpt = (gsx + (size // 2), gsy + (size // 2))
            apt = (asx + (size // 2), asy + (size // 2))
            bpt = (bsx + (size // 2), bsy + (size // 2))

            if satisfied:
                pygame.draw.line(tension_surface, TENSION_LOW, gpt, apt, 2)
                pygame.draw.line(tension_surface, TENSION_LOW, gpt, bpt, 2)
            else:
                jx, jy = _jitter(hash((gate, now_tick)))
                gj = (gpt[0] + jx, gpt[1] + jy)
                aj = (apt[0] - jx, apt[1] - jy)
                bj = (bpt[0] + jy, bpt[1] - jx)
                # Red high-tension lines arc outward in one direction.
                _loop_line(tension_surface, gj, aj, TENSION_HIGH, 2, direction=1, magnitude=18.0)
                _loop_line(tension_surface, gj, bj, TENSION_HIGH, 2, direction=1, magnitude=18.0)

            tcoord = None
            col_idx = col_index_by_x.get(gx)
            if col_idx is not None and col_idx < len(target_coords_le):
                tcoord = target_coords_le[col_idx]
            if tcoord is not None:
                tsx, tsy = viewport.world_to_screen(tcoord[0], tcoord[1])
                tpt = (tsx + (size // 2), tsy + (size // 2))
                link_color = TARGET_LINK_MATCH if column_match.get(gx, False) else TARGET_LINK_MISMATCH
                link_w = 2 if column_match.get(gx, False) else 1
                if column_match.get(gx, False):
                    # Green match lines arc in the opposite direction from red.
                    _loop_line(tension_surface, gpt, tpt, link_color, link_w, direction=-1, magnitude=14.0)
                else:
                    pygame.draw.line(tension_surface, link_color, gpt, tpt, link_w)

        # Carry links from left-most gate column to high-order target bits.
        if gate_cols and len(target_coords_le) > len(gate_cols):
            left_col_x = min(gate_cols)
            bottom_row_y = max((gy for _, gy in gate_coords), default=0)
            lsx, lsy = viewport.world_to_screen(left_col_x, bottom_row_y)
            carry_anchor = (lsx + (size // 2), lsy + (size // 2))
            for bit_idx in range(len(gate_cols), len(target_coords_le)):
                tcoord = target_coords_le[bit_idx]
                tsx, tsy = viewport.world_to_screen(tcoord[0], tcoord[1])
                tpt = (tsx + (size // 2), tsy + (size // 2))
                match = extra_carry_match.get(bit_idx, False)
                link_color = TARGET_LINK_MATCH if match else TARGET_LINK_MISMATCH
                link_w = 2 if match else 1
                if match:
                    _loop_line(tension_surface, carry_anchor, tpt, link_color, link_w, direction=-1, magnitude=10.0)
                else:
                    pygame.draw.line(tension_surface, link_color, carry_anchor, tpt, link_w)

        screen.blit(tension_surface, (0, 0))

    for coord in sampled_cells:
        parent = sim.parent_at(coord)
        if parent is not None:
            sx, sy = viewport.world_to_screen(coord[0], coord[1])
            psx, psy = viewport.world_to_screen(parent[0], parent[1])
            if (
                (sx + size < 0 or sy + size < 0 or sx >= viewport.width or sy >= viewport.height)
                and (psx + size < 0 or psy + size < 0 or psx >= viewport.width or psy >= viewport.height)
            ):
                continue
            pygame.draw.line(screen, PARENT_LINE_COLOR, (psx, psy), (sx, sy), 1)

    heat_surface = pygame.Surface((viewport.width, viewport.height), pygame.SRCALPHA)
    ghost_surface = pygame.Surface((viewport.width, viewport.height), pygame.SRCALPHA)
    structural_surface = pygame.Surface((viewport.width, viewport.height), pygame.SRCALPHA)
    total_energy = sim.total_energy()
    pulse_alpha = skeleton_pulse_alpha(total_energy, snapshot_tick)

    energy_values = [sim.grid.energy(coord) for coord in sampled_cells]
    heat_threshold = 0
    if energy_values:
        sorted_energy = sorted(energy_values)
        idx = max(0, int(len(sorted_energy) * 0.9) - 1)
        heat_threshold = sorted_energy[idx]

    screen.lock()
    heat_surface.lock()
    ghost_surface.lock()
    structural_surface.lock()
    try:
        for coord in sampled_cells:
            sx, sy = viewport.world_to_screen(coord[0], coord[1])
            rect = pygame.Rect(sx, sy, size, size)
            solved_override = sim.grid.mode == SimMode.LOGIC_FACTORIZER and bool(sim.grid.logic_solved_cells) and coord in sim.grid.logic_solved_cells
            if solved_override:
                role = sim.grid.logic_role.get(coord, "gate")
                state = 1 if int(sim.grid.state.get(coord, 0)) != 0 else 0
                if role in {"input_a", "input_b", "target"}:
                    base_color = (255, 255, 255) if state == 1 else (70, 70, 70)
                else:
                    gate_base = LOGIC_MUTATION_COLORS.get(sim.grid.mutation_type(coord), (180, 180, 180))
                    base_color = gate_base if state == 1 else (50, 50, 50)
            else:
                base_color = _cell_color(sim, coord)
            if (not solved_override) and coord in sim.grid.overcrowded_structural_cells:
                base_color = CALCIFIED_COLOR
            screen.fill(base_color, rect)

            vx, vy = sim.grid.growth_vector(coord)
            if vx != 0 or vy != 0:
                cx = sx + (size // 2)
                cy = sy + (size // 2)
                tx = cx - vx
                ty = cy - vy
                if 0 <= tx < viewport.width and 0 <= ty < viewport.height:
                    screen.set_at((tx, ty), base_color)
            if sim.is_structural_at(coord):
                structural_surface.fill((base_color[0], base_color[1], base_color[2], pulse_alpha), rect)

            age = now_tick - sim.grid.last_touched_tick(coord)
            
            intensity = 0
            # Keep structural lineage colors readable by excluding structural cells from heat tinting.
            if (
                sim.grid.mode != SimMode.LOGIC_FACTORIZER
                and not sim.is_structural_at(coord)
                and sim.grid.energy(coord) >= heat_threshold
            ):
                age = now_tick - sim.last_touched_at(coord)
                intensity = max(0, min(180, 180 - (age * 8)))
            if intensity > 0:
                heat = (HEAT_COLOR[0], HEAT_COLOR[1], HEAT_COLOR[2], intensity)
                heat_surface.fill(heat, rect)

        for coord in structural_only_visible[::stride]:
            sx, sy = viewport.world_to_screen(coord[0], coord[1])
            rect = pygame.Rect(sx, sy, size, size)
            ghost_color = STRUCTURAL_WHITE if ((coord[0] + coord[1]) & 1) == 0 else STRUCTURAL_BLUE
            ghost_surface.fill((ghost_color[0], ghost_color[1], ghost_color[2], pulse_alpha), rect)

        for coord in visible_food[::stride]:
            sx, sy = viewport.world_to_screen(coord[0], coord[1])
            food_rect = pygame.Rect(sx, sy, size, size)
            screen.fill(FOOD_COLOR, food_rect)

        for coord in visible_outposts[::stride]:
            sx, sy = viewport.world_to_screen(coord[0], coord[1])
            center = (sx + (size // 2), sy + (size // 2))
            radius = max(1, size // 2)
            _draw_star(screen, center, radius, OUTPOST_COLOR)
    finally:
        structural_surface.unlock()
        ghost_surface.unlock()
        heat_surface.unlock()
        screen.unlock()

    screen.blit(ghost_surface, (0, 0))
    screen.blit(structural_surface, (0, 0))
    screen.blit(heat_surface, (0, 0))

    centroid_guess = _guess_seed_from_centroid(structural_coords, seed_history)
    blob_guess = _guess_seed_from_blob(alive_coords)
    guess = centroid_guess if centroid_guess != "unknown" else blob_guess
    last_seed = sim.last_seeded_text()
    sim.set_coherence_match(bool(last_seed) and guess == last_seed)
    coherence = coherence_percent_active(alive_coords, last_seed, seed_history)
    sim.set_coherence_percent(coherence)

    input_prompt = f"seed> {input_text}"
    input_surface = font.render(input_prompt, True, TEXT_COLOR)
    input_y = viewport.height - input_surface.get_height() - 10
    screen.blit(input_surface, (10, input_y))

    if not sim.config.auto_step:
        overlay = font.render("PAUSED - [F1] to Play", True, PAUSED_TEXT_COLOR)
        ox = (viewport.width - overlay.get_width()) // 2
        oy = 40
        screen.blit(overlay, (ox, oy))
        pygame.draw.rect(screen, PAUSED_BORDER_COLOR, pygame.Rect(2, 2, viewport.width - 4, viewport.height - 4), width=2)

    if sim.grid.mode == SimMode.LOGIC_FACTORIZER and sim.grid.logic_jolt_notice_ticks > 0:
        jolt_text = font.render("System Stagnant - Applying Thermal Jolt", True, (255, 220, 120))
        jx = max(10, (viewport.width - jolt_text.get_width()) // 2)
        jy = 12
        screen.blit(jolt_text, (jx, jy))

    visible_items = _visible_control_items(sim)
    if panel_index >= len(visible_items):
        panel_index = max(0, len(visible_items) - 1)
    panel_rect, rows = _panel_layout(viewport, visible_items, sidebar_width, panel_scroll=panel_scroll)
    pygame.draw.rect(root_screen, PANEL_BG, panel_rect)
    pygame.draw.rect(root_screen, PANEL_BORDER, panel_rect, width=2)

    if editing_attr is None:
        title_text = "Settings  (Click +/- or use arrows)"
    else:
        title_text = "Settings  (Editing value: Enter=apply, Esc=cancel)"
    title = panel_font.render(title_text, True, PANEL_TEXT)
    root_screen.blit(title, (panel_rect.x + 10, panel_rect.y + 12))

    hovered_attr: str | None = None
    for idx, row_rect, minus_rect, plus_rect in rows:
        label, attr, kind, *_ = visible_items[idx]
        value = _format_control_value(getattr(sim.grid, attr), kind)
        if editing_attr == attr and kind in {"int", "float"}:
            value = f"[{editing_text}]"
        color = PANEL_ACTIVE if idx == panel_index else PANEL_TEXT
        compact_label = label if len(label) <= 26 else f"{label[:25]}…"
        row = panel_font.render(f"{compact_label}: {value}", True, color)
        root_screen.blit(row, (row_rect.x + 2, row_rect.y))

        pygame.draw.rect(root_screen, PANEL_BORDER, minus_rect, width=1)
        pygame.draw.rect(root_screen, PANEL_BORDER, plus_rect, width=1)
        minus_text = panel_font.render("-", True, PANEL_TEXT)
        plus_text = panel_font.render("+", True, PANEL_TEXT)
        root_screen.blit(minus_text, (minus_rect.x + 8, minus_rect.y - 1))
        root_screen.blit(plus_text, (plus_rect.x + 8, plus_rect.y - 1))

        if row_rect.collidepoint(mouse_pos) or minus_rect.collidepoint(mouse_pos) or plus_rect.collidepoint(mouse_pos):
            hovered_attr = attr

    if editing_attr is None:
        hint_text = "Enter submits seed when text exists."
    else:
        hint_text = "Typing edits selected setting. Enter apply, Esc cancel."
    hint = panel_font.render(hint_text, True, PANEL_TEXT)
    root_screen.blit(hint, (panel_rect.x + 10, panel_rect.bottom - 28))

    logic_reset_rect = pygame.Rect(panel_rect.x + 10, panel_rect.bottom - 54, panel_rect.width - 20, 20)
    logic_active = sim.grid.mode == SimMode.LOGIC_FACTORIZER
    logic_btn_bg = (36, 64, 96) if logic_active else (28, 34, 44)
    logic_btn_border = PANEL_ACTIVE if logic_active else PANEL_BORDER
    pygame.draw.rect(root_screen, logic_btn_bg, logic_reset_rect)
    pygame.draw.rect(root_screen, logic_btn_border, logic_reset_rect, width=1)
    logic_label = "Reset Logic Lattice"
    logic_text = panel_font.render(logic_label, True, PANEL_TEXT if logic_active else (160, 170, 185))
    root_screen.blit(logic_text, (logic_reset_rect.x + 8, logic_reset_rect.y + 3))

    pygame.draw.rect(root_screen, PANEL_BG, info_rect)
    pygame.draw.rect(root_screen, PANEL_BORDER, info_rect, width=2)
    info_title = panel_font.render("Simulation Info", True, PANEL_TEXT)
    root_screen.blit(info_title, (info_rect.x + 10, info_rect.y + 12))

    info_lines = [
        f"tick: {snapshot_tick}",
        f"alive: {len(alive_coords)}",
        f"structural: {sim.structural_count()}",
        f"energy: {total_energy}",
        f"peak: {sim.peak_population}",
        f"food: {len(food_coords)}",
        f"outposts: {len(outpost_coords)}",
        f"radius: {sim.current_radius()}",
        f"guess: {guess}",
        f"coherence: {coherence:5.1f}%",
        f"zoom: {viewport.cell_size:.2f}",
        "panel: LEFT(settings)",
    ]
    if sim.grid.mode == SimMode.LOGIC_FACTORIZER:
        input_a = sorted((coord for coord, role in sim.grid.logic_role.items() if role == "input_a"), key=lambda c: c[1], reverse=True)
        input_b = sorted((coord for coord, role in sim.grid.logic_role.items() if role == "input_b"), key=lambda c: c[0], reverse=True)
        target_bits = [
            1 if int(sim.grid.state.get(coord, 0)) != 0 else 0
            for coord in sorted((coord for coord, role in sim.grid.logic_role.items() if role == "target"), key=lambda c: c[0], reverse=True)
        ]
        target_value = sum((bit << i) for i, bit in enumerate(target_bits))
        a_value = sum((1 << i) for i, coord in enumerate(input_a) if int(sim.grid.state.get(coord, 0)) != 0)
        b_value = sum((1 << i) for i, coord in enumerate(input_b) if int(sim.grid.state.get(coord, 0)) != 0)
        info_lines.append(f"Target: {target_value}")
        info_lines.append(f"Current Guess: {a_value} x {b_value} = {a_value * b_value}")
    iy = info_rect.y + 42
    for line in info_lines:
        txt = panel_font.render(line, True, PANEL_TEXT)
        root_screen.blit(txt, (info_rect.x + 10, iy))
        iy += 20

    legend_title = panel_font.render("Color Legend", True, PANEL_TEXT)
    root_screen.blit(legend_title, (info_rect.x + 10, iy + 8))
    iy += 34

    if sim.grid.mode == SimMode.LOGIC_FACTORIZER:
        legend_items: list[tuple[str, str, tuple[int, int, int]]] = [
            ("Input / Gate OFF", "swatch", (48, 48, 48)),
            ("Input / Gate ON", "swatch", LOGIC_MUTATION_COLORS[4]),
            ("Target (Locked)", "swatch", LOGIC_MUTATION_COLORS[7]),
            ("Resolved Inputs", "swatch", SUCCESS_COLOR),
            ("Logic M0", "swatch", LOGIC_MUTATION_COLORS[0]),
            ("Logic M1", "swatch", LOGIC_MUTATION_COLORS[1]),
            ("Logic M2", "swatch", LOGIC_MUTATION_COLORS[2]),
            ("Logic M3", "swatch", LOGIC_MUTATION_COLORS[3]),
            ("Logic M4", "swatch", LOGIC_MUTATION_COLORS[4]),
            ("Logic M5", "swatch", LOGIC_MUTATION_COLORS[5]),
            ("Logic M6", "swatch", LOGIC_MUTATION_COLORS[6]),
            ("Logic M7", "swatch", LOGIC_MUTATION_COLORS[7]),
        ]
    else:
        legend_items = [
            ("Live Cell", "swatch", CELL_COLOR),
            ("Old Growth", "swatch", OLD_GROWTH_COLOR),
            ("Structural (Blue)", "swatch", STRUCTURAL_BLUE),
            ("Structural (White)", "swatch", STRUCTURAL_WHITE),
            ("Structural Ghost", "swatch", (GHOST_BLUE[0], GHOST_BLUE[1], GHOST_BLUE[2])),
            ("Calcified/Overcrowded", "swatch", CALCIFIED_COLOR),
            ("Food", "swatch", FOOD_COLOR),
            ("Outpost Anchor (star)", "star", OUTPOST_COLOR),
            ("Lineage Link", "line", PARENT_LINE_COLOR),
            ("Space Grid", "line", GRID_COLOR),
            ("Heat", "swatch", HEAT_COLOR),
            ("Mutation M0", "swatch", MUTATION_COLORS[0]),
            ("Mutation M1", "swatch", MUTATION_COLORS[1]),
            ("Mutation M2", "swatch", MUTATION_COLORS[2]),
            ("Mutation M3", "swatch", MUTATION_COLORS[3]),
            ("Mutation M4", "swatch", MUTATION_COLORS[4]),
            ("Mutation M5", "swatch", MUTATION_COLORS[5]),
            ("Mutation M6", "swatch", MUTATION_COLORS[6]),
            ("Mutation M7", "swatch", MUTATION_COLORS[7]),
        ]
    for label, kind, color in legend_items:
        row_rect = pygame.Rect(info_rect.x + 6, iy - 1, info_rect.width - 12, 16)
        if hovered_legend_label == label:
            pygame.draw.rect(root_screen, (58, 74, 102), row_rect)
            pygame.draw.rect(root_screen, PANEL_ACTIVE, row_rect, width=1)
        swatch = pygame.Rect(info_rect.x + 10, iy + 2, 12, 12)
        if kind == "star":
            pygame.draw.rect(root_screen, PANEL_BORDER, swatch, width=1)
            _draw_star(root_screen, swatch.center, max(2, swatch.width // 2), color)
        elif kind == "line":
            pygame.draw.rect(root_screen, PANEL_BORDER, swatch, width=1)
            pygame.draw.line(root_screen, color, (swatch.left + 1, swatch.centery), (swatch.right - 1, swatch.centery), 1)
        else:
            pygame.draw.rect(root_screen, color, swatch)
            pygame.draw.rect(root_screen, PANEL_BORDER, swatch, width=1)
        lbl = panel_font.render(label, True, PANEL_TEXT)
        root_screen.blit(lbl, (info_rect.x + 30, iy))
        iy += 18

    if hovered_attr is not None:
        help_text = CONTROL_PANEL_HELP.get(hovered_attr, "No description available.")
        setting_label = next((label for label, attr, *_ in visible_items if attr == hovered_attr), hovered_attr)
        help_rect = pygame.Rect(info_rect.x + 10, info_rect.bottom - 150, info_rect.width - 20, 138)
        pygame.draw.rect(root_screen, (24, 30, 42), help_rect)
        pygame.draw.rect(root_screen, PANEL_ACTIVE, help_rect, width=1)

        help_title = panel_font.render("Hovered setting", True, PANEL_ACTIVE)
        root_screen.blit(help_title, (help_rect.x + 6, help_rect.y + 4))
        setting_surface = panel_font.render(setting_label, True, PANEL_TEXT)
        root_screen.blit(setting_surface, (help_rect.x + 6, help_rect.y + 22))

        wrapped = _wrap_text(help_text, panel_font, help_rect.width - 12)
        ty = help_rect.y + 42
        for line in wrapped[:5]:
            line_surf = panel_font.render(line, True, PANEL_TEXT)
            root_screen.blit(line_surf, (help_rect.x + 6, ty))
            ty += 18


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Non-Matrix Phase 1")

    viewport = Viewport()
    screen = pygame.display.set_mode((viewport.width + SIDEBAR_WIDTH + INFO_PANEL_WIDTH, viewport.height))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)
    panel_font = pygame.font.SysFont("consolas", 14)

    sim = Simulation()
    sim.config.auto_step = False
    sim.start_heartbeat()

    running = True
    dragging = False
    last_mouse = (0, 0)
    input_text = ""
    accumulator = 0.0
    panel_index = 0
    panel_scroll = 0
    editing_attr: str | None = None
    editing_text = ""

    while running:
        dt = clock.tick(60) / 1000.0
        accumulator += dt

        pressed = pygame.key.get_pressed()
        pan_step = max(4, int(220 * dt))
        if pressed[pygame.K_LEFT]:
            viewport.pan(pan_step, 0)
        if pressed[pygame.K_RIGHT]:
            viewport.pan(-pan_step, 0)
        if pressed[pygame.K_UP]:
            viewport.pan(0, pan_step)
        if pressed[pygame.K_DOWN]:
            viewport.pan(0, -pan_step)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if editing_attr is not None:
                        editing_attr = None
                        editing_text = ""
                    logic_reset_rect = pygame.Rect(10, viewport.height - 54, SIDEBAR_WIDTH - 20, 20)
                    if logic_reset_rect.collidepoint(event.pos) and sim.grid.mode == SimMode.LOGIC_FACTORIZER:
                        sim.grid._init_logic_lattice()
                        sim.snapshot = set(sim.grid.alive_coords)
                        sim.snapshot_tick = sim.grid.tick
                        sim.peak_population = max(sim.peak_population, len(sim.grid.alive_coords))
                        sim.config.auto_step = True
                        continue

                    visible_items = _visible_control_items(sim)
                    if panel_index >= len(visible_items):
                        panel_index = max(0, len(visible_items) - 1)
                    panel_rect, rows = _panel_layout(viewport, visible_items, SIDEBAR_WIDTH, panel_scroll=panel_scroll)
                    if panel_rect.collidepoint(event.pos):
                        handled = False
                        for idx, row_rect, minus_rect, plus_rect in rows:
                            if minus_rect.collidepoint(event.pos):
                                panel_index = idx
                                _adjust_control_value(sim, visible_items[panel_index], direction=-1)
                                handled = True
                                break
                            if plus_rect.collidepoint(event.pos):
                                panel_index = idx
                                _adjust_control_value(sim, visible_items[panel_index], direction=1)
                                handled = True
                                break
                            if row_rect.collidepoint(event.pos):
                                panel_index = idx
                                item = visible_items[panel_index]
                                _, attr, kind, *_ = item
                                if kind in {"int", "float"}:
                                    editing_attr = attr
                                    editing_text = _format_control_value(getattr(sim.grid, attr), kind)
                                handled = True
                                break
                        if handled:
                            line_h = 22
                            max_rows = max(1, (viewport.height - 80) // line_h)
                            visible_items = _visible_control_items(sim)
                            if panel_index < panel_scroll:
                                panel_scroll = panel_index
                            elif panel_index >= panel_scroll + max_rows:
                                panel_scroll = panel_index - max_rows + 1
                            max_start = max(0, len(visible_items) - max_rows)
                            panel_scroll = max(0, min(panel_scroll, max_start))
                            continue

                    if event.pos[0] < SIDEBAR_WIDTH or event.pos[0] >= (SIDEBAR_WIDTH + viewport.width):
                        continue

                    dragging = True
                    last_mouse = event.pos
                elif event.button == 4:
                    if event.pos[0] < SIDEBAR_WIDTH:
                        panel_scroll = max(0, panel_scroll - 2)
                        continue
                    if SIDEBAR_WIDTH <= event.pos[0] < (SIDEBAR_WIDTH + viewport.width):
                        viewport.zoom_at(1.1, event.pos[0] - SIDEBAR_WIDTH, event.pos[1])
                elif event.button == 5:
                    if event.pos[0] < SIDEBAR_WIDTH:
                        line_h = 22
                        max_rows = max(1, (viewport.height - 80) // line_h)
                        visible_items = _visible_control_items(sim)
                        max_start = max(0, len(visible_items) - max_rows)
                        panel_scroll = min(max_start, panel_scroll + 2)
                        continue
                    if SIDEBAR_WIDTH <= event.pos[0] < (SIDEBAR_WIDTH + viewport.width):
                        viewport.zoom_at(1 / 1.1, event.pos[0] - SIDEBAR_WIDTH, event.pos[1])
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if dragging and event.pos == last_mouse:
                    wx, wy = viewport.screen_to_world(event.pos[0] - SIDEBAR_WIDTH, event.pos[1])
                    sim.seed_root((wx, wy))
                dragging = False
            elif event.type == pygame.MOUSEMOTION and dragging:
                dx = event.pos[0] - last_mouse[0]
                dy = event.pos[1] - last_mouse[1]
                viewport.pan(dx, dy)
                last_mouse = event.pos
            elif event.type == pygame.KEYDOWN:
                if editing_attr is not None:
                    visible_items = _visible_control_items(sim)
                    edit_item = next((item for item in visible_items if item[1] == editing_attr), None)
                    if event.key == pygame.K_ESCAPE:
                        editing_attr = None
                        editing_text = ""
                    elif event.key == pygame.K_RETURN:
                        if edit_item is not None:
                            _apply_direct_control_value(sim, edit_item, editing_text)
                        editing_attr = None
                        editing_text = ""
                    elif event.key == pygame.K_BACKSPACE:
                        editing_text = editing_text[:-1]
                    elif event.unicode and event.unicode in "0123456789.-":
                        editing_text += event.unicode
                elif event.key == pygame.K_RETURN and input_text:
                    sim.seed_text(input_text, origin=(0, 0))
                    input_text = ""
                    accumulator = 0.0
                    sim.config.auto_step = True
                elif event.key == pygame.K_F3:
                    sim.clear_world()
                    sim.config.auto_step = False
                    accumulator = 0.0
                elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT) or (
                    event.key == pygame.K_RETURN and not input_text
                ):
                    visible_items = _visible_control_items(sim)
                    if panel_index >= len(visible_items):
                        panel_index = max(0, len(visible_items) - 1)
                    if event.key == pygame.K_UP:
                        panel_index = max(0, panel_index - 1)
                    elif event.key == pygame.K_DOWN:
                        panel_index = min(len(visible_items) - 1, panel_index + 1)
                    elif event.key == pygame.K_LEFT:
                        if visible_items:
                            _adjust_control_value(sim, visible_items[panel_index], direction=-1)
                    elif event.key == pygame.K_RIGHT:
                        if visible_items:
                            _adjust_control_value(sim, visible_items[panel_index], direction=1)
                    elif event.key == pygame.K_RETURN:
                        if visible_items:
                            _adjust_control_value(sim, visible_items[panel_index], direction=1)

                    line_h = 22
                    max_rows = max(1, (viewport.height - 80) // line_h)
                    if panel_index < panel_scroll:
                        panel_scroll = panel_index
                    elif panel_index >= panel_scroll + max_rows:
                        panel_scroll = panel_index - max_rows + 1
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.key == pygame.K_F1:
                    sim.config.auto_step = not sim.config.auto_step
                elif event.key == pygame.K_F2:
                    sim.step()
                elif event.unicode and event.unicode.isprintable():
                    input_text += event.unicode

        fps = clock.get_fps()
        render_stride = 1 if sim.grid.mode == SimMode.LOGIC_FACTORIZER else (4 if fps > 0 and fps < 15 else 1)
        render_every = max(1, int(getattr(sim.grid, "render_every_x_ticks", 1)))
        force_final_render = bool(getattr(sim.grid, "needs_final_render", False))
        current_tick = int(getattr(sim.grid, "tick", 0))
        should_draw = force_final_render or (current_tick % render_every == 0)
        visible_items = _visible_control_items(sim)
        if panel_index >= len(visible_items):
            panel_index = max(0, len(visible_items) - 1)
        snapshot = sim.snapshot_coords()
        structural_snapshot = sim.structural_coords_snapshot()
        food_snapshot = sim.food_coords_snapshot()
        outpost_snapshot = sim.outpost_coords_snapshot()
        seed_history = sim.seed_history_snapshot()
        if should_draw:
            _draw(
                sim,
                viewport,
                screen,
                font,
                panel_font,
                input_text,
                alive_coords=snapshot,
                structural_coords=structural_snapshot,
                food_coords=food_snapshot,
                outpost_coords=outpost_snapshot,
                seed_history=seed_history,
                snapshot_tick=sim.snapshot_tick,
                panel_index=panel_index,
                panel_scroll=panel_scroll,
                sidebar_width=SIDEBAR_WIDTH,
                editing_attr=editing_attr,
                editing_text=editing_text,
                render_stride=render_stride,
            )
            pygame.display.flip()

        if force_final_render:
            sim.grid.needs_final_render = False
            sim.config.auto_step = False
            pygame.display.flip()

    sim.stop_heartbeat()
    pygame.quit()


if __name__ == "__main__":
    main()

