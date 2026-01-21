#!/usr/bin/env python3
"""
Bekenstein Bound: Preventing Storage Bloat

THE PRINCIPLE (From The Architect):
    The Horizon cannot grow infinitely. Information has limits.
    The Universe doesn't keep every random mutation - only STABLE HARMONICS.

THE MECHANISM:
    1. DRIFT BUFFER:
       - Allow the lattice to drift locally in RAM while processing
       - Don't persist every micro-change
    
    2. THE SNAP (Golden Threshold):
       - Only save changes if they exceed φ% improvement (1.618%)
       - This is the "Crystallization Threshold"
    
    3. ENTROPY PRUNING:
       - If a node hasn't been used in N cycles, it DECAYS
       - Custom positions return to default E8 roots
       - Mimics the Universe's entropy-driven forgetting
    
    4. DIFF STORAGE:
       - Do NOT store full N×8 matrix
       - Store only vectors that moved significantly
       - Quantize movements as discrete PHASON FLIPS (integers)

THE RESULT:
    Storage remains bounded regardless of how much data is processed.
    Only stable, useful patterns are preserved.

Author: The Architect
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
import json

from .phi_adic import PHI, PHI_INV
from .e8_lattice import generate_e8_roots


# The Golden Threshold: φ% = 1.618%
GOLDEN_THRESHOLD = PHI / 100.0  # 0.01618

# Decay parameters
DEFAULT_DECAY_CYCLES = 100  # After N unused cycles, decay begins
DECAY_RATE = 0.1  # How fast unused nodes decay per cycle

# Quantization parameters
PHASON_QUANT_LEVELS = 256  # Discrete levels for quantization
MOVEMENT_THRESHOLD = 0.01  # Minimum movement to store


@dataclass
class PhasonFlip:
    """
    A quantized movement in E8 space.
    
    Instead of storing full float64 vectors, we store:
    - node_idx: Which vocabulary node moved
    - direction: Quantized direction (index into E8 roots)
    - magnitude: Quantized magnitude (0-255)
    
    This reduces storage from 8*8 = 64 bytes to 3 bytes per flip.
    """
    node_idx: int
    direction_idx: int  # Index into 240 E8 roots
    magnitude: int      # 0-255 quantized magnitude
    
    def to_tuple(self) -> Tuple[int, int, int]:
        return (self.node_idx, self.direction_idx, self.magnitude)
    
    @classmethod
    def from_tuple(cls, t: Tuple[int, int, int]) -> 'PhasonFlip':
        return cls(t[0], t[1], t[2])


@dataclass
class CrystallizedState:
    """
    Compact storage for evolved embeddings.
    
    Instead of storing full embeddings, we store:
    - base_embeddings: Initial E8-snapped positions (can be regenerated)
    - phason_diffs: List of quantized movements from base
    - last_used: Cycle number when each node was last used
    - fitness_at_crystallization: The fitness when this state was saved
    
    This implements the Bekenstein Bound - finite storage for infinite learning.
    """
    vocabulary: Dict[str, int]
    phason_diffs: List[PhasonFlip]
    last_used: Dict[int, int]  # node_idx -> last cycle used
    fitness_at_crystallization: float
    generation: int
    total_tokens_seen: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'vocabulary': self.vocabulary,
            'phason_diffs': [p.to_tuple() for p in self.phason_diffs],
            'last_used': self.last_used,
            'fitness': self.fitness_at_crystallization,
            'generation': self.generation,
            'tokens_seen': self.total_tokens_seen,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'CrystallizedState':
        return cls(
            vocabulary=d['vocabulary'],
            phason_diffs=[PhasonFlip.from_tuple(t) for t in d.get('phason_diffs', [])],
            last_used=d.get('last_used', {}),
            fitness_at_crystallization=d.get('fitness', 0.0),
            generation=d.get('generation', 0),
            total_tokens_seen=d.get('tokens_seen', 0),
        )
    
    def storage_size_bytes(self) -> int:
        """Estimate storage size in bytes."""
        vocab_size = len(json.dumps(self.vocabulary))
        diffs_size = len(self.phason_diffs) * 3  # 3 bytes per flip
        metadata_size = 100  # Rough estimate for metadata
        return vocab_size + diffs_size + metadata_size


class BekensteinBound:
    """
    Implements storage-bounded learning for the GQE system.
    
    THE BEKENSTEIN BOUND:
    The maximum information in a region is proportional to its surface area,
    not its volume. Similarly, our storage grows with vocabulary size,
    not with the amount of data processed.
    """
    
    def __init__(self, 
                 golden_threshold: float = GOLDEN_THRESHOLD,
                 decay_cycles: int = DEFAULT_DECAY_CYCLES,
                 decay_rate: float = DECAY_RATE,
                 max_diffs: int = 10000):
        """
        Args:
            golden_threshold: Minimum improvement to trigger crystallization (φ%)
            decay_cycles: Cycles before unused nodes start decaying
            decay_rate: Rate of decay per cycle
            max_diffs: Maximum number of phason diffs to store
        """
        self.golden_threshold = golden_threshold
        self.decay_cycles = decay_cycles
        self.decay_rate = decay_rate
        self.max_diffs = max_diffs
        
        # E8 roots for quantization
        self.e8_roots = generate_e8_roots()
        self.n_roots = len(self.e8_roots)
        
        # Drift buffer (in-RAM state)
        self.drift_buffer: Dict[int, np.ndarray] = {}
        self.last_used: Dict[int, int] = {}
        self.current_cycle: int = 0
        
        # Crystallized state (persistent)
        self.crystallized: Optional[CrystallizedState] = None
        self.last_fitness: float = 0.0
    
    def quantize_movement(self, movement: np.ndarray) -> Optional[PhasonFlip]:
        """
        Quantize a movement vector into a PhasonFlip.
        
        Args:
            movement: 8D movement vector
        
        Returns:
            PhasonFlip if movement is significant, None otherwise
        """
        magnitude = np.linalg.norm(movement)
        
        if magnitude < MOVEMENT_THRESHOLD:
            return None
        
        # Find closest E8 root direction
        normalized = movement / magnitude
        dots = np.dot(self.e8_roots, normalized)
        direction_idx = int(np.argmax(np.abs(dots)))
        
        # Get the sign of the projection
        sign = np.sign(dots[direction_idx])
        
        # Quantize magnitude to 0-255
        # Scale such that typical movements map to mid-range
        # Use log scale for better precision at small magnitudes
        quant_mag = min(255, max(1, int(magnitude * 500)))
        
        # Encode sign in the high bit of direction_idx
        # direction_idx is 0-239, so we can use 0-239 for positive, 240-479 for negative
        if sign < 0:
            direction_idx += 240
        
        return PhasonFlip(
            node_idx=-1,  # Will be set by caller
            direction_idx=direction_idx,
            magnitude=quant_mag
        )
    
    def dequantize_movement(self, flip: PhasonFlip) -> np.ndarray:
        """
        Reconstruct a movement vector from a PhasonFlip.
        
        Args:
            flip: Quantized phason flip
        
        Returns:
            8D movement vector
        """
        # Decode sign from direction_idx
        if flip.direction_idx >= 240:
            direction = -self.e8_roots[flip.direction_idx - 240]
        else:
            direction = self.e8_roots[flip.direction_idx]
        
        magnitude = flip.magnitude / 500.0
        return direction * magnitude
    
    def update_drift(self, node_idx: int, movement: np.ndarray):
        """
        Add movement to the drift buffer.
        
        Args:
            node_idx: Index of the node that moved
            movement: 8D movement vector
        """
        if node_idx not in self.drift_buffer:
            self.drift_buffer[node_idx] = np.zeros(8)
        
        self.drift_buffer[node_idx] += movement
        self.last_used[node_idx] = self.current_cycle
    
    def mark_used(self, node_indices: np.ndarray):
        """
        Mark nodes as used in this cycle.
        
        Args:
            node_indices: Array of node indices that were used
        """
        for idx in np.unique(node_indices):
            self.last_used[int(idx)] = self.current_cycle
    
    def apply_decay(self, base_embeddings: np.ndarray) -> Tuple[np.ndarray, int]:
        """
        Apply entropy decay to unused nodes.
        
        Nodes that haven't been used in decay_cycles will start
        returning to their base positions.
        
        Args:
            base_embeddings: Original E8-based embeddings
        
        Returns:
            (decayed_drift_buffer, n_decayed)
        """
        n_decayed = 0
        nodes_to_remove = []
        
        for node_idx, drift in list(self.drift_buffer.items()):
            last_use = self.last_used.get(node_idx, 0)
            cycles_unused = self.current_cycle - last_use
            
            if cycles_unused > self.decay_cycles:
                # Apply decay
                decay_factor = np.exp(-self.decay_rate * (cycles_unused - self.decay_cycles))
                self.drift_buffer[node_idx] = drift * decay_factor
                
                # Remove if decayed to near zero
                if np.linalg.norm(self.drift_buffer[node_idx]) < MOVEMENT_THRESHOLD:
                    nodes_to_remove.append(node_idx)
                    n_decayed += 1
        
        # Remove fully decayed nodes
        for node_idx in nodes_to_remove:
            del self.drift_buffer[node_idx]
            if node_idx in self.last_used:
                del self.last_used[node_idx]
        
        return n_decayed
    
    def should_crystallize(self, current_fitness: float) -> bool:
        """
        Check if we should crystallize (save) the current state.
        
        THE GOLDEN THRESHOLD:
        Only crystallize if fitness improved by more than φ%.
        
        Args:
            current_fitness: Current compression fitness
        
        Returns:
            True if we should crystallize
        """
        if self.last_fitness == 0:
            return True  # First crystallization
        
        improvement = (current_fitness - self.last_fitness) / abs(self.last_fitness + 1e-10)
        
        return improvement > self.golden_threshold
    
    def crystallize(self, 
                    vocabulary: Dict[str, int],
                    generation: int,
                    total_tokens: int,
                    current_fitness: float) -> CrystallizedState:
        """
        Crystallize the current drift buffer into persistent storage.
        
        THE SNAP:
        Convert floating-point drifts into quantized phason flips.
        
        Args:
            vocabulary: Current vocabulary
            generation: Current generation number
            total_tokens: Total tokens processed
            current_fitness: Current fitness value
        
        Returns:
            CrystallizedState object
        """
        phason_diffs = []
        
        # Convert drift buffer to quantized flips
        for node_idx, drift in self.drift_buffer.items():
            flip = self.quantize_movement(drift)
            if flip is not None:
                flip.node_idx = node_idx
                phason_diffs.append(flip)
        
        # Sort by magnitude (most significant first)
        phason_diffs.sort(key=lambda f: f.magnitude, reverse=True)
        
        # Enforce max_diffs limit (Bekenstein Bound)
        if len(phason_diffs) > self.max_diffs:
            phason_diffs = phason_diffs[:self.max_diffs]
        
        self.crystallized = CrystallizedState(
            vocabulary=vocabulary,
            phason_diffs=phason_diffs,
            last_used=dict(self.last_used),
            fitness_at_crystallization=current_fitness,
            generation=generation,
            total_tokens_seen=total_tokens,
        )
        
        self.last_fitness = current_fitness
        
        return self.crystallized
    
    def get_effective_embeddings(self, base_embeddings: np.ndarray) -> np.ndarray:
        """
        Get the effective embeddings including drift.
        
        Args:
            base_embeddings: Original E8-based embeddings
        
        Returns:
            Embeddings with drift applied
        """
        result = base_embeddings.copy()
        
        # Apply drift buffer
        for node_idx, drift in self.drift_buffer.items():
            if node_idx < len(result):
                result[node_idx] += drift
        
        return result
    
    def reconstruct_from_crystallized(self, 
                                       base_embeddings: np.ndarray) -> np.ndarray:
        """
        Reconstruct full embeddings from crystallized state.
        
        Args:
            base_embeddings: Original E8-based embeddings
        
        Returns:
            Full embeddings with crystallized diffs applied
        """
        if self.crystallized is None:
            return base_embeddings
        
        result = base_embeddings.copy()
        
        for flip in self.crystallized.phason_diffs:
            if flip.node_idx < len(result):
                movement = self.dequantize_movement(flip)
                result[flip.node_idx] += movement
        
        return result
    
    def load_crystallized(self, path: str) -> bool:
        """
        Load crystallized state from file.
        
        Args:
            path: Path to crystallized state file
        
        Returns:
            True if loaded successfully
        """
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            if not data or 'vocabulary' not in data:
                return False
            
            self.crystallized = CrystallizedState.from_dict(data)
            self.last_fitness = self.crystallized.fitness_at_crystallization
            self.last_used = dict(self.crystallized.last_used)
            self.current_cycle = self.crystallized.generation
            
            # Reconstruct drift buffer from phason diffs
            self.drift_buffer.clear()
            for flip in self.crystallized.phason_diffs:
                self.drift_buffer[flip.node_idx] = self.dequantize_movement(flip)
            
            return True
            
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            return False
    
    def save_crystallized(self, path: str):
        """
        Save crystallized state to file.
        
        Args:
            path: Path to save file
        """
        if self.crystallized is None:
            return
        
        with open(path, 'w') as f:
            json.dump(self.crystallized.to_dict(), f)
    
    def advance_cycle(self):
        """Advance to the next cycle."""
        self.current_cycle += 1
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current storage usage.
        
        Returns:
            Dictionary with storage statistics
        """
        drift_nodes = len(self.drift_buffer)
        crystallized_diffs = len(self.crystallized.phason_diffs) if self.crystallized else 0
        
        # Estimate sizes
        drift_size = drift_nodes * 8 * 8  # float64 per dimension
        crystallized_size = self.crystallized.storage_size_bytes() if self.crystallized else 0
        
        return {
            'drift_buffer_nodes': drift_nodes,
            'drift_buffer_bytes': drift_size,
            'crystallized_diffs': crystallized_diffs,
            'crystallized_bytes': crystallized_size,
            'total_bytes': drift_size + crystallized_size,
            'current_cycle': self.current_cycle,
            'last_fitness': self.last_fitness,
        }


def demonstrate_bekenstein():
    """Demonstrate the Bekenstein Bound in action."""
    print("=" * 60)
    print("BEKENSTEIN BOUND DEMONSTRATION")
    print("=" * 60)
    
    print("\nTHE PRINCIPLE:")
    print(f"  Golden Threshold: {GOLDEN_THRESHOLD*100:.3f}% (φ%)")
    print(f"  Decay Cycles: {DEFAULT_DECAY_CYCLES}")
    print(f"  Quantization Levels: {PHASON_QUANT_LEVELS}")
    
    # Create bound manager
    bound = BekensteinBound()
    
    # Simulate some movements
    print("\n--- Simulating Node Movements ---")
    
    for i in range(10):
        # Random movement
        movement = np.random.randn(8) * 0.1
        bound.update_drift(i, movement)
    
    print(f"  Drift buffer nodes: {len(bound.drift_buffer)}")
    
    # Try to crystallize
    print("\n--- Crystallization Check ---")
    
    should_cryst = bound.should_crystallize(0.5)
    print(f"  Should crystallize (first): {should_cryst}")
    
    if should_cryst:
        vocab = {f"word_{i}": i for i in range(10)}
        state = bound.crystallize(vocab, 1, 1000, 0.5)
        print(f"  Crystallized {len(state.phason_diffs)} phason diffs")
        print(f"  Storage size: {state.storage_size_bytes()} bytes")
    
    # Check if marginal improvement triggers crystallization
    bound.last_fitness = 0.5
    should_cryst_marginal = bound.should_crystallize(0.505)  # 1% improvement
    print(f"  Should crystallize (1% improvement): {should_cryst_marginal}")
    
    should_cryst_golden = bound.should_crystallize(0.51)  # 2% improvement > φ%
    print(f"  Should crystallize (2% improvement): {should_cryst_golden}")
    
    # Test quantization
    print("\n--- Quantization Test ---")
    
    original = np.array([0.1, 0.2, 0.3, 0.4, -0.1, -0.2, -0.3, -0.4])
    flip = bound.quantize_movement(original)
    
    if flip:
        reconstructed = bound.dequantize_movement(flip)
        error = np.linalg.norm(original - reconstructed)
        print(f"  Original magnitude: {np.linalg.norm(original):.4f}")
        print(f"  Quantized magnitude: {flip.magnitude}")
        print(f"  Reconstruction error: {error:.4f}")
    
    print("\n" + "=" * 60)
    print("THE RESULT:")
    print("  Storage is BOUNDED by the Bekenstein limit.")
    print("  Only stable harmonics (significant improvements) are kept.")
    print("=" * 60)


if __name__ == "__main__":
    demonstrate_bekenstein()
