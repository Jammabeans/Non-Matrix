from non_matrix.signal_coherence import (
    _seed_template_coords,
    coherence_percent,
    coherence_percent_active,
    skeleton_pulse_alpha,
)


def test_coherence_percent_uses_last_seed_origin_and_overlap() -> None:
    seed_history = [("Hi", (10, 20))]
    # "Hi" template includes (0,0) and (1,0) bits among others.
    structural = {(10, 20), (11, 20)}
    coherence = coherence_percent(structural, "Hi", seed_history)
    assert coherence > 0.0
    assert coherence <= 100.0


def test_coherence_percent_zero_without_seed_text() -> None:
    coherence = coherence_percent({(0, 0)}, "", [])
    assert coherence == 0.0


def test_coherence_percent_active_uses_active_pixels_only() -> None:
    seed_history = [("Hi", (10, 20))]
    active = {(10, 20), (11, 20)}
    coherence = coherence_percent_active(active, "Hi", seed_history)
    assert coherence > 0.0
    assert coherence <= 100.0


def test_coherence_percent_active_collapses_to_noise_floor_on_mismatch() -> None:
    seed_history = [("Hi", (10, 20))]
    active = {(300, 300), (301, 300), (300, 301)}
    coherence = coherence_percent_active(active, "Hi", seed_history)
    assert coherence == 10.0


def test_coherence_percent_active_penalizes_noisy_shape() -> None:
    seed_text = "Hi"
    seed_history = [(seed_text, (0, 0))]
    template = _seed_template_coords(seed_text)
    perfect = set(template)
    noisy = set(template)
    noisy.update({(200 + i, 200) for i in range(40)})

    perfect_score = coherence_percent_active(perfect, seed_text, seed_history)
    noisy_score = coherence_percent_active(noisy, seed_text, seed_history)
    assert perfect_score > noisy_score


def test_skeleton_pulse_alpha_within_expected_bounds() -> None:
    low = skeleton_pulse_alpha(total_energy=0, tick=0)
    high = skeleton_pulse_alpha(total_energy=100_000, tick=200)
    assert 100 <= low <= 255
    assert 100 <= high <= 255

