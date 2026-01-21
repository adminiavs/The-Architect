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
from .tda import tokenize, build_cooccurrence_graph, Token
from .fibonacci_hash import GoldenIndexEncoder


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
        total_size = len(data)
        frame_index = 0
        start = 0
        while start < total_size:
            end = min(start + self.chunk_size, total_size)
            yield frame_index, data[start:end], (start, end)
            start = end
            frame_index += 1
    
    def _build_global_vocabulary(self, data: bytes, mode: str = 'word') -> Tuple[Dict[str, int], List[Token]]:
        if isinstance(data, bytes):
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError:
                text = None
        else:
            text = data
        
        all_tokens = tokenize(text if text is not None else data, mode=mode if text is not None else 'byte')
        
        vocabulary = {}
        for token in all_tokens:
            if token.value not in vocabulary:
                vocabulary[token.value] = len(vocabulary)
        
        return vocabulary, all_tokens
    
    def build_singularity(self, data: bytes, mode: str = 'word') -> GlobalSingularity:
        from .tda import build_cooccurrence_graph, compute_laplacian_eigenvectors
        
        # Build vocabulary
        vocabulary, all_tokens = self._build_global_vocabulary(data, mode)
        vocab_size = len(vocabulary)
        
        if vocab_size == 0:
            return GlobalSingularity({}, np.array([]).reshape(0, 8), np.array([]), self.e8_roots)
        
        # For embedding, we sample tokens to avoid O(N²) memory
        sample_size = min(len(all_tokens), max(1000, int(np.sqrt(len(all_tokens)) * 10)))
        sample_tokens = all_tokens[:sample_size]
        
        # Build co-occurrence graph on sample
        sample_graph = build_cooccurrence_graph(sample_tokens, self.window_size)
        
        # Compute spectral embedding
        laplacian_coords = compute_laplacian_eigenvectors(sample_graph, k=8)
        
        # Map coordinates to vocabulary
        embeddings_8d = np.zeros((vocab_size, 8), dtype=np.float32)
        phases = np.zeros(vocab_size, dtype=np.float32)
        
        for node, coords in laplacian_coords.items():
            if node in vocabulary:
                idx = vocabulary[node]
                if len(coords) < 8:
                    padded = np.zeros(8)
                    padded[:len(coords)] = coords
                    coords = padded
                embeddings_8d[idx] = coords[:8]
                phases[idx] = (idx * PHI) % (2 * np.pi)
        
        return GlobalSingularity(
            vocabulary=vocabulary,
            embeddings_8d=embeddings_8d,
            phases=phases,
            e8_roots=self.e8_roots,
        )
    
    def process_frames(self, 
                       data: bytes,
                       singularity: GlobalSingularity,
                       mode: str = 'word') -> Iterator[HorizonFrame]:
        """
        Process data into Horizon Frames.
        
        Uses Golden Search optimization for vocabulary lookup.
        """
        # Pre-build lookup array for O(1) numpy indexing (Golden Search)
        vocab_size = len(singularity.vocabulary)
        if vocab_size == 0:
            return
        
        # Create a direct token -> index array for fast lookup
        # This leverages numpy's vectorized operations
        token_to_idx = singularity.vocabulary
        
        for frame_idx, chunk_bytes, byte_range in self._chunk_data(data):
            if isinstance(chunk_bytes, bytes):
                try:
                    chunk_text = chunk_bytes.decode('utf-8')
                    chunk_tokens = tokenize(chunk_text, mode='word')
                except UnicodeDecodeError:
                    chunk_tokens = tokenize(chunk_bytes, mode='byte')
            else:
                chunk_tokens = tokenize(chunk_bytes, mode='word')
            
            if not chunk_tokens:
                continue
            
            # Vectorized lookup using pre-built array
            indices = np.array([token_to_idx.get(t.value, 0) for t in chunk_tokens], dtype=np.uint32)
            
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
