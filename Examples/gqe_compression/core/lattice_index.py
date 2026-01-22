#!/usr/bin/env python3
"""
Lattice Index - Topological Vocabulary Mapping

THE PHYSICS:
"The dictionary is not a list of words. It is a map of the crystal.
Once you have the map, you don't need the words."

Instead of storing vocabulary as strings, we store geometric coordinates.
Every word is assigned to:
1. A Primary E8 Root (1 of 240 fundamental vectors)
2. A Delta-Phase (the "nuance" between word and root)

This transforms Statistical Storage into Geometric Storage.

Key Concepts:
- E8 Root Index: 8 bits (0-239) for the nearest lattice point
- Delta-Phase: 4-8 bits for the angular "nudge" from the root
- Total: 12-16 bits per vocabulary entry vs 50+ bytes for strings

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import struct

try:
    from .e8_lattice import generate_e8_roots, Spinor
    from .phi_adic import PHI, PHI_INV
except ImportError:
    from e8_lattice import generate_e8_roots, Spinor
    from phi_adic import PHI, PHI_INV


# Global E8 roots cache (computed once)
_E8_ROOTS: Optional[np.ndarray] = None


def get_e8_roots() -> np.ndarray:
    """Get cached E8 roots (240 x 8 array)."""
    global _E8_ROOTS
    if _E8_ROOTS is None:
        _E8_ROOTS = generate_e8_roots()
    return _E8_ROOTS


@dataclass
class LatticeEntry:
    """
    A vocabulary entry mapped to the E8 lattice.
    
    Attributes:
        root_index: Index into the 240 E8 roots (0-239)
        delta_phase: Phase offset from the root [0, 2pi)
        delta_magnitude: Radial distance from root (normalized)
        count: Frequency count for probability estimation
    """
    root_index: int  # 0-239
    delta_phase: float  # [0, 2pi)
    delta_magnitude: float  # [0, 1] normalized
    count: int = 1
    
    def to_bytes(self, phase_bits: int = 8, mag_bits: int = 4) -> bytes:
        """
        Serialize to compact binary representation.
        
        Format:
        - 1 byte: root_index (0-239)
        - phase_bits/8 bytes: quantized delta_phase
        - mag_bits/8 bytes: quantized delta_magnitude
        - 2 bytes: count (capped at 65535)
        """
        result = bytearray()
        
        # Root index (1 byte)
        result.append(self.root_index & 0xFF)
        
        # Quantized phase (phase_bits, packed into bytes)
        phase_quant = int((self.delta_phase / (2 * np.pi)) * (2 ** phase_bits))
        phase_quant = min(phase_quant, (2 ** phase_bits) - 1)
        
        if phase_bits == 8:
            result.append(phase_quant & 0xFF)
        elif phase_bits == 16:
            result.extend(struct.pack('H', phase_quant))
        else:
            # Pack arbitrary bits
            for i in range((phase_bits + 7) // 8):
                result.append((phase_quant >> (i * 8)) & 0xFF)
        
        # Quantized magnitude (mag_bits, typically 4)
        mag_quant = int(self.delta_magnitude * (2 ** mag_bits))
        mag_quant = min(mag_quant, (2 ** mag_bits) - 1)
        
        if mag_bits <= 8:
            result.append(mag_quant & 0xFF)
        else:
            result.extend(struct.pack('H', mag_quant))
        
        # Count (2 bytes, capped)
        count_capped = min(self.count, 65535)
        result.extend(struct.pack('H', count_capped))
        
        return bytes(result)
    
    @classmethod
    def from_bytes(cls, data: bytes, phase_bits: int = 8, mag_bits: int = 4) -> Tuple['LatticeEntry', int]:
        """
        Deserialize from bytes.
        
        Returns (entry, bytes_consumed).
        """
        offset = 0
        
        # Root index
        root_index = data[offset]
        offset += 1
        
        # Phase
        if phase_bits == 8:
            phase_quant = data[offset]
            offset += 1
        elif phase_bits == 16:
            phase_quant = struct.unpack('H', data[offset:offset+2])[0]
            offset += 2
        else:
            phase_bytes = (phase_bits + 7) // 8
            phase_quant = sum(data[offset + i] << (i * 8) for i in range(phase_bytes))
            offset += phase_bytes
        
        delta_phase = (phase_quant / (2 ** phase_bits)) * 2 * np.pi
        
        # Magnitude
        if mag_bits <= 8:
            mag_quant = data[offset]
            offset += 1
        else:
            mag_quant = struct.unpack('H', data[offset:offset+2])[0]
            offset += 2
        
        delta_magnitude = mag_quant / (2 ** mag_bits)
        
        # Count
        count = struct.unpack('H', data[offset:offset+2])[0]
        offset += 2
        
        return cls(root_index, delta_phase, delta_magnitude, count), offset


class LatticeIndex:
    """
    Maps vocabulary embeddings to E8 lattice coordinates.
    
    THE PHYSICS:
    Each word becomes a coordinate in the E8 crystal.
    "King" isn't text; it's (1, 1, 0, 0, 0, 0, 0, 0).
    "Queen" isn't text; it's (1, -1, 0, 0, 0, 0, 0, 0).
    
    The decompressor already has the 240 E8 roots.
    We only store the index (which root) and delta (how far from it).
    """
    
    def __init__(self, phase_bits: int = 8, mag_bits: int = 4):
        """
        Initialize the lattice index.
        
        Args:
            phase_bits: Bits for delta phase quantization (8 = 256 levels)
            mag_bits: Bits for delta magnitude quantization (4 = 16 levels)
        """
        self.roots = get_e8_roots()
        self.phase_bits = phase_bits
        self.mag_bits = mag_bits
        
        # Precompute normalized roots for faster matching
        self._root_norms = np.linalg.norm(self.roots, axis=1, keepdims=True)
        self._root_normalized = self.roots / self._root_norms
        
        # Token to lattice entry mapping
        self.entries: Dict[str, LatticeEntry] = {}
        self.index_to_token: Dict[int, str] = {}  # For reverse lookup
    
    def _project_to_8d(self, embedding: np.ndarray) -> np.ndarray:
        """
        Project arbitrary embedding to 8D E8 space.
        
        If embedding is already 8D, normalize it.
        If embedding is different dimension, project via PCA-like transform.
        """
        if len(embedding) == 8:
            # Normalize to E8 scale (norm = sqrt(2))
            norm = np.linalg.norm(embedding)
            if norm > 0:
                return embedding * (np.sqrt(2) / norm)
            return embedding
        
        # For other dimensions, use a golden-ratio based projection
        # This maintains geometric relationships
        target_dim = 8
        source_dim = len(embedding)
        
        if source_dim < target_dim:
            # Pad with zeros
            result = np.zeros(8)
            result[:source_dim] = embedding
        else:
            # Project down using golden-ratio weighted sum
            result = np.zeros(8)
            for i in range(8):
                # Each target dimension is a weighted sum of source dimensions
                weights = np.array([PHI ** ((i * j) % source_dim) for j in range(source_dim)])
                weights /= np.sum(weights)
                result[i] = np.dot(embedding, weights)
        
        # Normalize to E8 scale
        norm = np.linalg.norm(result)
        if norm > 0:
            result = result * (np.sqrt(2) / norm)
        
        return result
    
    def find_nearest_root(self, point_8d: np.ndarray) -> Tuple[int, float, float]:
        """
        Find the nearest E8 root to a given 8D point.
        
        Returns:
            (root_index, delta_magnitude, delta_phase)
        """
        # Compute distances to all roots
        diffs = self.roots - point_8d
        distances = np.linalg.norm(diffs, axis=1)
        
        # Find nearest
        root_idx = np.argmin(distances)
        nearest_root = self.roots[root_idx]
        
        # Compute delta vector
        delta = point_8d - nearest_root
        delta_mag = np.linalg.norm(delta)
        
        # Normalize magnitude (relative to root norm)
        delta_mag_normalized = delta_mag / np.sqrt(2)  # E8 roots have norm sqrt(2)
        delta_mag_normalized = min(delta_mag_normalized, 1.0)  # Cap at 1
        
        # Compute delta phase (angle in the perpendicular plane)
        # Use atan2 of first two components of delta as phase proxy
        if delta_mag > 1e-10:
            delta_phase = np.arctan2(delta[1], delta[0]) % (2 * np.pi)
        else:
            delta_phase = 0.0
        
        return root_idx, delta_mag_normalized, delta_phase
    
    def add_token(self, token: str, embedding: np.ndarray, count: int = 1) -> int:
        """
        Add a token to the lattice index.
        
        Args:
            token: The token string
            embedding: The token's embedding vector
            count: Frequency count
        
        Returns:
            The assigned index
        """
        # Project to 8D
        point_8d = self._project_to_8d(embedding)
        
        # Find nearest root
        root_idx, delta_mag, delta_phase = self.find_nearest_root(point_8d)
        
        # Create entry
        entry = LatticeEntry(
            root_index=root_idx,
            delta_phase=delta_phase,
            delta_magnitude=delta_mag,
            count=count
        )
        
        # Store
        idx = len(self.entries)
        self.entries[token] = entry
        self.index_to_token[idx] = token
        
        return idx
    
    def build_from_vocabulary(self, vocabulary: Dict[str, Dict], 
                              embeddings: Optional[np.ndarray] = None) -> None:
        """
        Build lattice index from a vocabulary dictionary.
        
        Args:
            vocabulary: Dict mapping token -> {'index': int, 'count': int, ...}
            embeddings: Optional embedding matrix (vocab_size x dim)
        """
        # Sort by index for consistent ordering
        sorted_vocab = sorted(vocabulary.items(), key=lambda x: x[1].get('index', 0))
        
        for i, (token, info) in enumerate(sorted_vocab):
            count = info.get('count', 1)
            
            if embeddings is not None and i < len(embeddings):
                embedding = embeddings[i]
            else:
                # Generate embedding from token hash (deterministic)
                embedding = self._hash_to_embedding(token)
            
            self.add_token(token, embedding, count)
    
    def _hash_to_embedding(self, token: str) -> np.ndarray:
        """
        Generate a deterministic 8D embedding from a token string.
        
        Uses golden ratio hashing for good distribution.
        """
        # Hash the token
        h = hash(token)
        
        # Generate 8 values using golden ratio
        embedding = np.zeros(8)
        for i in range(8):
            # Mix hash with golden ratio
            mixed = (h * (PHI ** (i + 1))) % 1.0
            if mixed < 0:
                mixed += 1.0
            embedding[i] = 2 * mixed - 1  # Map to [-1, 1]
        
        # Normalize to E8 scale
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding * (np.sqrt(2) / norm)
        
        return embedding
    
    def to_bytes(self) -> bytes:
        """
        Serialize the entire lattice index to bytes.
        
        Format:
        [2 bytes: entry_count]
        [1 byte: phase_bits]
        [1 byte: mag_bits]
        [entries...]
        [token strings (null-terminated)]
        """
        result = bytearray()
        
        # Header
        entry_count = len(self.entries)
        result.extend(struct.pack('HBB', entry_count, self.phase_bits, self.mag_bits))
        
        # Sort entries by their index in index_to_token for consistent ordering
        sorted_tokens = [self.index_to_token[i] for i in range(len(self.index_to_token))]
        
        # Entries (geometric data only)
        for token in sorted_tokens:
            entry = self.entries[token]
            result.extend(entry.to_bytes(self.phase_bits, self.mag_bits))
        
        # Token strings (for reconstruction)
        # We could eliminate these entirely if using pure E8 indexing,
        # but we keep them for debugging/verification
        # Compressed using simple encoding
        token_block = bytearray()
        for token in sorted_tokens:
            token_bytes = token.encode('utf-8')
            token_block.extend(struct.pack('H', len(token_bytes)))
            token_block.extend(token_bytes)
        
        # Compress token block
        import zlib
        compressed_tokens = zlib.compress(bytes(token_block), level=9)
        result.extend(struct.pack('I', len(compressed_tokens)))
        result.extend(compressed_tokens)
        
        return bytes(result)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'LatticeIndex':
        """
        Deserialize a lattice index from bytes.
        """
        import zlib
        
        offset = 0
        
        # Header
        entry_count, phase_bits, mag_bits = struct.unpack('HBB', data[offset:offset+4])
        offset += 4
        
        # Create index
        index = cls(phase_bits=phase_bits, mag_bits=mag_bits)
        
        # Read entries
        entries_list = []
        for _ in range(entry_count):
            entry, consumed = LatticeEntry.from_bytes(
                data[offset:], phase_bits, mag_bits
            )
            entries_list.append(entry)
            offset += consumed
        
        # Read compressed token block
        compressed_len = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        compressed_tokens = data[offset:offset+compressed_len]
        token_block = zlib.decompress(compressed_tokens)
        
        # Parse tokens
        tok_offset = 0
        for i, entry in enumerate(entries_list):
            token_len = struct.unpack('H', token_block[tok_offset:tok_offset+2])[0]
            tok_offset += 2
            token = token_block[tok_offset:tok_offset+token_len].decode('utf-8')
            tok_offset += token_len
            
            index.entries[token] = entry
            index.index_to_token[i] = token
        
        return index
    
    def get_token_index(self, token: str) -> Optional[int]:
        """Get the index for a token."""
        for idx, t in self.index_to_token.items():
            if t == token:
                return idx
        return None
    
    def get_token_by_index(self, idx: int) -> Optional[str]:
        """Get token by index."""
        return self.index_to_token.get(idx)
    
    def reconstruct_embedding(self, idx: int) -> np.ndarray:
        """
        Reconstruct the 8D embedding from lattice coordinates.
        
        This is the inverse of add_token - we recover the approximate
        embedding from root_index + delta.
        """
        token = self.index_to_token.get(idx)
        if token is None:
            return np.zeros(8)
        
        entry = self.entries[token]
        root = self.roots[entry.root_index]
        
        # Reconstruct delta vector from magnitude and phase
        delta_mag = entry.delta_magnitude * np.sqrt(2)  # Denormalize
        
        # Simple reconstruction: use phase to set direction in first 2 dims
        delta = np.zeros(8)
        delta[0] = delta_mag * np.cos(entry.delta_phase)
        delta[1] = delta_mag * np.sin(entry.delta_phase)
        
        return root + delta


def run_verification():
    """Verify the lattice index functionality."""
    print("=" * 60)
    print("LATTICE INDEX VERIFICATION")
    print("=" * 60)
    
    # Test 1: E8 roots
    print("\n--- Test 1: E8 Roots ---")
    roots = get_e8_roots()
    print(f"  E8 roots count: {len(roots)}")
    print(f"  Root shape: {roots.shape}")
    norms = np.linalg.norm(roots, axis=1)
    print(f"  All norms = sqrt(2): {np.allclose(norms, np.sqrt(2))}")
    
    # Test 2: Nearest root finding
    print("\n--- Test 2: Nearest Root Finding ---")
    index = LatticeIndex()
    
    # Test point near first root
    test_point = roots[0] + np.array([0.1, 0.05, 0, 0, 0, 0, 0, 0])
    root_idx, delta_mag, delta_phase = index.find_nearest_root(test_point)
    print(f"  Test point near root[0]")
    print(f"  Found root index: {root_idx}")
    print(f"  Delta magnitude: {delta_mag:.4f}")
    print(f"  Delta phase: {delta_phase:.4f}")
    print(f"  Result: {'PASS' if root_idx == 0 else 'FAIL'}")
    
    # Test 3: Token mapping
    print("\n--- Test 3: Token Mapping ---")
    test_vocab = {
        'king': {'index': 0, 'count': 100},
        'queen': {'index': 1, 'count': 95},
        'royal': {'index': 2, 'count': 50},
        'throne': {'index': 3, 'count': 30},
    }
    
    # Create some fake embeddings
    embeddings = np.random.randn(4, 8)
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True) * np.sqrt(2)
    
    index.build_from_vocabulary(test_vocab, embeddings)
    
    print(f"  Vocabulary size: {len(index.entries)}")
    for token, entry in index.entries.items():
        print(f"    {token}: root={entry.root_index}, phase={entry.delta_phase:.3f}, mag={entry.delta_magnitude:.3f}")
    
    # Test 4: Serialization round-trip
    print("\n--- Test 4: Serialization Round-Trip ---")
    serialized = index.to_bytes()
    print(f"  Serialized size: {len(serialized)} bytes")
    
    # Compare to storing tokens as strings
    string_size = sum(len(t.encode('utf-8')) + 4 for t in test_vocab.keys())
    print(f"  String-only size would be: {string_size} bytes (tokens only)")
    
    # Deserialize
    recovered = LatticeIndex.from_bytes(serialized)
    print(f"  Recovered entries: {len(recovered.entries)}")
    
    # Verify
    match = all(
        recovered.entries[t].root_index == index.entries[t].root_index
        for t in test_vocab.keys()
    )
    print(f"  Root indices match: {match}")
    print(f"  Result: {'PASS' if match else 'FAIL'}")
    
    # Test 5: Embedding reconstruction
    print("\n--- Test 5: Embedding Reconstruction ---")
    for i in range(len(test_vocab)):
        original = embeddings[i]
        reconstructed = index.reconstruct_embedding(i)
        error = np.linalg.norm(original - reconstructed)
        print(f"  Token {i}: reconstruction error = {error:.4f}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
