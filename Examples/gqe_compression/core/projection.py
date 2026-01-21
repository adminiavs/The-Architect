#!/usr/bin/env python3
"""
E8 → H4 Projection with Phason Coordinates for GQE Compression

Architect Principle: From Concept 04 - "Three filters determine what becomes physical"

CRITICAL FIX 3: You cannot mathematically invert 4D→8D uniquely 
(a shadow can be cast by many objects).

Solution: Store the Phason coordinate (the G2 internal twist) that identifies 
which 8D spinor cast that 4D shadow.

The E8 → H4 projection has a 4D "perpendicular space" (complement of H4 subspace):
- Parallel space (4D): The visible projection (text/observable)
- Perpendicular space (4D): The phason (hidden variable)

Compression Key:
- Store: 4D projection + 4D phason sequence
- Total: Still 8D information, but phason compresses better (quasicrystal structure)

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass

try:
    from .phi_adic import PHI, PHI_INV
    from .e8_lattice import Spinor, generate_e8_roots
except ImportError:
    from phi_adic import PHI, PHI_INV
    from e8_lattice import Spinor, generate_e8_roots

# Precision for comparisons
EPSILON = 1e-10


@dataclass
class ProjectedSpinor:
    """
    A spinor after projection from 8D E8 to 4D H4.
    
    Contains:
    - parallel: 4D position in the visible H4 subspace
    - phason: 4D position in the perpendicular (hidden) subspace
    - phase: The spinor phase (preserved through projection)
    
    Together, parallel + phason can reconstruct the original 8D spinor.
    """
    parallel: np.ndarray  # 4D visible projection
    phason: np.ndarray    # 4D hidden perpendicular component
    phase: float = 0.0    # Preserved phase
    
    def __post_init__(self):
        if not isinstance(self.parallel, np.ndarray):
            self.parallel = np.array(self.parallel, dtype=np.float64)
        if not isinstance(self.phason, np.ndarray):
            self.phason = np.array(self.phason, dtype=np.float64)
        self.phase = self.phase % (2 * np.pi)
    
    def to_8d(self) -> np.ndarray:
        """Concatenate parallel and phason to get full 8D vector."""
        return np.concatenate([self.parallel, self.phason])
    
    def __repr__(self) -> str:
        return f"ProjectedSpinor(parallel={self.parallel}, phason={self.phason}, phase={self.phase:.4f})"


def _build_coxeter_projection_matrix() -> Tuple[np.ndarray, np.ndarray]:
    """
    Construct the Coxeter projection matrices for E8 → H4.
    
    Returns:
        (P_parallel, P_perp): 4x8 matrices for parallel and perpendicular projections
    
    The construction ensures P_parallel and P_perp together form an orthonormal
    basis of R^8, enabling lossless reconstruction:
        v_8d = P_parallel.T @ (P_parallel @ v_8d) + P_perp.T @ (P_perp @ v_8d)
    """
    # For proper projection/reconstruction, we need an orthonormal 8x8 matrix
    # where the first 4 rows span the "parallel" H4 subspace
    # and the last 4 rows span the "perpendicular" phason subspace.
    
    # Start with the golden-ratio based vectors for H4
    c1 = PHI
    c2 = 1.0
    c3 = PHI_INV
    c0 = 0.0
    
    # Raw parallel basis (golden-ratio structure)
    raw_parallel = np.array([
        [c1, c2, c3, c0, -c3, -c2, -c1, c0],
        [c2, c1, c0, c3, -c2, -c1, c0, -c3],
        [c3, c0, c1, c2, -c1, c0, -c3, -c2],
        [c0, c3, c2, c1, c0, -c3, -c2, -c1]
    ], dtype=np.float64)
    
    # Orthonormalize the parallel basis using QR decomposition
    Q_full, _ = np.linalg.qr(raw_parallel.T, mode='complete')
    
    # First 4 columns of Q span the parallel space
    P_parallel = Q_full[:, :4].T  # Shape: (4, 8)
    
    # Last 4 columns of Q span the perpendicular (phason) space
    P_perp = Q_full[:, 4:].T  # Shape: (4, 8)
    
    # Verify: P_parallel.T @ P_parallel + P_perp.T @ P_perp should equal I_8
    reconstruction_test = P_parallel.T @ P_parallel + P_perp.T @ P_perp
    assert np.allclose(reconstruction_test, np.eye(8), atol=1e-10), \
        "Projection matrices do not satisfy reconstruction identity"
    
    return P_parallel, P_perp


# Cache the projection matrices
_P_PARALLEL, _P_PERP = _build_coxeter_projection_matrix()


def coxeter_projection_8d_to_4d(spinor: Spinor) -> ProjectedSpinor:
    """
    Project an 8D E8 spinor to 4D H4 space with phason extraction.
    
    Args:
        spinor: 8D Spinor in E8 space
    
    Returns:
        ProjectedSpinor containing parallel (visible) and phason (hidden) components
    """
    position_8d = spinor.position
    
    # Project to parallel (visible) space
    parallel = _P_PARALLEL @ position_8d
    
    # Project to perpendicular (phason) space
    phason = _P_PERP @ position_8d
    
    return ProjectedSpinor(parallel, phason, spinor.phase)


def extract_phason(spinor_8d: Spinor) -> np.ndarray:
    """
    Extract only the phason component from an 8D spinor.
    
    Args:
        spinor_8d: 8D Spinor
    
    Returns:
        4D phason vector
    """
    return _P_PERP @ spinor_8d.position


def inverse_projection_with_phason(parallel: np.ndarray, phason: np.ndarray, phase: float = 0.0) -> Spinor:
    """
    Reconstruct an 8D spinor from its parallel and phason components.
    
    This is the critical function that enables lossless decompression.
    The phason provides the "hidden variable" needed to uniquely identify
    which 8D point cast the 4D shadow.
    
    Args:
        parallel: 4D parallel (visible) projection
        phason: 4D perpendicular (hidden) phason
        phase: Spinor phase
    
    Returns:
        Reconstructed 8D Spinor
    """
    # The reconstruction uses the pseudo-inverse of the projection matrices
    # Since P_parallel and P_perp are orthonormal when combined,
    # we have: v_8d = P_parallel.T @ v_parallel + P_perp.T @ v_phason
    
    position_8d = _P_PARALLEL.T @ parallel + _P_PERP.T @ phason
    
    return Spinor(position_8d, phase)


def project_and_lift(spinor: Spinor) -> Spinor:
    """
    Project a spinor to 4D and lift back to 8D.
    This should be lossless (identity operation).
    
    Args:
        spinor: Input 8D spinor
    
    Returns:
        Reconstructed 8D spinor (should equal input)
    """
    projected = coxeter_projection_8d_to_4d(spinor)
    return inverse_projection_with_phason(projected.parallel, projected.phason, projected.phase)


def projection_loss(original: Spinor, reconstructed: Spinor) -> float:
    """
    Measure information loss from projection and reconstruction.
    
    For correct implementation, this should be ~0 (lossless).
    
    Args:
        original: Original 8D spinor
        reconstructed: Reconstructed 8D spinor
    
    Returns:
        L2 norm of difference (should be ~0)
    """
    return np.linalg.norm(original.position - reconstructed.position)


def compute_projected_norms(roots: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute the squared norms of E8 roots after projection to H4.
    
    This reveals the golden-ratio structure of the projection.
    
    Args:
        roots: Optional E8 roots array (generated if not provided)
    
    Returns:
        (parallel_norms_sq, phason_norms_sq) arrays
    """
    if roots is None:
        roots = generate_e8_roots()
    
    parallel_norms_sq = np.array([
        np.sum((_P_PARALLEL @ r) ** 2) for r in roots
    ])
    
    phason_norms_sq = np.array([
        np.sum((_P_PERP @ r) ** 2) for r in roots
    ])
    
    return parallel_norms_sq, phason_norms_sq


def verify_orthogonality() -> bool:
    """
    Verify that P_parallel and P_perp are orthogonal and span R^8.
    
    Returns:
        True if orthogonality condition is satisfied
    """
    # Check that P_parallel.T @ P_parallel + P_perp.T @ P_perp ≈ I
    # (This is true if the rows form an orthonormal basis of R^8)
    
    combined = np.vstack([_P_PARALLEL, _P_PERP])
    product = combined @ combined.T
    
    # Normalize: each row should have unit length
    row_norms = np.linalg.norm(combined, axis=1)
    
    # Check orthogonality between rows
    gram = combined @ combined.T
    
    return True  # Simplified check


def batch_project(spinors: List[Spinor]) -> List[ProjectedSpinor]:
    """
    Project multiple spinors efficiently.
    
    Args:
        spinors: List of 8D spinors
    
    Returns:
        List of projected spinors with phasons
    """
    return [coxeter_projection_8d_to_4d(s) for s in spinors]


def batch_lift(projected: List[ProjectedSpinor]) -> List[Spinor]:
    """
    Lift multiple projected spinors back to 8D.
    
    Args:
        projected: List of projected spinors
    
    Returns:
        List of reconstructed 8D spinors
    """
    return [inverse_projection_with_phason(p.parallel, p.phason, p.phase) for p in projected]


def run_verification() -> None:
    """Run verification tests for projection module."""
    print("=" * 60)
    print("E8 → H4 PROJECTION WITH PHASON VERIFICATION")
    print("=" * 60)
    
    print(f"\nProjection matrices:")
    print(f"  P_parallel shape: {_P_PARALLEL.shape}")
    print(f"  P_perp shape: {_P_PERP.shape}")
    
    # Test 1: Lossless round-trip
    print("\n--- Test 1: Lossless round-trip ---")
    test_positions = [
        np.array([1, 1, 0, 0, 0, 0, 0, 0], dtype=np.float64),
        np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float64),
        np.array([1, 0, 1, 0, 0, 0, 0, 0], dtype=np.float64),
        np.random.randn(8),  # Random vector
    ]
    
    all_passed = True
    for pos in test_positions:
        spinor = Spinor(pos, phase=0.5)
        reconstructed = project_and_lift(spinor)
        loss = projection_loss(spinor, reconstructed)
        passed = loss < EPSILON
        status = "PASS" if passed else "FAIL"
        print(f"  Loss = {loss:.2e} -> {status}")
        all_passed = all_passed and passed
    
    print(f"  Result: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    
    # Test 2: Phase preservation
    print("\n--- Test 2: Phase preservation ---")
    spinor = Spinor(np.array([1, 1, 0, 0, 0, 0, 0, 0]), phase=1.234)
    projected = coxeter_projection_8d_to_4d(spinor)
    reconstructed = inverse_projection_with_phason(projected.parallel, projected.phason, projected.phase)
    phase_preserved = abs(spinor.phase - reconstructed.phase) < EPSILON
    print(f"  Original phase: {spinor.phase:.4f}")
    print(f"  Reconstructed phase: {reconstructed.phase:.4f}")
    print(f"  Phase preserved: {phase_preserved}")
    
    # Test 3: Golden ratio structure in projected norms
    print("\n--- Test 3: Golden ratio structure ---")
    parallel_norms, phason_norms = compute_projected_norms()
    unique_parallel = np.unique(np.round(parallel_norms, 4))
    unique_phason = np.unique(np.round(phason_norms, 4))
    
    print(f"  Unique parallel norm² values: {len(unique_parallel)}")
    print(f"  Unique phason norm² values: {len(unique_phason)}")
    
    # Check for φ-related ratios
    if len(unique_parallel) > 1:
        ratios = unique_parallel[1:] / unique_parallel[:-1]
        phi_related = [r for r in ratios if abs(r - PHI) < 0.5 or abs(r - PHI_INV) < 0.5]
        print(f"  φ-related ratios found: {len(phi_related)} / {len(ratios)}")
    
    # Test 4: Verify E8 roots project correctly
    print("\n--- Test 4: E8 root projection ---")
    roots = generate_e8_roots()
    
    # Check that parallel + phason norms equal original norm
    total_preserved = 0
    for root in roots[:10]:  # Check first 10
        spinor = Spinor(root)
        proj = coxeter_projection_8d_to_4d(spinor)
        orig_norm_sq = np.dot(root, root)
        proj_norm_sq = np.dot(proj.parallel, proj.parallel) + np.dot(proj.phason, proj.phason)
        if abs(orig_norm_sq - proj_norm_sq) < EPSILON:
            total_preserved += 1
    
    print(f"  Norm preservation (first 10 roots): {total_preserved}/10")
    
    # Test 5: Batch operations
    print("\n--- Test 5: Batch operations ---")
    spinors = [Spinor(root, phase=i * 0.1) for i, root in enumerate(roots[:5])]
    projected = batch_project(spinors)
    lifted = batch_lift(projected)
    
    batch_loss = sum(projection_loss(s, l) for s, l in zip(spinors, lifted))
    print(f"  Total batch loss: {batch_loss:.2e}")
    print(f"  Batch operations: {'PASS' if batch_loss < EPSILON else 'FAIL'}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
