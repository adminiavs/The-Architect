#!/usr/bin/env python3
"""
E8 Lattice Spinor Operations for GQE Compression

Architect Principle: From Lexicon - "Spinor: The fundamental information unit. 
A geometric bit with orientation & phase."

CRITICAL FIX 2: The Architect's "Atom" is the Spinor (vector + phase), not a static point.

Key operations:
- Generate E8 roots
- Spinor class with position and phase
- Spinor distance including angular component
- Interference computation (constructive vs destructive)

Author: The Architect
License: Public Domain
"""

import numpy as np
from itertools import combinations, product
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass, field
import heapq

try:
    from .phi_adic import PHI, PHI_INV
except ImportError:
    from phi_adic import PHI, PHI_INV

# Precision for comparisons
EPSILON = 1e-10


@dataclass
class Spinor:
    """
    The fundamental information unit in The Architect's model.
    
    A Spinor is a geometric bit with:
    - position: 8D vector in E8 lattice space
    - phase: Angular orientation in [0, 2π)
    
    Two spinors at the same position but different phases are DISTINCT.
    This enables interference-aware compression.
    
    Attributes:
        position: 8D numpy array representing position in E8 space
        phase: Phase angle in radians [0, 2π)
    """
    position: np.ndarray
    phase: float = 0.0
    
    def __post_init__(self):
        """Ensure position is a numpy array and phase is normalized."""
        if not isinstance(self.position, np.ndarray):
            self.position = np.array(self.position, dtype=np.float64)
        # Normalize phase to [0, 2π)
        self.phase = self.phase % (2 * np.pi)
    
    def __hash__(self):
        """Hash for use in sets/dicts."""
        return hash((tuple(self.position.round(6)), round(self.phase, 6)))
    
    def __eq__(self, other):
        """Equality check including phase."""
        if not isinstance(other, Spinor):
            return False
        return (np.allclose(self.position, other.position, atol=EPSILON) and 
                abs(self.phase - other.phase) < EPSILON)
    
    def copy(self) -> 'Spinor':
        """Create a copy of this spinor."""
        return Spinor(self.position.copy(), self.phase)
    
    @property
    def norm(self) -> float:
        """Euclidean norm of position."""
        return np.linalg.norm(self.position)
    
    def to_complex(self) -> np.ndarray:
        """Convert to complex representation (position * e^(i*phase))."""
        return self.position * np.exp(1j * self.phase)
    
    def __repr__(self) -> str:
        pos_str = np.array2string(self.position, precision=3, suppress_small=True)
        return f"Spinor(pos={pos_str}, phase={self.phase:.4f})"


def spinor_distance(s1: Spinor, s2: Spinor) -> float:
    """
    Compute distance between two spinors.
    
    Distance metric includes both spatial and angular components:
        distance = sqrt(euclidean_distance² + (phase_difference / π)²)
    
    This ensures spinors with opposite phases (destructive interference)
    are considered "far apart" even if spatially close.
    
    Args:
        s1: First spinor
        s2: Second spinor
    
    Returns:
        Combined distance metric
    """
    # Euclidean distance in position space
    euclidean_dist = np.linalg.norm(s1.position - s2.position)
    
    # Phase difference (normalized to [-π, π])
    phase_diff = s1.phase - s2.phase
    phase_diff = (phase_diff + np.pi) % (2 * np.pi) - np.pi  # Wrap to [-π, π]
    
    # Normalized phase component
    phase_component = abs(phase_diff) / np.pi
    
    # Combined distance
    return np.sqrt(euclidean_dist ** 2 + phase_component ** 2)


def compute_interference(s1: Spinor, s2: Spinor) -> float:
    """
    Compute interference factor between two spinors.
    
    Interference:
        - Constructive: phase_diff ≈ 0 → +1
        - Destructive: phase_diff ≈ π → -1
    
    This is analogous to wave interference in physics.
    The compressor should prioritize constructive interference paths.
    
    Args:
        s1: First spinor
        s2: Second spinor
    
    Returns:
        Interference factor in [-1, +1]
    """
    phase_diff = s1.phase - s2.phase
    return np.cos(phase_diff)


def generate_e8_roots() -> np.ndarray:
    """
    Generate all 240 roots of the E8 lattice.
    
    Type I: (±1, ±1, 0, 0, 0, 0, 0, 0) and permutations (112 roots)
    Type II: (±1/2, ..., ±1/2) with even number of minus signs (128 roots)
    
    Returns:
        numpy array of shape (240, 8)
    """
    roots = []
    
    # Type I: Choose 2 positions out of 8, assign ±1 to each
    for i, j in combinations(range(8), 2):
        for s1, s2 in product([1, -1], repeat=2):
            v = np.zeros(8)
            v[i] = s1
            v[j] = s2
            roots.append(v)
    
    # Type II: All half-integer coordinates with even number of minus signs
    for signs in product([1, -1], repeat=8):
        if sum(1 for s in signs if s == -1) % 2 == 0:
            v = np.array([0.5 * s for s in signs])
            roots.append(v)
    
    roots = np.array(roots)
    
    # Verify count and norms
    assert len(roots) == 240, f"Expected 240 roots, got {len(roots)}"
    norms = np.linalg.norm(roots, axis=1)
    assert np.allclose(norms, np.sqrt(2)), "All roots should have norm sqrt(2)"
    
    return roots


def generate_e8_spinors(include_phases: bool = False) -> List[Spinor]:
    """
    Generate E8 roots as Spinors.
    
    Args:
        include_phases: If True, generate spinors with multiple phase values
                       (at golden angle intervals for quasicrystal structure)
    
    Returns:
        List of Spinor objects
    """
    roots = generate_e8_roots()
    spinors = []
    
    if include_phases:
        # Generate multiple phase values at golden angle intervals
        golden_angle = 2 * np.pi * PHI_INV  # ≈ 137.5°
        n_phases = 5  # 5 phases gives good coverage
        phases = [i * golden_angle for i in range(n_phases)]
        
        for root in roots:
            for phase in phases:
                spinors.append(Spinor(root.copy(), phase))
    else:
        spinors = [Spinor(root.copy(), 0.0) for root in roots]
    
    return spinors


def find_nearest_lattice_spinor(
    query: Spinor, 
    lattice_spinors: List[Spinor],
    prioritize_constructive: bool = True
) -> Tuple[Spinor, float]:
    """
    Find the nearest lattice spinor to a query spinor.
    
    If prioritize_constructive is True, prefers spinors with constructive
    interference (similar phase) over purely spatial proximity.
    
    Args:
        query: Query spinor
        lattice_spinors: List of lattice spinors to search
        prioritize_constructive: Whether to weight constructive interference
    
    Returns:
        (nearest_spinor, distance) tuple
    """
    best_spinor = None
    best_score = float('inf')
    
    for spinor in lattice_spinors:
        if prioritize_constructive:
            # Score combines distance and interference
            dist = spinor_distance(query, spinor)
            interference = compute_interference(query, spinor)
            # Lower score is better; interference bonus when positive
            score = dist * (2 - interference)  # Score in [dist, 3*dist]
        else:
            score = spinor_distance(query, spinor)
        
        if score < best_score:
            best_score = score
            best_spinor = spinor
    
    return best_spinor.copy(), spinor_distance(query, best_spinor)


def find_k_nearest_spinors(
    query: Spinor,
    lattice_spinors: List[Spinor],
    k: int = 5,
    prioritize_constructive: bool = True
) -> List[Tuple[Spinor, float]]:
    """
    Find the k nearest lattice spinors to a query.
    
    Args:
        query: Query spinor
        lattice_spinors: List of lattice spinors to search
        k: Number of nearest neighbors
        prioritize_constructive: Whether to weight constructive interference
    
    Returns:
        List of (spinor, distance) tuples, sorted by distance
    """
    results = []
    
    for spinor in lattice_spinors:
        if prioritize_constructive:
            dist = spinor_distance(query, spinor)
            interference = compute_interference(query, spinor)
            score = dist * (2 - interference)
        else:
            score = spinor_distance(query, spinor)
        
        results.append((spinor.copy(), score, spinor_distance(query, spinor)))
    
    # Sort by score, return with actual distance
    results.sort(key=lambda x: x[1])
    return [(r[0], r[2]) for r in results[:k]]


def compute_voronoi_neighbors(center: Spinor, lattice_spinors: List[Spinor]) -> List[Spinor]:
    """
    Compute the Voronoi neighbors of a spinor in the lattice.
    
    These are the lattice points that share a Voronoi cell face with the center.
    
    Args:
        center: Center spinor
        lattice_spinors: List of all lattice spinors
    
    Returns:
        List of Voronoi neighbor spinors
    """
    # For E8, each point has 240 nearest neighbors (the roots)
    # In general, Voronoi neighbors are found by checking if any point
    # is closer to center than to any other lattice point
    
    # Simplified: return nearest neighbors within a threshold
    distances = [(spinor, spinor_distance(center, spinor)) for spinor in lattice_spinors]
    distances.sort(key=lambda x: x[1])
    
    # Skip self (distance ~0)
    neighbors = []
    threshold = np.sqrt(2) + EPSILON  # E8 root length
    
    for spinor, dist in distances:
        if dist < EPSILON:
            continue  # Skip self
        if dist > threshold * 1.5:
            break  # Beyond nearest shell
        neighbors.append(spinor.copy())
    
    return neighbors


def e8_inner_product(v1: np.ndarray, v2: np.ndarray) -> float:
    """Standard inner product for E8 vectors."""
    return np.dot(v1, v2)


def is_valid_e8_root(v: np.ndarray) -> bool:
    """Check if a vector is a valid E8 root."""
    norm_sq = np.dot(v, v)
    if not np.isclose(norm_sq, 2.0, atol=EPSILON):
        return False
    
    # Check Type I: two ±1s, rest zeros
    nonzero = np.abs(v) > EPSILON
    if np.sum(nonzero) == 2:
        return np.allclose(np.abs(v[nonzero]), 1.0, atol=EPSILON)
    
    # Check Type II: all ±1/2
    if np.sum(nonzero) == 8:
        if np.allclose(np.abs(v), 0.5, atol=EPSILON):
            # Check even number of negatives
            return np.sum(v < 0) % 2 == 0
    
    return False


def snap_to_e8_lattice(v: np.ndarray) -> np.ndarray:
    """
    Snap a vector to the nearest E8 lattice point.
    
    The E8 lattice is the union of:
    - Integer vectors with even sum
    - Half-integer vectors with even sum
    
    Args:
        v: Input 8D vector
    
    Returns:
        Nearest E8 lattice point
    """
    # Round to nearest integers
    int_v = np.round(v)
    int_sum = np.sum(int_v)
    
    # Make sum even by adjusting closest component to boundary
    if int_sum % 2 != 0:
        diffs = np.abs(v - int_v)
        idx = np.argmin(diffs)  # Component closest to rounding boundary
        if v[idx] > int_v[idx]:
            int_v[idx] += 1
        else:
            int_v[idx] -= 1
    
    # Also try half-integer lattice
    half_v = np.round(v - 0.5) + 0.5
    half_sum = np.sum(half_v)
    
    if half_sum % 2 != 0:
        diffs = np.abs(v - half_v)
        idx = np.argmin(diffs)
        if v[idx] > half_v[idx]:
            half_v[idx] += 1
        else:
            half_v[idx] -= 1
    
    # Return whichever is closer
    dist_int = np.linalg.norm(v - int_v)
    dist_half = np.linalg.norm(v - half_v)
    
    return int_v if dist_int <= dist_half else half_v


def snap_spinor_to_e8(spinor: Spinor) -> Spinor:
    """
    Snap a spinor to the E8 lattice, preserving phase.
    
    Args:
        spinor: Input spinor
    
    Returns:
        Spinor with position snapped to E8 lattice
    """
    snapped_pos = snap_to_e8_lattice(spinor.position)
    return Spinor(snapped_pos, spinor.phase)


def run_verification() -> None:
    """Run verification tests for E8 spinor module."""
    print("=" * 60)
    print("E8 SPINOR OPERATIONS VERIFICATION")
    print("=" * 60)
    
    # Test 1: E8 root generation
    print("\n--- Test 1: E8 root generation ---")
    roots = generate_e8_roots()
    print(f"  Generated {len(roots)} E8 roots")
    print(f"  All norms = sqrt(2): {np.allclose(np.linalg.norm(roots, axis=1), np.sqrt(2))}")
    
    # Test 2: Spinor creation and properties
    print("\n--- Test 2: Spinor creation ---")
    s1 = Spinor(np.array([1, 1, 0, 0, 0, 0, 0, 0]), phase=0.0)
    s2 = Spinor(np.array([1, 1, 0, 0, 0, 0, 0, 0]), phase=np.pi)
    print(f"  s1 = {s1}")
    print(f"  s2 = {s2}")
    print(f"  Same position, different phase: {s1 != s2}")
    
    # Test 3: Spinor distance
    print("\n--- Test 3: Spinor distance ---")
    dist = spinor_distance(s1, s2)
    print(f"  Distance(s1, s2) = {dist:.4f}")
    print(f"  Expected: ~1.0 (phase diff = π, normalized by π)")
    
    s3 = Spinor(np.array([1, 0, 1, 0, 0, 0, 0, 0]), phase=0.0)
    dist13 = spinor_distance(s1, s3)
    print(f"  Distance(s1, s3) = {dist13:.4f}")
    print(f"  Expected: ~sqrt(2) (positions differ by sqrt(2), same phase)")
    
    # Test 4: Interference
    print("\n--- Test 4: Interference computation ---")
    print(f"  Interference(s1, s1) = {compute_interference(s1, s1):.4f} (constructive)")
    print(f"  Interference(s1, s2) = {compute_interference(s1, s2):.4f} (destructive)")
    
    # Test 5: Nearest neighbor search
    print("\n--- Test 5: Nearest neighbor search ---")
    spinors = generate_e8_spinors(include_phases=False)
    query = Spinor(np.array([0.9, 0.9, 0.1, 0.1, 0, 0, 0, 0]), phase=0.1)
    nearest, dist = find_nearest_lattice_spinor(query, spinors)
    print(f"  Query: {query}")
    print(f"  Nearest: {nearest}")
    print(f"  Distance: {dist:.4f}")
    
    # Test 6: E8 lattice snapping
    print("\n--- Test 6: E8 lattice snapping ---")
    test_points = [
        np.array([0.9, 1.1, 0.1, -0.1, 0, 0, 0, 0]),
        np.array([0.4, 0.6, 0.4, 0.6, 0.4, 0.6, 0.4, 0.6]),
    ]
    for point in test_points:
        snapped = snap_to_e8_lattice(point)
        print(f"  {point} -> {snapped}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
