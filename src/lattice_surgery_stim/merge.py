"""
Module for merging lattice surgery circuits in Stim.
"""

import stim

from lattice_surgery_stim.circuit import (
    MeasurementLog,
    add_round_detectors,
    index_map,
    syndrome_round,
)
from lattice_surgery_stim.patch import check_patch, data_qubits, logical_z


def merge_circuits(d, merged_rounds, p) -> stim.Circuit:
    """
    Three phases of error correction:
    1. A, B seprately
    2. M as a big lattice
    3. A,B separately again.
    """
    A = (0, 0, d, d)
    B = (d + 1, 0, d, d)
    M = (0, 0, 2 * d + 1, d)
    idx = index_map((A, B, M))
    checks_AB = check_patch(*A) + check_patch(*B)
    checks_M = check_patch(*M)
    data_AB = sorted(data_qubits(*A)) + sorted(data_qubits(*B))
    data_M = sorted(data_qubits(*M))
    weight_AB = {check.ancilla: check.weight for check in checks_AB}
    ancilla_AB = {check.ancilla for check in checks_AB}
    checks_New = [check for check in checks_M if check.ancilla not in ancilla_AB]
    checks_grown = [
        check
        for check in checks_M
        if (check.ancilla in ancilla_AB) and (check.weight != weight_AB[check.ancilla])
    ]
    log = MeasurementLog()
    circuit = stim.Circuit()
    for qubit, index in idx.items():
        circuit.append("QUBIT_COORDS", [index], [qubit[0], qubit[1]])

    """
    The protocol, with one global round counter r:
    Prepare: R and X_ERROR(p) on data_AB, then TICK.
    
    
    Split:
    Z_ERROR(p) on the seam, then MX on it
    log.record((s, "split")) for each seam qubit, in the same order
    TICK
    Phase 3: for the remaining d rounds, syndrome_round with checks_AB and data_AB. In the first round only, the boundary X checks that had grown need their own detector. Put their ancillas in skip, and add for each one a detector with four targets:
    its record now
    its record in the previous round (that was g′)
    the two seam qubits’ split records (the seam qubits in g′ but not in g)
    This is g = g′ X_s X_s′ from the note. Every other check uses the normal rule.
    End: the final data readout on data_AB and the final Z-check detectors, exactly as in memory_circuit, using the last round number.
    Observables:
    0 = the XOR of log.rec((n.ancilla, d)) over the new checks (Z_A Z_B)
    1 = A’s logical_z column
    2 = B’s logical_z column
    """
    circuit.append("R", [idx[qubit] for qubit in data_AB])
    circuit.append("X_ERROR", [idx[qubit] for qubit in data_AB], p)
    circuit.append("TICK")

    """
    Phase 1: for r = 0 … d−1, syndrome_round with checks_AB and data_AB, then detectors (skip nothing).
    Merge: RX on the seam indices, Z_ERROR(p) on them, then TICK. (For X-basis operations, the harmful flip is Z.)
    """
    for r in range(d):
        syndrome_round(circuit, checks_AB, idx, data_AB, log, r, p)
        add_round_detectors(circuit, checks_AB, log, r)

    """
    Seam reset:
    RX on the seam indices
    Z_ERROR(p) on them (a reset-to-|+⟩ fault is a Z flip)
    TICK
    """
    seam_indices = [idx[(d, y)] for y in range(d)]
    circuit.append("RX", seam_indices)
    circuit.append("Z_ERROR", seam_indices, p)
    circuit.append("TICK")
    """
    Phase 2: for r = d … d + merged_rounds − 1, syndrome_round with checks_M and data_M, then detectors with skip = the new checks’ ancillas when r == d, and nothing otherwise. Grown and unchanged checks compare with round d − 1 automatically.
    """
    for r in range(d, d + merged_rounds):
        syndrome_round(circuit, checks_M, idx, data_M, log, r, p)
        add_round_detectors(
            circuit,
            checks_M,
            log,
            r,
            skip=[check.ancilla for check in checks_New] if r == d else [],
        )

    """
    The seam measurement: Z_ERROR(p) then MX on seam_indices, then log.record(((d, y), "split")) for y in range(d), in the same order as seam_indices, then TICK.
    """
    circuit.append("Z_ERROR", seam_indices, p)
    circuit.append("MX", seam_indices)
    for y in range(d):
        log.record(((d, y), "split"))
    circuit.append("TICK")

    """
    Phase 3: r0 = d + merged_rounds, loop r over r0 … r0 + d − 1:
    syndrome_round with checks_AB and data_AB
    add_round_detectors with checks_AB, and skip = the ancillas of checks_grown when r == r0
    when r == r0, the 4-target detector for each grown check g: (g.ancilla, r), (g.ancilla, r − 1), and (q, "split") for each corner q of g with q[0] == d
    """
    r0 = d + merged_rounds
    for r in range(r0, r0 + d):
        syndrome_round(circuit, checks_AB, idx, data_AB, log, r, p)
        add_round_detectors(
            circuit,
            checks_AB,
            log,
            r,
            skip=[check.ancilla for check in checks_grown] if r == r0 else [],
        )
        if r == r0:
            for check in checks_grown:
                targets = [
                    log.rec((check.ancilla, r)),
                    log.rec((check.ancilla, r - 1)),
                ]
                targets.extend(
                    log.rec((q, "split"))
                    for q in check.corners
                    if q is not None and q[0] == d
                )
                circuit.append(
                    "DETECTOR", targets, [check.ancilla[0], check.ancilla[1], r]
                )

    """
        X_ERROR(p) and M on data_AB, then record(q) for each
        final detectors for the Z checks of checks_AB (not checks_M), using round r0 + d − 1 and time coordinate r0 + d
        """
    circuit.append("X_ERROR", [idx[qubit] for qubit in data_AB], p)
    circuit.append("M", [idx[qubit] for qubit in data_AB])
    for qubit in data_AB:
        log.record(qubit)
    circuit.append("TICK")
    for check in checks_AB:
        if check.type == "Z":
            targets = [log.rec((check.ancilla, r0 + d - 1))]
            targets.extend(
                log.rec(qubit) for qubit in check.corners if qubit is not None
            )
            circuit.append(
                "DETECTOR", targets, [check.ancilla[0], check.ancilla[1], r0 + d]
            )
    """
    Observables:
    0: log.rec((n.ancilla, d)) for each new check n (the measured Z_A Z_B)
    1: log.rec(q) for q in logical_z(*A) (Z_A)
    2: log.rec(q) for q in logical_z(*B) (Z_B)
    """
    for check in checks_New:
        circuit.append("OBSERVABLE_INCLUDE", [log.rec((check.ancilla, d))], 0)
    for qubit in logical_z(*A):
        circuit.append("OBSERVABLE_INCLUDE", [log.rec(qubit)], 1)
    for qubit in logical_z(*B):
        circuit.append("OBSERVABLE_INCLUDE", [log.rec(qubit)], 2)

    return circuit
