from __future__ import annotations

import pygame

from .signal_coherence import coherence_percent_active, skeleton_pulse_alpha
from .simulation import Simulation
from .viewport import Viewport

BACKGROUND = (8, 10, 16)
GRID_COLOR = (22, 28, 40)
CELL_COLOR = (80, 220, 160)
PARENT_LINE_COLOR = (70, 90, 130)
HEAT_COLOR = (255, 110, 30)
TEXT_COLOR = (230, 235, 240)
OLD_GROWTH_COLOR = (0, 255, 255)
STRUCTURAL_BLUE = (120, 180, 255)
STRUCTURAL_WHITE = (230, 245, 255)
GHOST_BLUE = (90, 140, 255, 50)
FOOD_COLOR = (255, 210, 90)
OUTPOST_COLOR = (255, 245, 180)
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
    if kind == "bool":
        return "ON" if bool(value) else "OFF"
    if kind == "int":
        return str(int(value))
    return f"{float(value):.2f}"


def _adjust_control_value(sim: Simulation, item: ControlItem, direction: int) -> None:
    label, attr, kind, step, min_value, max_value = item
    _ = label
    current = getattr(sim.grid, attr)
    if kind == "bool":
        setattr(sim.grid, attr, not bool(current))
        return

    raw_next = float(current) + (float(direction) * float(step))
    clamped = max(float(min_value), min(float(max_value), raw_next))
    if kind == "int":
        setattr(sim.grid, attr, int(round(clamped)))
    else:
        setattr(sim.grid, attr, float(clamped))


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


def _panel_layout(
    viewport: Viewport,
    panel_index: int,
    sidebar_width: int,
) -> tuple[pygame.Rect, list[tuple[int, pygame.Rect, pygame.Rect, pygame.Rect]]]:
    panel_rect = pygame.Rect(0, 0, sidebar_width, viewport.height)

    line_h = 22
    max_rows = max(1, (panel_rect.height - 80) // line_h)
    start = max(0, min(panel_index - (max_rows // 2), max(0, len(CONTROL_PANEL_ITEMS) - max_rows)))
    end = min(len(CONTROL_PANEL_ITEMS), start + max_rows)

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


def _cell_color(sim: Simulation, coord: tuple[int, int]) -> tuple[int, int, int]:
    if sim.is_structural_at(coord):
        return STRUCTURAL_WHITE if ((coord[0] + coord[1]) & 1) == 0 else STRUCTURAL_BLUE
    if sim.is_old_growth_at(coord):
        return OLD_GROWTH_COLOR
    return MUTATION_COLORS.get(sim.grid.mutation_type(coord), CELL_COLOR)


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
    sidebar_width: int,
    render_stride: int = 1,
) -> None:
    root_screen = screen
    root_screen.fill(PANEL_BG)
    world_rect = pygame.Rect(sidebar_width, 0, viewport.width, viewport.height)
    info_rect = pygame.Rect(sidebar_width + viewport.width, 0, INFO_PANEL_WIDTH, viewport.height)
    screen = root_screen.subsurface(world_rect)
    now_tick = snapshot_tick
    size = max(1, int(viewport.cell_size))

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
            base_color = _cell_color(sim, coord)
            if coord in sim.grid.overcrowded_structural_cells:
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
            if sim.grid.energy(coord) >= heat_threshold:
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

    panel_rect, rows = _panel_layout(viewport, panel_index, sidebar_width)
    pygame.draw.rect(root_screen, PANEL_BG, panel_rect)
    pygame.draw.rect(root_screen, PANEL_BORDER, panel_rect, width=2)

    title = panel_font.render("Settings  (Click +/- or use arrows)", True, PANEL_TEXT)
    root_screen.blit(title, (panel_rect.x + 10, panel_rect.y + 12))

    hovered_attr: str | None = None
    mouse_pos = pygame.mouse.get_pos()
    for idx, row_rect, minus_rect, plus_rect in rows:
        label, attr, kind, *_ = CONTROL_PANEL_ITEMS[idx]
        value = _format_control_value(getattr(sim.grid, attr), kind)
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

    hint = panel_font.render("Enter submits seed when text exists.", True, PANEL_TEXT)
    root_screen.blit(hint, (panel_rect.x + 10, panel_rect.bottom - 28))

    if hovered_attr is not None:
        help_text = CONTROL_PANEL_HELP.get(hovered_attr, "No description available.")
        tooltip_rect = pygame.Rect(panel_rect.x + 10, panel_rect.bottom - 140, panel_rect.width - 20, 106)
        pygame.draw.rect(root_screen, (24, 30, 42), tooltip_rect)
        pygame.draw.rect(root_screen, PANEL_ACTIVE, tooltip_rect, width=1)
        help_title = panel_font.render("Setting details", True, PANEL_ACTIVE)
        root_screen.blit(help_title, (tooltip_rect.x + 6, tooltip_rect.y + 4))
        wrapped = _wrap_text(help_text, panel_font, tooltip_rect.width - 12)
        ty = tooltip_rect.y + 24
        for line in wrapped[:4]:
            line_surf = panel_font.render(line, True, PANEL_TEXT)
            root_screen.blit(line_surf, (tooltip_rect.x + 6, ty))
            ty += 18

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
    iy = info_rect.y + 42
    for line in info_lines:
        txt = panel_font.render(line, True, PANEL_TEXT)
        root_screen.blit(txt, (info_rect.x + 10, iy))
        iy += 20

    legend_title = panel_font.render("Color Legend", True, PANEL_TEXT)
    root_screen.blit(legend_title, (info_rect.x + 10, iy + 8))
    iy += 34

    legend_items: list[tuple[str, tuple[int, int, int]]] = [
        ("Live Cell", CELL_COLOR),
        ("Old Growth", OLD_GROWTH_COLOR),
        ("Structural (Blue)", STRUCTURAL_BLUE),
        ("Structural (White)", STRUCTURAL_WHITE),
        ("Calcified/Overcrowded", CALCIFIED_COLOR),
        ("Food", FOOD_COLOR),
        ("Outpost", OUTPOST_COLOR),
        ("Heat", HEAT_COLOR),
    ]
    for label, color in legend_items:
        swatch = pygame.Rect(info_rect.x + 10, iy + 2, 12, 12)
        pygame.draw.rect(root_screen, color, swatch)
        pygame.draw.rect(root_screen, PANEL_BORDER, swatch, width=1)
        lbl = panel_font.render(label, True, PANEL_TEXT)
        root_screen.blit(lbl, (info_rect.x + 30, iy))
        iy += 18


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
                    panel_rect, rows = _panel_layout(viewport, panel_index, SIDEBAR_WIDTH)
                    if panel_rect.collidepoint(event.pos):
                        handled = False
                        for idx, row_rect, minus_rect, plus_rect in rows:
                            if minus_rect.collidepoint(event.pos):
                                panel_index = idx
                                _adjust_control_value(sim, CONTROL_PANEL_ITEMS[panel_index], direction=-1)
                                handled = True
                                break
                            if plus_rect.collidepoint(event.pos):
                                panel_index = idx
                                _adjust_control_value(sim, CONTROL_PANEL_ITEMS[panel_index], direction=1)
                                handled = True
                                break
                            if row_rect.collidepoint(event.pos):
                                panel_index = idx
                                handled = True
                                break
                        if handled:
                            continue

                    if event.pos[0] < SIDEBAR_WIDTH or event.pos[0] >= (SIDEBAR_WIDTH + viewport.width):
                        continue

                    dragging = True
                    last_mouse = event.pos
                elif event.button == 4:
                    if SIDEBAR_WIDTH <= event.pos[0] < (SIDEBAR_WIDTH + viewport.width):
                        viewport.zoom_at(1.1, event.pos[0] - SIDEBAR_WIDTH, event.pos[1])
                elif event.button == 5:
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
                if event.key == pygame.K_RETURN and input_text:
                    sim.seed_text(input_text, origin=(0, 0))
                    input_text = ""
                    accumulator = 0.0
                    sim.config.auto_step = True
                elif event.key == pygame.K_F3:
                    sim.clear_world()
                    sim.config.auto_step = False
                    accumulator = 0.0
                elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN):
                    if event.key == pygame.K_UP:
                        panel_index = max(0, panel_index - 1)
                    elif event.key == pygame.K_DOWN:
                        panel_index = min(len(CONTROL_PANEL_ITEMS) - 1, panel_index + 1)
                    elif event.key == pygame.K_LEFT:
                        _adjust_control_value(sim, CONTROL_PANEL_ITEMS[panel_index], direction=-1)
                    elif event.key == pygame.K_RIGHT:
                        _adjust_control_value(sim, CONTROL_PANEL_ITEMS[panel_index], direction=1)
                    elif event.key == pygame.K_RETURN:
                        _adjust_control_value(sim, CONTROL_PANEL_ITEMS[panel_index], direction=1)
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.key == pygame.K_F1:
                    sim.config.auto_step = not sim.config.auto_step
                elif event.key == pygame.K_F2:
                    sim.step()
                elif event.unicode and event.unicode.isprintable():
                    input_text += event.unicode

        fps = clock.get_fps()
        render_stride = 4 if fps > 0 and fps < 15 else 1
        snapshot = sim.snapshot_coords()
        structural_snapshot = sim.structural_coords_snapshot()
        food_snapshot = sim.food_coords_snapshot()
        outpost_snapshot = sim.outpost_coords_snapshot()
        seed_history = sim.seed_history_snapshot()
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
            sidebar_width=SIDEBAR_WIDTH,
            render_stride=render_stride,
        )
        pygame.display.flip()

    sim.stop_heartbeat()
    pygame.quit()


if __name__ == "__main__":
    main()

