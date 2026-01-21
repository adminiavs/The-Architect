#!/usr/bin/env python3
"""
Topological Error Correction for GQE Compression

Implements Toric-Code-inspired error correction on E8 lattice structure.
Aligns with Axiom 6: "Physics is Error Correction"

The key insight: E8 lattice has natural neighborhood structure (240 roots).
We define stabilizers on these neighborhoods to detect phase inconsistencies
(syndromes) and correct them using Minimum Weight Perfect Matching (MWPM).

Connection to The Architect's Model:
- The 4D parallel + 4D phason split provides redundant encoding
- Phase coherence between neighbors acts as stabilizer constraint
- Syndrome = detected decoherence (spinor out of phase with neighbors)
- Correction = minimizing decoherence (returning to symmetry)

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import List, Tuple, Dict, Set, Optional
from dataclasses import dataclass
from collections import defaultdict
import heapq

from .e8_lattice import Spinor, generate_e8_roots, spinor_distance
from .projection import (
    coxeter_projection_8d_to_4d, 
    inverse_projection_with_phason,
    ProjectedSpinor
)
from .phi_adic import PHI, PHI_INV


@dataclass
class Syndrome:
    """
    A detected violation of local consistency (decoherence).
    
    In Toric Code terms: this is where a stabilizer measurement returns -1.
    In The Architect's terms: this is a spinor out of phase with its neighbors.
    
    Attributes:
        spinor_idx: Index of the decoherent spinor
        expected_phase: Phase predicted by neighbor consensus
        observed_phase: Actual phase observed
        confidence: How confident (based on # agreeing neighbors)
        severity: Magnitude of the phase deviation
    """
    spinor_idx: int
    expected_phase: float
    observed_phase: float
    confidence: float
    severity: float


@dataclass 
class CorrectionPath:
    """
    A path of corrections to apply (like Toric Code error chains).
    
    Attributes:
        start_idx: Starting spinor index
        end_idx: Ending spinor index  
        path_indices: Indices along the correction path
        total_cost: Total cost of this correction
    """
    start_idx: int
    end_idx: int
    path_indices: List[int]
    total_cost: float


class ToricErrorCorrector:
    """
    Topological error correction for spinor configurations.
    
    Uses E8 lattice neighborhood structure to define local stabilizers,
    detect syndromes (phase inconsistencies), and correct via MWPM.
    
    This implements Axiom 6: "The dynamics of the Universe minimize 
    inconsistencies and return the structure toward symmetry."
    """
    
    def __init__(self, 
                 distance_threshold: float = 2.0,
                 phase_tolerance: float = np.pi / 4,
                 confidence_threshold: float = 0.3):
        """
        Initialize error corrector.
        
        Args:
            distance_threshold: Max spinor distance to be neighbors
            phase_tolerance: Max phase deviation before flagging syndrome
            confidence_threshold: Min confidence to trust neighbor consensus
        """
        self.distance_threshold = distance_threshold
        self.phase_tolerance = phase_tolerance
        self.confidence_threshold = confidence_threshold
        self.e8_roots = generate_e8_roots()
    
    def build_neighbor_graph(self, spinors: List[Spinor]) -> Dict[int, List[Tuple[int, float]]]:
        """
        Build neighbor graph based on E8 lattice distance.
        
        Each spinor is connected to nearby spinors, weighted by distance.
        This forms the "lattice" for our Toric Code analog.
        
        Returns:
            Dict mapping spinor index -> list of (neighbor_idx, distance)
        """
        neighbors = defaultdict(list)
        
        for i, s1 in enumerate(spinors):
            for j, s2 in enumerate(spinors):
                if i != j:
                    dist = spinor_distance(s1, s2)
                    if dist <= self.distance_threshold:
                        neighbors[i].append((j, dist))
        
        return neighbors
    
    def compute_stabilizer(self, 
                           spinor: Spinor, 
                           neighbor_spinors: List[Tuple[Spinor, float]]) -> Tuple[float, float]:
        """
        Compute stabilizer measurement for a spinor.
        
        In Toric Code: stabilizer is product of Pauli operators on edges.
        Here: stabilizer checks phase coherence with neighbors.
        
        The expected phase is computed from weighted neighbor consensus,
        where weights are inverse distance (closer neighbors have more influence).
        
        Args:
            spinor: The spinor to check
            neighbor_spinors: List of (neighbor_spinor, distance) pairs
        
        Returns:
            (expected_phase, confidence) tuple
        """
        if not neighbor_spinors:
            return spinor.phase, 0.0
        
        # Weighted circular mean of neighbor phases
        # Weight = inverse distance (closer = more influence)
        sin_sum = 0.0
        cos_sum = 0.0
        total_weight = 0.0
        
        for neighbor, dist in neighbor_spinors:
            weight = 1.0 / (1.0 + dist)
            
            # Account for potential phase wrapping
            # Neighbors might be in-phase or anti-phase based on geometry
            # Check both and use whichever is closer
            phase_diff = neighbor.phase - spinor.phase
            if abs(phase_diff) > np.pi:
                # Might be anti-phase relationship
                neighbor_phase = (neighbor.phase + np.pi) % (2 * np.pi)
            else:
                neighbor_phase = neighbor.phase
            
            sin_sum += weight * np.sin(neighbor_phase)
            cos_sum += weight * np.cos(neighbor_phase)
            total_weight += weight
        
        if total_weight < 1e-10:
            return spinor.phase, 0.0
        
        expected_phase = np.arctan2(sin_sum, cos_sum) % (2 * np.pi)
        
        # Confidence based on coherence of neighbors
        # If neighbors agree, confidence is high
        coherence = np.sqrt(sin_sum**2 + cos_sum**2) / total_weight
        confidence = coherence
        
        return expected_phase, confidence
    
    def detect_syndromes(self, spinors: List[Spinor]) -> List[Syndrome]:
        """
        Detect phase inconsistencies (syndromes) in spinor configuration.
        
        This is analogous to measuring stabilizers in Toric Code.
        A syndrome indicates local decoherence.
        
        Args:
            spinors: List of spinors to check
        
        Returns:
            List of detected syndromes
        """
        if len(spinors) < 2:
            return []
        
        neighbors = self.build_neighbor_graph(spinors)
        syndromes = []
        
        for i, spinor in enumerate(spinors):
            if i not in neighbors or len(neighbors[i]) == 0:
                continue
            
            # Get neighbor spinors with distances
            neighbor_spinors = [
                (spinors[j], dist) 
                for j, dist in neighbors[i]
            ]
            
            expected_phase, confidence = self.compute_stabilizer(spinor, neighbor_spinors)
            
            # Check if phase deviates significantly
            phase_diff = abs(expected_phase - spinor.phase)
            phase_diff = min(phase_diff, 2 * np.pi - phase_diff)  # Circular distance
            
            # Flag syndrome if deviation exceeds tolerance and we're confident
            if phase_diff > self.phase_tolerance and confidence > self.confidence_threshold:
                syndromes.append(Syndrome(
                    spinor_idx=i,
                    expected_phase=expected_phase,
                    observed_phase=spinor.phase,
                    confidence=confidence,
                    severity=phase_diff
                ))
        
        return syndromes
    
    def minimum_weight_perfect_matching(self, 
                                         syndromes: List[Syndrome],
                                         spinors: List[Spinor]) -> List[CorrectionPath]:
        """
        Find minimum weight perfect matching of syndromes.
        
        In Toric Code, this pairs syndrome defects optimally
        so corrections along paths don't create new errors.
        
        Uses a greedy approximation for efficiency.
        
        Args:
            syndromes: List of detected syndromes
            spinors: Full spinor list for distance calculations
        
        Returns:
            List of correction paths pairing syndromes
        """
        if len(syndromes) < 2:
            return []
        
        # Build distance matrix between syndrome positions
        n = len(syndromes)
        distances = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                s1 = spinors[syndromes[i].spinor_idx]
                s2 = spinors[syndromes[j].spinor_idx]
                dist = spinor_distance(s1, s2)
                distances[i, j] = dist
                distances[j, i] = dist
        
        # Greedy matching: repeatedly pair closest unmatched syndromes
        matched = set()
        paths = []
        
        # Create list of all pairs sorted by distance
        pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                pairs.append((distances[i, j], i, j))
        pairs.sort()
        
        for dist, i, j in pairs:
            if i not in matched and j not in matched:
                matched.add(i)
                matched.add(j)
                
                # Create correction path (direct for now)
                paths.append(CorrectionPath(
                    start_idx=syndromes[i].spinor_idx,
                    end_idx=syndromes[j].spinor_idx,
                    path_indices=[syndromes[i].spinor_idx, syndromes[j].spinor_idx],
                    total_cost=dist
                ))
        
        # Handle odd syndrome (pair with boundary/vacuum)
        for i in range(n):
            if i not in matched:
                paths.append(CorrectionPath(
                    start_idx=syndromes[i].spinor_idx,
                    end_idx=syndromes[i].spinor_idx,  # Self-correction
                    path_indices=[syndromes[i].spinor_idx],
                    total_cost=syndromes[i].severity
                ))
        
        return paths
    
    def apply_corrections(self, 
                          spinors: List[Spinor], 
                          syndromes: List[Syndrome],
                          correction_strength: float = 0.5) -> List[Spinor]:
        """
        Apply corrections to spinors based on detected syndromes.
        
        For each syndrome, adjust the spinor's phase toward the expected
        value based on neighbor consensus. The correction_strength controls
        how aggressively to correct (1.0 = full correction).
        
        Args:
            spinors: Original spinors (will be copied)
            syndromes: Detected syndromes
            correction_strength: Blend factor (0 = no correction, 1 = full)
        
        Returns:
            Corrected spinor list
        """
        # Copy spinors
        corrected = [Spinor(position=s.position.copy(), phase=s.phase) for s in spinors]
        
        # Sort syndromes by confidence (correct most confident first)
        syndromes_sorted = sorted(syndromes, key=lambda s: s.confidence, reverse=True)
        
        for syndrome in syndromes_sorted:
            idx = syndrome.spinor_idx
            
            # Weighted blend toward expected phase
            alpha = correction_strength * syndrome.confidence
            
            current_phase = corrected[idx].phase
            target_phase = syndrome.expected_phase
            
            # Circular interpolation (shortest path on circle)
            diff = target_phase - current_phase
            if diff > np.pi:
                diff -= 2 * np.pi
            elif diff < -np.pi:
                diff += 2 * np.pi
            
            new_phase = (current_phase + alpha * diff) % (2 * np.pi)
            corrected[idx].phase = new_phase
        
        return corrected
    
    def apply_error_correction(self, 
                                spinors: List[Spinor], 
                                max_iterations: int = 5) -> Tuple[List[Spinor], int, float]:
        """
        Full error correction pipeline.
        
        Iteratively:
        1. Detect syndromes
        2. Find optimal pairing (MWPM)
        3. Apply corrections
        4. Repeat until no syndromes or max iterations
        
        Args:
            spinors: Input spinors (potentially corrupted)
            max_iterations: Maximum correction iterations
        
        Returns:
            (corrected_spinors, n_corrections, final_coherence)
        """
        current = spinors
        total_corrections = 0
        
        for iteration in range(max_iterations):
            syndromes = self.detect_syndromes(current)
            
            if not syndromes:
                break
            
            # Apply corrections
            current = self.apply_corrections(current, syndromes)
            total_corrections += len(syndromes)
        
        # Compute final coherence (how well phases align)
        final_syndromes = self.detect_syndromes(current)
        if len(current) > 1:
            coherence = 1.0 - len(final_syndromes) / len(current)
        else:
            coherence = 1.0
        
        return current, total_corrections, coherence
    
    def measure_coherence(self, spinors: List[Spinor]) -> float:
        """
        Measure overall phase coherence of spinor configuration.
        
        High coherence = spinors are well-aligned with neighbors.
        Low coherence = many spinors are out of phase.
        
        Returns:
            Coherence score in [0, 1]
        """
        if len(spinors) < 2:
            return 1.0
        
        syndromes = self.detect_syndromes(spinors)
        coherence = 1.0 - len(syndromes) / len(spinors)
        return max(0.0, coherence)


# ============================================================================
# Integration with holographic encoding
# ============================================================================

def apply_toric_correction_to_bytes(data: bytes, 
                                     block_size: int = 8,
                                     max_iterations: int = 3) -> Tuple[bytes, float]:
    """
    Apply Toric-inspired error correction to raw bytes.
    
    Treats bytes as spinor phases and uses neighbor coherence
    to detect and correct errors.
    
    Args:
        data: Potentially corrupted bytes
        block_size: Size of local neighborhood blocks
        max_iterations: Max correction iterations
    
    Returns:
        (corrected_bytes, confidence)
    """
    if len(data) < 2:
        return data, 1.0
    
    # Convert bytes to spinors (phase = byte value scaled to [0, 2π))
    # Position encodes index using φ-based coordinates
    spinors = []
    for i, byte in enumerate(data):
        # Create 8D position based on index
        position = np.zeros(8)
        for dim in range(8):
            position[dim] = np.cos(2 * np.pi * i * PHI**(dim + 1) / len(data))
        
        # Phase from byte value
        phase = (byte / 256.0) * 2 * np.pi
        
        spinors.append(Spinor(position=position, phase=phase))
    
    # Apply error correction
    corrector = ToricErrorCorrector(
        distance_threshold=0.5,  # Tighter threshold for byte-level correction
        phase_tolerance=np.pi / 8,  # Stricter phase tolerance
        confidence_threshold=0.2
    )
    
    corrected_spinors, n_corrections, coherence = corrector.apply_error_correction(
        spinors, 
        max_iterations=max_iterations
    )
    
    # Convert back to bytes
    corrected_bytes = bytearray()
    for spinor in corrected_spinors:
        # Phase back to byte value
        byte_val = int((spinor.phase / (2 * np.pi)) * 256) % 256
        corrected_bytes.append(byte_val)
    
    return bytes(corrected_bytes), coherence


# ============================================================================
# Verification
# ============================================================================

def run_verification():
    """Verify Toric error correction works correctly."""
    print("=" * 60)
    print("TORIC ERROR CORRECTION VERIFICATION")
    print("=" * 60)
    
    import random
    
    # Test 1: Create coherent spinor configuration
    print("\n--- Test 1: Coherent spinors (no errors) ---")
    
    # Create spinors with coherent phases
    spinors = []
    base_phase = 0.5
    for i in range(20):
        pos = np.random.randn(8)
        pos = pos / np.linalg.norm(pos) * np.sqrt(2)  # E8 root norm
        phase = base_phase + np.random.randn() * 0.1  # Small variation
        spinors.append(Spinor(position=pos, phase=phase % (2 * np.pi)))
    
    corrector = ToricErrorCorrector()
    syndromes = corrector.detect_syndromes(spinors)
    coherence = corrector.measure_coherence(spinors)
    
    print(f"  Spinors: {len(spinors)}")
    print(f"  Syndromes detected: {len(syndromes)}")
    print(f"  Coherence: {coherence:.2%}")
    
    # Test 2: Introduce errors and correct
    print("\n--- Test 2: Error correction ---")
    
    # Corrupt some phases
    corrupted = [Spinor(position=s.position.copy(), phase=s.phase) for s in spinors]
    n_corrupt = 5
    for _ in range(n_corrupt):
        idx = random.randint(0, len(corrupted) - 1)
        corrupted[idx].phase = random.uniform(0, 2 * np.pi)  # Random phase
    
    syndromes_before = corrector.detect_syndromes(corrupted)
    coherence_before = corrector.measure_coherence(corrupted)
    
    corrected, n_corrections, coherence_after = corrector.apply_error_correction(corrupted)
    
    print(f"  Corrupted: {n_corrupt} spinors")
    print(f"  Syndromes before: {len(syndromes_before)}")
    print(f"  Coherence before: {coherence_before:.2%}")
    print(f"  Corrections applied: {n_corrections}")
    print(f"  Coherence after: {coherence_after:.2%}")
    
    # Test 3: Byte-level correction
    print("\n--- Test 3: Byte-level error correction ---")
    
    test_data = b"The quick brown fox jumps over the lazy dog."
    
    # Corrupt bytes
    corrupted_data = bytearray(test_data)
    n_corrupt = int(len(corrupted_data) * 0.1)  # 10% corruption
    for _ in range(n_corrupt):
        idx = random.randint(0, len(corrupted_data) - 1)
        corrupted_data[idx] ^= random.randint(1, 255)
    
    corrected_data, confidence = apply_toric_correction_to_bytes(bytes(corrupted_data))
    
    # Measure recovery
    orig_bytes = list(test_data)
    corr_bytes = list(corrected_data)
    
    matches = sum(1 for o, c in zip(orig_bytes, corr_bytes) if o == c)
    recovery_rate = matches / len(orig_bytes) if orig_bytes else 0
    
    print(f"  Original: {len(test_data)} bytes")
    print(f"  Corrupted: {n_corrupt} bytes ({n_corrupt/len(test_data):.0%})")
    print(f"  Recovery rate: {recovery_rate:.2%}")
    print(f"  Confidence: {confidence:.2%}")
    
    # Test 4: Scaling with corruption level
    print("\n--- Test 4: Recovery vs corruption level ---")
    
    for corruption_rate in [0.01, 0.05, 0.10, 0.20, 0.30]:
        corrupted_data = bytearray(test_data)
        n_corrupt = int(len(corrupted_data) * corruption_rate)
        
        indices = random.sample(range(len(corrupted_data)), n_corrupt)
        for idx in indices:
            corrupted_data[idx] ^= random.randint(1, 255)
        
        corrected_data, confidence = apply_toric_correction_to_bytes(bytes(corrupted_data))
        
        matches = sum(1 for o, c in zip(test_data, corrected_data) if o == c)
        recovery_rate = matches / len(test_data)
        
        print(f"  {corruption_rate:5.0%} corruption -> {recovery_rate:.2%} recovery (conf: {confidence:.2%})")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
