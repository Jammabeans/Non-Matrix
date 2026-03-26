from __future__ import annotations

import pygame

from .signal_coherence import coherence_percent, skeleton_pulse_alpha
from .simulation import Simulation
from .viewport import Viewport

BACKGROUND = (8, 10, 16)
CELL_COLOR = (80, 220, 160)
PARENT_LINE_COLOR = (70, 90, 130)
HEAT_COLOR = (255, 110, 30)
TEXT_COLOR = (230, 235, 240)
OLD_GROWTH_COLOR = (0, 255, 255)
STRUCTURAL_BLUE = (120, 180, 255)
STRUCTURAL_WHITE = (230, 245, 255)
GHOST_BLUE = (90, 140, 255, 50)

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
    input_text: str,
    alive_coords: set[tuple[int, int]],
    structural_coords: set[tuple[int, int]],
    seed_history: list[tuple[str, tuple[int, int]]],
    snapshot_tick: int,
    render_stride: int = 1,
) -> None:
    screen.fill(BACKGROUND)
    now_tick = snapshot_tick
    size = max(1, int(viewport.cell_size))

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
            screen.fill(base_color, rect)
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
    coherence = coherence_percent(structural_coords, last_seed, seed_history)

    hud = (
        f"tick={snapshot_tick} alive={len(alive_coords)} "
        f"structural={sim.structural_count()} "
        f"energy={total_energy} peak={sim.peak_population} "
        f"guess={guess} coherence={coherence:5.1f}% zoom={viewport.cell_size:.2f}"
    )
    text = font.render(hud, True, TEXT_COLOR)
    screen.blit(text, (10, 10))

    input_prompt = f"seed> {input_text}"
    input_surface = font.render(input_prompt, True, TEXT_COLOR)
    input_y = viewport.height - input_surface.get_height() - 10
    screen.blit(input_surface, (10, input_y))


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Non-Matrix Phase 1")

    viewport = Viewport()
    screen = pygame.display.set_mode((viewport.width, viewport.height))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)

    sim = Simulation()
    sim.config.auto_step = False
    sim.start_heartbeat()

    running = True
    dragging = False
    last_mouse = (0, 0)
    input_text = ""
    accumulator = 0.0

    while running:
        dt = clock.tick(60) / 1000.0
        accumulator += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    dragging = True
                    last_mouse = event.pos
                elif event.button == 4:
                    viewport.zoom_at(1.1, event.pos[0], event.pos[1])
                elif event.button == 5:
                    viewport.zoom_at(1 / 1.1, event.pos[0], event.pos[1])
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if dragging and event.pos == last_mouse:
                    wx, wy = viewport.screen_to_world(event.pos[0], event.pos[1])
                    sim.seed_root((wx, wy))
                dragging = False
            elif event.type == pygame.MOUSEMOTION and dragging:
                dx = event.pos[0] - last_mouse[0]
                dy = event.pos[1] - last_mouse[1]
                viewport.pan(dx, dy)
                last_mouse = event.pos
            elif event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                ctrl_held = (mods & pygame.KMOD_CTRL) != 0

                if event.key == pygame.K_DELETE:
                    sim.clear_world()
                    sim.config.auto_step = False
                    accumulator = 0.0
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.key == pygame.K_RETURN:
                    if input_text:
                        sim.seed_text(input_text, origin=(0, 0))
                        input_text = ""
                        accumulator = 0.0
                        sim.config.auto_step = True
                elif ctrl_held and event.key == pygame.K_SPACE:
                    sim.config.auto_step = not sim.config.auto_step
                elif ctrl_held and event.key == pygame.K_n:
                    sim.step()
                elif event.unicode and event.unicode.isprintable():
                    input_text += event.unicode

        fps = clock.get_fps()
        render_stride = 4 if fps > 0 and fps < 15 else 1
        snapshot = sim.snapshot_coords()
        structural_snapshot = sim.structural_coords_snapshot()
        seed_history = sim.seed_history_snapshot()
        _draw(
            sim,
            viewport,
            screen,
            font,
            input_text,
            alive_coords=snapshot,
            structural_coords=structural_snapshot,
            seed_history=seed_history,
            snapshot_tick=sim.snapshot_tick,
            render_stride=render_stride,
        )
        pygame.display.flip()

    sim.stop_heartbeat()
    pygame.quit()


if __name__ == "__main__":
    main()

