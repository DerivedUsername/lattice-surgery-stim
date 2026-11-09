"""
This module defines the geometry used in our rotated surface code without using stim.
It contains three functions:
1. data qubits of a dxd patch as coordinates (x,y) in a rectangular patch with height and width as input.
2. Check for the patch: For each surface with lower left corner (x,y), record: XZ type the ancilla coordinate, the four corner slots in CNOT gates in their order, and their weight.
3. Logical X and Z operators of the patch as coordinates.
Conventions: 
- The lower left corner of the patch is at (x0, y0).
- Data qubits are indexed by their coordinates (x, y) within the patch.
- Ancilla coordinates are at the center of each surface.
- CNOT gate order for X-type surfaces is (0,0), (0,1), (1,0), (1,1).
- CNOT gate order for Z-type surfaces is (0,0), (1,0), (0,1), (1,1).
- X surfaces are X-type when (x + y) is even, and Z surfaces are Z-type when (x + y) is odd.
- triangular patches are the weight two ones, and square patches are the weight four ones. X-type triangular patches are on the left-right edges, and Z-type triangular patches are on the top-bottom edges.

"""
from typing import NamedTuple

def data_qubits(x0:int, y0:int, width:int, height :int) -> set[tuple[int,int]]:
    """
    Return the data qubit coordinates for a rectangular patch.
    """
    return set((x0+x, y0+y) for x in range(width) for y in range(height))
class Check(NamedTuple):
    ancilla:tuple[float, float]
    type:str
    corners:tuple[tuple[float, float] | None, ...]
    weight:int
X_order = ((0,0), (0,1),(1,0),(1,1))
Z_order = ((0,0), (1,0),(0,1),(1,1))
def check_patch(x0:int, y0:int, width:int, height:int) -> list[Check]:
    """
    Record the ancilla, type and four corner positions in CNOT order for its type for each surface in the patch.Patch is indexed by its lower left corner.
    """
    checks = []
    data = data_qubits(x0, y0, width, height)
    for x in range(x0-1, x0 + width):
        lr_edge = True if x == x0 - 1 or x == x0 + width - 1 else False
        for y in range(y0-1, y0 + height):
            ud_edge = True if y == y0 - 1 or y == y0 + height - 1 else False
            type_temp="X" if (x + y) % 2 == 0 else "Z"
            corners_temp=tuple(
                (x + dx, y + dy) if (x + dx, y + dy) in data else None
                for dx, dy in (X_order if type_temp == "X" else Z_order)
            )
            checks_temp = Check(
                ancilla=(x + 0.5, y + 0.5),
                type=type_temp,
                corners=corners_temp,
                weight=sum(corner is not None for corner in corners_temp),
            )
            if (checks_temp.weight == 2 and checks_temp.type == "X" and lr_edge) or (checks_temp.weight == 2 and checks_temp.type == "Z" and ud_edge) or checks_temp.weight == 4:
                checks.append(checks_temp)
            else:
                continue

    return checks
     
def logical_x(x0:int, y0:int, width:int, height:int) -> set[tuple[int,int]]:
    """
    Return the logical X operator coordinates for this patch.
    """
    return set((x0+x, y0) for x in range(width))
def logical_z(x0:int, y0:int, width:int, height:int) -> set[tuple[int,int]]:
    """
    Return the logical Z operator coordinates for this patch.
    """
    return set((x0, y0+y) for y in range(height))
