#!/usr/bin/env python3
"""
Context Mixer - The N-Frame Predictor

THE PHYSICS:
"The current moment is the Integral of the last N frames."

This module implements PAQ-style context mixing to predict the next byte.
We combine predictions from multiple context lengths (1, 2, 4, 8 bytes)
to achieve extremely high prediction accuracy.

Key Concepts:
- Context Hashing: Hash the last N bytes to index prediction tables
- Probability Mixing: Combine predictions from multiple contexts
- Adaptive Learning: Update tables based on what actually appears

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import struct


@dataclass
class PredictionResult:
    """Result of context prediction."""
    predicted_byte: int
    probability: float  # Probability of predicted byte
    rank: int           # Rank of actual byte (0 = correct prediction)
    bits_needed: float  # Bits to encode the actual byte


class ContextModel:
    """
    Single-context prediction model.
    
    Uses a hash table to track byte frequencies given a context.
    """
    
    def __init__(self, context_size: int, table_bits: int = 16):
        self.context_size = context_size
        self.table_size = 1 << table_bits
        self.mask = self.table_size - 1
        
        # For each hash bucket: count[256] for each byte
        # Use sparse storage for memory efficiency
        self._counts: Dict[int, np.ndarray] = {}
        
        # Total count per bucket
        self._totals: Dict[int, int] = {}
    
    def _hash_context(self, context: bytes) -> int:
        """Hash the context bytes to a table index."""
        if len(context) < self.context_size:
            context = b'\x00' * (self.context_size - len(context)) + context
        
        # FNV-1a hash
        h = 2166136261
        for b in context[-self.context_size:]:
            h ^= b
            h = (h * 16777619) & 0xFFFFFFFF
        
        return h & self.mask
    
    def predict(self, context: bytes) -> np.ndarray:
        """
        Predict probability distribution for next byte.
        
        Returns array of 256 probabilities.
        """
        if self.context_size == 0:
            # Order-0: uniform distribution
            return np.ones(256) / 256
        
        h = self._hash_context(context)
        
        if h in self._counts:
            counts = self._counts[h].astype(np.float64)
            total = self._totals[h]
            # Laplace smoothing
            return (counts + 1) / (total + 256)
        else:
            # No data: uniform
            return np.ones(256) / 256
    
    def update(self, context: bytes, actual_byte: int):
        """Update the model with observed byte."""
        if self.context_size == 0:
            return
        
        h = self._hash_context(context)
        
        if h not in self._counts:
            self._counts[h] = np.zeros(256, dtype=np.uint16)
            self._totals[h] = 0
        
        # Increment count (with overflow protection)
        if self._counts[h][actual_byte] < 65535:
            self._counts[h][actual_byte] += 1
            self._totals[h] += 1
        else:
            # Rescale to prevent overflow
            self._counts[h] = (self._counts[h] // 2).astype(np.uint16)
            self._totals[h] = int(np.sum(self._counts[h]))
            self._counts[h][actual_byte] += 1
            self._totals[h] += 1
    
    def get_stats(self) -> Dict:
        """Get model statistics."""
        return {
            'context_size': self.context_size,
            'buckets_used': len(self._counts),
            'table_size': self.table_size,
        }


class ContextMixer:
    """
    PAQ-style context mixer combining multiple prediction models.
    
    THE PHYSICS:
    The crystal looks at the last 1, 2, 4, and 8 bytes.
    Each view gives a probability distribution.
    We mix these distributions to get the best prediction.
    
    The mixing weights are learned adaptively.
    """
    
    # Context sizes to use
    CONTEXT_SIZES = [0, 1, 2, 4, 8]
    
    def __init__(self, table_bits: int = 18):
        # Create a model for each context size
        self.models = [ContextModel(size, table_bits) for size in self.CONTEXT_SIZES]
        
        # Mixing weights (learned adaptively)
        self.weights = np.ones(len(self.CONTEXT_SIZES)) / len(self.CONTEXT_SIZES)
        
        # Learning rate for weight updates
        self.learning_rate = 0.01
        
        # Statistics
        self._total_predictions = 0
        self._correct_predictions = 0
        self._total_bits = 0.0
    
    def predict(self, context: bytes) -> np.ndarray:
        """
        Get mixed probability distribution for next byte.
        
        Returns array of 256 probabilities (sum to 1).
        """
        # Get prediction from each model
        predictions = np.zeros((len(self.models), 256))
        for i, model in enumerate(self.models):
            predictions[i] = model.predict(context)
        
        # Weighted combination
        mixed = np.zeros(256)
        for i, w in enumerate(self.weights):
            mixed += w * predictions[i]
        
        # Normalize
        mixed /= mixed.sum()
        
        return mixed
    
    def predict_byte(self, context: bytes) -> Tuple[int, float]:
        """
        Predict the most likely next byte.
        
        Returns (predicted_byte, probability).
        """
        probs = self.predict(context)
        predicted = int(np.argmax(probs))
        return predicted, float(probs[predicted])
    
    def update(self, context: bytes, actual_byte: int):
        """
        Update all models and mixing weights.
        
        THE PHYSICS:
        The crystal learns from what actually happened.
        Models that predicted well get higher weights.
        """
        # Get predictions before updating
        predictions = np.zeros((len(self.models), 256))
        for i, model in enumerate(self.models):
            predictions[i] = model.predict(context)
        
        # Mixed prediction
        mixed = np.zeros(256)
        for i, w in enumerate(self.weights):
            mixed += w * predictions[i]
        mixed /= mixed.sum()
        
        # Compute bits needed (negative log probability)
        prob = max(mixed[actual_byte], 1e-10)
        bits = -np.log2(prob)
        
        # Update statistics
        self._total_predictions += 1
        self._total_bits += bits
        if np.argmax(mixed) == actual_byte:
            self._correct_predictions += 1
        
        # Update mixing weights based on individual model performance
        for i, model in enumerate(self.models):
            model_prob = predictions[i, actual_byte]
            # Reward models that assigned high probability to actual
            self.weights[i] *= (1 + self.learning_rate * (model_prob - mixed[actual_byte]))
        
        # Normalize weights
        self.weights = np.clip(self.weights, 0.01, 10)
        self.weights /= self.weights.sum()
        
        # Update all models
        for model in self.models:
            model.update(context, actual_byte)
    
    def encode_byte(self, context: bytes, actual_byte: int) -> Tuple[int, int]:
        """
        Encode a byte given context.
        
        Returns (rank, bits_needed) where:
        - rank: Position of actual byte in sorted probability order (0 = most likely)
        - bits_needed: Theoretical bits to encode this byte
        
        THE PHYSICS:
        We encode the "surprise" - how unexpected this byte was.
        """
        probs = self.predict(context)
        
        # Sort by probability (descending)
        sorted_indices = np.argsort(probs)[::-1]
        rank = int(np.where(sorted_indices == actual_byte)[0][0])
        
        # Bits needed
        prob = max(probs[actual_byte], 1e-10)
        bits = -np.log2(prob)
        
        # Update model
        self.update(context, actual_byte)
        
        return rank, bits
    
    def decode_byte(self, context: bytes, rank: int) -> int:
        """
        Decode a byte from its rank.
        """
        probs = self.predict(context)
        sorted_indices = np.argsort(probs)[::-1]
        actual = int(sorted_indices[rank])
        
        # Update model
        self.update(context, actual)
        
        return actual
    
    def get_stats(self) -> Dict:
        """Get mixer statistics."""
        accuracy = (self._correct_predictions / self._total_predictions 
                   if self._total_predictions > 0 else 0)
        avg_bits = (self._total_bits / self._total_predictions 
                   if self._total_predictions > 0 else 8)
        
        return {
            'total_predictions': self._total_predictions,
            'accuracy': accuracy,
            'avg_bits_per_byte': avg_bits,
            'weights': self.weights.tolist(),
            'model_stats': [m.get_stats() for m in self.models],
        }
    
    def reset_stats(self):
        """Reset statistics but keep learned weights."""
        self._total_predictions = 0
        self._correct_predictions = 0
        self._total_bits = 0.0


class GeometricParallelMixer:
    """
    Geometric Parallelism Context Mixer.
    
    THE PHYSICS:
    In the 4D projection, we only care about the "Pixel" the vector falls into.
    High-precision floats are "Vacuum Energy" that we don't need to store.
    
    Key optimizations:
    1. Vectorized Hash Map: Calculate 1, 2, 4, 8-byte context hashes for entire frame at once
    2. 8-bit Integer Quantization: Probability weights binned to uint8 (256 levels)
    
    The crystal processes the entire 233KB frame as a single geometric operation.
    """
    
    # Context sizes: The N-Frame windows
    CONTEXT_SIZES = np.array([1, 2, 4, 8], dtype=np.int32)
    
    # FNV-1a constants
    FNV_OFFSET = np.uint64(2166136261)
    FNV_PRIME = np.uint64(16777619)
    
    def __init__(self, table_bits: int = 18):
        self.table_bits = table_bits
        self.table_size = 1 << table_bits
        self.mask = np.uint32(self.table_size - 1)
        
        # Quantized probability tables: hash -> uint8[256]
        # 8-bit quantization: 0-255 maps to probability 0.0-1.0
        self._qtables: Dict[int, np.ndarray] = {}
        
        # Mixing weights: 8-bit quantized (sum to 256)
        self._qweights = np.array([64, 64, 64, 64], dtype=np.uint8)  # Equal weights
        
        # Pre-compute FNV prime powers for vectorized hashing
        self._prime_powers = np.array([
            self.FNV_PRIME ** i for i in range(9)
        ], dtype=np.uint64)
    
    def _vectorized_multi_hash(self, data: bytes) -> Dict[int, np.ndarray]:
        """
        Vectorized context hashing for ALL context sizes at once.
        
        THE PHYSICS:
        The last 1, 2, 4, and 8 bytes form N-Frame windows.
        We compute hashes for the ENTIRE frame in parallel.
        
        Returns dict: context_size -> array of hashes for each position.
        """
        n = len(data)
        data_arr = np.frombuffer(data, dtype=np.uint8).astype(np.uint64)
        
        result = {}
        
        for ctx_size in self.CONTEXT_SIZES:
            # Create sliding window views
            hashes = np.full(n, self.FNV_OFFSET, dtype=np.uint64)
            
            # Vectorized FNV-1a: process all positions in parallel
            for offset in range(ctx_size):
                # Positions where we have enough context
                valid_start = offset + 1
                if valid_start > n:
                    continue
                
                # Shift to get the context byte at this offset from current position
                # For position i, context byte is at i - ctx_size + offset
                context_indices = np.arange(valid_start - 1, n - ctx_size + offset + 1)
                target_indices = np.arange(ctx_size - offset, n)
                
                if len(context_indices) > 0 and len(target_indices) > 0:
                    min_len = min(len(context_indices), len(target_indices))
                    context_indices = context_indices[:min_len]
                    target_indices = target_indices[:min_len]
                    
                    # XOR step
                    hashes[target_indices] ^= data_arr[context_indices]
                    # Multiply step (vectorized)
                    hashes[target_indices] = (hashes[target_indices] * self.FNV_PRIME) & 0xFFFFFFFF
            
            # Apply mask
            result[int(ctx_size)] = (hashes & self.mask).astype(np.uint32)
        
        return result
    
    def _quantize_probability(self, prob: float) -> np.uint8:
        """
        Quantize probability to 8-bit integer.
        
        THE PHYSICS:
        We only care about the "Pixel" - 256 probability buckets.
        """
        return np.uint8(min(255, max(0, int(prob * 255))))
    
    def _dequantize_probability(self, qprob: np.uint8) -> float:
        """Dequantize 8-bit probability back to float."""
        return float(qprob) / 255.0
    
    def train_vectorized(self, data: bytes):
        """
        Train on entire frame using Geometric Parallelism.
        
        THE PHYSICS:
        The entire 233KB frame is processed as a single operation.
        Byte frequencies are accumulated into 8-bit quantized tables.
        """
        n = len(data)
        data_arr = np.frombuffer(data, dtype=np.uint8)
        
        # Compute ALL hashes for ALL context sizes at once
        all_hashes = self._vectorized_multi_hash(data)
        
        # Accumulate frequencies using numpy bincount for speed
        temp_tables: Dict[int, np.ndarray] = {}
        
        for ctx_size, hashes in all_hashes.items():
            # Get valid range (positions with enough context)
            valid_hashes = hashes[ctx_size:]
            valid_bytes = data_arr[ctx_size:]
            
            # Find unique hashes and accumulate counts
            unique_hashes = np.unique(valid_hashes)
            
            for h in unique_hashes:
                h = int(h)
                mask = valid_hashes == h
                byte_vals = valid_bytes[mask]
                
                if h not in temp_tables:
                    temp_tables[h] = np.zeros(256, dtype=np.uint32)
                
                # Vectorized counting with bincount
                counts = np.bincount(byte_vals, minlength=256)
                temp_tables[h] += counts.astype(np.uint32)
        
        # Quantize to 8-bit probabilities
        for h, counts in temp_tables.items():
            total = counts.sum()
            if total > 0:
                # Laplace smoothing + quantization
                probs = (counts + 1) / (total + 256)
                # Quantize to 8-bit (0-255)
                self._qtables[h] = (probs * 255).astype(np.uint8)
    
    def predict_vectorized(self, data: bytes) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict all bytes using Geometric Parallelism.
        
        THE PHYSICS:
        All predictions computed in parallel across the entire frame.
        Mixed probabilities use 8-bit integer arithmetic.
        
        Returns:
            ranks: uint8 array of prediction ranks
            qprobs: uint8 array of quantized probabilities for actual bytes
        """
        n = len(data)
        data_arr = np.frombuffer(data, dtype=np.uint8)
        
        # Compute all hashes once
        all_hashes = self._vectorized_multi_hash(data)
        
        # Build dense probability matrix for all positions: shape (n, 256)
        # Use uint16 for mixing accumulation
        mixed_probs = np.zeros((n, 256), dtype=np.uint16)
        
        # Uniform distribution as uint8 (scaled by 255)
        uniform = np.ones(256, dtype=np.uint8)  # Equal probability for all bytes
        
        for ctx_idx, ctx_size in enumerate(self.CONTEXT_SIZES):
            ctx_size = int(ctx_size)
            weight = self._qweights[ctx_idx]
            hashes = all_hashes[ctx_size]
            
            # Positions with enough context
            for i in range(n):
                if i < ctx_size:
                    # Not enough context - add uniform weighted contribution
                    mixed_probs[i] += weight
                else:
                    h = int(hashes[i])
                    if h in self._qtables:
                        # Add weighted quantized probability
                        mixed_probs[i] += (self._qtables[h].astype(np.uint16) * weight) >> 8
                    else:
                        mixed_probs[i] += weight
        
        # Fast batch rank calculation using vectorized operations
        ranks = np.zeros(n, dtype=np.uint8)
        qprobs = np.zeros(n, dtype=np.uint8)
        
        # Normalize and compute ranks in batches
        totals = mixed_probs.sum(axis=1, keepdims=True)
        totals = np.maximum(totals, 1)  # Avoid division by zero
        
        # Get probability for actual bytes (vectorized)
        actual_probs = mixed_probs[np.arange(n), data_arr]
        qprobs = ((actual_probs * 255) // totals.flatten()).astype(np.uint8)
        
        # Compute ranks: count of bytes with higher probability than actual
        # Vectorized comparison: for each position, count how many probs > actual_prob
        for i in range(n):
            ranks[i] = min(255, np.sum(mixed_probs[i] > actual_probs[i]))
        
        return ranks, qprobs
    
    def predict_batch_fast(self, data: bytes) -> Tuple[np.ndarray, np.ndarray]:
        """
        Ultra-fast batch prediction using precomputed lookup.
        
        THE PHYSICS:
        The 4D projection collapses to pixel coordinates.
        We precompute the probability matrix and vectorize all rank calculations.
        """
        n = len(data)
        data_arr = np.frombuffer(data, dtype=np.uint8)
        
        # Compute all hashes
        all_hashes = self._vectorized_multi_hash(data)
        
        # Convert qtables to dense array for vectorized lookup
        # Find all unique hashes across all context sizes
        unique_hashes = set()
        for hashes in all_hashes.values():
            unique_hashes.update(hashes.tolist())
        
        # Create hash-to-index mapping for dense storage
        hash_to_idx = {h: i for i, h in enumerate(unique_hashes)}
        num_hashes = len(unique_hashes)
        
        # Build dense probability array: (num_hashes, 256)
        dense_probs = np.ones((num_hashes, 256), dtype=np.uint8)  # Default uniform
        for h, idx in hash_to_idx.items():
            if h in self._qtables:
                dense_probs[idx] = self._qtables[h]
        
        # Build index arrays for each context size
        idx_arrays = {}
        for ctx_size in self.CONTEXT_SIZES:
            ctx_size = int(ctx_size)
            hashes = all_hashes[ctx_size]
            idx_arrays[ctx_size] = np.array([hash_to_idx[int(h)] for h in hashes])
        
        # Compute mixed probabilities using advanced indexing
        mixed_probs = np.zeros((n, 256), dtype=np.uint32)
        
        for ctx_idx, ctx_size in enumerate(self.CONTEXT_SIZES):
            ctx_size = int(ctx_size)
            weight = int(self._qweights[ctx_idx])
            indices = idx_arrays[ctx_size]
            
            # Lookup and weight - vectorized across all positions
            # Shape: (n, 256)
            probs = dense_probs[indices].astype(np.uint32)
            
            # Apply context validity mask
            validity = np.arange(n) >= ctx_size
            probs[~validity] = 1  # Uniform for positions without enough context
            
            mixed_probs += probs * weight
        
        # Normalize
        totals = mixed_probs.sum(axis=1, keepdims=True)
        totals = np.maximum(totals, 1)
        
        # Get actual byte probabilities
        actual_probs = mixed_probs[np.arange(n), data_arr]
        qprobs = ((actual_probs * 255) // totals.flatten()).astype(np.uint8)
        
        # Vectorized rank calculation
        # ranks[i] = number of bytes with probability > actual_probs[i]
        # Broadcast comparison: (n, 256) > (n, 1)
        ranks = (mixed_probs > actual_probs[:, np.newaxis]).sum(axis=1).astype(np.uint8)
        
        return ranks, qprobs
    
    def get_compression_stats(self, data: bytes, use_fast: bool = True) -> Dict:
        """Get compression statistics using quantized predictions."""
        if use_fast:
            ranks, qprobs = self.predict_batch_fast(data)
        else:
            ranks, qprobs = self.predict_vectorized(data)
        
        zero_ranks = np.sum(ranks == 0)
        avg_rank = np.mean(ranks)
        
        # Estimate bits from quantized probabilities
        # -log2(qprob/255) but avoid log(0)
        safe_qprobs = np.maximum(qprobs, 1)
        bits_per_byte = -np.log2(safe_qprobs.astype(np.float32) / 255)
        total_bits = np.sum(bits_per_byte)
        
        return {
            'total_bytes': len(data),
            'zero_rank_predictions': int(zero_ranks),
            'accuracy': float(zero_ranks) / len(data),
            'avg_rank': float(avg_rank),
            'theoretical_bits': float(total_bits),
            'bits_per_byte': float(total_bits) / len(data),
            'quantization_bits': 8,
            'context_sizes': self.CONTEXT_SIZES.tolist(),
            'table_entries': len(self._qtables),
        }


class FastContextMixer:
    """
    Optimized context mixer for batch processing.
    
    THE PHYSICS:
    Process entire files at once using vectorized operations.
    
    NOTE: For Geometric Parallelism, use GeometricParallelMixer instead.
    """
    
    def __init__(self, context_size: int = 8, table_bits: int = 20):
        self.context_size = context_size
        self.table_size = 1 << table_bits
        self.mask = self.table_size - 1
        
        # Prediction table: hash -> [byte frequencies]
        # Sparse storage
        self._table: Dict[int, np.ndarray] = {}
    
    def _hash_context(self, context: bytes) -> int:
        """Fast context hash."""
        h = 2166136261
        for b in context:
            h ^= b
            h = (h * 16777619) & 0xFFFFFFFF
        return h & self.mask
    
    def _vectorized_hash(self, data: bytes) -> np.ndarray:
        """
        Vectorized context hashing using rolling hash.
        
        THE PHYSICS:
        The context forms a "window" that slides across the data.
        We compute all hashes in parallel using NumPy.
        """
        n = len(data)
        hashes = np.zeros(n, dtype=np.uint32)
        
        # Pre-compute powers of the FNV multiplier
        mult = 16777619
        
        # For small context, use direct computation
        for i in range(n):
            start = max(0, i - self.context_size)
            h = 2166136261
            for j in range(start, i):
                h ^= data[j]
                h = (h * mult) & 0xFFFFFFFF
            hashes[i] = h & self.mask
        
        return hashes
    
    def train(self, data: bytes):
        """
        Train on data (first pass).
        
        Builds frequency tables for all contexts seen.
        """
        # Pre-compute all hashes
        hashes = self._vectorized_hash(data)
        data_arr = np.frombuffer(data, dtype=np.uint8)
        
        for i in range(len(data)):
            h = hashes[i]
            
            # Update table
            if h not in self._table:
                self._table[h] = np.zeros(256, dtype=np.uint32)
            
            self._table[h][data_arr[i]] += 1
    
    def predict_all(self, data: bytes) -> Tuple[np.ndarray, float]:
        """
        Predict all bytes in data (second pass).
        
        THE PHYSICS:
        The Integral of the last N frames determines the current moment.
        We compute all predictions using pre-cached hashes.
        
        Returns (ranks, total_bits) where:
        - ranks: Array of prediction ranks for each byte
        - total_bits: Total theoretical bits needed
        """
        n = len(data)
        ranks = np.zeros(n, dtype=np.uint8)
        total_bits = 0.0
        
        # Pre-compute all hashes
        hashes = self._vectorized_hash(data)
        data_arr = np.frombuffer(data, dtype=np.uint8)
        
        # Pre-allocate uniform probability for missing contexts
        uniform_probs = np.ones(256) / 256
        
        for i in range(n):
            h = hashes[i]
            
            actual_byte = data_arr[i]
            
            if h in self._table:
                counts = self._table[h]
                total = counts.sum()
                
                # Fast rank calculation: count bytes with higher probability
                actual_count = counts[actual_byte]
                rank = np.sum(counts > actual_count)
                
                # For ties, add fraction of equal counts that come before
                equal_mask = counts == actual_count
                if np.sum(equal_mask) > 1:
                    equal_indices = np.where(equal_mask)[0]
                    rank += np.searchsorted(equal_indices, actual_byte)
                
                ranks[i] = min(rank, 255)
                
                # Bits needed
                prob = (actual_count + 1) / (total + 256)
                total_bits -= np.log2(max(prob, 1e-10))
            else:
                # Uniform distribution - all ranks equally likely
                ranks[i] = actual_byte  # Default to byte value as "rank"
                total_bits += 8  # Full 8 bits needed
        
        return ranks, total_bits
    
    def encode_ranks(self, ranks: np.ndarray) -> bytes:
        """
        Encode ranks to bytes.
        
        Uses variable-length encoding:
        - Rank 0: 1 bit (1)
        - Rank 1-3: 4 bits (01XX)
        - Rank 4-19: 7 bits (001XXXX)
        - Rank 20-255: 10 bits (000XXXXXXXX)
        """
        bits = []
        
        for rank in ranks:
            if rank == 0:
                bits.append(1)
            elif rank < 4:
                bits.extend([0, 1])
                bits.extend([(rank >> j) & 1 for j in range(2)])
            elif rank < 20:
                bits.extend([0, 0, 1])
                bits.extend([(rank >> j) & 1 for j in range(4)])
            else:
                bits.extend([0, 0, 0])
                bits.extend([(rank >> j) & 1 for j in range(8)])
        
        # Pack to bytes
        result = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j, bit in enumerate(bits[i:i+8]):
                byte |= (bit << j)
            result.append(byte)
        
        return bytes(result), len(bits)
    
    def decode_ranks(self, data: bytes, count: int) -> np.ndarray:
        """Decode ranks from bytes."""
        bits = []
        for byte in data:
            for j in range(8):
                bits.append((byte >> j) & 1)
        
        ranks = np.zeros(count, dtype=np.uint8)
        pos = 0
        
        for i in range(count):
            if bits[pos] == 1:
                ranks[i] = 0
                pos += 1
            elif bits[pos + 1] == 1:
                ranks[i] = sum(bits[pos + 2 + j] << j for j in range(2))
                pos += 4
            elif bits[pos + 2] == 1:
                ranks[i] = sum(bits[pos + 3 + j] << j for j in range(4))
                pos += 7
            else:
                ranks[i] = sum(bits[pos + 3 + j] << j for j in range(8))
                pos += 11
        
        return ranks
    
    def reconstruct(self, ranks: np.ndarray, seed_context: bytes = b'') -> bytes:
        """
        Reconstruct original data from ranks.
        """
        result = bytearray(seed_context)
        
        for i, rank in enumerate(ranks):
            start = max(0, len(result) - self.context_size)
            context = bytes(result[start:])
            h = self._hash_context(context)
            
            if h in self._table:
                counts = self._table[h].astype(np.float64)
                total = counts.sum()
                probs = (counts + 1) / (total + 256)
            else:
                probs = np.ones(256) / 256
            
            sorted_indices = np.argsort(probs)[::-1]
            actual = sorted_indices[rank]
            result.append(actual)
        
        return bytes(result[len(seed_context):])


def run_verification():
    """Verify the Context Mixer functionality."""
    import time
    
    print("=" * 60)
    print("CONTEXT MIXER VERIFICATION")
    print("=" * 60)
    
    # Test 1: Basic prediction
    print("\n--- Test 1: Basic Prediction ---")
    mixer = ContextMixer(table_bits=16)
    
    # Train on pattern
    pattern = b"the quick brown fox " * 100
    for i in range(len(pattern) - 1):
        context = pattern[max(0, i-8):i]
        mixer.update(context, pattern[i])
    
    stats = mixer.get_stats()
    print(f"  Accuracy: {stats['accuracy']*100:.1f}%")
    print(f"  Avg bits/byte: {stats['avg_bits_per_byte']:.2f}")
    print(f"  Weights: {[f'{w:.2f}' for w in stats['weights']]}")
    
    # Test 2: Fast mixer training
    print("\n--- Test 2: Fast Mixer ---")
    fast_mixer = FastContextMixer(context_size=8)
    
    test_data = b"Hello World! " * 1000
    
    start = time.time()
    fast_mixer.train(test_data)
    train_time = time.time() - start
    print(f"  Train time: {train_time*1000:.1f}ms")
    
    start = time.time()
    ranks, total_bits = fast_mixer.predict_all(test_data)
    predict_time = time.time() - start
    print(f"  Predict time: {predict_time*1000:.1f}ms")
    
    zero_ranks = np.sum(ranks == 0)
    avg_rank = np.mean(ranks)
    print(f"  Zero-rank (correct prediction): {zero_ranks}/{len(ranks)} ({zero_ranks/len(ranks)*100:.1f}%)")
    print(f"  Average rank: {avg_rank:.2f}")
    print(f"  Theoretical bits: {total_bits:.0f} ({total_bits/len(test_data):.2f} bits/byte)")
    
    # Test 3: Rank encoding
    print("\n--- Test 3: Rank Encoding ---")
    encoded, total_bits_enc = fast_mixer.encode_ranks(ranks)
    print(f"  Encoded size: {len(encoded)} bytes")
    print(f"  Bits/rank: {total_bits_enc/len(ranks):.2f}")
    
    # Test 4: Round-trip
    print("\n--- Test 4: Round-Trip ---")
    decoded_ranks = fast_mixer.decode_ranks(encoded, len(ranks))
    reconstructed = fast_mixer.reconstruct(decoded_ranks)
    
    match = reconstructed == test_data
    print(f"  Reconstruction: {'PASS' if match else 'FAIL'}")
    
    # Test 5: Compression ratio
    print("\n--- Test 5: Compression Metrics ---")
    input_size = len(test_data)
    output_size = len(encoded)
    ratio = input_size / output_size if output_size > 0 else 0
    print(f"  Input: {input_size} bytes")
    print(f"  Output: {output_size} bytes")
    print(f"  Ratio: {ratio:.2f}:1")
    
    # Test 6: GEOMETRIC PARALLELISM
    print("\n" + "=" * 60)
    print("GEOMETRIC PARALLELISM VERIFICATION")
    print("=" * 60)
    
    print("\n--- Test 6: GeometricParallelMixer ---")
    gp_mixer = GeometricParallelMixer(table_bits=18)
    
    # Test with larger data (simulate 233KB frame concept)
    large_data = (b"The crystal processes the entire frame. " * 250 + 
                  b"Patterns emerge from the N-Frame windows. " * 250)
    
    print(f"  Test data size: {len(large_data):,} bytes")
    
    # Train
    start = time.time()
    gp_mixer.train_vectorized(large_data)
    train_time = time.time() - start
    print(f"  Vectorized train time: {train_time*1000:.1f}ms")
    print(f"  Table entries created: {len(gp_mixer._qtables):,}")
    
    # Predict with standard method
    start = time.time()
    gp_ranks, gp_qprobs = gp_mixer.predict_vectorized(large_data)
    predict_time = time.time() - start
    print(f"  Standard predict time: {predict_time*1000:.1f}ms")
    
    # Predict with FAST batch method
    start = time.time()
    fast_ranks, fast_qprobs = gp_mixer.predict_batch_fast(large_data)
    fast_predict_time = time.time() - start
    print(f"  FAST batch predict time: {fast_predict_time*1000:.1f}ms")
    speedup = predict_time / fast_predict_time if fast_predict_time > 0 else 0
    print(f"  Speedup: {speedup:.1f}x")
    
    # Verify both methods produce same results
    match = np.allclose(gp_ranks, fast_ranks)
    print(f"  Results match: {'PASS' if match else 'FAIL'}")
    
    # Stats (using fast method)
    stats = gp_mixer.get_compression_stats(large_data, use_fast=True)
    print(f"\n  Geometric Parallelism Results:")
    print(f"    Zero-rank accuracy: {stats['accuracy']*100:.1f}%")
    print(f"    Average rank: {stats['avg_rank']:.2f}")
    print(f"    Bits/byte: {stats['bits_per_byte']:.2f}")
    print(f"    Quantization: {stats['quantization_bits']}-bit")
    print(f"    Context sizes: {stats['context_sizes']}")
    
    # Test 7: 8-bit Quantization verification
    print("\n--- Test 7: 8-bit Quantization Physics ---")
    print("  THE PHYSICS: We only care about the 'Pixel' the vector falls into.")
    print("  High-precision floats are 'Vacuum Energy' we don't store.")
    print(f"  Probability buckets: 256 (uint8)")
    print(f"  Memory per table entry: 256 bytes (vs 2048 for float64)")
    print(f"  Memory savings: 8x reduction")
    
    # Verify quantization round-trip
    test_probs = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
    print("\n  Quantization round-trip:")
    for p in test_probs:
        q = gp_mixer._quantize_probability(p)
        p_back = gp_mixer._dequantize_probability(q)
        error = abs(p - p_back)
        print(f"    {p:.2f} -> {q:3d} -> {p_back:.3f} (error: {error:.4f})")
    
    # Test 8: Multi-context hash verification
    print("\n--- Test 8: Vectorized Multi-Hash ---")
    sample = b"ABCDEFGHIJKLMNOP"
    all_hashes = gp_mixer._vectorized_multi_hash(sample)
    print(f"  Sample: {sample.decode()}")
    for ctx_size, hashes in all_hashes.items():
        print(f"    {ctx_size}-byte context hashes: [{hashes[ctx_size]:5d}, {hashes[ctx_size+1]:5d}, {hashes[ctx_size+2]:5d}, ...]")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
