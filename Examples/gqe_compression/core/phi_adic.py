#!/usr/bin/env python3
"""
φ-adic Number System for GQE Compression

Architect Principle: From Proof 02 - "φ is the unique solution to aperiodicity constraints"

The golden ratio φ = (1+√5)/2 is the "most irrational" number (Hurwitz's theorem).
Using φ as a number base allows efficient encoding of quasicrystal structures.

Key properties:
- φ² = φ + 1 (the defining property)
- φ-adic naturally represents Fibonacci sequences
- Optimal for encoding aperiodic structures

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass

# Fundamental constants
PHI = (1 + np.sqrt(5)) / 2  # Golden ratio ≈ 1.6180339887
PHI_INV = 1 / PHI           # = φ - 1 ≈ 0.6180339887
PHI_SQ = PHI ** 2           # = φ + 1 ≈ 2.6180339887

# Precision for comparisons
EPSILON = 1e-12


@dataclass
class PhiAdicNumber:
    """
    Represents a number in φ-adic (golden ratio base) form.
    
    A φ-adic number is represented as:
        n = Σ d_i * φ^i
    
    where d_i ∈ {0, 1} and no two consecutive 1s appear (Zeckendorf representation).
    
    Attributes:
        digits: List of digits (0 or 1), index 0 is the ones place (φ^0)
        negative: Whether the number is negative
        fractional_digits: Digits after the "decimal" point (φ^-1, φ^-2, ...)
    """
    digits: List[int]  # Integer part: d_0, d_1, d_2, ... (φ^0, φ^1, φ^2, ...)
    fractional_digits: List[int] = None  # Fractional part: d_-1, d_-2, ... (φ^-1, φ^-2, ...)
    negative: bool = False
    
    def __post_init__(self):
        if self.fractional_digits is None:
            self.fractional_digits = []
    
    def to_float(self) -> float:
        """Convert to floating point value."""
        value = 0.0
        
        # Integer part uses Fibonacci numbers (Zeckendorf)
        # F_1=1, F_2=2, F_3=3, F_4=5, ...
        fibs = [1, 2]
        while len(fibs) < len(self.digits):
            fibs.append(fibs[-1] + fibs[-2])
        
        for i, d in enumerate(self.digits):
            if d and i < len(fibs):
                value += fibs[i]
        
        # Fractional part uses negative powers of φ
        for i, d in enumerate(self.fractional_digits):
            if d:
                value += PHI ** (-(i + 1))
        
        return -value if self.negative else value
    
    def to_bits(self) -> bytes:
        """
        Convert to compact bit representation.
        
        Format:
        - 1 bit: sign
        - 8 bits: integer digit count
        - 8 bits: fractional digit count
        - N bits: integer digits
        - M bits: fractional digits
        """
        bits = []
        
        # Sign bit
        bits.append(1 if self.negative else 0)
        
        # Integer digit count (max 255)
        int_count = min(len(self.digits), 255)
        bits.extend([(int_count >> i) & 1 for i in range(8)])
        
        # Fractional digit count (max 255)
        frac_count = min(len(self.fractional_digits), 255)
        bits.extend([(frac_count >> i) & 1 for i in range(8)])
        
        # Integer digits
        bits.extend(self.digits[:int_count])
        
        # Fractional digits
        bits.extend(self.fractional_digits[:frac_count])
        
        # Pad to byte boundary
        while len(bits) % 8 != 0:
            bits.append(0)
        
        # Convert to bytes
        result = bytearray()
        for i in range(0, len(bits), 8):
            byte = sum(bits[i + j] << j for j in range(8) if i + j < len(bits))
            result.append(byte)
        
        return bytes(result)
    
    @classmethod
    def from_bits(cls, data: bytes) -> 'PhiAdicNumber':
        """Reconstruct from bit representation."""
        bits = []
        for byte in data:
            bits.extend([(byte >> i) & 1 for i in range(8)])
        
        idx = 0
        
        # Sign bit
        negative = bits[idx] == 1
        idx += 1
        
        # Integer digit count
        int_count = sum(bits[idx + i] << i for i in range(8))
        idx += 8
        
        # Fractional digit count
        frac_count = sum(bits[idx + i] << i for i in range(8))
        idx += 8
        
        # Integer digits
        digits = bits[idx:idx + int_count]
        idx += int_count
        
        # Fractional digits
        fractional_digits = bits[idx:idx + frac_count]
        
        return cls(digits=digits, fractional_digits=fractional_digits, negative=negative)
    
    def to_compact_bits(self) -> Tuple[List[int], int]:
        """
        Convert to minimal bit representation without padding.
        
        THE PHYSICS:
        This is the "Pixelation" of the Singularity's continuous output.
        Each bit represents a phason flip - a discrete step in the E8 lattice.
        
        Format (variable length):
        - 1 bit: sign
        - Integer digits (raw, no count header)
        - Fractional digits (raw)
        
        The digit counts are stored externally or inferred from context.
        
        Returns:
            (bit_list, bit_count) for precise packing.
        """
        bits = []
        
        # 1. Sign bit
        bits.append(1 if self.negative else 0)
        
        # 2. Integer digits (reversed for LSB-first storage)
        for d in self.digits:
            bits.append(d)
        
        # 3. Fractional digits
        for d in self.fractional_digits:
            bits.append(d)
        
        return bits, len(bits)
    
    @classmethod
    def from_compact_bits(cls, bits: List[int], int_count: int, frac_count: int) -> 'PhiAdicNumber':
        """
        Reconstruct from compact bit representation.
        
        Args:
            bits: The raw bit list
            int_count: Number of integer digits
            frac_count: Number of fractional digits
        """
        idx = 0
        
        # 1. Sign bit
        negative = bits[idx] == 1
        idx += 1
        
        # 2. Integer digits
        digits = bits[idx:idx + int_count] if int_count > 0 else [0]
        idx += int_count
        
        # 3. Fractional digits
        fractional_digits = bits[idx:idx + frac_count] if frac_count > 0 else []
        
        return cls(digits=digits, fractional_digits=fractional_digits, negative=negative)
    
    def __repr__(self) -> str:
        sign = '-' if self.negative else ''
        int_str = ''.join(str(d) for d in reversed(self.digits)) or '0'
        if self.fractional_digits:
            frac_str = ''.join(str(d) for d in self.fractional_digits)
            return f"{sign}{int_str}.{frac_str}φ"
        return f"{sign}{int_str}φ"


def _zeckendorf_normalize(digits: List[int]) -> List[int]:
    """
    Normalize to Zeckendorf representation (no consecutive 1s).
    
    Uses the identity: φ^n + φ^(n+1) = φ^(n+2)
    """
    result = list(digits)
    
    # Extend if needed
    while len(result) < 2:
        result.append(0)
    
    # Keep normalizing until no consecutive 1s
    changed = True
    while changed:
        changed = False
        
        # Handle digits > 1 (carry)
        for i in range(len(result)):
            while result[i] > 1:
                result[i] -= 2
                if i + 2 >= len(result):
                    result.extend([0] * (i + 3 - len(result)))
                result[i + 2] += 1
                if i > 0:
                    result[i - 1] += 1
                changed = True
        
        # Handle consecutive 1s
        for i in range(len(result) - 1):
            if result[i] == 1 and result[i + 1] == 1:
                result[i] = 0
                result[i + 1] = 0
                if i + 2 >= len(result):
                    result.append(0)
                result[i + 2] += 1
                changed = True
    
    # Remove trailing zeros
    while len(result) > 1 and result[-1] == 0:
        result.pop()
    
    return result


def encode_phi(n: float, max_precision: int = 64) -> PhiAdicNumber:
    """
    Encode a number in φ-adic (Zeckendorf) representation.
    
    Args:
        n: The number to encode
        max_precision: Maximum number of fractional digits
    
    Returns:
        PhiAdicNumber in normalized Zeckendorf form
    
    The encoding uses Fibonacci-based Zeckendorf decomposition:
    - For integer part: use Fibonacci numbers (F_1=1, F_2=2, F_3=3, ...)
    - For fractional part: use negative powers of φ
    
    Key insight: In Zeckendorf representation, the value of digit d_i at position i is:
    - Integer positions: F_{i+2} (where F_1=1, F_2=1, F_3=2, ...)
    - This ensures integer inputs yield integer outputs
    """
    negative = n < 0
    n = abs(n)
    
    # Separate integer and fractional parts properly
    int_part = int(n)  # floor for positive numbers
    frac_part = n - int_part
    
    # Handle edge case where frac_part is very close to 1 due to floating point
    if frac_part > 1 - EPSILON:
        int_part += 1
        frac_part = 0.0
    
    # Encode integer part using Zeckendorf (Fibonacci) decomposition
    if int_part == 0:
        int_digits = [0]
    else:
        int_digits = encode_phi_int(int_part)
    
    # Encode fractional part using negative powers of φ
    frac_digits = []
    if frac_part > EPSILON:
        remaining = frac_part
        power = PHI_INV  # φ^-1 ≈ 0.618
        
        for _ in range(max_precision):
            if remaining < EPSILON:
                break
            if remaining >= power - EPSILON:
                frac_digits.append(1)
                remaining -= power
            else:
                frac_digits.append(0)
            power *= PHI_INV
    
    return PhiAdicNumber(
        digits=int_digits,
        fractional_digits=frac_digits,
        negative=negative
)


def decode_phi(phi_num: PhiAdicNumber) -> float:
    """
    Decode a φ-adic number back to float.
    
    Args:
        phi_num: The φ-adic number to decode
    
    Returns:
        The floating point value
    """
    return phi_num.to_float()


def encode_phi_int(n: int) -> List[int]:
    """
    Encode a non-negative integer using Zeckendorf representation.
    
    This is the standard Fibonacci coding used in data compression.
    
    Args:
        n: Non-negative integer
    
    Returns:
        List of digits (0 or 1), index 0 is ones place
    """
    if n < 0:
        raise ValueError("Input must be non-negative")
    if n == 0:
        return [0]
    
    # Generate Fibonacci numbers up to n
    fibs = [1, 2]
    while fibs[-1] < n:
        fibs.append(fibs[-1] + fibs[-2])
    
    # Greedy decomposition
    digits = [0] * len(fibs)
    remaining = n
    
    for i in range(len(fibs) - 1, -1, -1):
        if fibs[i] <= remaining:
            digits[i] = 1
            remaining -= fibs[i]
    
    # Remove trailing zeros but keep at least one digit
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
    
    return digits


def decode_phi_int(digits: List[int]) -> int:
    """
    Decode Zeckendorf representation back to integer.
    
    Args:
        digits: List of digits (0 or 1)
    
    Returns:
        The integer value
    """
    # Generate Fibonacci numbers
    if len(digits) == 0:
        return 0
    
    fibs = [1, 2]
    while len(fibs) < len(digits):
        fibs.append(fibs[-1] + fibs[-2])
    
    return sum(d * f for d, f in zip(digits, fibs))


def phi_adic_add(a: PhiAdicNumber, b: PhiAdicNumber) -> PhiAdicNumber:
    """Add two φ-adic numbers."""
    # Simple implementation via float (for now)
    # A proper implementation would work directly on digits
    return encode_phi(a.to_float() + b.to_float())


def phi_adic_distance(a: float, b: float) -> PhiAdicNumber:
    """Compute |a - b| in φ-adic form."""
    return encode_phi(abs(a - b))


def fibonacci(n: int) -> int:
    """Compute nth Fibonacci number (F_0 = 0, F_1 = 1)."""
    if n <= 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b


def verify_fibonacci_property(n: int) -> bool:
    """
    Verify that Fibonacci(n) requires at most n φ-adic digits.
    
    This is a key property from Proof 02: Fibonacci numbers have
    optimal representation in φ-adic form.
    """
    fib_n = fibonacci(n)
    encoded = encode_phi_int(fib_n)
    return len(encoded) <= n


# Verification functions
def verify_round_trip(value: float, tolerance: float = 1e-10) -> Tuple[bool, float]:
    """
    Verify that encode/decode round-trip preserves value.
    
    Returns:
        (success, error) tuple
    """
    encoded = encode_phi(value)
    decoded = decode_phi(encoded)
    error = abs(value - decoded)
    return error < tolerance, error


def run_verification() -> None:
    """Run all verification tests for φ-adic module."""
    print("=" * 60)
    print("φ-ADIC NUMBER SYSTEM VERIFICATION")
    print("=" * 60)
    
    print(f"\nFundamental constants:")
    print(f"  φ = {PHI:.15f}")
    print(f"  1/φ = {PHI_INV:.15f}")
    print(f"  φ² = {PHI_SQ:.15f}")
    print(f"  φ² - φ - 1 = {PHI_SQ - PHI - 1:.2e} (should be ~0)")
    
    # Test 1: Round-trip accuracy
    print(f"\n--- Test 1: Round-trip accuracy ---")
    test_values = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144,  # Fibonacci
                   0.5, 0.618, 1.618, 2.718, 3.14159,  # Common values
                   PHI, PHI_INV, PHI_SQ]  # Golden constants
    
    all_passed = True
    for v in test_values:
        passed, error = verify_round_trip(v)
        status = "PASS" if passed else "FAIL"
        print(f"  {v:12.6f} -> {status} (error: {error:.2e})")
        all_passed = all_passed and passed
    
    print(f"\n  Result: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    
    # Test 2: Fibonacci digit count
    print(f"\n--- Test 2: Fibonacci digit count ---")
    all_passed = True
    for n in range(1, 20):
        fib_n = fibonacci(n)
        encoded = encode_phi_int(fib_n)
        passed = len(encoded) <= n
        status = "PASS" if passed else "FAIL"
        print(f"  F_{n:2d} = {fib_n:6d}, digits = {len(encoded):2d}, limit = {n:2d} -> {status}")
        all_passed = all_passed and passed
    
    print(f"\n  Result: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    
    # Test 3: Bit encoding/decoding
    print(f"\n--- Test 3: Bit encoding/decoding ---")
    test_values = [42, 100, 1000, PHI * 100, 0.123456]
    all_passed = True
    for v in test_values:
        encoded = encode_phi(v)
        bits = encoded.to_bits()
        decoded = PhiAdicNumber.from_bits(bits)
        error = abs(v - decoded.to_float())
        passed = error < 1e-6
        status = "PASS" if passed else "FAIL"
        print(f"  {v:12.6f} -> {len(bits):3d} bytes -> {status} (error: {error:.2e})")
        all_passed = all_passed and passed
    
    print(f"\n  Result: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
