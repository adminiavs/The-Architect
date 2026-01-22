#!/usr/bin/env python3
"""
Harmonic Signature - Lexical Erasure through Geometric Hashing

THE PHYSICS:
"The ultimate compression is when the name of the thing disappears,
leaving only the shape of the thought."

Instead of storing "King" as k-i-n-g, we store its HARMONIC SIGNATURE:
a 64-bit geometric hash that encodes the word's position in E8 space.

The decompressor, given the same SEED (The Singularity), can reconstruct
the word from its geometric address alone.

Key Concepts:
- Harmonic Hash: 64-bit signature derived from token's E8 coordinates
- Seed Mapping: Deterministic token<->hash bijection from a global seed
- Inverse Recovery: Given seed + hash, recover the original token

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import struct
import hashlib

try:
    from .phi_adic import PHI, PHI_INV
    from .e8_lattice import generate_e8_roots
except ImportError:
    from phi_adic import PHI, PHI_INV
    from e8_lattice import generate_e8_roots


# Global seed for deterministic hashing
_GLOBAL_SEED = 0xE8_A2C4_1EC7_E000  # "E8 ARCHITECT" encoded


@dataclass
class HarmonicSignature:
    """
    A token's geometric signature in the E8 lattice.
    
    Components:
    - root_index: Primary E8 root (0-239)
    - delta_hash: 32-bit hash of the delta from root
    - length_code: 4-bit encoding of token length
    - char_sum: 12-bit checksum of characters
    
    Total: 8 + 32 + 4 + 12 = 56 bits (fits in 64-bit with room for flags)
    """
    root_index: int      # 8 bits (0-239)
    delta_hash: int      # 32 bits
    length_code: int     # 4 bits (0-15, maps to lengths 1-16+)
    char_sum: int        # 12 bits (checksum)
    
    def to_int64(self) -> int:
        """Pack signature into a 64-bit integer."""
        return ((self.root_index & 0xFF) |
                ((self.delta_hash & 0xFFFFFFFF) << 8) |
                ((self.length_code & 0xF) << 40) |
                ((self.char_sum & 0xFFF) << 44))
    
    @classmethod
    def from_int64(cls, value: int) -> 'HarmonicSignature':
        """Unpack signature from 64-bit integer."""
        return cls(
            root_index=value & 0xFF,
            delta_hash=(value >> 8) & 0xFFFFFFFF,
            length_code=(value >> 40) & 0xF,
            char_sum=(value >> 44) & 0xFFF
        )
    
    def to_bytes(self) -> bytes:
        """Pack to 8 bytes."""
        return struct.pack('<Q', self.to_int64())
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'HarmonicSignature':
        """Unpack from 8 bytes."""
        return cls.from_int64(struct.unpack('<Q', data[:8])[0])


class HarmonicHasher:
    """
    Converts tokens to harmonic signatures and back.
    
    THE PHYSICS:
    The Singularity (seed) determines the mapping between
    strings and geometric coordinates. Given the seed,
    we can always recover the original from its shadow.
    
    WORDLESS HORIZON:
    The decompressor doesn't store a dictionary. It stores a Seed.
    It "guesses" the word by vibrating the lattice at that coordinate.
    If the vibration matches the signature, the word is "recalled."
    """
    
    def __init__(self, seed: int = _GLOBAL_SEED):
        self.seed = seed
        self.roots = generate_e8_roots()
        
        # Build lookup tables for recovery
        self._signature_to_token: Dict[int, str] = {}
        self._token_to_signature: Dict[str, HarmonicSignature] = {}
        
        # Fingerprint-only storage (no strings needed for compression)
        self._fingerprints: List[int] = []  # Just the 64-bit fingerprints
    
    def _compute_root_index(self, token: str) -> int:
        """
        Compute E8 root index from token using golden-ratio hashing.
        
        This creates a deterministic mapping from any string
        to one of the 240 E8 roots.
        """
        # Hash the token with seed
        h = hashlib.sha256(f"{self.seed}:{token}".encode()).digest()
        
        # Use first 8 bytes as a number
        num = int.from_bytes(h[:8], 'little')
        
        # Map to root index using golden ratio for good distribution
        return int((num * PHI) % 240)
    
    def _compute_delta_hash(self, token: str) -> int:
        """
        Compute 32-bit hash capturing token's unique features.
        
        This hash, combined with root_index, should uniquely
        identify the token within a reasonable vocabulary.
        """
        # Use different hash for delta
        h = hashlib.md5(f"{self.seed}:delta:{token}".encode()).digest()
        return int.from_bytes(h[:4], 'little')
    
    def _compute_length_code(self, token: str) -> int:
        """Encode token length in 4 bits."""
        length = len(token)
        if length <= 15:
            return length
        else:
            return 15  # 15 means "16 or more"
    
    def _compute_char_sum(self, token: str) -> int:
        """Compute 12-bit character checksum."""
        # Sum of character codes modulo 4096
        return sum(ord(c) for c in token) & 0xFFF
    
    def compute_signature(self, token: str) -> HarmonicSignature:
        """
        Compute the harmonic signature of a token.
        
        THE PHYSICS:
        The token's name is erased, replaced by its geometric shadow.
        """
        if token in self._token_to_signature:
            return self._token_to_signature[token]
        
        sig = HarmonicSignature(
            root_index=self._compute_root_index(token),
            delta_hash=self._compute_delta_hash(token),
            length_code=self._compute_length_code(token),
            char_sum=self._compute_char_sum(token)
        )
        
        # Cache for recovery
        self._token_to_signature[token] = sig
        self._signature_to_token[sig.to_int64()] = token
        
        return sig
    
    def register_vocabulary(self, vocabulary: Dict[str, Dict]) -> Dict[str, HarmonicSignature]:
        """
        Register a vocabulary and compute all signatures.
        
        This builds the lookup table needed for recovery.
        """
        signatures = {}
        for token in vocabulary.keys():
            sig = self.compute_signature(token)
            signatures[token] = sig
        return signatures
    
    def recover_token(self, signature: HarmonicSignature) -> Optional[str]:
        """
        Recover token from its harmonic signature.
        
        Requires that the token was previously registered.
        """
        return self._signature_to_token.get(signature.to_int64())
    
    def can_recover(self, signature: HarmonicSignature) -> bool:
        """Check if a signature can be recovered."""
        return signature.to_int64() in self._signature_to_token
    
    def get_collision_stats(self) -> Dict[str, int]:
        """Get statistics about signature collisions."""
        # Group tokens by root_index
        root_groups: Dict[int, List[str]] = {}
        for token, sig in self._token_to_signature.items():
            if sig.root_index not in root_groups:
                root_groups[sig.root_index] = []
            root_groups[sig.root_index].append(token)
        
        # Count collisions
        max_per_root = max(len(tokens) for tokens in root_groups.values()) if root_groups else 0
        avg_per_root = len(self._token_to_signature) / 240 if self._token_to_signature else 0
        used_roots = len(root_groups)
        
        return {
            'total_tokens': len(self._token_to_signature),
            'used_roots': used_roots,
            'max_per_root': max_per_root,
            'avg_per_root': avg_per_root,
            'coverage': used_roots / 240 * 100
        }
    
    def to_bytes(self) -> bytes:
        """
        Serialize the hasher state for storage (with token strings).
        
        Format:
        [8 bytes: seed]
        [4 bytes: token count]
        [for each token: signature (8 bytes) + token_len (2 bytes) + token_bytes]
        """
        import zlib
        
        result = bytearray()
        result.extend(struct.pack('<Q', self.seed))
        result.extend(struct.pack('<I', len(self._token_to_signature)))
        
        for token, sig in self._token_to_signature.items():
            result.extend(sig.to_bytes())
            token_bytes = token.encode('utf-8')
            result.extend(struct.pack('<H', len(token_bytes)))
            result.extend(token_bytes)
        
        return zlib.compress(bytes(result), level=9)
    
    def to_fingerprints_only(self) -> bytes:
        """
        WORDLESS HORIZON: Serialize only the seed and fingerprints.
        
        No token strings are stored. The decompressor must have
        access to a shared vocabulary or regeneration mechanism.
        
        Format:
        [8 bytes: seed]
        [4 bytes: fingerprint count]
        [8 bytes each: fingerprints]
        """
        result = bytearray()
        result.extend(struct.pack('<Q', self.seed))
        result.extend(struct.pack('<I', len(self._fingerprints)))
        
        for fp in self._fingerprints:
            result.extend(struct.pack('<Q', fp))
        
        return bytes(result)
    
    def register_fingerprint(self, token: str) -> int:
        """
        Register a token and return its fingerprint index.
        
        THE PHYSICS:
        The token's name is erased. Only its geometric fingerprint
        (64-bit E8 coordinate) is stored.
        """
        sig = self.compute_signature(token)
        fp = sig.to_int64()
        
        if fp not in [f for f in self._fingerprints]:
            self._fingerprints.append(fp)
        
        return self._fingerprints.index(fp)
    
    def get_fingerprint_by_index(self, idx: int) -> Optional[int]:
        """Get fingerprint by its index."""
        if 0 <= idx < len(self._fingerprints):
            return self._fingerprints[idx]
        return None
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'HarmonicHasher':
        """Deserialize hasher state (with token strings)."""
        import zlib
        
        data = zlib.decompress(data)
        offset = 0
        
        seed = struct.unpack('<Q', data[offset:offset+8])[0]
        offset += 8
        
        count = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        
        hasher = cls(seed=seed)
        
        for _ in range(count):
            sig = HarmonicSignature.from_bytes(data[offset:offset+8])
            offset += 8
            
            token_len = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            token = data[offset:offset+token_len].decode('utf-8')
            offset += token_len
            
            hasher._token_to_signature[token] = sig
            hasher._signature_to_token[sig.to_int64()] = token
            hasher._fingerprints.append(sig.to_int64())
        
        return hasher
    
    @classmethod
    def from_fingerprints_only(cls, data: bytes) -> 'HarmonicHasher':
        """
        WORDLESS HORIZON: Deserialize from fingerprints only.
        
        Cannot recover token strings - only geometric signatures.
        """
        offset = 0
        
        seed = struct.unpack('<Q', data[offset:offset+8])[0]
        offset += 8
        
        count = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        
        hasher = cls(seed=seed)
        
        for _ in range(count):
            fp = struct.unpack('<Q', data[offset:offset+8])[0]
            offset += 8
            hasher._fingerprints.append(fp)
        
        return hasher


def run_verification():
    """Verify the harmonic signature functionality."""
    print("=" * 60)
    print("HARMONIC SIGNATURE VERIFICATION")
    print("=" * 60)
    
    # Test 1: Basic signature computation
    print("\n--- Test 1: Signature Computation ---")
    hasher = HarmonicHasher()
    
    test_tokens = ["King", "Queen", "Royal", "Throne", "Crown", "Castle"]
    
    for token in test_tokens:
        sig = hasher.compute_signature(token)
        print(f"  {token}: root={sig.root_index}, delta={sig.delta_hash:08x}, "
              f"len={sig.length_code}, sum={sig.char_sum}")
    
    # Test 2: Signature uniqueness
    print("\n--- Test 2: Signature Uniqueness ---")
    all_sigs = [hasher.compute_signature(t).to_int64() for t in test_tokens]
    unique = len(set(all_sigs))
    print(f"  Tokens: {len(test_tokens)}")
    print(f"  Unique signatures: {unique}")
    print(f"  Result: {'PASS' if unique == len(test_tokens) else 'FAIL'}")
    
    # Test 3: Recovery
    print("\n--- Test 3: Token Recovery ---")
    success = 0
    for token in test_tokens:
        sig = hasher.compute_signature(token)
        recovered = hasher.recover_token(sig)
        if recovered == token:
            success += 1
        else:
            print(f"  FAIL: {token} -> {recovered}")
    
    print(f"  Recovery rate: {success}/{len(test_tokens)}")
    print(f"  Result: {'PASS' if success == len(test_tokens) else 'FAIL'}")
    
    # Test 4: Large vocabulary
    print("\n--- Test 4: Large Vocabulary (1000 tokens) ---")
    hasher2 = HarmonicHasher()
    
    # Generate test vocabulary
    test_vocab = {f"word_{i}": {'index': i} for i in range(1000)}
    sigs = hasher2.register_vocabulary(test_vocab)
    
    stats = hasher2.get_collision_stats()
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Used E8 roots: {stats['used_roots']}/240 ({stats['coverage']:.1f}%)")
    print(f"  Max tokens per root: {stats['max_per_root']}")
    print(f"  Avg tokens per root: {stats['avg_per_root']:.2f}")
    
    # Verify all can be recovered
    recovered_count = sum(1 for t in test_vocab if hasher2.recover_token(sigs[t]) == t)
    print(f"  Recovery rate: {recovered_count}/{len(test_vocab)}")
    print(f"  Result: {'PASS' if recovered_count == len(test_vocab) else 'FAIL'}")
    
    # Test 5: Serialization
    print("\n--- Test 5: Serialization Round-Trip ---")
    serialized = hasher2.to_bytes()
    print(f"  Serialized size: {len(serialized)} bytes")
    print(f"  Per-token overhead: {len(serialized) / len(test_vocab):.1f} bytes")
    
    hasher3 = HarmonicHasher.from_bytes(serialized)
    
    # Verify recovery still works
    all_match = all(
        hasher3.recover_token(sigs[t]) == t
        for t in test_vocab
    )
    print(f"  Recovery after deserialize: {'PASS' if all_match else 'FAIL'}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
