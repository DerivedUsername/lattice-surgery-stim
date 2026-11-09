"""
This module defines the circuit construction for the rotated surface code using stim.
It contains functions to generate the circuits for logical X and Z measurements and corrections.
"""
from src.lattice_surgery_stim.patch import check_patch, data_qubits
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
        self.index = {}
        self.count = 0

    def record(self, key: tuple) -> None:
        self.index[key] = self.count
        self.count += 1

    def rec(self, key: tuple[float, float]) -> stim.GateTarget:
        return stim.target_rec(-self.count + self.index[key])

    
