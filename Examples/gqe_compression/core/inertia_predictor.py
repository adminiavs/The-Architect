#!/usr/bin/env python3
"""
Inertia Predictor - The Expected Next Rotation

THE PHYSICS:
"The crystal has momentum. It tends to continue spinning
in the same direction unless perturbed."

This module predicts the next E8 root based on context.
When the prediction is correct, we store NOTHING (0 bits).
When wrong, we store only the PREDICTION ERROR.

Key Concepts:
- Inertia: Tendency to continue in same direction
- Context Window: Recent roots influence prediction
- Error Quantization: Small errors = few bits

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict

try:
    from .phi_adic import PHI, PHI_INV
except ImportError:
    from phi_adic import PHI, PHI_INV


@dataclass
class PredictionResult:
    """Result of a prediction."""
    predicted_root: int
    actual_root: int
    error: int  # Signed error in [-120, 119]
    confidence: float  # 0-1
    
    @property
    def is_correct(self) -> bool:
        return self.error == 0


class InertiaPredictor:
    """
    Predicts the next E8 root based on geometric momentum.
    
    THE PHYSICS:
    The predictor learns the "inertia" of the crystal - its tendency
    to rotate in predictable patterns. Language has structure;
    after "the" often comes an adjective or noun.
    
    Encoding Strategy:
    - Correct prediction: 1 bit (flag only)
    - Small error (1-3): 4 bits
    - Medium error (4-15): 7 bits  
    - Large error (16-119): 11 bits
    """
    
    def __init__(self, num_roots: int = 240, context_size: int = 3):
        self.num_roots = num_roots
        self.context_size = context_size
        
        # Transition statistics: context -> next root counts
        self._transitions: Dict[Tuple, np.ndarray] = {}
        
        # Simple bigram model for fast prediction
        self._bigram_counts = np.ones((num_roots, num_roots), dtype=np.float32)
        
        # Momentum tracking
        self._last_velocity = 0  # Last observed displacement
        self._velocity_weight = 0.3  # How much to trust momentum
        
        # Statistics
        self._total_predictions = 0
        self._correct_predictions = 0
    
    def _get_context_key(self, context: List[int]) -> Tuple:
        """Convert context to hashable key."""
        return tuple(context[-self.context_size:])
    
    def update(self, context: List[int], actual_root: int):
        """
        Update the predictor with an observed transition.
        
        THE PHYSICS:
        The crystal learns from experience. Each observation
        strengthens certain rotation paths.
        """
        if len(context) >= 1:
            # Update bigram
            prev_root = context[-1]
            self._bigram_counts[prev_root, actual_root] += 1
            
            # Update velocity
            self._last_velocity = (actual_root - prev_root + 120) % 240 - 120
        
        # Update n-gram if we have enough context
        if len(context) >= self.context_size:
            key = self._get_context_key(context)
            if key not in self._transitions:
                self._transitions[key] = np.ones(self.num_roots, dtype=np.float32)
            self._transitions[key][actual_root] += 1
    
    def predict(self, context: List[int]) -> Tuple[int, float]:
        """
        Predict the next root given context.
        
        Returns (predicted_root, confidence).
        
        THE PHYSICS:
        Combine multiple prediction signals:
        1. N-gram model (learned patterns)
        2. Bigram model (immediate context)
        3. Momentum (continue current velocity)
        """
        if not context:
            # No context: predict most common root
            return (0, 0.0)
        
        prev_root = context[-1]
        
        # Start with bigram probabilities
        probs = self._bigram_counts[prev_root].copy()
        
        # Add n-gram if available
        if len(context) >= self.context_size:
            key = self._get_context_key(context)
            if key in self._transitions:
                probs *= self._transitions[key]
        
        # Add momentum prediction
        momentum_pred = (prev_root + self._last_velocity) % self.num_roots
        probs[momentum_pred] += probs.sum() * self._velocity_weight
        
        # Normalize
        probs /= probs.sum()
        
        # Return highest probability root
        predicted = int(np.argmax(probs))
        confidence = float(probs[predicted])
        
        return (predicted, confidence)
    
    def predict_and_encode(self, context: List[int], actual_root: int) -> PredictionResult:
        """
        Predict, compare with actual, and compute error.
        
        THE PHYSICS:
        The prediction error is the "surprise" - how much
        the crystal deviated from its expected path.
        """
        predicted, confidence = self.predict(context)
        
        # Compute signed error (centered around 0)
        error = (actual_root - predicted + 120) % 240 - 120
        
        # Update statistics
        self._total_predictions += 1
        if error == 0:
            self._correct_predictions += 1
        
        # Update model
        self.update(context, actual_root)
        
        return PredictionResult(
            predicted_root=predicted,
            actual_root=actual_root,
            error=error,
            confidence=confidence
        )
    
    def decode(self, context: List[int], error: int) -> int:
        """
        Decode actual root from prediction error.
        
        THE PHYSICS:
        Given the error, reconstruct what actually happened.
        """
        predicted, _ = self.predict(context)
        actual = (predicted + error) % self.num_roots
        
        # Update model
        self.update(context, actual)
        
        return actual
    
    def encode_error(self, error: int) -> List[int]:
        """
        Encode prediction error to bits.
        
        Bit allocation:
        - 0 error: 1 bit (1)
        - 1-3 error: 4 bits (01 + sign + 2-bit value)
        - 4-15 error: 7 bits (001 + sign + 4-bit value)
        - 16-119 error: 11 bits (000 + sign + 7-bit value)
        """
        bits = []
        abs_error = abs(error)
        sign = 0 if error >= 0 else 1
        
        if abs_error == 0:
            bits.append(1)
        elif abs_error <= 3:
            bits.extend([0, 1, sign])
            bits.extend([(abs_error >> i) & 1 for i in range(2)])
        elif abs_error <= 15:
            bits.extend([0, 0, 1, sign])
            bits.extend([(abs_error >> i) & 1 for i in range(4)])
        else:
            bits.extend([0, 0, 0, sign])
            bits.extend([(abs_error >> i) & 1 for i in range(7)])
        
        return bits
    
    def decode_error_bits(self, bits: List[int], pos: int) -> Tuple[int, int]:
        """
        Decode error from bit stream.
        
        Returns (error, new_position).
        """
        if bits[pos] == 1:
            return (0, pos + 1)
        elif bits[pos + 1] == 1:
            sign = bits[pos + 2]
            abs_error = sum(bits[pos + 3 + i] << i for i in range(2))
            error = -abs_error if sign else abs_error
            return (error, pos + 5)
        elif bits[pos + 2] == 1:
            sign = bits[pos + 3]
            abs_error = sum(bits[pos + 4 + i] << i for i in range(4))
            error = -abs_error if sign else abs_error
            return (error, pos + 8)
        else:
            sign = bits[pos + 3]
            abs_error = sum(bits[pos + 4 + i] << i for i in range(7))
            error = -abs_error if sign else abs_error
            return (error, pos + 11)
    
    def get_stats(self) -> Dict:
        """Get predictor statistics."""
        accuracy = (self._correct_predictions / self._total_predictions 
                   if self._total_predictions > 0 else 0)
        return {
            'total_predictions': self._total_predictions,
            'correct_predictions': self._correct_predictions,
            'accuracy': accuracy,
            'context_patterns': len(self._transitions),
        }
    
    def reset(self):
        """Reset predictor state (but keep learned transitions)."""
        self._last_velocity = 0
        self._total_predictions = 0
        self._correct_predictions = 0


class FastInertiaPredictor:
    """
    Optimized predictor using vectorized operations.
    
    THE PHYSICS:
    Same prediction logic, but processes entire sequences at once.
    """
    
    def __init__(self, num_roots: int = 240):
        self.num_roots = num_roots
        
        # Pre-compute transition matrix (learns during use)
        self._bigram = np.ones((num_roots, num_roots), dtype=np.float32)
        
    def learn_from_sequence(self, root_sequence: np.ndarray):
        """Learn transitions from a sequence (vectorized)."""
        if len(root_sequence) < 2:
            return
        
        # Count all transitions
        for i in range(len(root_sequence) - 1):
            self._bigram[root_sequence[i], root_sequence[i+1]] += 1
    
    def predict_sequence(self, root_sequence: np.ndarray) -> np.ndarray:
        """
        Predict next root for each position (vectorized).
        
        Returns array of predicted roots.
        """
        n = len(root_sequence)
        predictions = np.zeros(n, dtype=np.int32)
        
        # First element: no prediction (use 0)
        predictions[0] = 0
        
        # Rest: use bigram
        if n > 1:
            for i in range(1, n):
                prev = root_sequence[i-1]
                predictions[i] = np.argmax(self._bigram[prev])
        
        return predictions
    
    def compute_errors(self, root_sequence: np.ndarray) -> np.ndarray:
        """
        Compute prediction errors for entire sequence (vectorized).
        """
        predictions = self.predict_sequence(root_sequence)
        
        # Compute signed errors
        errors = ((root_sequence.astype(np.int32) - predictions + 120) % 240) - 120
        
        # First error is just the root itself (no prediction)
        errors[0] = root_sequence[0]
        
        return errors
    
    def encode_errors_fast(self, errors: np.ndarray) -> Tuple[bytes, int]:
        """
        Encode all errors to bitstream (fast batch processing).
        
        Returns (bytes, total_bits).
        """
        bits = []
        
        # First element: raw 8 bits
        first = int(errors[0])
        for j in range(8):
            bits.append((first >> j) & 1)
        
        # Rest: variable-length
        for error in errors[1:]:
            error = int(error)
            abs_error = abs(error)
            sign = 0 if error >= 0 else 1
            
            if abs_error == 0:
                bits.append(1)
            elif abs_error <= 3:
                bits.extend([0, 1, sign])
                bits.extend([(abs_error >> i) & 1 for i in range(2)])
            elif abs_error <= 15:
                bits.extend([0, 0, 1, sign])
                bits.extend([(abs_error >> i) & 1 for i in range(4)])
            else:
                bits.extend([0, 0, 0, sign])
                bits.extend([(abs_error >> i) & 1 for i in range(7)])
        
        # Pack to bytes
        result = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j, bit in enumerate(bits[i:i+8]):
                byte |= (bit << j)
            result.append(byte)
        
        return bytes(result), len(bits)
    
    def decode_errors_fast(self, data: bytes, count: int) -> np.ndarray:
        """Decode errors from bitstream."""
        # Unpack to bits
        bits = []
        for byte in data:
            for j in range(8):
                bits.append((byte >> j) & 1)
        
        errors = np.zeros(count, dtype=np.int32)
        pos = 0
        
        # First: raw 8 bits
        errors[0] = sum(bits[j] << j for j in range(8))
        pos = 8
        
        # Rest: variable-length
        for i in range(1, count):
            if bits[pos] == 1:
                errors[i] = 0
                pos += 1
            elif bits[pos + 1] == 1:
                sign = bits[pos + 2]
                abs_e = sum(bits[pos + 3 + j] << j for j in range(2))
                errors[i] = -abs_e if sign else abs_e
                pos += 5
            elif bits[pos + 2] == 1:
                sign = bits[pos + 3]
                abs_e = sum(bits[pos + 4 + j] << j for j in range(4))
                errors[i] = -abs_e if sign else abs_e
                pos += 8
            else:
                sign = bits[pos + 3]
                abs_e = sum(bits[pos + 4 + j] << j for j in range(7))
                errors[i] = -abs_e if sign else abs_e
                pos += 11
        
        return errors
    
    def reconstruct_sequence(self, errors: np.ndarray) -> np.ndarray:
        """Reconstruct root sequence from errors."""
        n = len(errors)
        roots = np.zeros(n, dtype=np.int32)
        
        # First element is stored directly
        roots[0] = errors[0]
        
        # Rest: predict + add error
        for i in range(1, n):
            predicted = np.argmax(self._bigram[roots[i-1]])
            roots[i] = (predicted + errors[i]) % self.num_roots
        
        return roots


def run_verification():
    """Verify the Inertia Predictor functionality."""
    import time
    
    print("=" * 60)
    print("INERTIA PREDICTOR VERIFICATION")
    print("=" * 60)
    
    # Test 1: Basic prediction
    print("\n--- Test 1: Basic Prediction ---")
    predictor = InertiaPredictor()
    
    # Simulate a pattern: 0 -> 1 -> 2 -> 0 -> 1 -> 2 ...
    pattern = [0, 1, 2] * 100
    context = []
    errors = []
    
    for root in pattern:
        if context:
            result = predictor.predict_and_encode(context, root)
            errors.append(result.error)
        context.append(root)
        if len(context) > 5:
            context.pop(0)
    
    stats = predictor.get_stats()
    print(f"  Pattern: [0, 1, 2] repeated")
    print(f"  Accuracy: {stats['accuracy']*100:.1f}%")
    print(f"  Zero-error rate: {sum(1 for e in errors if e == 0) / len(errors) * 100:.1f}%")
    
    # Test 2: Error encoding
    print("\n--- Test 2: Error Encoding ---")
    test_errors = [0, 1, -1, 5, -10, 50, -100]
    for error in test_errors:
        bits = predictor.encode_error(error)
        decoded, _ = predictor.decode_error_bits(bits, 0)
        match = "PASS" if decoded == error else "FAIL"
        print(f"  Error {error:4d}: {len(bits):2d} bits, decoded={decoded:4d} [{match}]")
    
    # Test 3: Fast predictor
    print("\n--- Test 3: Fast Predictor ---")
    fast_pred = FastInertiaPredictor()
    
    # Random sequence
    np.random.seed(42)
    random_roots = np.random.randint(0, 240, 10000, dtype=np.int32)
    
    # Learn from first half
    fast_pred.learn_from_sequence(random_roots[:5000])
    
    # Test on second half
    start = time.time()
    errors = fast_pred.compute_errors(random_roots[5000:])
    error_time = time.time() - start
    
    zero_rate = np.sum(errors[1:] == 0) / (len(errors) - 1)
    avg_abs_error = np.mean(np.abs(errors[1:]))
    
    print(f"  Time: {error_time*1000:.1f}ms for 5000 predictions")
    print(f"  Zero-error rate: {zero_rate*100:.1f}%")
    print(f"  Avg |error|: {avg_abs_error:.1f}")
    
    # Test 4: Encode/decode round-trip
    print("\n--- Test 4: Encode/Decode Round-Trip ---")
    start = time.time()
    encoded, total_bits = fast_pred.encode_errors_fast(errors)
    encode_time = time.time() - start
    
    start = time.time()
    decoded = fast_pred.decode_errors_fast(encoded, len(errors))
    decode_time = time.time() - start
    
    match = np.array_equal(errors, decoded)
    bits_per_error = total_bits / len(errors)
    
    print(f"  Encode time: {encode_time*1000:.1f}ms")
    print(f"  Decode time: {decode_time*1000:.1f}ms")
    print(f"  Bits per error: {bits_per_error:.2f}")
    print(f"  Round-trip: {'PASS' if match else 'FAIL'}")
    
    # Test 5: Sequence reconstruction
    print("\n--- Test 5: Sequence Reconstruction ---")
    # Use a fresh predictor for reconstruction
    fast_pred2 = FastInertiaPredictor()
    fast_pred2.learn_from_sequence(random_roots[:5000])
    
    original = random_roots[5000:]
    errors = fast_pred2.compute_errors(original)
    
    # Reset and reconstruct
    fast_pred3 = FastInertiaPredictor()
    fast_pred3.learn_from_sequence(random_roots[:5000])
    reconstructed = fast_pred3.reconstruct_sequence(errors)
    
    match = np.array_equal(original, reconstructed)
    print(f"  Reconstruction: {'PASS' if match else 'FAIL'}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
