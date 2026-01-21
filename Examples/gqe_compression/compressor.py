#!/usr/bin/env python3
"""
GQE Compressor - Golden Quasicrystal Encoding

Main compression pipeline based on The Architect's model.

Pipeline:
1. Tokenize input data (universal: text, bytes, etc.)
2. Build co-occurrence graph (TDA)
3. Embed tokens to 8D spinors
4. Project to 4D + extract phasons
5. Apply holographic encoding (distributed redundancy)
6. Package with Toric error correction capability

Key insight: The holographic encoding distributes information so that
every piece contains the whole (like a true hologram). This provides
error correction capabilities aligned with Axiom 6.

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import Union, List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
import json
import struct
import zlib
import os

from .core.phi_adic import encode_phi, decode_phi, PhiAdicNumber, PHI, PHI_INV
from .core.e8_lattice import Spinor, snap_spinor_to_e8
from .core.projection import (
    coxeter_projection_8d_to_4d, 
    inverse_projection_with_phason,
    ProjectedSpinor
)
from .core.tda import tokenize, build_cooccurrence_graph, embed_all_tokens, Token
from .core.holographic_encoding import (
    simple_holographic_spread,
    simple_holographic_recover,
    add_distributed_parity,
    recover_from_distributed_parity
)
from .core.geometric_reed_solomon import (
    rs_encode_with_geometry,
    rs_decode_with_geometry
)
from .core.geometric_evolver import GeometricEvolver, EvolutionState


@dataclass
class CompressedData:
    """
    Container for compressed data.
    
    Components:
    - vocabulary: Unique tokens and their 8D spinor embeddings
    - token_sequence: Indices into vocabulary for each token (stored as binary)
    - projections_4d: 4D parallel projections (visible)
    - phasons_4d: 4D perpendicular components (hidden, compresses well)
    - phases: Spinor phases
    - metadata: Additional information for reconstruction
    """
    vocabulary: Dict[str, Dict]
    token_sequence: Union[List[int], np.ndarray]
    projections_4d: np.ndarray
    phasons_4d: np.ndarray
    phases: np.ndarray
    metadata: Dict[str, Any]
    
    def to_bytes(self) -> bytes:
        """
        Serialize to bytes with geometric efficiency.
        
        CRITICAL FIX: token_sequence is now a binary array, NOT part of JSON header.
        This prevents RAM explosion during serialization of large files.
        """
        # Pack token sequence as binary (uint32)
        seq_array = np.array(self.token_sequence, dtype=np.uint32)
        seq_bytes = seq_array.tobytes()
        
        # Build optimized header (exclude the heavy sequence)
        header = {
            'vocabulary': {str(k): v for k, v in self.vocabulary.items()},
            'metadata': self.metadata
        }
        
        header_json = json.dumps(header).encode('utf-8')
        header_len = len(header_json)
        
        # Binary arrays for 8D geometry
        proj_bytes = self.projections_4d.astype(np.float32).tobytes()
        phason_bytes = self.phasons_4d.astype(np.float32).tobytes()
        phase_bytes = self.phases.astype(np.float32).tobytes()
        
        # Pack order: 
        # 1. header_len (4) + header_json
        # 2. seq_len (4) + seq_bytes
        # 3. geom_arrays (proj, phason, phase)
        packed = struct.pack('I', header_len)
        packed += header_json
        packed += struct.pack('I', len(seq_bytes))
        packed += seq_bytes
        packed += struct.pack('I', len(proj_bytes))
        packed += proj_bytes
        packed += struct.pack('I', len(phason_bytes))
        packed += phason_bytes
        packed += struct.pack('I', len(phase_bytes))
        packed += phase_bytes
        
        # Apply GEOMETRIC error correction (RS encoding)
        geometric_encoded = rs_encode_with_geometry(packed, n_copies=7)
        
        # Compressed-only version for fast path
        compressed_only = zlib.compress(packed, level=9)
        
        magic = b'\xE8\x52'  # v52: Binary History Optimized
        compressed_len = len(compressed_only)
        
        return (magic * 5 + 
                struct.pack('I', compressed_len) * 5 + 
                compressed_only + 
                geometric_encoded)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'CompressedData':
        """Deserialize with support for Binary History (v52)."""
        from .core.holographic_encoding import simple_holographic_recover, recover_from_distributed_parity
        from .core.toric_error_correction import apply_toric_correction_to_bytes
        from collections import Counter
        
        packed = None
        
        if len(data) >= 30:
            magic_votes = [data[i*2:(i+1)*2] for i in range(5)]
            recovered_magic = Counter(magic_votes).most_common(1)[0][0]
            
            if recovered_magic in (b'\xE8\x52', b'\xE8\x51', b'\xE8\x50'):
                len_start = 10
                len_votes = [struct.unpack('I', data[len_start+i*4:len_start+(i+1)*4])[0] for i in range(5)]
                compressed_len = Counter(len_votes).most_common(1)[0][0]
                
                data_start = 30
                compressed_only = data[data_start:data_start+compressed_len]
                encoded_data = data[data_start+compressed_len:]
                
                try:
                    packed = zlib.decompress(compressed_only)
                except zlib.error:
                    if recovered_magic == b'\xE8\x52' or recovered_magic == b'\xE8\x51':
                        packed, _, _ = rs_decode_with_geometry(encoded_data)
                    else:
                        recovered, _ = recover_from_distributed_parity(encoded_data)
                        packed = simple_holographic_recover(recovered)
        
        if packed is None:
            raise ValueError("Failed to decode compressed data")
            
        offset = 0
        
        # Header
        header_len = struct.unpack('I', packed[offset:offset+4])[0]
        offset += 4
        header_json = packed[offset:offset+header_len].decode('utf-8')
        offset += header_len
        header = json.loads(header_json)
        
        # Token Sequence (Binary History)
        if recovered_magic == b'\xE8\x52':
            seq_len = struct.unpack('I', packed[offset:offset+4])[0]
            offset += 4
            token_sequence = np.frombuffer(packed[offset:offset+seq_len], dtype=np.uint32).tolist()
            offset += seq_len
        else:
            # Legacy v51/50 stored sequence in JSON
            token_sequence = header.get('token_sequence', [])
            
        # Projections
        proj_len = struct.unpack('I', packed[offset:offset+4])[0]
        offset += 4
        projections_4d = np.frombuffer(packed[offset:offset+proj_len], dtype=np.float32)
        offset += proj_len
        
        # Phasons
        phason_len = struct.unpack('I', packed[offset:offset+4])[0]
        offset += 4
        phasons_4d = np.frombuffer(packed[offset:offset+phason_len], dtype=np.float32)
        offset += phason_len
        
        # Phases
        phase_len = struct.unpack('I', packed[offset:offset+4])[0]
        offset += 4
        phases = np.frombuffer(packed[offset:offset+phase_len], dtype=np.float32)
        
        n_unique = len(header['vocabulary'])
        if n_unique > 0:
            projections_4d = projections_4d.reshape(n_unique, 4)
            phasons_4d = phasons_4d.reshape(n_unique, 4)
        else:
            projections_4d = np.array([]).reshape(0, 4)
            phasons_4d = np.array([]).reshape(0, 4)
            
        return cls(
            vocabulary=header['vocabulary'],
            token_sequence=token_sequence,
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=header['metadata']
        )


class GQECompressor:
    """
    Golden Quasicrystal Encoding Compressor.
    
    SELF-LEARNING (The Möbius Strip):
    When self_learning=True, the compressor updates its E8 basis
    after each compression, learning the geometric structure of language.
    
    Words that co-occur frequently move closer in 8D space.
    Random "phason flips" allow emergence of new concepts.
    """
    
    HORIZON_THRESHOLD = 233 * 1024
    
    def __init__(self, window_size: int = 5, tokenize_mode: str = 'auto', 
                 use_horizon_batching: bool = True, chunk_size: Optional[int] = None,
                 self_learning: bool = False, evolution_state_path: Optional[str] = None,
                 learning_rate: float = 0.01, mutation_rate: float = 0.001):
        """
        Initialize compressor.
        
        Args:
            window_size: Co-occurrence window for graph building
            tokenize_mode: Tokenization mode ('auto', 'word', 'char', 'byte')
            use_horizon_batching: Enable Horizon Batching for large inputs
            chunk_size: Custom chunk size for Horizon Batching
            self_learning: Enable geometric self-learning
            evolution_state_path: Path to save/load learned state
            learning_rate: How fast nodes move toward co-occurring neighbors
            mutation_rate: Probability of random phason flips
        """
        self.window_size = window_size
        self.tokenize_mode = tokenize_mode
        self.use_horizon_batching = use_horizon_batching
        self.chunk_size = chunk_size or self.HORIZON_THRESHOLD
        
        # Self-learning configuration
        self.self_learning = self_learning
        self.evolver: Optional[GeometricEvolver] = None
        self.evolution_stats: List[Dict] = []
        
        if self_learning:
            self.evolver = GeometricEvolver(
                learning_rate=learning_rate,
                mutation_rate=mutation_rate,
                state_path=evolution_state_path,
            )
    
    def _apply_learning(self, vocabulary: Dict[str, Dict], 
                        embeddings_8d: np.ndarray, 
                        phases: np.ndarray,
                        token_indices: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Apply self-learning feedback loop.
        
        THE MÖBIUS STRIP:
        1. Initialize evolver with current vocabulary
        2. Observe co-occurrences
        3. Apply attraction + mutations
        4. Return evolved embeddings
        
        Returns:
            (evolved_embeddings, evolved_phases, evolution_stats)
        """
        if self.evolver is None:
            return embeddings_8d, phases, {}
        
        # Convert vocabulary from {'word': {'index': i}} to {'word': i}
        simple_vocab = {token: info['index'] for token, info in vocabulary.items()}
        
        # Initialize evolver if needed
        if self.evolver.state is None:
            self.evolver.initialize_from_vocabulary(simple_vocab, embeddings_8d, phases)
        else:
            # Update vocabulary if it has grown
            for token, idx in simple_vocab.items():
                if token not in self.evolver.state.vocabulary:
                    self.evolver.state.vocabulary[token] = idx
                    # Expand embeddings array
                    if idx >= len(self.evolver.state.embeddings_8d):
                        new_embed = np.random.randn(8).astype(np.float32) * 0.5
                        self.evolver.state.embeddings_8d = np.vstack([
                            self.evolver.state.embeddings_8d, new_embed
                        ])
                        self.evolver.state.phases = np.append(
                            self.evolver.state.phases, 
                            np.random.uniform(0, 2 * np.pi)
                        )
        
        # Run evolution step
        stats = self.evolver.evolve_step(token_indices, apply_mutations=True)
        self.evolution_stats.append(stats)
        
        # Return evolved embeddings
        evolved_embed, evolved_phases = self.evolver.get_evolved_embeddings()
        
        # Resize to match vocabulary if needed
        n_vocab = len(vocabulary)
        if len(evolved_embed) < n_vocab:
            pad_size = n_vocab - len(evolved_embed)
            evolved_embed = np.vstack([evolved_embed, np.zeros((pad_size, 8))])
            evolved_phases = np.append(evolved_phases, np.zeros(pad_size))
        elif len(evolved_embed) > n_vocab:
            evolved_embed = evolved_embed[:n_vocab]
            evolved_phases = evolved_phases[:n_vocab]
        
        return evolved_embed, evolved_phases, stats
    
    def get_learned_concepts(self) -> List[Dict]:
        """
        Get emergent concepts learned by the compressor.
        
        Returns:
            List of concept clusters (tokens that have moved close together)
        """
        if self.evolver is None:
            return []
        return self.evolver.get_learned_concepts()
    
    def _compress_with_horizon_batching(self, data: bytes, mode: str) -> CompressedData:
        """
        Compress using Horizon Batching for large inputs.
        
        CRITICAL FIX: We do NOT accumulate frames in memory.
        We stream them into the CompressedData object.
        """
        from .core.horizon_batcher import HorizonBatcher
        
        batcher = HorizonBatcher(
            chunk_size=self.chunk_size,
            window_size=self.window_size
        )
        
        # Build Global Singularity (eternal basis)
        singularity = batcher.build_singularity(data, mode=mode)
        
        if len(singularity.vocabulary) == 0:
            return CompressedData({}, np.array([], dtype=np.uint32), 
                                  np.array([]).reshape(0, 4), np.array([]).reshape(0, 4), 
                                  np.array([]), {'mode': mode, 'original_length': len(data), 'horizon_batched': True})
        
        # STREAMING: Process frames one by one
        # For now, we still return a CompressedData object, but its internal storage
        # uses efficient numpy arrays instead of Python lists.
        
        frame_data_list = []
        frame_count = 0
        total_tokens = 0
        
        for frame in batcher.process_frames(data, singularity, mode=mode):
            frame_data_list.append(frame.token_indices)
            total_tokens += len(frame.token_indices)
            frame_count += 1
            
        # Concatenate all frame indices into ONE binary array (uint32)
        # This is much more efficient than a Python list
        all_indices = np.concatenate(frame_data_list)
        
        # Build vocabulary statistics
        vocabulary = {}
        unique_indices, counts = np.unique(all_indices, return_counts=True)
        idx_to_count = dict(zip(unique_indices, counts))
        
        for token_str, idx in singularity.vocabulary.items():
            vocabulary[token_str] = {
                'index': idx,
                'count': int(idx_to_count.get(idx, 0))
            }
        
        # SELF-LEARNING: Apply the Möbius Feedback Loop
        embeddings_8d = singularity.embeddings_8d.copy()
        phases = singularity.phases.copy()
        evolution_stats = {}
        
        if self.self_learning and self.evolver is not None:
            embeddings_8d, phases, evolution_stats = self._apply_learning(
                vocabulary,  # Use formatted vocabulary (with 'index' keys)
                embeddings_8d,
                phases,
                all_indices
            )
        
        # Compute 4D projections (using potentially evolved embeddings)
        from .core.projection import coxeter_projection_8d_to_4d
        from .core.e8_lattice import Spinor
        
        n_unique = len(singularity.vocabulary)
        projections_4d = np.zeros((n_unique, 4), dtype=np.float32)
        phasons_4d = np.zeros((n_unique, 4), dtype=np.float32)
        
        for i in range(n_unique):
            if i < len(embeddings_8d):
                spinor = Spinor(position=embeddings_8d[i], phase=phases[i])
                projected = coxeter_projection_8d_to_4d(spinor)
                projections_4d[i] = projected.parallel
                phasons_4d[i] = projected.phason
        
        metadata = {
            'mode': mode,
            'original_length': len(data),
            'n_tokens': total_tokens,
            'n_unique': n_unique,
            'window_size': self.window_size,
            'horizon_batched': True,
            'n_frames': frame_count,
            'chunk_size': self.chunk_size,
            'self_learning': self.self_learning,
            'evolution_stats': evolution_stats,
        }
        
        return CompressedData(
            vocabulary=vocabulary,
            token_sequence=all_indices,
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=metadata
        )
    
    def compress_file(self, file_path: str) -> CompressedData:
        """
        Compress a file using true streaming to maintain low RSS.
        """
        mode = self.tokenize_mode
        if mode == 'auto':
            mode = 'word' # Default for files
            
        from .core.horizon_batcher import HorizonBatcher
        batcher = HorizonBatcher(chunk_size=self.chunk_size, window_size=self.window_size)
        
        # 1. First pass: Build Global Singularity (eternal basis)
        # We read the first chunk to establish the vocabulary
        with open(file_path, 'rb') as f:
            first_chunk = f.read(self.chunk_size)
            singularity = batcher.build_singularity(first_chunk, mode=mode)
            
        # 2. Second pass: Process frames and collect indices into a single binary array
        # We pre-allocate the array if possible, or use a list of arrays
        frame_arrays = []
        total_tokens = 0
        
        with open(file_path, 'rb') as f:
            frame_idx = 0
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk: break
                
                # Process one frame at a time
                try:
                    tokens = tokenize(chunk.decode('utf-8'), mode=mode)
                except UnicodeDecodeError:
                    tokens = tokenize(chunk, mode='byte')
                
                indices = np.array([singularity.vocabulary.get(t.value, 0) for t in tokens], dtype=np.uint32)
                frame_arrays.append(indices)
                total_tokens += len(indices)
                frame_idx += 1
                
        all_indices = np.concatenate(frame_arrays)
        del frame_arrays # Immediate GC
        
        # ... (rest of the logic remains the same)
        n_unique = len(singularity.vocabulary)
        projections_4d = np.zeros((n_unique, 4), dtype=np.float32)
        phasons_4d = np.zeros((n_unique, 4), dtype=np.float32)
        phases = singularity.phases.copy()
        
        from .core.projection import coxeter_projection_8d_to_4d
        from .core.e8_lattice import Spinor
        P_par, P_perp = coxeter_projection_matrices() if 'coxeter_projection_matrices' in dir() else (None, None)
        
        for i in range(n_unique):
            if i < len(singularity.embeddings_8d):
                spinor = Spinor(position=singularity.embeddings_8d[i], phase=phases[i])
                projected = coxeter_projection_8d_to_4d(spinor)
                projections_4d[i] = projected.parallel
                phasons_4d[i] = projected.phason
                
        metadata = {
            'mode': mode,
            'original_length': os.path.getsize(file_path),
            'n_tokens': total_tokens,
            'n_unique': n_unique,
            'window_size': self.window_size,
            'horizon_batched': True,
            'n_frames': frame_idx,
            'chunk_size': self.chunk_size
        }
        
        return CompressedData(
            vocabulary={t: {'index': i, 'count': 0} for t, i in singularity.vocabulary.items()},
            token_sequence=all_indices,
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=metadata
        )

    def compress(self, data: Union[str, bytes]) -> CompressedData:
        """
        Compress input data.
        
        For large inputs (> 233KB), uses Horizon Batching:
        - GLOBAL: Vocabulary / E8 Basis (The Singularity)
        - LOCAL: Phason sequences per chunk (Horizon Frames)
        
        This follows The Architect's principle:
        "The Universe renders in FRAMES, not all at once."
        
        Args:
            data: Input data (text or bytes)
        
        Returns:
            CompressedData object
        """
        # Determine mode
        mode = self.tokenize_mode
        if mode == 'auto':
            mode = 'byte' if isinstance(data, bytes) else 'word'
        
        # Convert to bytes for size check
        data_bytes = data.encode('utf-8') if isinstance(data, str) else data
        
        # Use Horizon Batching for large inputs
        if self.use_horizon_batching and len(data_bytes) > self.HORIZON_THRESHOLD:
            return self._compress_with_horizon_batching(data_bytes, mode)
        
        # Standard compression for small inputs
        tokens = tokenize(data, mode=mode)
        
        if len(tokens) == 0:
            return CompressedData(
                vocabulary={},
                token_sequence=[],
                projections_4d=np.array([]).reshape(0, 4),
                phasons_4d=np.array([]).reshape(0, 4),
                phases=np.array([]),
                metadata={'mode': mode, 'original_length': 0}
            )
        
        # Step 2: Build co-occurrence graph
        graph = build_cooccurrence_graph(tokens, window_size=self.window_size)
        
        # Step 3: Embed tokens to 8D spinors
        spinors = embed_all_tokens(tokens, graph)
        
        # Step 4: Build vocabulary (unique tokens)
        vocabulary = {}
        token_to_idx = {}
        unique_spinors = []
        
        for token, spinor in zip(tokens, spinors):
            token_str = str(token.value)
            if token_str not in vocabulary:
                idx = len(vocabulary)
                vocabulary[token_str] = {
                    'index': idx,
                    'count': 1
                }
                token_to_idx[token_str] = idx
                unique_spinors.append(spinor)
            else:
                vocabulary[token_str]['count'] += 1
        
        # Step 5: Create token sequence (indices)
        token_sequence = np.array([token_to_idx[str(t.value)] for t in tokens], dtype=np.uint32)
        
        # SELF-LEARNING: Apply the Möbius Feedback Loop (standard path)
        embeddings_8d = np.array([s.position for s in unique_spinors], dtype=np.float32)
        phases = np.array([s.phase for s in unique_spinors], dtype=np.float32)
        evolution_stats = {}
        
        if self.self_learning and self.evolver is not None:
            embeddings_8d, phases, evolution_stats = self._apply_learning(
                vocabulary,
                embeddings_8d,
                phases,
                token_sequence
            )
        
        # Step 6: Project spinors to 4D + extract phasons (using evolved embeddings)
        n_unique = len(unique_spinors)
        projections_4d = np.zeros((n_unique, 4))
        phasons_4d = np.zeros((n_unique, 4))
        
        for i in range(n_unique):
            spinor = Spinor(position=embeddings_8d[i], phase=phases[i])
            projected = coxeter_projection_8d_to_4d(spinor)
            projections_4d[i] = projected.parallel
            phasons_4d[i] = projected.phason
        
        # Metadata
        metadata = {
            'mode': mode,
            'original_length': len(data) if isinstance(data, (str, bytes)) else len(tokens),
            'n_tokens': len(tokens),
            'n_unique': n_unique,
            'window_size': self.window_size,
            'self_learning': self.self_learning,
            'evolution_stats': evolution_stats,
        }
        
        return CompressedData(
            vocabulary=vocabulary,
            token_sequence=token_sequence.tolist(),
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=metadata
        )


def compress_text(text: str, **kwargs) -> CompressedData:
    """
    Convenience function to compress text.
    
    Args:
        text: Input text
        **kwargs: Additional arguments for GQECompressor
    
    Returns:
        CompressedData object
    """
    compressor = GQECompressor(**kwargs)
    return compressor.compress(text)


def run_verification() -> None:
    """Run verification tests for compressor."""
    print("=" * 60)
    print("GQE COMPRESSOR VERIFICATION")
    print("=" * 60)
    
    # Test text
    test_text = """
    The quick brown fox jumps over the lazy dog.
    The dog was sleeping peacefully in the sun.
    A fox is quick and clever, while a dog is loyal.
    """
    
    print(f"\nOriginal text length: {len(test_text)} bytes")
    
    # Test 1: Basic compression
    print("\n--- Test 1: Basic compression ---")
    compressor = GQECompressor(window_size=5)
    compressed = compressor.compress(test_text)
    
    print(f"  Tokens: {compressed.metadata['n_tokens']}")
    print(f"  Unique tokens: {compressed.metadata['n_unique']}")
    print(f"  Projections shape: {compressed.projections_4d.shape}")
    print(f"  Phasons shape: {compressed.phasons_4d.shape}")
    
    # Test 2: Serialization
    print("\n--- Test 2: Serialization ---")
    serialized = compressed.to_bytes()
    print(f"  Serialized size: {len(serialized)} bytes")
    print(f"  Compression ratio: {len(serialized) / len(test_text):.4f}")
    
    # Test 3: Deserialization
    print("\n--- Test 3: Deserialization ---")
    restored = CompressedData.from_bytes(serialized)
    print(f"  Vocabulary restored: {len(restored.vocabulary)} tokens")
    print(f"  Sequence restored: {len(restored.token_sequence)} indices")
    
    # Verify data integrity
    proj_match = np.allclose(compressed.projections_4d, restored.projections_4d)
    phason_match = np.allclose(compressed.phasons_4d, restored.phasons_4d)
    print(f"  Projections match: {proj_match}")
    print(f"  Phasons match: {phason_match}")
    
    # Test 4: Byte data compression
    print("\n--- Test 4: Byte data ---")
    byte_data = b"ATCGATCGATCGATCG" * 20
    compressor_byte = GQECompressor(tokenize_mode='byte')
    compressed_bytes = compressor_byte.compress(byte_data)
    serialized_bytes = compressed_bytes.to_bytes()
    
    print(f"  Original: {len(byte_data)} bytes")
    print(f"  Compressed: {len(serialized_bytes)} bytes")
    print(f"  Ratio: {len(serialized_bytes) / len(byte_data):.4f}")
    
    # Test 5: Various text sizes
    print("\n--- Test 5: Scaling behavior ---")
    for size_mult in [1, 5, 10]:
        text = test_text * size_mult
        comp = compressor.compress(text)
        ser = comp.to_bytes()
        ratio = len(ser) / len(text)
        print(f"  {len(text):6d} bytes -> {len(ser):6d} bytes (ratio: {ratio:.4f})")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
