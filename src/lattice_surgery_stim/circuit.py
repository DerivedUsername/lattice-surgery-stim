"""
This module defines the circuit construction for the rotated surface code using stim.
It contains functions to generate the circuits for logical X and Z measurements and corrections.
"""
from lattice_surgery_stim.patch import Check, check_patch, data_qubits, logical_z
import stim

def index_map(rectangles: tuple[tuple[int, int, int, int], ...]) -> dict[tuple[float, float], int]:
    """
    Return a mapping from data qubit coordinates to their indices in the circuit. Both data and ancilla qubits are included. We implement a version that supports multiple rectangles.
    """
    data = set()
    ancilla = []
    for x0, y0, width, height in rectangles:
        data.update(data_qubits(x0, y0, width, height))
        for check in check_patch(x0, y0, width, height):
            ancilla.append(check.ancilla)
    data = sorted(data)
    ancilla = sorted(set(ancilla))
    return {
        **{
            coord: (i)
            for i, coord in enumerate(data)
        },
        **{
            coord: len(data) + i
            for i, coord in enumerate(ancilla)
        },
    }

class MeasurementLog:
    """
    Assigns each measurement an absolute index in emission order and converts it to 
    a stim rec target relative to the current measurement count.
    """
    def __init__(self) -> None:
        """index is the mapping from (ancilla qubit, round) or a data qubit for final measurements to its measurement index, i.e. how many measurements came before it."""
        self.index = {}
        self.count = 0

    def record(self, key: tuple) -> None:
        """Record the measurement index for the given key."""
        self.index[key] = self.count
        self.count += 1

    def rec(self, key: tuple) -> stim.GateTarget:
        return stim.target_rec(-self.count + self.index[key])

def syndrome_round(circuit, checks, idx : dict[tuple[float, float], int], data, log, r ,p) -> None:
    """
    Inputs are from the current circuit, the list of checks, the qubit index mapping, the measurement log, and the round and patch parameters.
    Measure every check once.
    0/n. DEPOLARIZE1(p) on data at the start
    1. Reset all ancilla qubits to zero.
    1/n. X_ERROR(p) after the reset
    2. H on all X-check ancillas.
    2/n. DEPOLARIZE1(p) after each H
    3. Four CNOT steps in order. In step k, every ancilla interacts with its kth data qubit.
    3/n. DEPOLARIZE2(p) on each CNOT layer's targets
    4. H on the X ancillas again.
    4/n. X_ERROR(p) before the M
    5. Measure all ancilla qubits in Z. Log with the input measurementlog object.
    6. TICK, after each time step.
    """
    """
    Record all ancilla qubit indices, and all X qubit indices, and data indices, all in order
    """
    ancilla_indices = [
        idx[check.ancilla]
        for check in checks
    ]
    x_indices = [
        idx[check.ancilla]
        for check in checks
        if check.type == "X"
    ]
    data_indices = [idx[i] for i in data]
    """
    DEPOLARIZE1(p) on data at the start
    """
    circuit.append("DEPOLARIZE1", [
        i
        for i in data_indices
    ], p)
    """
    Reset all ancilla qubits to zero.
    """
    circuit.append("RZ", [
        i
        for i in ancilla_indices
    ])
    """
    X_ERROR(p) after the reset
    """
    circuit.append("X_ERROR", [
        i
        for i in ancilla_indices
    ], p)

    circuit.append("TICK")
    
    """
    H on all X-check ancillas.
    """
    circuit.append("H", [
        i
        for i in x_indices
    ])
    """
    DEPOLARIZE1(p) after each H
    """
    circuit.append("DEPOLARIZE1", [
        i
        for i in x_indices
    ], p)
    circuit.append("TICK")
    """
    Four CNOT steps in order. In step k, every ancilla interacts with its kth data qubit. Note CNOT direction depends on the check type.
    """
    for step in range(4):
        targets = []
        for check in checks:
            data_qubit = check.corners[step]
            if data_qubit == None:
               continue
            if check.type == "Z":
                targets.extend([
                    idx[data_qubit],
                    idx[check.ancilla],
                ])
            else:
                targets.extend([
                    idx[check.ancilla],
                    idx[data_qubit],
                ])
        circuit.append("CX", targets)
        """
        DEPOLARIZE2(p) on each CNOT layer's targets
        """
        circuit.append("DEPOLARIZE2", targets, p)
        circuit.append("TICK")
    """
    H on the X ancillas again.
    """
    circuit.append("H", [
        i
        for i in x_indices
    ])
    """
    DEPOLARIZE1(p) after each H
    """
    circuit.append("DEPOLARIZE1", [
        i
        for i in x_indices
    ], p)
    circuit.append("TICK")
    """
    X_ERROR(p) before the M
    """
    circuit.append("X_ERROR", [
        i
        for i in ancilla_indices
    ], p)
    """
    Measure all ancilla qubits in Z.
    """
    for check in checks:
        circuit.append("M", [idx[check.ancilla]])
        log.record((check.ancilla,r))

    
def add_round_detectors(circuit, checks, log, r) -> None:
    """
    Add detectors for the current round of measurements.
    For each check add a detector that compares the current measurement with the previous.
    If round == 0, compare the measurement against known 0.
    """
    for check in checks:
        if r == 0:
            if check.type == "Z":
                targets = [log.rec((check.ancilla, 0))]
            else:
                continue
        else:
            targets = [
                log.rec((check.ancilla, r)),
                log.rec((check.ancilla, r - 1)),
            ]
        circuit.append("DETECTOR", targets, [check.ancilla[0], check.ancilla[1], r])

def memory_circuit(rectangles, rounds, p) -> stim.Circuit:
    """
    Build a memory experiment circuit for the given rectangles, rounds, and noise probability.
    """
    """
    Noise: X error on data after reset of data qubits
    """
    """
    X error on data before final measurement
    """
    """
    Initialize the data needed for the circuit: checks, data, idx, log, circuit
    """
    idx = index_map(rectangles)
    log = MeasurementLog()
    circuit = stim.Circuit()
    checks = []
    data = []
    for rectangle in rectangles:
        checks.extend(check_patch(*rectangle))
        data.extend(data_qubits(*rectangle))
    data = sorted(data)
    """
    bookkeep coordinates of all our qubits in stim picture
    """
    for qubit, index in idx.items():
        circuit.append("QUBIT_COORDS", [index], [qubit[0], qubit[1]])
    
    """
    initialize data in 0
    """
    circuit.append("R", [
        idx[qubit]
        for qubit in data
    ])
    """
    X error on data after reset of data qubits, tick
    """
    circuit.append("X_ERROR", [
        idx[qubit]
        for qubit in data
    ], p)
    circuit.append("TICK")
    """
    DO all rounds, syndrom first, then add detectors
    """
    for r in range(rounds):
        syndrome_round(circuit, checks,idx, data, log, r, p)
        add_round_detectors(circuit, checks, log, r)
    """
    X error on data before final measurement
    """
    circuit.append("X_ERROR", [
        idx[qubit]
        for qubit in data
    ], p)
    """
    Measure all data qubits in Z for Z memory, tick
    """
    for qubit in data:
        circuit.append("M", [idx[qubit]])
        log.record((qubit))
    circuit.append("TICK")

    """
    Add final detectors for the data qubit measurements, Z checks only, targets are log.rec((check.ancilla, rounds - 1)) and log.rec(qubit) on its corners if not None, coordinates are (qubit coordinates,rounds)
    """
    for check in checks:
        if check.type == "Z":
            targets = [log.rec((check.ancilla, rounds - 1))]
            targets.extend(log.rec(qubit) for qubit in check.corners if qubit is not None)
            circuit.append("DETECTOR", targets, [check.ancilla[0], check.ancilla[1], rounds])
    """
    Observables are logical Z operators.
    """
    rr = 0
    targets_obs = []
    for rectangle in rectangles:
        for qubit in logical_z(*rectangle):
            targets_obs.append(log.rec(qubit))
        circuit.append("OBSERVABLE_INCLUDE", targets_obs, rr)
        targets_obs = []
        rr += 1
    return circuit





        
    
    