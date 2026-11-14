"""Tests for the memory circuit (circuit.py).

Expected values are derived by hand where possible and otherwise checked
against Stim's own generated rotated-surface-code memory circuit.
"""

import pytest
import stim

from lattice_surgery_stim.circuit import index_map, memory_circuit

DISTANCES = [3, 5]


def one_patch(d):
    return ((0, 0, d, d),)


def two_patches(d):
    return ((0, 0, d, d), (d + 1, 0, d, d))


def logical_error_rate(circuit, shots, seed):
    """Sample, decode with PyMatching, return the fraction of shots with any wrong observable."""
    import pymatching

    dem = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(dem)
    dets, obs = circuit.compile_detector_sampler(seed=seed).sample(
        shots, separate_observables=True
    )
    return (matching.decode_batch(dets) != obs).any(axis=1).mean()


@pytest.mark.parametrize("d", DISTANCES)
def test_index_map_numbers_every_qubit_once(d):
    # d^2 data qubits and d^2 - 1 ancillas, numbered 0, ..., 2d^2 - 2.
    idx = index_map(one_patch(d))
    assert len(idx) == 2 * d * d - 1
    assert sorted(idx.values()) == list(range(2 * d * d - 1))


@pytest.mark.parametrize("d", DISTANCES)
def test_detector_and_observable_counts(d):
    # Half the checks (the Z checks) in round 0, all d^2 - 1 in each later round,
    # and half again in the final round: (d^2 - 1) * rounds in total.
    circuit = memory_circuit(one_patch(d), d, 0.001)
    assert circuit.num_detectors == (d * d - 1) * d
    assert circuit.num_observables == 1


@pytest.mark.parametrize("d", DISTANCES)
def test_detectors_are_deterministic(d):
    # Stim refuses to build the error model if any detector or observable is random.
    memory_circuit(one_patch(d), d, 0.001).detector_error_model(decompose_errors=True)


def test_noiseless_circuit_is_silent():
    circuit = memory_circuit(one_patch(3), 3, 0.0)
    dets, obs = circuit.compile_detector_sampler(seed=0).sample(
        200, separate_observables=True
    )
    assert not dets.any()
    assert not obs.any()


@pytest.mark.parametrize("d", DISTANCES)
def test_circuit_distance_is_d(d):
    circuit = memory_circuit(one_patch(d), d, 0.001)
    assert len(circuit.shortest_graphlike_error()) == d


@pytest.mark.parametrize("d", DISTANCES)
def test_two_patch_baseline(d):
    circuit = memory_circuit(two_patches(d), d, 0.001)
    assert circuit.num_observables == 2
    assert circuit.num_detectors == 2 * (d * d - 1) * d
    assert len(circuit.shortest_graphlike_error()) == d


def test_error_rate_matches_stim_reference():
    # Independent reference: our layout is Stim's mirrored, with the same noise model,
    # so the logical error rates must agree within sampling error.
    d, p, shots = 3, 0.004, 20_000
    ours = memory_circuit(one_patch(d), d, p)
    ref = stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        distance=d,
        rounds=d,
        after_clifford_depolarization=p,
        before_round_data_depolarization=p,
        before_measure_flip_probability=p,
        after_reset_flip_probability=p,
    )
    a = logical_error_rate(ours, shots, seed=1)
    b = logical_error_rate(ref, shots, seed=2)
    sigma = ((a * (1 - a) + b * (1 - b)) / shots) ** 0.5
    assert abs(a - b) < 5 * sigma
