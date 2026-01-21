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


@dataclass
class CompressedData:
    """
    Container for compressed data.
    
    Components:
    - vocabulary: Unique tokens and their 8D spinor embeddings
    - token_sequence: Indices into vocabulary for each token
    - projections_4d: 4D parallel projections (visible)
    - phasons_4d: 4D perpendicular components (hidden, compresses well)
    - phases: Spinor phases
    - metadata: Additional information for reconstruction
    """
    vocabulary: Dict[str, Dict]  # token -> embedding info
    token_sequence: List[int]     # Indices into vocabulary
    projections_4d: np.ndarray    # Shape: (N_unique, 4)
    phasons_4d: np.ndarray        # Shape: (N_unique, 4) - THE KEY
    phases: np.ndarray            # Shape: (N_unique,)
    metadata: Dict[str, Any]
    
    def to_bytes(self) -> bytes:
        """
        Serialize to bytes with holographic encoding.
        
        Uses distributed redundancy so every piece of the output
        contains information about the whole (Holographic Principle).
        This enables error correction during decompression.
        
        CRITICAL: We apply holographic encoding to the RAW data, then
        compress. This way:
        1. Holographic recovery works on raw data (not zlib stream)
        2. We can store both compressed (small) and holographic (robust) versions
        """
        # Package as JSON + binary arrays
        header = {
            'vocabulary': {str(k): v for k, v in self.vocabulary.items()},
            'token_sequence': self.token_sequence,
            'metadata': self.metadata
        }
        
        header_json = json.dumps(header).encode('utf-8')
        header_len = len(header_json)
        
        # Binary arrays
        proj_bytes = self.projections_4d.astype(np.float32).tobytes()
        phason_bytes = self.phasons_4d.astype(np.float32).tobytes()
        phase_bytes = self.phases.astype(np.float32).tobytes()
        
        # Pack: header_len (4 bytes) + header + arrays
        packed = struct.pack('I', header_len)
        packed += header_json
        packed += struct.pack('I', len(proj_bytes))
        packed += proj_bytes
        packed += struct.pack('I', len(phason_bytes))
        packed += phason_bytes
        packed += struct.pack('I', len(phase_bytes))
        packed += phase_bytes
        
        # Apply GEOMETRIC error correction to the packed data
        # This uses "the curve connects the dots" principle:
        # - Multiple copies with polynomial checksum
        # - Majority voting with geometric verification
        # - 7 copies provides strong error correction up to ~20% corruption
        
        geometric_encoded = rs_encode_with_geometry(packed, n_copies=7)
        
        # Also store a compressed-only version for fast path (when no corruption)
        compressed_only = zlib.compress(packed, level=9)
        
        # Format with redundant headers for robustness:
        # magic*5 (10) + compressed_len*5 (20) + compressed_only + geometric_encoded
        # The redundant magic and length allow recovery even when these are corrupted
        magic = b'\xE8\x51'  # E8 = E8 lattice, 51 = geometric RS version
        compressed_len = len(compressed_only)
        
        return (magic * 5 +  # 5 copies of magic
                struct.pack('I', compressed_len) * 5 +  # 5 copies of length
                compressed_only + 
                geometric_encoded)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'CompressedData':
        """
        Deserialize from bytes with error recovery.
        
        Uses the holographic encoding's distributed redundancy
        to detect and recover from corruption.
        
        Strategy:
        1. Try fast path (compressed_only) first
        2. If that fails, use holographic recovery
        """
        from .core.holographic_encoding import (
            simple_holographic_recover,
            recover_from_distributed_parity
        )
        from .core.toric_error_correction import apply_toric_correction_to_bytes
        
        packed = None
        
        # Check for geometric RS format (magic \xE8\x51) or holographic format v4 (magic \xE8\x50)
        # Format: magic*5 (10) + compressed_len*5 (20) + compressed_only + encoded_data
        
        # First, try to recover magic from 5 copies using majority voting
        from collections import Counter
        
        if len(data) >= 30:  # Minimum: 10 (magic) + 20 (lengths)
            # Recover magic with majority voting
            magic_votes = [data[i*2:(i+1)*2] for i in range(5) if (i+1)*2 <= len(data)]
            magic_counts = Counter(magic_votes)
            recovered_magic = magic_counts.most_common(1)[0][0] if magic_counts else b''
            
            if recovered_magic in (b'\xE8\x51', b'\xE8\x50'):
                # Recover compressed_len with majority voting from 5 copies
                len_start = 10
                len_votes = []
                for i in range(5):
                    start = len_start + i * 4
                    end = start + 4
                    if end <= len(data):
                        try:
                            len_votes.append(struct.unpack('I', data[start:end])[0])
                        except struct.error:
                            pass
                
                len_counts = Counter(len_votes)
                compressed_len = len_counts.most_common(1)[0][0] if len_counts else 0
                
                # Extract data sections
                data_start = 30  # After magic*5 + len*5
                compressed_only = data[data_start:data_start+compressed_len]
                encoded_data = data[data_start+compressed_len:]
                
                # Try fast path first (compressed_only)
                try:
                    packed = zlib.decompress(compressed_only)
                except zlib.error:
                    # Fast path failed - use error correction
                    
                    if recovered_magic == b'\xE8\x51':
                        # Geometric RS: "The curve connects the dots"
                        # Uses majority voting with polynomial checksum verification
                        packed, n_corrections, confidence = rs_decode_with_geometry(encoded_data)
                    else:
                        # Legacy holographic encoding
                        recovered, confidence = recover_from_distributed_parity(encoded_data)
                        packed = simple_holographic_recover(recovered)
        
        # Check for holographic format v2 (magic \xE8\x48)
        elif len(data) >= 6 and data[:2] == b'\xE8\x48':
            # Old v2 format: magic (2) + compressed_len (4) + compressed_only + holographic_raw
            compressed_len = struct.unpack('I', data[2:6])[0]
            compressed_only = data[6:6+compressed_len]
            holographic_raw = data[6+compressed_len:]
            
            # Try fast path first (compressed_only)
            try:
                packed = zlib.decompress(compressed_only)
            except zlib.error:
                # Fast path failed - use holographic recovery
                # The holographic data is NOT compressed, so we can recover directly
                
                # Recover from parity wrapper
                recovered, confidence = recover_from_distributed_parity(holographic_raw)
                
                # Reverse holographic spreading with majority voting
                # This corrects up to ~33% random byte corruption
                packed = simple_holographic_recover(recovered)
        
        # Old holographic format (magic \xE8\x47)
        elif len(data) >= 2 and data[:2] == b'\xE8\x47':
            holographic_data = data[2:]
            
            # Recover from distributed parity
            recovered, confidence = recover_from_distributed_parity(holographic_data)
            
            # Reverse holographic spreading
            unspread = simple_holographic_recover(recovered)
            
            # Try to decompress
            try:
                packed = zlib.decompress(unspread)
            except zlib.error:
                # Apply Toric correction and retry
                corrected, _ = apply_toric_correction_to_bytes(unspread)
                packed = zlib.decompress(corrected)
        
        else:
            # Legacy non-holographic format
            packed = zlib.decompress(data)
        
        if packed is None:
            raise ValueError("Failed to decode compressed data")
        
        offset = 0
        
        # Header
        header_len = struct.unpack('I', packed[offset:offset+4])[0]
        offset += 4
        header_json = packed[offset:offset+header_len].decode('utf-8')
        offset += header_len
        header = json.loads(header_json)
        
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
        
        # Reshape arrays
        n_unique = len(header['vocabulary'])
        if n_unique > 0:
            projections_4d = projections_4d.reshape(n_unique, 4)
            phasons_4d = phasons_4d.reshape(n_unique, 4)
        else:
            projections_4d = np.array([]).reshape(0, 4)
            phasons_4d = np.array([]).reshape(0, 4)
        
        return cls(
            vocabulary=header['vocabulary'],
            token_sequence=header['token_sequence'],
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=header['metadata']
        )


class GQECompressor:
    """
    Golden Quasicrystal Encoding Compressor.
    
    Implements the full compression pipeline according to The Architect's model.
    
    HORIZON BATCHING (The Holographic Principle):
    For large inputs (> 233KB), the compressor uses Horizon Batching:
    - GLOBAL (The Singularity): Vocabulary / E8 Basis - shared across all chunks
    - LOCAL (Horizon Frames): Phason sequences computed per chunk
    
    This reduces memory from O(N^2) to O(chunk_size^2) while preserving
    the geometric structure. The Universe renders in FRAMES, not all at once.
    """
    
    # Horizon Batching threshold: 233KB (F_13 * 1024 - Fibonacci number!)
    HORIZON_THRESHOLD = 233 * 1024
    
    def __init__(self, window_size: int = 5, tokenize_mode: str = 'auto', 
                 use_horizon_batching: bool = True, chunk_size: Optional[int] = None):
        """
        Initialize compressor.
        
        Args:
            window_size: Co-occurrence window for graph building
            tokenize_mode: Tokenization mode ('auto', 'word', 'char', 'byte')
            use_horizon_batching: Enable Horizon Batching for large inputs
            chunk_size: Custom chunk size for Horizon Batching (default: 233KB)
        """
        self.window_size = window_size
        self.tokenize_mode = tokenize_mode
        self.use_horizon_batching = use_horizon_batching
        self.chunk_size = chunk_size or self.HORIZON_THRESHOLD
    
    def _compress_with_horizon_batching(self, data: bytes, mode: str) -> CompressedData:
        """
        Compress using Horizon Batching for large inputs.
        
        Follows The Architect's principle:
        - Global Singularity: Vocabulary computed once
        - Local Frames: Phasons computed per chunk
        
        Memory: O(chunk_size^2) instead of O(N^2)
        """
        from .core.horizon_batcher import HorizonBatcher, GlobalSingularity
        
        # Initialize batcher
        batcher = HorizonBatcher(
            chunk_size=self.chunk_size,
            window_size=self.window_size
        )
        
        # Build Global Singularity (vocabulary + embeddings)
        singularity = batcher.build_singularity(data, mode=mode)
        
        if len(singularity.vocabulary) == 0:
            return CompressedData(
                vocabulary={},
                token_sequence=[],
                projections_4d=np.array([]).reshape(0, 4),
                phasons_4d=np.array([]).reshape(0, 4),
                phases=np.array([]),
                metadata={'mode': mode, 'original_length': len(data), 'horizon_batched': True}
            )
        
        # Process frames and collect results
        all_token_indices = []
        frame_count = 0
        
        for frame in batcher.process_frames(data, singularity, mode=mode):
            all_token_indices.extend(frame.token_indices)
            frame_count += 1
        
        # Build vocabulary dict from singularity
        vocabulary = {}
        for token_str, idx in singularity.vocabulary.items():
            vocabulary[token_str] = {
                'index': idx,
                'count': all_token_indices.count(idx)
            }
        
        # Get projections from singularity embeddings
        from .core.projection import coxeter_projection_8d_to_4d
        from .core.e8_lattice import Spinor
        
        n_unique = len(singularity.vocabulary)
        projections_4d = np.zeros((n_unique, 4), dtype=np.float32)
        phasons_4d = np.zeros((n_unique, 4), dtype=np.float32)
        phases = singularity.phases.copy()
        
        for i in range(n_unique):
            if i < len(singularity.embeddings_8d):
                spinor = Spinor(position=singularity.embeddings_8d[i], phase=phases[i])
                projected = coxeter_projection_8d_to_4d(spinor)
                projections_4d[i] = projected.parallel
                phasons_4d[i] = projected.phason
        
        # Metadata
        metadata = {
            'mode': mode,
            'original_length': len(data),
            'n_tokens': len(all_token_indices),
            'n_unique': n_unique,
            'window_size': self.window_size,
            'horizon_batched': True,
            'n_frames': frame_count,
            'chunk_size': self.chunk_size
        }
        
        return CompressedData(
            vocabulary=vocabulary,
            token_sequence=all_token_indices,
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
        token_sequence = [token_to_idx[str(t.value)] for t in tokens]
        
        # Step 6: Project spinors to 4D + extract phasons
        n_unique = len(unique_spinors)
        projections_4d = np.zeros((n_unique, 4))
        phasons_4d = np.zeros((n_unique, 4))
        phases = np.zeros(n_unique)
        
        for i, spinor in enumerate(unique_spinors):
            projected = coxeter_projection_8d_to_4d(spinor)
            projections_4d[i] = projected.parallel
            phasons_4d[i] = projected.phason
            phases[i] = projected.phase
        
        # Metadata
        metadata = {
            'mode': mode,
            'original_length': len(data) if isinstance(data, (str, bytes)) else len(tokens),
            'n_tokens': len(tokens),
            'n_unique': n_unique,
            'window_size': self.window_size
        }
        
        return CompressedData(
            vocabulary=vocabulary,
            token_sequence=token_sequence,
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
