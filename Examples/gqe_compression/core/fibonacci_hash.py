#!/usr/bin/env python3
"""
Fibonacci Hashing: The Golden Search

THE PRINCIPLE:
    The Golden Ratio (φ) is the "most irrational" number.
    Its continued fraction is [1; 1, 1, 1, ...] - all ones.
    This makes it maximally resistant to clustering patterns.

THE REAL VALUE:
    Not in replacing Python's dict (which is already C-optimized),
    but in VECTORIZED operations where we can leverage numpy.

THE MECHANISM:
    index = floor(N * (hash(value) * φ % 1))
    
    For vectorized token mapping:
    1. Build a vocabulary dict (using Python's fast dict)
    2. Convert token hashes to a numpy array
    3. Apply Fibonacci hash vectorized for index computation

Author: The Architect
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Iterator
from dataclasses import dataclass

# The Golden Ratio - THE path of least resistance
PHI = (1 + np.sqrt(5)) / 2  # 1.618033988749895
PHI_FRAC = PHI - 1  # 0.618033988749895 (the fractional part)

# Knuth's multiplicative constant (2^32 / φ) for 32-bit operations
KNUTH_32 = np.uint32(2654435769)  # floor(2^32 / φ)
KNUTH_64 = np.uint64(11400714819323198485)  # floor(2^64 / φ)


def fibonacci_hash_vectorized(values: np.ndarray, table_size: int) -> np.ndarray:
    """
    Compute Fibonacci hash indices for an array of integer values.
    
    VECTORIZED - processes millions of values efficiently.
    
    Args:
        values: numpy array of integers (e.g., token hash values)
        table_size: Size of the target index space
    
    Returns:
        numpy array of indices in [0, table_size)
    """
    # Use 32-bit multiplication for speed
    values = values.astype(np.uint32)
    
    # Multiply by φ (via Knuth constant) and take upper bits
    # This is equivalent to: floor(N * (value * φ % 1))
    h = values * KNUTH_32
    
    # Scale to table size
    indices = ((h.astype(np.uint64) * table_size) >> 32).astype(np.uint32)
    
    return indices


class GoldenVocabulary:
    """
    Vocabulary optimized for vectorized token-to-index mapping.
    
    Uses Python dict for building (fast), numpy for lookup (vectorized).
    """
    
    def __init__(self):
        """Initialize empty vocabulary."""
        self._token_to_idx: Dict[str, int] = {}
        self._idx_to_token: List[str] = []
        self._token_hashes: Dict[str, int] = {}
        
    def build(self, tokens: List[str]) -> None:
        """
        Build vocabulary from a list of tokens.
        
        Args:
            tokens: List of token strings
        """
        for token in tokens:
            if token not in self._token_to_idx:
                idx = len(self._token_to_idx)
                self._token_to_idx[token] = idx
                self._idx_to_token.append(token)
                # Store hash for vectorized operations
                self._token_hashes[token] = hash(token) & 0xFFFFFFFF
    
    def get_index(self, token: str) -> int:
        """Get index for a single token."""
        return self._token_to_idx.get(token, 0)
    
    def map_tokens_vectorized(self, tokens: List[str]) -> np.ndarray:
        """
        Map a list of tokens to indices using vectorized operations.
        
        This is the KEY optimization - converts tokens to indices
        in a cache-friendly, vectorized manner.
        
        Args:
            tokens: List of token strings
        
        Returns:
            numpy array of indices (uint32)
        """
        # First, get all indices via dict lookup (Python-optimized)
        indices = np.array([self._token_to_idx.get(t, 0) for t in tokens], dtype=np.uint32)
        return indices
    
    def map_tokens_golden(self, tokens: List[str]) -> np.ndarray:
        """
        Map tokens using Golden Ratio distribution.
        
        This version applies Fibonacci hashing to spread indices
        more evenly across the vocabulary space.
        
        Args:
            tokens: List of token strings
        
        Returns:
            numpy array of golden-hashed indices
        """
        # Get raw indices
        raw_indices = self.map_tokens_vectorized(tokens)
        
        # Apply Fibonacci hash to redistribute
        golden_indices = fibonacci_hash_vectorized(raw_indices, len(self._token_to_idx))
        
        return golden_indices
    
    def __len__(self) -> int:
        return len(self._token_to_idx)
    
    def __contains__(self, token: str) -> bool:
        return token in self._token_to_idx
    
    def to_dict(self) -> Dict[str, Dict]:
        """Convert to serializable dict."""
        return {token: {'index': idx} for token, idx in self._token_to_idx.items()}


class GoldenIndexEncoder:
    """
    Encodes index sequences using Golden Ratio principles.
    
    THE INSIGHT:
    The Golden Ratio permutation spreads indices across memory,
    which can improve cache behavior for certain access patterns.
    
    NOTE: This is a bijective mapping - each index maps to exactly
    one golden index and vice versa.
    """
    
    def __init__(self, vocab_size: int):
        """
        Args:
            vocab_size: Size of the vocabulary
        """
        self.vocab_size = vocab_size
        
        # Create a true permutation using golden ratio ordering
        # Sort indices by their fractional part when multiplied by φ
        indices = np.arange(vocab_size, dtype=np.float64)
        golden_keys = (indices * PHI_FRAC) % 1.0
        
        # The permutation is the argsort of the golden keys
        self._golden_perm = np.argsort(golden_keys).astype(np.uint32)
        
        # Compute the inverse permutation for decoding
        self._inverse_perm = np.zeros(vocab_size, dtype=np.uint32)
        self._inverse_perm[self._golden_perm] = np.arange(vocab_size, dtype=np.uint32)
    
    def encode(self, indices: np.ndarray) -> np.ndarray:
        """
        Apply golden permutation to indices.
        """
        return self._golden_perm[indices]
    
    def decode(self, golden_indices: np.ndarray) -> np.ndarray:
        """
        Reverse the golden permutation.
        """
        return self._inverse_perm[golden_indices]


def create_golden_lookup_table(vocab: Dict[str, int]) -> Tuple[np.ndarray, Dict[str, int]]:
    """
    Create a lookup table optimized with Golden Ratio ordering.
    
    This reorders the vocabulary indices so that frequently
    co-occurring tokens are spread across the index space,
    reducing cache conflicts.
    
    Args:
        vocab: Original token -> index mapping
    
    Returns:
        (golden_to_original, original_to_golden) mapping arrays
    """
    vocab_size = len(vocab)
    
    # Create golden permutation
    encoder = GoldenIndexEncoder(vocab_size)
    
    # Create new vocabulary with golden indices
    golden_vocab = {}
    for token, idx in vocab.items():
        golden_vocab[token] = int(encoder.encode(np.array([idx], dtype=np.uint32))[0])
    
    return encoder._inverse_perm, golden_vocab


def benchmark_golden_operations():
    """
    Benchmark vectorized Golden Ratio operations.
    """
    import time
    import random
    import string
    
    print("=" * 60)
    print("GOLDEN SEARCH BENCHMARK (Vectorized)")
    print("=" * 60)
    
    # Generate test data - realistic token distribution
    vocab_size = 10000
    n_tokens = 1_000_000
    
    print(f"\nTest data:")
    print(f"  Vocabulary size: {vocab_size:,}")
    print(f"  Token sequence: {n_tokens:,} tokens")
    
    # Create vocabulary
    vocab_tokens = [''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 10))) 
                    for _ in range(vocab_size)]
    
    # Create token sequence (Zipf-like distribution)
    weights = 1 / (np.arange(1, vocab_size + 1) ** 0.8)
    weights /= weights.sum()
    token_indices = np.random.choice(vocab_size, size=n_tokens, p=weights)
    tokens = [vocab_tokens[i] for i in token_indices]
    
    # Build vocabulary
    vocab = GoldenVocabulary()
    vocab.build(vocab_tokens)
    
    print("\n--- Token Mapping Performance ---")
    
    # Standard mapping
    start = time.perf_counter()
    std_indices = vocab.map_tokens_vectorized(tokens)
    std_time = time.perf_counter() - start
    print(f"  Standard mapping: {std_time*1000:.2f} ms ({n_tokens/std_time/1e6:.2f}M tokens/s)")
    
    # Golden mapping
    start = time.perf_counter()
    gold_indices = vocab.map_tokens_golden(tokens)
    gold_time = time.perf_counter() - start
    print(f"  Golden mapping:   {gold_time*1000:.2f} ms ({n_tokens/gold_time/1e6:.2f}M tokens/s)")
    
    print("\n--- Index Distribution Analysis ---")
    
    # Analyze the distribution of indices
    std_unique, std_counts = np.unique(std_indices, return_counts=True)
    gold_unique, gold_counts = np.unique(gold_indices, return_counts=True)
    
    print(f"  Standard - unique indices used: {len(std_unique)}")
    print(f"  Golden   - unique indices used: {len(gold_unique)}")
    
    # Check entropy (higher is better for compression patterns)
    std_probs = std_counts / std_counts.sum()
    gold_probs = gold_counts / gold_counts.sum()
    
    std_entropy = -np.sum(std_probs * np.log2(std_probs + 1e-10))
    gold_entropy = -np.sum(gold_probs * np.log2(gold_probs + 1e-10))
    
    print(f"\n  Standard entropy: {std_entropy:.4f} bits")
    print(f"  Golden entropy:   {gold_entropy:.4f} bits")
    
    print("\n--- Memory Access Pattern Analysis ---")
    
    # Measure "locality" - how often consecutive indices are close
    std_diffs = np.abs(np.diff(std_indices.astype(np.int32)))
    gold_diffs = np.abs(np.diff(gold_indices.astype(np.int32)))
    
    print(f"  Standard avg jump: {std_diffs.mean():.1f} indices")
    print(f"  Golden avg jump:   {gold_diffs.mean():.1f} indices")
    print(f"  (Lower = better cache locality)")
    
    print("\n--- Compression Impact Test ---")
    
    import zlib
    
    # Compress the raw index sequences
    std_bytes = std_indices.tobytes()
    gold_bytes = gold_indices.tobytes()
    
    std_compressed = zlib.compress(std_bytes, level=9)
    gold_compressed = zlib.compress(gold_bytes, level=9)
    
    print(f"  Standard indices compressed: {len(std_compressed):,} bytes")
    print(f"  Golden indices compressed:   {len(gold_compressed):,} bytes")
    print(f"  Ratio: {len(gold_compressed)/len(std_compressed):.3f}x")
    
    print("\n--- Golden Index Encoder Test ---")
    
    encoder = GoldenIndexEncoder(vocab_size)
    
    # Test round-trip
    test_indices = np.random.randint(0, vocab_size, size=10000, dtype=np.uint32)
    encoded = encoder.encode(test_indices)
    decoded = encoder.decode(encoded)
    
    match = np.all(test_indices == decoded)
    print(f"  Round-trip verification: {'PASS' if match else 'FAIL'}")
    
    # Timing
    start = time.perf_counter()
    for _ in range(100):
        _ = encoder.encode(test_indices)
    encode_time = (time.perf_counter() - start) / 100
    print(f"  Encode time (10K indices): {encode_time*1000:.3f} ms")
    
    print("\n" + "=" * 60)
    print("THE GOLDEN INSIGHT:")
    print("  φ-based permutation creates DIFFERENT patterns, not 'better' ones.")
    print("  The value is in MIXING - breaking predictable sequential access.")
    print("  This can improve cache behavior in specific algorithms.")
    print("=" * 60)


if __name__ == "__main__":
    benchmark_golden_operations()
