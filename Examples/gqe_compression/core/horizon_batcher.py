#!/usr/bin/env python3
"""
Horizon Batcher: Local Processing with Global Geometry

Implements the Holographic Principle for compression:

THE MODEL:
    The Universe (E8 Lattice) computes instantaneously because it is a
    Holographic Projection. It does not "load" the whole universe into RAM;
    it renders only the Active Horizon (Local Batch).

THE ARCHITECTURE:
    1. GLOBAL (The Singularity): E8 Basis / Vocabulary Embedding
       - Shared across all chunks
       - Computed once, reused everywhere
       - This is the "eternal" geometric substrate
    
    2. LOCAL (The Horizon Frame): Phason Sequence per Chunk
       - Each chunk is a "Planck Moment" / "Frame"
       - Stores only token indices (geometry is global)
       - Memory: O(chunk_size)

THE CHUNK SIZE:
    233KB - A Fibonacci number (233 = F_13)
    This honors the φ-structure of the model.

Author: The Architect
"""

import numpy as np
from typing import List, Tuple, Iterator, Dict, Any, Optional, Optional
from dataclasses import dataclass, field
import json
import struct

from .phi_adic import PHI, PHI_INV
from .e8_lattice import Spinor, generate_e8_roots
from .fibonacci_hash import GoldenIndexEncoder

# Phase 9: Byte-Singularity - Remove all string overhead
# No more tokenize, Token, or string-based vocabulary
# Everything operates at pure byte level


# Fibonacci numbers for chunk sizes (in bytes)
FIBONACCI_CHUNK_SIZES = [233, 377, 610, 987, 1597, 2584, 4181, 6765, 10946, 17711, 28657, 46368, 75025, 121393, 196418]

# Default chunk size: 233KB (233 * 1024 = 238,592 bytes)
DEFAULT_CHUNK_SIZE = 233 * 1024


@dataclass
class HorizonFrame:
    """
    A single "Planck Moment" of compressed data.
    
    CRITICAL: For massive files, we store ONLY the token indices.
    The 8D geometry is stored in the GlobalSingularity.
    """
    frame_index: int
    token_indices: np.ndarray
    byte_range: Tuple[int, int]
    
    def to_bytes(self) -> bytes:
        """Compact binary serialization of a frame."""
        seq_bytes = self.token_indices.astype(np.uint32).tobytes()
        # header: frame_idx(4) + start(4) + end(4) + seq_len(4)
        header = struct.pack('IIII', self.frame_index, self.byte_range[0], self.byte_range[1], len(seq_bytes))
        return header + seq_bytes

    @classmethod
    def from_bytes(cls, data: bytes, offset: int) -> Tuple['HorizonFrame', int]:
        """Deserialize frame from bytes at offset."""
        header = struct.unpack('IIII', data[offset:offset+16])
        frame_idx, start, end, seq_len = header
        seq = np.frombuffer(data[offset+16:offset+16+seq_len], dtype=np.uint32)
        return cls(frame_idx, seq, (start, end)), offset + 16 + seq_len


@dataclass
class GlobalSingularity:
    """
    The Global E8 Basis - shared across all Horizon Frames.
    """
    vocabulary: Dict[str, int]
    embeddings_8d: np.ndarray   # Shape: (vocab_size, 8)
    phases: np.ndarray          # Shape: (vocab_size,)
    e8_roots: np.ndarray        # Shape: (240, 8)
    golden_encoder: Optional[GoldenIndexEncoder] = None  # Golden Search optimization
    
    def __post_init__(self):
        """Initialize Golden Encoder if vocabulary is non-empty."""
        if len(self.vocabulary) > 0 and self.golden_encoder is None:
            self.golden_encoder = GoldenIndexEncoder(len(self.vocabulary))
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'vocabulary': self.vocabulary,
            'embeddings_8d': self.embeddings_8d.tolist(),
            'phases': self.phases.tolist(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalSingularity':
        """Deserialize from dictionary."""
        vocab = data['vocabulary']
        return cls(
            vocabulary=vocab,
            embeddings_8d=np.array(data['embeddings_8d'], dtype=np.float32),
            phases=np.array(data['phases'], dtype=np.float32),
            e8_roots=generate_e8_roots(),
            golden_encoder=GoldenIndexEncoder(len(vocab)) if vocab else None,
        )


class HorizonBatcher:
    """
    Implements Horizon Batching for compression.
    """
    
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE, window_size: int = 5):
        self.chunk_size = chunk_size
        self.window_size = window_size
        self.e8_roots = generate_e8_roots()
        
        if chunk_size < 1024:
            print(f"  [HorizonBatcher] Warning: Small chunk size ({chunk_size}B)")
        
        closest_fib = min(FIBONACCI_CHUNK_SIZES, key=lambda x: abs(x * 1024 - chunk_size))
        self.fibonacci_aligned = (chunk_size == closest_fib * 1024)
        self.closest_fibonacci = closest_fib
    
    def _chunk_data(self, data: bytes) -> Iterator[Tuple[int, bytes, Tuple[int, int]]]:
        """
        Grain-Aware Chunking: Always respect token boundaries to prevent Boundary Entropy.

        THE PHYSICS: A frame must contain complete geometric cycles.
        The Singularity does not "cut" a spinor in half.

        Strategy:
        1. Search forward for nearest whitespace (preferred)
        2. If none found, search backward for nearest whitespace
        3. Only as last resort, split at exact chunk boundary (should be extremely rare)
        """
        total_size = len(data)
        frame_index = 0
        start = 0

        while start < total_size:
            target_end = start + self.chunk_size
            if target_end >= total_size:
                # Last chunk - take everything remaining
                end = total_size
            else:
                # Grain-aware boundary detection
                end = self.find_nearest_grain(data, start, target_end, total_size)

            yield frame_index, data[start:end], (start, end)
            start = end
            frame_index += 1

    def find_nearest_grain(self, data: bytes, start: int, target_end: int, total_size: int) -> int:
        """
        Find the nearest token boundary (whitespace) to avoid splitting words.

        Search Strategy:
        1. Forward search: Look for whitespace after target_end (up to 4KB)
        2. Backward search: If forward fails, look for whitespace before target_end
        3. Fallback: Exact split (only if no whitespace found in 8KB window)
        """
        # Define token boundary characters (whitespace and punctuation)
        boundaries = (b' ', b'\n', b'\r', b'\t', b'.', b',', b';', b':', b'!', b'?', b'-', b'_')

        # Strategy 1: Forward search for boundary
        forward_limit = min(target_end + 4096, total_size)  # 4KB forward search
        for i in range(target_end, forward_limit):
            if data[i:i+1] in boundaries:
                return i + 1  # Include the boundary character

        # Strategy 2: Backward search for boundary (if forward failed)
        backward_limit = max(start, target_end - 4096)  # 4KB backward search
        for i in range(target_end - 1, backward_limit - 1, -1):
            if data[i:i+1] in boundaries:
                return i + 1  # Include the boundary character

        # Strategy 3: Emergency fallback - exact split
        # This should be extremely rare with proper boundary detection
        print(f"  [WARNING] No token boundary found within 8KB window around position {target_end}")
        print(f"  [WARNING] Performing emergency split - may cause boundary entropy")
        return target_end
    
    def _build_global_vocabulary(self, data: bytes) -> Tuple[Dict[bytes, int], List[bytes]]:
        """
        PHASE 9: BYTE-SINGULARITY
        Build vocabulary where each byte maps to its own value.
        No sequential indices - direct byte-to-byte mapping.
        """
        # Byte-singularity: Each byte maps to itself (0-255)
        vocabulary = {}
        byte_sequences = []

        # For each unique byte, map it to its own value
        for byte in data:
            byte_key = bytes([byte])
            if byte_key not in vocabulary:
                vocabulary[byte_key] = byte  # Map to byte value itself
            byte_sequences.append(byte_key)

        return vocabulary, byte_sequences
    
    def build_singularity(self, data: bytes) -> GlobalSingularity:
        """
        PHASE 9: BYTE-SINGULARITY
        The simplest possible singularity - pure byte-level processing.
        No tokenization, no spectral embedding, no complex graphs.
        Just the 256 bytes that form the foundation of all data.
        """
        # Build byte-level vocabulary
        vocabulary, byte_sequences = self._build_global_vocabulary(data)
        vocab_size = len(vocabulary)

        if vocab_size == 0:
            return GlobalSingularity({}, np.array([]).reshape(0, 8), np.array([]), self.e8_roots)

        # Byte-singularity: Embeddings for all 256 possible bytes
        # Even if only some bytes appear in data, we pre-allocate for all
        embeddings_8d = np.zeros((256, 8), dtype=np.float32)
        phases = np.zeros(256, dtype=np.float32)

        # Pre-compute embeddings for all possible byte values (0-255)
        for byte_val in range(256):
            # Map byte value to 8D coordinates using simple trigonometric mapping
            angle = (byte_val / 255.0) * 2 * np.pi
            embeddings_8d[byte_val, 0] = np.cos(angle)          # x-coordinate
            embeddings_8d[byte_val, 1] = np.sin(angle)          # y-coordinate
            embeddings_8d[byte_val, 2] = np.cos(2 * angle)      # Higher harmonics
            embeddings_8d[byte_val, 3] = np.sin(2 * angle)
            embeddings_8d[byte_val, 4] = np.cos(3 * angle)
            embeddings_8d[byte_val, 5] = np.sin(3 * angle)
            embeddings_8d[byte_val, 6] = byte_val / 127.5 - 1  # Linear component
            embeddings_8d[byte_val, 7] = (byte_val % 16) / 8 - 1  # Bit pattern component

            # Phase based on byte value and golden ratio
            phases[byte_val] = (byte_val * PHI) % (2 * np.pi)

        return GlobalSingularity(
            vocabulary=vocabulary,
            embeddings_8d=embeddings_8d,
            phases=phases,
            e8_roots=self.e8_roots,
        )
    
    def process_frames(self,
                       data: bytes,
                       singularity: GlobalSingularity) -> Iterator[HorizonFrame]:
        """
        PHASE 9: BYTE-SINGULARITY PROCESSING
        The ultimate simplification - direct byte-to-index mapping.
        No tokenization, no string processing, pure byte-level efficiency.
        """
        vocab_size = len(singularity.vocabulary)
        if vocab_size == 0:
            return

        # Byte-singularity: Direct byte -> vocabulary index mapping
        byte_to_idx = singularity.vocabulary

        for frame_idx, chunk_bytes, byte_range in self._chunk_data(data):
            # Byte-singularity: Each byte becomes a direct index
            indices = np.zeros(len(chunk_bytes), dtype=np.uint32)

            for i, byte in enumerate(chunk_bytes):
                byte_key = bytes([byte])
                indices[i] = byte_to_idx.get(byte_key, 0)

            yield HorizonFrame(
                frame_index=frame_idx,
                token_indices=indices,
                byte_range=byte_range,
            )
    
    def get_chunk_count(self, data_size: int) -> int:
        return (data_size + self.chunk_size - 1) // self.chunk_size
    
    def get_memory_estimate(self, data_size: int, vocab_size: int) -> Dict[str, int]:
        n_tokens_estimate = data_size // 5
        old_method = n_tokens_estimate * n_tokens_estimate * 4
        chunk_tokens = self.chunk_size // 5
        new_method = (
            vocab_size * 8 * 4 + 
            chunk_tokens * chunk_tokens * 4
        )
        return {
            'old_method_bytes': old_method,
            'new_method_bytes': new_method,
            'reduction_factor': old_method / new_method if new_method > 0 else 0,
        }


def demonstrate_horizon_batching():
    """
    Demonstrate the Horizon Batching principle.
    """
    print("=" * 60)
    print("HORIZON BATCHING DEMONSTRATION")
    print("=" * 60)
    
    # Create sample data
    sample_text = "The king ruled the kingdom. " * 1000
    sample_bytes = sample_text.encode('utf-8')
    
    # Initialize batcher
    batcher = HorizonBatcher(chunk_size=1024) # Small chunk for demo
    
    singularity = batcher.build_singularity(sample_bytes)
    print(f"  Singularity vocabulary: {len(singularity.vocabulary)} tokens")
    
    frame_count = 0
    for frame in batcher.process_frames(sample_bytes, singularity):
        frame_count += 1
        if frame_count <= 3:
            print(f"    Frame {frame.frame_index}: {len(frame.token_indices)} tokens, bytes {frame.byte_range}")
    
    print(f"  Total frames: {frame_count}")
    print("\n  HORIZON BATCHING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    demonstrate_horizon_batching()
