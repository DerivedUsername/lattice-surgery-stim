"""Tests for the lattice-surgery circuit (merge.py) and the merge geometry it relies on."""

import pytest

from lattice_surgery_stim.merge import merge_circuits
from lattice_surgery_stim.patch import check_patch


def new_and_grown_checks(d):
    """Split the checks of the merged patch into those new to M and those that grew."""
    old = {c.ancilla: c for c in check_patch(0, 0, d, d) + check_patch(d + 1, 0, d, d)}
    merged = check_patch(0, 0, 2 * d + 1, d)
    new = [c for c in merged if c.ancilla not in old]
    grown = [c for c in merged if c.ancilla in old and c.weight != old[c.ancilla].weight]
    return new, grown


@pytest.mark.parametrize("d", [3, 5, 7])
def test_new_checks_multiply_to_ZA_ZB(d):
    # The theorem behind the merge: there are d + 1 new checks, all Z type, and the
    # product of their supports (sum over F_2) is A's right column plus B's left column.
    new, _ = new_and_grown_checks(d)
    assert len(new) == d + 1
    assert all(c.type == "Z" for c in new)
    product = set()
    for c in new:
        product ^= {q for q in c.corners if q is not None}
    expected = {(d - 1, y) for y in range(d)} | {(d + 1, y) for y in range(d)}
    assert product == expected


@pytest.mark.parametrize("d", [3, 5, 7])
def test_grown_checks_gain_two_seam_qubits(d):
    # Each grown X check is g' = g X_s X_s' with s, s' on the seam column x = d.
    old = {c.ancilla: c for c in check_patch(0, 0, d, d) + check_patch(d + 1, 0, d, d)}
    _, grown = new_and_grown_checks(d)
    assert len(grown) == d - 1
    for c in grown:
        assert c.type == "X"
        added = {q for q in c.corners if q is not None} - {q for q in old[c.ancilla].corners if q is not None}
        assert len(added) == 2
        assert all(q[0] == d for q in added)


@pytest.mark.parametrize("d", [3, 5])
def test_qubit_and_observable_counts(d):
    # (2d+1)d data qubits and (2d+1)d - 1 ancillas; observables Z_A Z_B, Z_A, Z_B.
    circuit = merge_circuits(d, d, 0.001)
    assert circuit.num_qubits == 2 * (2 * d + 1) * d - 1
    assert circuit.num_observables == 3


@pytest.mark.parametrize("merged_rounds", [1, 2, 3])
def test_detectors_are_deterministic(merged_rounds):
    merge_circuits(3, merged_rounds, 0.001).detector_error_model(decompose_errors=True)


def test_noiseless_circuit_is_silent():
    circuit = merge_circuits(3, 3, 0.0)
    dets, obs = circuit.compile_detector_sampler(seed=0).sample(200, separate_observables=True)
    assert not dets.any()
    assert not obs.any()


@pytest.mark.parametrize(
    "d, merged_rounds",
    [(3, 1), (3, 2), (3, 3), (5, 1), (5, 3), (5, 5)],
)
def test_distance_equals_merged_rounds(d, merged_rounds):
    # The time-like distance: the Z_A Z_B outcome comes from checks that exist only
    # during the merged phase, so r merged rounds give distance min(r, d).
    circuit = merge_circuits(d, merged_rounds, 0.001)
    assert len(circuit.shortest_graphlike_error()) == min(merged_rounds, d)
