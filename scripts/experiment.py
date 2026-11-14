"""
Experiment module for lattice surgery using Stim.

"""

import csv
import pathlib
import time

import pymatching

from lattice_surgery_stim.circuit import memory_circuit
from lattice_surgery_stim.merge import merge_circuits


def logical_error_rate(circuit, shots, seed):
    dem = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(dem)
    t0 = time.perf_counter()
    dets, obs = circuit.compile_detector_sampler(seed=seed).sample(
        shots, separate_observables=True
    )
    t1 = time.perf_counter()
    pred = matching.decode_batch(dets)
    t2 = time.perf_counter()
    wrong = pred != obs
    return (
        wrong[:, 0].sum(),
        wrong.any(axis=1).sum(),
        (t1 - t0) / shots,
        (t2 - t1) / shots,
    )


rows = []
for d in (3, 5):
    for p in (0.002, 0.004, 0.006):
        """surgery"""
        c = merge_circuits(d, d, p)
        shots = 100000
        seed = 1000 * d + int(p * 1e4)
        zz_failures, any_failures, t_sample, t_decode = logical_error_rate(
            c, shots, seed
        )
        rows.append((d, p, "surgery ZZ", shots, zz_failures, t_sample, t_decode))
        rows.append((d, p, "surgery any", shots, any_failures, t_sample, t_decode))
        print(rows[-1])
        """baseline"""
        c = memory_circuit(((0, 0, d, d), (d + 1, 0, d, d)), 3 * d, p)
        shots = 100000
        seed = 1000 * d + int(p * 1e4) + 1
        zz_failures, any_failures, t_sample, t_decode = logical_error_rate(
            c, shots, seed
        )
        rows.append((d, p, "idle any", shots, any_failures, t_sample, t_decode))
        print(rows[-1])

pathlib.Path("results").mkdir(exist_ok=True)
with open("results/surgery_vs_idle.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["d", "p", "kind", "shots", "failures", "t_sample", "t_decode"])
    writer.writerows(rows)
