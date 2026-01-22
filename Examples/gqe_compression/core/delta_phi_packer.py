#!/usr/bin/env python3
"""
Delta-Phase Packer - Geometric Nuance Encoding

THE PHYSICS:
Human language is larger than 240 E8 roots.
We encode the "nuance" - the delta between data and nearest root.

The Mechanism:
1. Delta-Phase: The angular difference from the E8 root
2. Delta-Magnitude: The radial distance from the root
3. Predictive Geometry: Use angular frequency to predict next symbol

"If the previous token was a Subject, the probability of Verb is high."
We exploit this geometric correlation to store fewer bits.

Key Optimizations:
1. Quantized 4-bit "Nudge" for common deltas
2. Predictive coding based on E8 root adjacency
3. Run-length encoding for repeated patterns

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

try:
    from .bit_packer import BitStream
    from .phi_adic import PHI, PHI_INV
    from .lattice_index import get_e8_roots, LatticeEntry
except ImportError:
    from bit_packer import BitStream
    from phi_adic import PHI, PHI_INV
    from lattice_index import get_e8_roots, LatticeEntry


@dataclass
class DeltaPackConfig:
    """Configuration for delta packing."""
    phase_bits: int = 4  # Bits for phase quantization (4 = 16 levels)
    mag_bits: int = 4    # Bits for magnitude quantization
    use_prediction: bool = True  # Enable predictive geometry
    context_size: int = 3  # Symbols to consider for prediction


class GeometricPredictor:
    """
    Predicts the next E8 root based on geometric context.
    
    THE PHYSICS:
    Words that follow each other in language have geometric relationships.
    "The" -> "King" has an angular frequency between their E8 positions.
    If we know "The", we can predict which region of E8 space "King" lives in.
    
    LEARNED TRANSITIONS:
    Instead of using only E8 geometry, we can LEARN the transition
    probabilities from actual data. This captures linguistic patterns
    that may not be purely geometric.
    """
    
    def __init__(self, context_size: int = 3, use_learned: bool = False):
        self.roots = get_e8_roots()
        self.context_size = context_size
        self.use_learned = use_learned
        
        # Precompute root-to-root transition probabilities
        # Based on angular proximity (adjacent roots are more likely)
        self._build_transition_matrix()
        
        # Learned transitions (updated during compression)
        self.learned_transitions = None
        self.transition_counts = None
    
    def _build_transition_matrix(self):
        """
        Build transition probability matrix based on E8 geometry.
        
        Adjacent roots (smaller angular distance) have higher probability.
        """
        n_roots = len(self.roots)
        
        # Compute pairwise angular similarities
        # Using dot product as similarity measure
        self.similarities = np.dot(self.roots, self.roots.T)
        
        # Normalize to probabilities per row
        # Higher similarity = higher probability
        self.transitions = np.zeros((n_roots, n_roots))
        
        for i in range(n_roots):
            # Softmax-like normalization
            sims = self.similarities[i]
            sims = sims - sims.max()  # Numerical stability
            exp_sims = np.exp(sims * 2)  # Temperature = 0.5
            self.transitions[i] = exp_sims / exp_sims.sum()
    
    def learn_from_sequence(self, root_sequence: List[int], learning_rate: float = 0.1):
        """
        Learn transition probabilities from a root sequence.
        
        THE PHYSICS:
        The E8 lattice provides the prior (geometric similarity).
        The data provides the posterior (actual co-occurrence).
        We blend them using Bayesian updating.
        """
        n_roots = 240
        
        if self.transition_counts is None:
            # Initialize with geometric prior (pseudo-counts)
            self.transition_counts = self.transitions * 10 + 1e-6
        
        # Count actual transitions
        for i in range(len(root_sequence) - 1):
            from_root = root_sequence[i]
            to_root = root_sequence[i + 1]
            self.transition_counts[from_root, to_root] += 1
        
        # Normalize to get learned transitions
        self.learned_transitions = self.transition_counts / self.transition_counts.sum(axis=1, keepdims=True)
        self.use_learned = True
    
    def get_effective_transitions(self) -> np.ndarray:
        """Get the transition matrix to use (learned or geometric)."""
        if self.use_learned and self.learned_transitions is not None:
            return self.learned_transitions
        return self.transitions
    
    def predict_distribution(self, context_roots: List[int]) -> np.ndarray:
        """
        Predict probability distribution over next root given context.
        
        Args:
            context_roots: List of previous E8 root indices
        
        Returns:
            Probability distribution over 240 roots
        """
        n_roots = len(self.roots)
        
        if not context_roots:
            # No context - uniform distribution
            return np.ones(n_roots) / n_roots
        
        # Use learned or geometric transitions
        trans = self.get_effective_transitions()
        
        # Combine predictions from each context position
        # More recent positions have higher weight (golden ratio decay)
        combined = np.zeros(n_roots)
        total_weight = 0
        
        for i, root_idx in enumerate(reversed(context_roots[-self.context_size:])):
            weight = PHI_INV ** i  # Exponential decay
            combined += weight * trans[root_idx]
            total_weight += weight
        
        if total_weight > 0:
            combined /= total_weight
        
        return combined
    
    def get_predicted_root(self, context_roots: List[int]) -> int:
        """Get most likely next root."""
        probs = self.predict_distribution(context_roots)
        return int(np.argmax(probs))
    
    def get_rank(self, actual_root: int, context_roots: List[int]) -> int:
        """
        Get the rank of the actual root in the predicted distribution.
        
        Lower rank = better prediction = fewer bits needed.
        """
        probs = self.predict_distribution(context_roots)
        sorted_indices = np.argsort(probs)[::-1]  # Descending order
        
        for rank, idx in enumerate(sorted_indices):
            if idx == actual_root:
                return rank
        
        return len(probs) - 1  # Worst case


class DeltaPhiPacker:
    """
    Packs vocabulary entries using delta-phase encoding with prediction.
    
    Format per entry:
    1. If predicted correctly: 1 bit (flag)
    2. If not predicted: rank in distribution (gamma coded) + deltas
    
    THE PHYSICS:
    We're not storing the word; we're storing how much it deviates
    from the geometric prediction. Most deviations are small.
    """
    
    def __init__(self, config: Optional[DeltaPackConfig] = None):
        self.config = config or DeltaPackConfig()
        self.predictor = GeometricPredictor(self.config.context_size)
    
    def pack_entries(self, entries: List[LatticeEntry]) -> bytes:
        """
        Pack a sequence of lattice entries into a compressed bitstream.
        
        Args:
            entries: List of LatticeEntry objects (in sequence order)
        
        Returns:
            Compressed bytes
        """
        stream = BitStream()
        context_roots: List[int] = []
        
        for entry in entries:
            self._pack_single(entry, context_roots, stream)
            context_roots.append(entry.root_index)
            
            # Limit context size
            if len(context_roots) > self.config.context_size:
                context_roots.pop(0)
        
        return stream.to_bytes()
    
    def _pack_single(self, entry: LatticeEntry, context: List[int], stream: BitStream):
        """Pack a single entry using prediction."""
        if self.config.use_prediction and context:
            # Get prediction rank
            rank = self.predictor.get_rank(entry.root_index, context)
            
            if rank == 0:
                # Predicted correctly!
                stream.write_bit(1)  # Flag: prediction correct
            else:
                stream.write_bit(0)  # Flag: need to store deviation
                stream.write_gamma(rank)  # Store rank (variable length)
        else:
            # No prediction - store root index directly
            # 8 bits for 240 roots (fits in 8 bits)
            for i in range(8):
                stream.write_bit((entry.root_index >> i) & 1)
        
        # Pack delta phase (quantized)
        phase_quant = int((entry.delta_phase / (2 * np.pi)) * (2 ** self.config.phase_bits))
        phase_quant = min(phase_quant, (2 ** self.config.phase_bits) - 1)
        
        for i in range(self.config.phase_bits):
            stream.write_bit((phase_quant >> i) & 1)
        
        # Pack delta magnitude (quantized)
        mag_quant = int(entry.delta_magnitude * (2 ** self.config.mag_bits))
        mag_quant = min(mag_quant, (2 ** self.config.mag_bits) - 1)
        
        for i in range(self.config.mag_bits):
            stream.write_bit((mag_quant >> i) & 1)
    
    def unpack_entries(self, data: bytes, count: int) -> List[LatticeEntry]:
        """
        Unpack lattice entries from compressed bitstream.
        
        Args:
            data: Compressed bytes
            count: Number of entries to unpack
        
        Returns:
            List of LatticeEntry objects
        """
        stream = BitStream.from_bytes(data)
        context_roots: List[int] = []
        entries = []
        
        for _ in range(count):
            entry = self._unpack_single(context_roots, stream)
            entries.append(entry)
            context_roots.append(entry.root_index)
            
            if len(context_roots) > self.config.context_size:
                context_roots.pop(0)
        
        return entries
    
    def _unpack_single(self, context: List[int], stream: BitStream) -> LatticeEntry:
        """Unpack a single entry."""
        if self.config.use_prediction and context:
            prediction_correct = stream.read_bit() == 1
            
            if prediction_correct:
                root_index = self.predictor.get_predicted_root(context)
            else:
                rank = stream.read_gamma()
                # Get the root at this rank in the distribution
                probs = self.predictor.predict_distribution(context)
                sorted_indices = np.argsort(probs)[::-1]
                root_index = int(sorted_indices[rank])
        else:
            # Read root index directly
            root_index = 0
            for i in range(8):
                root_index |= (stream.read_bit() << i)
        
        # Read delta phase
        phase_quant = 0
        for i in range(self.config.phase_bits):
            phase_quant |= (stream.read_bit() << i)
        delta_phase = (phase_quant / (2 ** self.config.phase_bits)) * 2 * np.pi
        
        # Read delta magnitude
        mag_quant = 0
        for i in range(self.config.mag_bits):
            mag_quant |= (stream.read_bit() << i)
        delta_magnitude = mag_quant / (2 ** self.config.mag_bits)
        
        return LatticeEntry(
            root_index=root_index,
            delta_phase=delta_phase,
            delta_magnitude=delta_magnitude
        )
    
    def pack_root_sequence(self, root_indices: List[int]) -> bytes:
        """
        Pack just the root indices (without deltas) using prediction.
        
        This is useful when deltas are stored separately or not needed.
        """
        stream = BitStream()
        context: List[int] = []
        
        for root_idx in root_indices:
            if self.config.use_prediction and context:
                rank = self.predictor.get_rank(root_idx, context)
                
                if rank == 0:
                    stream.write_bit(1)
                else:
                    stream.write_bit(0)
                    stream.write_gamma(rank)
            else:
                for i in range(8):
                    stream.write_bit((root_idx >> i) & 1)
            
            context.append(root_idx)
            if len(context) > self.config.context_size:
                context.pop(0)
        
        return stream.to_bytes()
    
    def unpack_root_sequence(self, data: bytes, count: int) -> List[int]:
        """Unpack root indices from compressed bitstream."""
        stream = BitStream.from_bytes(data)
        context: List[int] = []
        roots = []
        
        for _ in range(count):
            if self.config.use_prediction and context:
                prediction_correct = stream.read_bit() == 1
                
                if prediction_correct:
                    root_idx = self.predictor.get_predicted_root(context)
                else:
                    rank = stream.read_gamma()
                    probs = self.predictor.predict_distribution(context)
                    sorted_indices = np.argsort(probs)[::-1]
                    root_idx = int(sorted_indices[rank])
            else:
                root_idx = 0
                for i in range(8):
                    root_idx |= (stream.read_bit() << i)
            
            roots.append(root_idx)
            context.append(root_idx)
            
            if len(context) > self.config.context_size:
                context.pop(0)
        
        return roots


def run_verification():
    """Verify the delta-phi packer functionality."""
    print("=" * 60)
    print("DELTA-PHI PACKER VERIFICATION")
    print("=" * 60)
    
    # Test 1: Geometric predictor
    print("\n--- Test 1: Geometric Predictor ---")
    predictor = GeometricPredictor(context_size=3)
    
    # Check transition matrix
    print(f"  Transition matrix shape: {predictor.transitions.shape}")
    print(f"  Row sums (should be 1): {predictor.transitions.sum(axis=1)[:5]}")
    
    # Test prediction with context
    context = [0, 1, 2]  # First 3 roots
    predicted = predictor.get_predicted_root(context)
    probs = predictor.predict_distribution(context)
    print(f"  Context roots: {context}")
    print(f"  Predicted next: {predicted}")
    print(f"  Top 5 probabilities: {np.sort(probs)[-5:][::-1]}")
    
    # Test 2: Entry packing with prediction
    print("\n--- Test 2: Entry Packing with Prediction ---")
    config = DeltaPackConfig(phase_bits=4, mag_bits=4, use_prediction=True)
    packer = DeltaPhiPacker(config)
    
    # Create test entries (simulating vocabulary)
    np.random.seed(42)
    test_entries = [
        LatticeEntry(root_index=np.random.randint(240), 
                    delta_phase=np.random.uniform(0, 2*np.pi),
                    delta_magnitude=np.random.uniform(0, 0.5))
        for _ in range(100)
    ]
    
    # Pack
    packed = packer.pack_entries(test_entries)
    print(f"  Entries: {len(test_entries)}")
    print(f"  Packed size: {len(packed)} bytes")
    
    # Compare to unpredicted (8 bits per root + 8 bits deltas = 16 bits = 2 bytes per entry)
    unpredicted_size = len(test_entries) * 2
    print(f"  Unpredicted size would be: {unpredicted_size} bytes")
    print(f"  Savings: {(1 - len(packed)/unpredicted_size)*100:.1f}%")
    
    # Unpack and verify
    unpacked = packer.unpack_entries(packed, len(test_entries))
    
    # Check root indices match
    roots_match = all(e1.root_index == e2.root_index 
                     for e1, e2 in zip(test_entries, unpacked))
    print(f"  Root indices match: {roots_match}")
    
    # Test 3: Root sequence packing
    print("\n--- Test 3: Root Sequence Packing ---")
    
    # Simulate coherent text (roots tend to be geometrically related)
    # Generate a sequence where adjacent roots are similar
    coherent_roots = [0]
    for _ in range(99):
        prev = coherent_roots[-1]
        # Pick a root that's similar to previous (high transition probability)
        probs = predictor.transitions[prev]
        next_root = np.random.choice(240, p=probs)
        coherent_roots.append(next_root)
    
    # Pack coherent sequence
    packed_coherent = packer.pack_root_sequence(coherent_roots)
    print(f"  Coherent sequence (100 roots)")
    print(f"  Packed size: {len(packed_coherent)} bytes")
    
    # Pack random sequence for comparison
    random_roots = list(np.random.randint(0, 240, 100))
    packed_random = packer.pack_root_sequence(random_roots)
    print(f"  Random sequence packed: {len(packed_random)} bytes")
    
    print(f"  Coherent vs Random: {len(packed_coherent)} vs {len(packed_random)}")
    print(f"  Coherent is {(1 - len(packed_coherent)/len(packed_random))*100:.1f}% smaller")
    
    # Verify round-trip
    unpacked_coherent = packer.unpack_root_sequence(packed_coherent, len(coherent_roots))
    unpacked_random = packer.unpack_root_sequence(packed_random, len(random_roots))
    
    print(f"  Coherent round-trip: {'PASS' if coherent_roots == unpacked_coherent else 'FAIL'}")
    print(f"  Random round-trip: {'PASS' if random_roots == unpacked_random else 'FAIL'}")
    
    # Test 4: Prediction accuracy on text-like patterns
    print("\n--- Test 4: Text-Like Pattern Prediction ---")
    
    # Simulate Subject-Verb-Object pattern
    # Assign geometric "roles" to certain root regions
    subject_roots = list(range(0, 40))    # Roots 0-39 are "subjects"
    verb_roots = list(range(40, 80))      # Roots 40-79 are "verbs"
    object_roots = list(range(80, 120))   # Roots 80-119 are "objects"
    
    # Generate S-V-O pattern
    svo_sequence = []
    for _ in range(33):  # 33 sentences
        svo_sequence.append(np.random.choice(subject_roots))
        svo_sequence.append(np.random.choice(verb_roots))
        svo_sequence.append(np.random.choice(object_roots))
    
    packed_svo = packer.pack_root_sequence(svo_sequence)
    print(f"  S-V-O pattern (99 roots)")
    print(f"  Packed size: {len(packed_svo)} bytes")
    
    unpacked_svo = packer.unpack_root_sequence(packed_svo, len(svo_sequence))
    print(f"  Round-trip: {'PASS' if svo_sequence == unpacked_svo else 'FAIL'}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
