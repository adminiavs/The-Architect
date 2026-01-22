#!/usr/bin/env python3
"""
Phi-Adic Bit Packer - The Phason Zip

THE PHYSICS:
Instead of storing 0.618... as a float, we store the BINARY PATH
(sequence of phason flips) required to reach that angle on the E8 lattice.

This is the quantization of the Singularity: continuous angles become
discrete bit patterns, matching how the Horizon renders the projection.

Key Optimizations:
1. Eliminate padding: No byte boundary alignment waste
2. Run-length encoding: Exploit Zeckendorf property (no consecutive 1s)
3. Variable-length encoding: Use terminators instead of fixed counters

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass

try:
    from .phi_adic import PhiAdicNumber, PHI, PHI_INV, encode_phi
except ImportError:
    from phi_adic import PhiAdicNumber, PHI, PHI_INV, encode_phi


@dataclass
class BitStream:
    """
    A mutable bit buffer for efficient packing/unpacking.
    
    THE PHYSICS:
    This is the "Horizon Screen" - the discrete surface where
    continuous angles become pixelated bits.
    """
    bits: List[int]
    position: int = 0
    
    def __init__(self):
        self.bits = []
        self.position = 0
    
    def write_bit(self, bit: int):
        """Write a single bit (0 or 1)."""
        self.bits.append(bit & 1)
    
    def write_bits(self, bits: List[int]):
        """Write multiple bits."""
        for b in bits:
            self.write_bit(b)
    
    def write_unary(self, n: int):
        """
        Write a number in unary encoding: n ones followed by a zero.
        
        This is optimal for small numbers (Zeckendorf digit counts).
        """
        for _ in range(n):
            self.write_bit(1)
        self.write_bit(0)
    
    def write_gamma(self, n: int):
        """
        Write a positive integer using Elias gamma coding.
        
        Gamma coding: floor(log2(n)) zeros, then n in binary.
        Optimal for geometrically distributed integers.
        """
        if n <= 0:
            self.write_bit(0)
            return
            
        # Number of bits needed
        bits_needed = n.bit_length()
        
        # Write (bits_needed - 1) zeros
        for _ in range(bits_needed - 1):
            self.write_bit(0)
        
        # Write n in binary (bits_needed bits)
        for i in range(bits_needed - 1, -1, -1):
            self.write_bit((n >> i) & 1)
    
    def read_bit(self) -> int:
        """Read a single bit."""
        if self.position >= len(self.bits):
            return 0
        bit = self.bits[self.position]
        self.position += 1
        return bit
    
    def read_bits(self, count: int) -> List[int]:
        """Read multiple bits."""
        return [self.read_bit() for _ in range(count)]
    
    def read_unary(self) -> int:
        """Read a unary-encoded number."""
        count = 0
        while self.read_bit() == 1:
            count += 1
        return count
    
    def read_gamma(self) -> int:
        """Read an Elias gamma-encoded integer."""
        # Count leading zeros
        zeros = 0
        while self.read_bit() == 0:
            zeros += 1
            if zeros > 32:  # Safety limit
                return 0
        
        if zeros == 0:
            return 1
        
        # Read the remaining bits
        n = 1
        for _ in range(zeros):
            n = (n << 1) | self.read_bit()
        return n
    
    def to_bytes(self) -> bytes:
        """
        Convert bit buffer to bytes.
        
        Format: [total_bits (4 bytes)][packed bits]
        """
        total_bits = len(self.bits)
        
        # Pack bits into bytes
        byte_count = (total_bits + 7) // 8
        result = bytearray(4 + byte_count)
        
        # Store total bit count (little-endian)
        result[0] = total_bits & 0xFF
        result[1] = (total_bits >> 8) & 0xFF
        result[2] = (total_bits >> 16) & 0xFF
        result[3] = (total_bits >> 24) & 0xFF
        
        # Pack bits
        for i, bit in enumerate(self.bits):
            byte_idx = 4 + (i // 8)
            bit_idx = i % 8
            if bit:
                result[byte_idx] |= (1 << bit_idx)
        
        return bytes(result)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'BitStream':
        """Reconstruct bit buffer from bytes."""
        if len(data) < 4:
            stream = cls()
            return stream
        
        # Read total bit count
        total_bits = (data[0] | (data[1] << 8) | 
                     (data[2] << 16) | (data[3] << 24))
        
        stream = cls()
        
        # Unpack bits
        for i in range(total_bits):
            byte_idx = 4 + (i // 8)
            bit_idx = i % 8
            if byte_idx < len(data):
                bit = (data[byte_idx] >> bit_idx) & 1
                stream.bits.append(bit)
            else:
                stream.bits.append(0)
        
        return stream


class PhiAdicBitPacker:
    """
    Converts phi-adic numbers to raw bitstreams.
    
    THE PHYSICS:
    The Singularity projects continuous angles. The Horizon renders
    discrete bits. This class performs the quantization - turning
    light into pixels.
    
    Format for each phi-adic number:
    1. Sign bit (1 bit)
    2. Integer digit count (gamma coded)
    3. Fractional digit count (gamma coded)
    4. Integer digits (Zeckendorf, no consecutive 1s)
    5. Fractional digits (Zeckendorf)
    
    Optimization: Since Zeckendorf has no consecutive 1s, we can use
    "1 1" as a terminator if needed, but gamma coding for counts is
    more efficient for variable-length sequences.
    """
    
    def pack_single(self, phi: PhiAdicNumber, stream: BitStream):
        """
        Pack a single phi-adic number into the bitstream.
        """
        # 1. Sign bit
        stream.write_bit(1 if phi.negative else 0)
        
        # 2. Integer digit count (gamma coded)
        int_count = len(phi.digits) if phi.digits else 0
        stream.write_gamma(int_count + 1)  # +1 to handle zero case
        
        # 3. Fractional digit count (gamma coded)
        frac_count = len(phi.fractional_digits) if phi.fractional_digits else 0
        stream.write_gamma(frac_count + 1)
        
        # 4. Integer digits (raw bits, Zeckendorf guaranteed)
        if phi.digits:
            stream.write_bits(phi.digits)
        
        # 5. Fractional digits
        if phi.fractional_digits:
            stream.write_bits(phi.fractional_digits)
    
    def unpack_single(self, stream: BitStream) -> PhiAdicNumber:
        """
        Unpack a single phi-adic number from the bitstream.
        """
        # 1. Sign bit
        negative = stream.read_bit() == 1
        
        # 2. Integer digit count
        int_count = stream.read_gamma() - 1
        
        # 3. Fractional digit count
        frac_count = stream.read_gamma() - 1
        
        # 4. Integer digits
        digits = stream.read_bits(int_count) if int_count > 0 else [0]
        
        # 5. Fractional digits
        fractional_digits = stream.read_bits(frac_count) if frac_count > 0 else []
        
        return PhiAdicNumber(
            digits=digits,
            fractional_digits=fractional_digits,
            negative=negative
        )
    
    def pack_sequence(self, phi_angles: List[PhiAdicNumber]) -> bytes:
        """
        Pack multiple phi-adic numbers into a dense bitstream.
        
        Format:
        [count (4 bytes)][packed phi-adic numbers]
        
        THE PHYSICS:
        Each angle is a "frame" of the light projection. We're compressing
        the entire movie of light triangles into a single bitstream.
        """
        stream = BitStream()
        
        for phi in phi_angles:
            self.pack_single(phi, stream)
        
        # Prepend count
        count_bytes = len(phi_angles).to_bytes(4, 'little')
        bit_bytes = stream.to_bytes()
        
        return count_bytes + bit_bytes
    
    def unpack_sequence(self, data: bytes) -> List[PhiAdicNumber]:
        """
        Unpack multiple phi-adic numbers from a bitstream.
        """
        if len(data) < 4:
            return []
        
        # Read count
        count = int.from_bytes(data[:4], 'little')
        
        # Unpack bitstream
        stream = BitStream.from_bytes(data[4:])
        
        result = []
        for _ in range(count):
            phi = self.unpack_single(stream)
            result.append(phi)
        
        return result
    
    def pack_token_indices(self, indices: List[int], vocab_size: int) -> bytes:
        """
        Pack token indices directly using optimal encoding.
        
        For small vocabularies (<= 256): Use 8-bit encoding
        For larger vocabularies: Use gamma-coded deltas
        
        THE PHYSICS:
        Token indices are the "addresses" in the E8 lattice.
        We store the path through the lattice, not the coordinates.
        """
        stream = BitStream()
        
        if vocab_size <= 256:
            # Fixed 8-bit encoding
            for idx in indices:
                for i in range(8):
                    stream.write_bit((idx >> i) & 1)
        else:
            # Variable-length encoding with delta compression
            prev = 0
            for idx in indices:
                # Store delta + vocab_size (to handle negative deltas)
                delta = idx - prev + vocab_size
                stream.write_gamma(delta + 1)
                prev = idx
        
        return stream.to_bytes()
    
    def unpack_token_indices(self, data: bytes, count: int, vocab_size: int) -> List[int]:
        """
        Unpack token indices.
        """
        stream = BitStream.from_bytes(data)
        
        indices = []
        
        if vocab_size <= 256:
            # Fixed 8-bit decoding
            for _ in range(count):
                idx = 0
                for i in range(8):
                    idx |= (stream.read_bit() << i)
                indices.append(idx)
        else:
            # Variable-length delta decoding
            prev = 0
            for _ in range(count):
                delta = stream.read_gamma() - 1 - vocab_size
                idx = prev + delta
                indices.append(idx)
                prev = idx
        
        return indices


def run_verification():
    """Verify the bit packer functionality."""
    print("=" * 60)
    print("PHI-ADIC BIT PACKER VERIFICATION")
    print("=" * 60)
    
    packer = PhiAdicBitPacker()
    
    # Test 1: Single phi-adic round-trip
    print("\n--- Test 1: Single Phi-Adic Round-Trip ---")
    original = encode_phi(3.14159, max_precision=32)
    print(f"  Original: {original}")
    print(f"  Float value: {original.to_float():.10f}")
    
    stream = BitStream()
    packer.pack_single(original, stream)
    packed_bytes = stream.to_bytes()
    print(f"  Packed size: {len(packed_bytes)} bytes")
    
    # Compare with old to_bits()
    old_bytes = original.to_bits()
    print(f"  Old to_bits() size: {len(old_bytes)} bytes")
    print(f"  Savings: {len(old_bytes) - len(packed_bytes)} bytes ({(1 - len(packed_bytes)/len(old_bytes))*100:.1f}%)")
    
    # Unpack and verify
    stream2 = BitStream.from_bytes(packed_bytes)
    recovered = packer.unpack_single(stream2)
    error = abs(original.to_float() - recovered.to_float())
    print(f"  Recovered: {recovered.to_float():.10f}")
    print(f"  Error: {error:.2e}")
    print(f"  Result: {'PASS' if error < 1e-10 else 'FAIL'}")
    
    # Test 2: Sequence packing
    print("\n--- Test 2: Sequence Packing ---")
    angles = [encode_phi(i * 0.1, max_precision=24) for i in range(100)]
    
    # Old method (to_bits for each)
    old_total = sum(len(a.to_bits()) for a in angles)
    
    # New method (packed sequence)
    packed = packer.pack_sequence(angles)
    print(f"  Old total size: {old_total} bytes")
    print(f"  New packed size: {len(packed)} bytes")
    print(f"  Savings: {old_total - len(packed)} bytes ({(1 - len(packed)/old_total)*100:.1f}%)")
    
    # Verify round-trip
    recovered_angles = packer.unpack_sequence(packed)
    max_error = max(abs(a.to_float() - r.to_float()) 
                   for a, r in zip(angles, recovered_angles))
    print(f"  Max reconstruction error: {max_error:.2e}")
    print(f"  Result: {'PASS' if max_error < 1e-10 else 'FAIL'}")
    
    # Test 3: Token index packing
    print("\n--- Test 3: Token Index Packing ---")
    indices = list(range(0, 1000, 7))  # Stride pattern
    vocab_size = 1000
    
    # Old method (uint32)
    old_size = len(indices) * 4
    
    # New method
    packed_indices = packer.pack_token_indices(indices, vocab_size)
    print(f"  Index count: {len(indices)}")
    print(f"  Old size (uint32): {old_size} bytes")
    print(f"  New packed size: {len(packed_indices)} bytes")
    print(f"  Savings: {old_size - len(packed_indices)} bytes ({(1 - len(packed_indices)/old_size)*100:.1f}%)")
    
    # Verify
    recovered_indices = packer.unpack_token_indices(packed_indices, len(indices), vocab_size)
    match = indices == recovered_indices
    print(f"  Round-trip match: {match}")
    print(f"  Result: {'PASS' if match else 'FAIL'}")
    
    # Test 4: Gamma coding verification
    print("\n--- Test 4: Gamma Coding Verification ---")
    stream = BitStream()
    test_values = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
    for v in test_values:
        stream.write_gamma(v)
    
    total_bits = len(stream.bits)
    print(f"  Values: {test_values}")
    print(f"  Total bits: {total_bits}")
    print(f"  Bits per value: {total_bits / len(test_values):.2f}")
    
    # Verify
    stream.position = 0
    recovered_values = [stream.read_gamma() for _ in test_values]
    match = test_values == recovered_values
    print(f"  Recovered: {recovered_values}")
    print(f"  Result: {'PASS' if match else 'FAIL'}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
