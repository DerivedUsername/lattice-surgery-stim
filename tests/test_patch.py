
"""
1. Check count: a w × h rectangle gives w·h − 1 checks. Test (3, 3) → 8, (5, 5) → 24, (7, 3) → 20.
2. Picture match at d = 3: the left-edge X check (ancilla (−0.5, 1.5)) has corners (None, None, (0,1), (0,2)), and the right-edge X check (ancilla (2.5, 0.5)) has ((2,0), (2,1), None, None).
3. Weights: every check has weight 2 or 4. Weight-2 X checks only on the left/right edges, weight-2 Z checks only on the top/bottom.
4. Commutation: every X–Z pair shares an even number of data qubits.
5. Logicals: logical Z overlaps every X check evenly, logical X overlaps every Z check evenly, and Z_L and X_L share exactly one qubit.
6. Merge geometry: for d = 3, the checks in the merged patch (0, 0, 7, 3) whose ancilla isn’t in A or B are exactly 4, all Z-type, and their supports XOR to A’s right column plus B’s left column (Z_A Z_B). This is your theorem as a test.

"""
from lattice_surgery_stim.patch import check_patch, logical_x, logical_z


def test_check_count():
    """
    Test that the number of checks for given rectangle sizes is correct.
    """
    assert len(check_patch(0, 0, 3, 3)) == 8
    assert len(check_patch(0, 0, 5, 5)) == 24
    assert len(check_patch(0, 0, 7, 3)) == 20
def test_picture_match():
    """
    Test that the picture match at d = 3 is correct.
    """
    checks = check_patch(0, 0, 3, 3)
    left_edge_x_check = next(check for check in checks if check.ancilla == (-0.5, 1.5))
    right_edge_x_check = next(check for check in checks if check.ancilla == (2.5, 0.5))
    assert left_edge_x_check.corners == (None, None, (0, 1), (0, 2))
    assert right_edge_x_check.corners == ((2, 0), (2, 1), None, None)
def test_weights():
    """
    Test that every check has weight 2 or 4 and that weight-2 checks are on the correct edges. for n=3 and n=5 and n=7.
    """
    for width, height in ((3, 3), (5, 5), (7, 3)):
        checks = check_patch(0, 0, width, height)
        for check in checks:
            assert check.weight in (2, 4)
            if check.weight == 2:
                if check.type == "X":
                    assert check.ancilla[0] in (-0.5, width - 0.5)
                else:
                    assert check.ancilla[1] in (-0.5, height - 0.5)
    

def test_commutation():
    """
    Test that every X–Z pair shares an even number of data qubits.
    """
    checks = check_patch(0, 0, 3, 3)
    for x_check in checks:
        if x_check.type != "X":
            continue
        for z_check in checks:
            if z_check.type != "Z":
                continue
            shared_qubits = (set(x_check.corners) - {None}) & (set(z_check.corners) - {None})
            assert len(shared_qubits) % 2 == 0

def test_logicals():
    """
    Test that the logical operators have the correct commutation relations.
    """
    checks = check_patch(0, 0, 3, 3)
   
    logical_z_3 = logical_z(0, 0, 3, 3)
    logical_x_3 = logical_x(0, 0, 3, 3)
    for check in checks:
        if check.type == "X":
            shared_qubits = (set(logical_z_3) - {None}) & (set(check.corners) - {None})
            assert len(shared_qubits) % 2 == 0
        elif check.type == "Z":
            shared_qubits = (set(logical_x_3) - {None}) & (set(check.corners) - {None})
            assert len(shared_qubits) % 2 == 0
    shared_qubits = (set(logical_z_3) - {None}) & (set(logical_x_3) - {None})
    assert len(shared_qubits) == 1
