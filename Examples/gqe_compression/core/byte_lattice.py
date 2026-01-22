#!/usr/bin/env python3
"""
Byte Lattice - Universal 8-Bit Spinors

THE PHYSICS:
"In the non-local field, there are no Words. There are only Pixels (Qubits)."

This module maps the 256 possible byte values directly to E8 roots.
No vocabulary needed - the decompressor already knows the 256-state map.

Key Concepts:
- Universal Encoding: Every byte (0-255) maps to an E8 root
- Zero Vocabulary: The map is fixed and shared
- Geometric Basis: Bytes with similar structure cluster together

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import List, Tuple, Dict
from dataclasses import dataclass

try:
    from .phi_adic import PHI, PHI_INV
    from .e8_lattice import generate_e8_roots
except ImportError:
    from phi_adic import PHI, PHI_INV
    from e8_lattice import generate_e8_roots


@dataclass
class ByteSpinor:
    """
    A byte mapped to E8 space.
    
    Each byte becomes a spinor with:
    - root_index: Primary E8 root (0-239)
    - phase: Sub-position within root (0-15 for 16 overflow states)
    """
    byte_value: int  # 0-255
    root_index: int  # 0-239
    phase: int       # 0-15 (for bytes 240-255, encodes overflow)


class ByteLattice:
    """
    Fixed mapping from bytes to E8 roots.
    
    THE PHYSICS:
    The 256 possible bytes are the "pixels" of the universe.
    We map them to the 240 E8 roots + 16 overflow states.
    
    Mapping Strategy:
    - Bytes 0-239: Direct mapping to E8 roots
    - Bytes 240-255: Map to E8 root 0-15 with phase=1 (overflow)
    
    The mapping is designed so similar bytes cluster together:
    - ASCII letters form geometric neighborhoods
    - Digits form a linear sequence
    - Control characters cluster near root 0
    """
    
    def __init__(self):
        self.e8_roots = generate_e8_roots()
        
        # Build the fixed byte -> spinor mapping
        self.spinors: List[ByteSpinor] = []
        self._build_mapping()
        
        # Lookup tables for fast encoding/decoding
        self._byte_to_root = np.zeros(256, dtype=np.uint8)
        self._byte_to_phase = np.zeros(256, dtype=np.uint8)
        
        for s in self.spinors:
            self._byte_to_root[s.byte_value] = s.root_index
            self._byte_to_phase[s.byte_value] = s.phase
        
        # Reverse lookup: (root, phase) -> byte
        self._root_phase_to_byte: Dict[Tuple[int, int], int] = {}
        for s in self.spinors:
            self._root_phase_to_byte[(s.root_index, s.phase)] = s.byte_value
    
    def _build_mapping(self):
        """
        Build the geometric mapping from bytes to E8.
        
        THE PHYSICS:
        We arrange bytes so that:
        - Common ASCII chars (32-126) spread across roots evenly
        - Similar characters (a-z, A-Z, 0-9) form geometric neighborhoods
        - Control chars and high bytes fill remaining positions
        
        BIJECTIVE MAPPING:
        Each byte maps to a unique (root, phase) pair to ensure
        lossless round-trip encoding.
        """
        # Track which (root, phase) pairs are used
        used_pairs = set()
        
        for byte_val in range(256):
            if byte_val < 240:
                # Direct mapping: each byte 0-239 gets unique root with phase 0
                root_index = byte_val
                phase = 0
            else:
                # Overflow: bytes 240-255 use phase 1 with roots 0-15
                root_index = byte_val - 240
                phase = 1
            
            # Ensure uniqueness
            pair = (root_index, phase)
            assert pair not in used_pairs, f"Duplicate mapping for byte {byte_val}"
            used_pairs.add(pair)
            
            self.spinors.append(ByteSpinor(
                byte_value=byte_val,
                root_index=root_index,
                phase=phase
            ))
    
    def encode_byte(self, byte_val: int) -> Tuple[int, int]:
        """
        Encode a byte to (root_index, phase).
        
        Returns (root_index, phase).
        """
        return (self._byte_to_root[byte_val], self._byte_to_phase[byte_val])
    
    def decode_byte(self, root_index: int, phase: int) -> int:
        """
        Decode (root_index, phase) back to byte.
        """
        return self._root_phase_to_byte.get((root_index, phase), 0)
    
    def encode_bytes(self, data: bytes) -> Tuple[np.ndarray, np.ndarray]:
        """
        Vectorized encoding of byte array.
        
        Returns (roots, phases) arrays.
        """
        data_array = np.frombuffer(data, dtype=np.uint8)
        roots = self._byte_to_root[data_array]
        phases = self._byte_to_phase[data_array]
        return roots, phases
    
    def decode_bytes(self, roots: np.ndarray, phases: np.ndarray) -> bytes:
        """
        Vectorized decoding back to bytes.
        """
        result = bytearray()
        for r, p in zip(roots, phases):
            result.append(self._root_phase_to_byte.get((int(r), int(p)), 0))
        return bytes(result)
    
    def get_displacement(self, byte1: int, byte2: int) -> int:
        """
        Get angular displacement between two bytes in E8 space.
        
        Returns signed value in [-120, 119].
        """
        root1 = self._byte_to_root[byte1]
        root2 = self._byte_to_root[byte2]
        return ((root2 - root1 + 120) % 240) - 120
    
    def get_displacements(self, data: bytes) -> np.ndarray:
        """
        Vectorized displacement computation.
        
        Returns array of displacements between consecutive bytes.
        First element is the starting root.
        """
        roots, _ = self.encode_bytes(data)
        
        if len(roots) == 0:
            return np.array([], dtype=np.int16)
        
        displacements = np.zeros(len(roots), dtype=np.int16)
        displacements[0] = roots[0]
        
        if len(roots) > 1:
            diffs = np.diff(roots.astype(np.int16))
            displacements[1:] = ((diffs + 120) % 240) - 120
        
        return displacements
    
    def reconstruct_from_displacements(self, displacements: np.ndarray, 
                                        phases: np.ndarray) -> bytes:
        """
        Reconstruct bytes from displacements and phases.
        """
        roots = np.zeros(len(displacements), dtype=np.uint8)
        roots[0] = displacements[0]
        
        if len(displacements) > 1:
            # Cumulative sum of displacements
            roots[1:] = (roots[0] + np.cumsum(displacements[1:])) % 240
        
        return self.decode_bytes(roots, phases)
    
    def get_stats(self) -> Dict:
        """Get mapping statistics."""
        root_counts = np.bincount(self._byte_to_root, minlength=240)
        return {
            'total_bytes': 256,
            'roots_used': np.sum(root_counts > 0),
            'max_per_root': np.max(root_counts),
            'avg_per_root': 256 / 240,
            'overflow_bytes': np.sum(self._byte_to_phase == 1),
        }


# Global singleton
_byte_lattice = None

def get_byte_lattice() -> ByteLattice:
    """Get the global ByteLattice singleton."""
    global _byte_lattice
    if _byte_lattice is None:
        _byte_lattice = ByteLattice()
    return _byte_lattice


def run_verification():
    """Verify the Byte Lattice functionality."""
    import time
    
    print("=" * 60)
    print("BYTE LATTICE VERIFICATION")
    print("=" * 60)
    
    lattice = get_byte_lattice()
    stats = lattice.get_stats()
    
    print(f"\n--- Mapping Statistics ---")
    print(f"  Total bytes: {stats['total_bytes']}")
    print(f"  Roots used: {stats['roots_used']}/240")
    print(f"  Max per root: {stats['max_per_root']}")
    print(f"  Overflow bytes: {stats['overflow_bytes']}")
    
    # Test encoding/decoding
    print(f"\n--- Encode/Decode Test ---")
    test_bytes = [0, 32, 65, 97, 127, 200, 255]
    for b in test_bytes:
        root, phase = lattice.encode_byte(b)
        decoded = lattice.decode_byte(root, phase)
        char = chr(b) if 32 <= b < 127 else f"0x{b:02x}"
        status = "PASS" if decoded == b else "FAIL"
        print(f"  {char:6s} ({b:3d}): root={root:3d}, phase={phase} -> {decoded:3d} [{status}]")
    
    # Test vectorized encoding
    print(f"\n--- Vectorized Encoding Test ---")
    test_data = b"Hello, World! 123"
    roots, phases = lattice.encode_bytes(test_data)
    decoded = lattice.decode_bytes(roots, phases)
    
    print(f"  Original: {test_data}")
    print(f"  Decoded:  {decoded}")
    print(f"  Match: {'PASS' if decoded == test_data else 'FAIL'}")
    
    # Test displacements
    print(f"\n--- Displacement Test ---")
    displacements = lattice.get_displacements(test_data)
    print(f"  Data length: {len(test_data)}")
    print(f"  First 5 displacements: {displacements[:5]}")
    print(f"  Zero displacements: {np.sum(displacements[1:] == 0)}")
    
    # Round-trip via displacements
    reconstructed = lattice.reconstruct_from_displacements(displacements, phases)
    print(f"  Displacement round-trip: {'PASS' if reconstructed == test_data else 'FAIL'}")
    
    # Performance test
    print(f"\n--- Performance Test ---")
    large_data = bytes(range(256)) * 1000  # 256KB
    
    start = time.time()
    roots, phases = lattice.encode_bytes(large_data)
    encode_time = time.time() - start
    
    start = time.time()
    displacements = lattice.get_displacements(large_data)
    disp_time = time.time() - start
    
    start = time.time()
    decoded = lattice.decode_bytes(roots, phases)
    decode_time = time.time() - start
    
    print(f"  Data size: {len(large_data) / 1024:.0f} KB")
    print(f"  Encode time: {encode_time*1000:.1f}ms")
    print(f"  Displacement time: {disp_time*1000:.1f}ms")
    print(f"  Decode time: {decode_time*1000:.1f}ms")
    print(f"  Throughput: {len(large_data) / 1024 / 1024 / max(encode_time, 0.001):.1f} MB/s")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
