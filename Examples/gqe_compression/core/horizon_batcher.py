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
       - Co-occurrence computed within the horizon
       - Memory: O(chunk_size²) instead of O(N²)

THE CHUNK SIZE:
    233KB - A Fibonacci number (233 = F_13)
    This honors the φ-structure of the model.

Author: The Architect
"""

import numpy as np
from typing import List, Tuple, Iterator, Dict, Any, Optional
from dataclasses import dataclass, field
import json

from .phi_adic import PHI, PHI_INV
from .e8_lattice import Spinor, generate_e8_roots
from .tda import tokenize, build_cooccurrence_graph, Token


# Fibonacci numbers for chunk sizes (in bytes)
# F_13 = 233, F_14 = 377, F_15 = 610, F_16 = 987, F_17 = 1597
FIBONACCI_CHUNK_SIZES = [233, 377, 610, 987, 1597, 2584, 4181, 6765, 10946, 17711, 28657, 46368, 75025, 121393, 196418]

# Default chunk size: 233KB (233 * 1024 = 238,592 bytes)
# Using F_13 * 1024 to honor the φ-structure
DEFAULT_CHUNK_SIZE = 233 * 1024  # 233KB - Fibonacci number!


@dataclass
class HorizonFrame:
    """
    A single "Planck Moment" of compressed data.
    
    Represents one chunk of the input processed locally,
    but referencing the global vocabulary.
    
    Attributes:
        frame_index: Position in the sequence of frames
        token_indices: Indices into global vocabulary for this chunk
        local_projections: 4D projections for tokens in this chunk
        local_phasons: Phason coordinates for this chunk
        local_phases: Phase angles for spinors in this chunk
        byte_range: (start, end) byte positions in original data
    """
    frame_index: int
    token_indices: List[int]
    local_projections: np.ndarray  # Shape: (n_local_tokens, 4)
    local_phasons: np.ndarray      # Shape: (n_local_tokens, 4)
    local_phases: np.ndarray       # Shape: (n_local_tokens,)
    byte_range: Tuple[int, int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'frame_index': self.frame_index,
            'token_indices': self.token_indices,
            'local_projections': self.local_projections.tolist(),
            'local_phasons': self.local_phasons.tolist(),
            'local_phases': self.local_phases.tolist(),
            'byte_range': list(self.byte_range),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HorizonFrame':
        """Deserialize from dictionary."""
        return cls(
            frame_index=data['frame_index'],
            token_indices=data['token_indices'],
            local_projections=np.array(data['local_projections'], dtype=np.float32),
            local_phasons=np.array(data['local_phasons'], dtype=np.float32),
            local_phases=np.array(data['local_phases'], dtype=np.float32),
            byte_range=tuple(data['byte_range']),
        )


@dataclass
class GlobalSingularity:
    """
    The Global E8 Basis - shared across all Horizon Frames.
    
    This is "The Singularity" - the eternal geometric substrate
    that all local projections reference.
    
    Attributes:
        vocabulary: Token -> index mapping
        embeddings_8d: 8D spinor positions for each vocabulary entry
        phases: Phase angles for each vocabulary entry
        e8_roots: The 240 E8 root vectors (basis of the lattice)
    """
    vocabulary: Dict[str, int]
    embeddings_8d: np.ndarray   # Shape: (vocab_size, 8)
    phases: np.ndarray          # Shape: (vocab_size,)
    e8_roots: np.ndarray        # Shape: (240, 8)
    
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
        return cls(
            vocabulary=data['vocabulary'],
            embeddings_8d=np.array(data['embeddings_8d'], dtype=np.float32),
            phases=np.array(data['phases'], dtype=np.float32),
            e8_roots=generate_e8_roots(),
        )


class HorizonBatcher:
    """
    Implements Horizon Batching for compression.
    
    The Universe renders in Frames (Planck Moments), not all at once.
    This batcher processes text in chunks, maintaining:
    
    - GLOBAL: Vocabulary / E8 Basis (The Singularity)
    - LOCAL: Phason sequences per chunk (Horizon Frames)
    
    This reduces memory from O(N²) to O(chunk_size²) while
    preserving the geometric structure.
    """
    
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE, window_size: int = 5):
        """
        Initialize the Horizon Batcher.
        
        Args:
            chunk_size: Size of each horizon frame in bytes (default: 233KB)
            window_size: Co-occurrence window for TDA embedding
        """
        self.chunk_size = chunk_size
        self.window_size = window_size
        self.e8_roots = generate_e8_roots()
        
        # Verify chunk size is reasonable
        if chunk_size < 1024:
            print(f"  [HorizonBatcher] Warning: Small chunk size ({chunk_size}B)")
        
        # Track Fibonacci alignment (silently)
        closest_fib = min(FIBONACCI_CHUNK_SIZES, key=lambda x: abs(x * 1024 - chunk_size))
        self.fibonacci_aligned = (chunk_size == closest_fib * 1024)
        self.closest_fibonacci = closest_fib
    
    def _chunk_data(self, data: bytes) -> Iterator[Tuple[int, bytes, Tuple[int, int]]]:
        """
        Split data into Horizon Frames (chunks).
        
        Yields:
            (frame_index, chunk_bytes, (start_byte, end_byte))
        """
        total_size = len(data)
        frame_index = 0
        start = 0
        
        while start < total_size:
            end = min(start + self.chunk_size, total_size)
            chunk = data[start:end]
            yield frame_index, chunk, (start, end)
            start = end
            frame_index += 1
    
    def _build_global_vocabulary(self, data: bytes, mode: str = 'word') -> Tuple[Dict[str, int], List[Token]]:
        """
        Build the GLOBAL vocabulary (The Singularity).
        
        This scans the entire input to build a unified vocabulary,
        but does NOT build the full co-occurrence matrix.
        
        Memory: O(vocabulary_size), not O(N²)
        
        Args:
            data: Full input data
            mode: Tokenization mode
        
        Returns:
            (vocabulary_dict, all_tokens)
        """
        # Convert to string for tokenization
        if isinstance(data, bytes):
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError:
                text = None
        else:
            text = data
        
        # Tokenize
        if text is not None:
            all_tokens = tokenize(text, mode='word')
        else:
            # Byte mode
            all_tokens = tokenize(data, mode='byte')
        
        # Build vocabulary (unique tokens)
        vocabulary = {}
        for token in all_tokens:
            if token.value not in vocabulary:
                vocabulary[token.value] = len(vocabulary)
        
        return vocabulary, all_tokens
    
    def _compute_local_embedding(self, 
                                  chunk_tokens: List[Token],
                                  global_vocab: Dict[str, int],
                                  global_embeddings: np.ndarray) -> Tuple[List[int], np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute LOCAL embedding for a single Horizon Frame.
        
        Uses the GLOBAL vocabulary but computes co-occurrence LOCALLY.
        
        Args:
            chunk_tokens: Tokens in this chunk
            global_vocab: Global vocabulary mapping
            global_embeddings: Global 8D embeddings
        
        Returns:
            (token_indices, local_projections, local_phasons, local_phases)
        """
        from .projection import coxeter_projection_8d_to_4d
        from .tda import build_cooccurrence_graph
        
        # Get token indices into global vocabulary
        token_indices = [global_vocab.get(t.value, 0) for t in chunk_tokens]
        
        # Build LOCAL co-occurrence graph (only for this chunk)
        # This is O(chunk_size²), not O(N²)
        local_graph = build_cooccurrence_graph(chunk_tokens, self.window_size)
        
        n_tokens = len(chunk_tokens)
        local_projections = np.zeros((n_tokens, 4), dtype=np.float32)
        local_phasons = np.zeros((n_tokens, 4), dtype=np.float32)
        local_phases = np.zeros(n_tokens, dtype=np.float32)
        
        for i, token in enumerate(chunk_tokens):
            global_idx = global_vocab.get(token.value, 0)
            
            if global_idx < len(global_embeddings):
                embedding_8d = global_embeddings[global_idx]
                
                # Create spinor
                spinor = Spinor(position=embedding_8d, phase=0.0)
                
                # Project to 4D parallel and perpendicular using Coxeter projection
                projected = coxeter_projection_8d_to_4d(spinor)
                local_projections[i] = projected.parallel
                local_phasons[i] = projected.phason
                local_phases[i] = projected.phase
        
        return token_indices, local_projections, local_phasons, local_phases
    
    def build_singularity(self, data: bytes, mode: str = 'word') -> GlobalSingularity:
        """
        Build the Global Singularity (vocabulary + embeddings).
        
        This is computed ONCE for the entire input.
        
        Args:
            data: Full input data
            mode: Tokenization mode
        
        Returns:
            GlobalSingularity object
        """
        from .tda import build_cooccurrence_graph, compute_laplacian_eigenvectors
        
        # Build vocabulary
        vocabulary, all_tokens = self._build_global_vocabulary(data, mode)
        vocab_size = len(vocabulary)
        
        if vocab_size == 0:
            return GlobalSingularity(
                vocabulary={},
                embeddings_8d=np.array([]).reshape(0, 8),
                phases=np.array([]),
                e8_roots=self.e8_roots,
            )
        
        # For embedding, we sample tokens to avoid O(N²) memory
        # Sample at most sqrt(N) tokens for co-occurrence
        sample_size = min(len(all_tokens), max(1000, int(np.sqrt(len(all_tokens)) * 10)))
        
        # Use first chunk for embedding (representative sample)
        sample_tokens = all_tokens[:sample_size]
        
        # Build co-occurrence graph on sample
        sample_graph = build_cooccurrence_graph(sample_tokens, self.window_size)
        
        # Compute laplacian eigenvectors (spectral embedding)
        laplacian_coords = compute_laplacian_eigenvectors(sample_graph, k=8)
        
        # Map coordinates to vocabulary
        embeddings_8d = np.zeros((vocab_size, 8), dtype=np.float32)
        phases = np.zeros(vocab_size, dtype=np.float32)
        
        for node, coords in laplacian_coords.items():
            if node in vocabulary:
                vocab_idx = vocabulary[node]
                # Pad to 8D if necessary
                if len(coords) < 8:
                    padded = np.zeros(8)
                    padded[:len(coords)] = coords
                    coords = padded
                embeddings_8d[vocab_idx] = coords[:8]
                # Phase from token position in vocabulary (deterministic)
                phases[vocab_idx] = (vocab_idx * PHI) % (2 * np.pi)
        
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
        
        Each frame is a local "Planck Moment" referencing the global Singularity.
        
        Args:
            data: Full input data
            singularity: The global vocabulary/embedding
            mode: Tokenization mode
        
        Yields:
            HorizonFrame objects
        """
        for frame_idx, chunk_bytes, byte_range in self._chunk_data(data):
            # Convert chunk to text
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
            
            # Compute local embedding using global vocabulary
            token_indices, local_proj, local_phason, local_phases = self._compute_local_embedding(
                chunk_tokens,
                singularity.vocabulary,
                singularity.embeddings_8d
            )
            
            yield HorizonFrame(
                frame_index=frame_idx,
                token_indices=token_indices,
                local_projections=local_proj,
                local_phasons=local_phason,
                local_phases=local_phases,
                byte_range=byte_range,
            )
    
    def get_chunk_count(self, data_size: int) -> int:
        """Return the number of chunks for given data size."""
        return (data_size + self.chunk_size - 1) // self.chunk_size
    
    def get_memory_estimate(self, data_size: int, vocab_size: int) -> Dict[str, int]:
        """
        Estimate memory usage.
        
        Returns bytes needed for:
        - old_method: Full N×N co-occurrence matrix
        - new_method: Chunk-based processing
        """
        n_tokens_estimate = data_size // 5  # Rough estimate: 5 bytes per token
        
        old_method = n_tokens_estimate * n_tokens_estimate * 4  # float32
        
        chunk_tokens = self.chunk_size // 5
        n_chunks = self.get_chunk_count(data_size)
        new_method = (
            vocab_size * 8 * 4 +  # Global embeddings
            chunk_tokens * chunk_tokens * 4  # One chunk co-occurrence at a time
        )
        
        return {
            'old_method_bytes': old_method,
            'new_method_bytes': new_method,
            'reduction_factor': old_method / new_method if new_method > 0 else float('inf'),
        }


def demonstrate_horizon_batching():
    """
    Demonstrate the Horizon Batching principle.
    """
    print("=" * 60)
    print("HORIZON BATCHING DEMONSTRATION")
    print("=" * 60)
    
    print("\nTHE PRINCIPLE:")
    print("  The Universe renders in FRAMES, not all at once.")
    print("  Each frame is a 'Planck Moment' in the Active Horizon.")
    print()
    print("THE ARCHITECTURE:")
    print("  GLOBAL (Singularity): Vocabulary + E8 Embeddings")
    print("  LOCAL (Horizon Frame): Phason sequence per chunk")
    print()
    print(f"  Chunk size: {DEFAULT_CHUNK_SIZE:,} bytes (233KB = F_13 * 1024)")
    
    # Create sample data
    sample_text = "The king ruled the kingdom. " * 10000
    sample_bytes = sample_text.encode('utf-8')
    
    print(f"\n  Sample data: {len(sample_bytes):,} bytes")
    
    # Initialize batcher
    batcher = HorizonBatcher(chunk_size=DEFAULT_CHUNK_SIZE)
    
    # Memory comparison
    mem = batcher.get_memory_estimate(len(sample_bytes), vocab_size=100)
    print(f"\n  Memory comparison:")
    print(f"    Old method (N×N matrix): {mem['old_method_bytes']:,} bytes")
    print(f"    New method (chunked): {mem['new_method_bytes']:,} bytes")
    print(f"    Reduction: {mem['reduction_factor']:.1f}x")
    
    # Process
    print(f"\n  Processing in {batcher.get_chunk_count(len(sample_bytes))} frames...")
    
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
