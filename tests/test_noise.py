"""Unit tests and verification checks for synthetic noise model module.

Requirements verified:
1. Configured synthetic noise rates (1Q=0.001, CX=0.005, Readout=0.01) and basis gates.
2. Successful noisy simulation on supported 4-node case (Processor A & B).
3. Unsupported 6-node Processor A case (capacity limitation cleanly enforced).
"""

import math
import unittest
import numpy as np

from src.noise import (
    DOCUMENTED_BASIS_GATES,
    build_synthetic_noise_model,
    run_noisy_transpiled_qaoa,
)
from src.graph_utils import create_sample_graph, create_pso1_6node_graph
from src.processors import load_development_processors
from src.benchmarking import run_processor_ab_noisy_comparison


class TestSyntheticNoiseModel(unittest.TestCase):
    """Test suite for synthetic noise modeling and processor benchmark integration."""

    def test_noise_model_configuration(self):
        """Verify noise rates, documented basis gates, and error assignments."""
        p1q = 0.001
        p2q = 0.005
        p_ro = 0.01

        model = build_synthetic_noise_model(
            p1q=p1q,
            p2q=p2q,
            p_ro=p_ro,
            noisy_1q_gates=("sx", "x"),
            include_rz=False,
        )

        # 1. Basis gates check
        self.assertIn("cx", model.basis_gates)
        self.assertIn("rz", model.basis_gates)
        self.assertIn("sx", model.basis_gates)
        self.assertIn("x", model.basis_gates)

        # 2. Documented basis gates check
        self.assertEqual(DOCUMENTED_BASIS_GATES, ["rz", "sx", "x", "cx"])

        # 3. Noise instructions: cx, measure, sx, x should have errors; rz should not
        noise_instructions = set(model.noise_instructions)
        self.assertIn("cx", noise_instructions)
        self.assertIn("measure", noise_instructions)
        self.assertIn("sx", noise_instructions)
        self.assertIn("x", noise_instructions)
        self.assertNotIn("rz", noise_instructions, "Virtual RZ should not have physical depolarizing noise")

    def test_supported_four_node_case(self):
        """Verify successful noisy simulation on a supported 4-node case for both processors."""
        g4 = create_sample_graph()
        df = run_processor_ab_noisy_comparison(
            graph=g4,
            p_list=[1],
            optimization_level=1,
            shots_ideal=500,
            shots_noisy=1024,
            maxiter=10,
            seed_simulator=42,
            seed_transpiler=42,
            output_csv=None,
        )

        self.assertEqual(len(df), 2)
        for _, row in df.iterrows():
            # Must be supported
            self.assertTrue(row["is_supported"])
            self.assertEqual(row["logical_qubits"], 4)
            self.assertEqual(row["noisy_shots"], 1024)

            # Metrics must be valid floats/ints
            self.assertGreater(row["transpiled_cx_count"], 0)
            self.assertGreater(row["transpiled_depth"], 0)
            self.assertGreater(row["opt_expected_cut"], 0.0)
            self.assertGreater(row["noisy_expected_cut"], 0.0)
            self.assertGreater(row["noisy_approx_ratio"], 0.0)
            self.assertLessEqual(row["noisy_approx_ratio"], 1.0)
            self.assertGreater(row["noisy_optimal_prob"], 0.0)
            self.assertIsNotNone(row["solution_quality_retention"])
            self.assertIsNotNone(row["quality_retention"])

            # Mathematical consistency checks
            self.assertAlmostEqual(
                row["noisy_expected_cut"] + row["expectation_drop"],
                row["opt_expected_cut"],
                places=3,
            )
            self.assertAlmostEqual(
                row["noisy_expected_cut"] / row["opt_expected_cut"],
                row["solution_quality_retention"],
                places=3,
            )

    def test_unsupported_six_node_processor_a(self):
        """Verify 6-node instance correctly flags Processor A as unsupported without fabricating metrics."""
        g6 = create_pso1_6node_graph(1)
        df = run_processor_ab_noisy_comparison(
            graph=g6,
            p_list=[1],
            optimization_level=1,
            shots_ideal=500,
            shots_noisy=1024,
            maxiter=10,
            seed_simulator=42,
            seed_transpiler=42,
            output_csv=None,
        )

        proc_a = df[df["processor_id"] == "processor_A"].iloc[0]
        proc_b = df[df["processor_id"] == "processor_B"].iloc[0]

        # Processor A has 5 qubits < 6 nodes: must be unsupported
        self.assertFalse(proc_a["is_supported"])
        self.assertEqual(proc_a["physical_qubits"], 5)
        self.assertEqual(proc_a["logical_qubits"], 6)
        self.assertTrue(
            math.isnan(proc_a["transpiled_cx_count"]) or proc_a["transpiled_cx_count"] is None
        )
        self.assertTrue(
            math.isnan(proc_a["noisy_expected_cut"]) or proc_a["noisy_expected_cut"] is None
        )
        self.assertIn("exceed physical capacity", proc_a["notes"])

        # Processor B has 9 qubits >= 6 nodes: must be supported
        self.assertTrue(proc_b["is_supported"])
        self.assertEqual(proc_b["physical_qubits"], 9)
        self.assertGreater(proc_b["transpiled_cx_count"], 0)
        self.assertGreater(proc_b["noisy_expected_cut"], 0.0)
        self.assertGreater(proc_b["noisy_approx_ratio"], 0.0)
        self.assertGreater(proc_b["opt_expected_cut"], 0.0)
        self.assertIsNotNone(proc_b["solution_quality_retention"])


if __name__ == "__main__":
    unittest.main()
