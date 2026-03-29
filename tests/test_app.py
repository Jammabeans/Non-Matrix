from non_matrix.signal_coherence import coherence_percent, coherence_percent_active, skeleton_pulse_alpha


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


def test_skeleton_pulse_alpha_within_expected_bounds() -> None:
    low = skeleton_pulse_alpha(total_energy=0, tick=0)
    high = skeleton_pulse_alpha(total_energy=100_000, tick=200)
    assert 100 <= low <= 255
    assert 100 <= high <= 255

