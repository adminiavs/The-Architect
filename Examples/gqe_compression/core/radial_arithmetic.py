#!/usr/bin/env python3
"""
Radial Arithmetic Coding (RAC) - The Light Triangle Integral

THE PHYSICS:
Standard calculus uses Riemann Sums (stacking rectangles).
Quantum Information Holography uses Sector Summation (stacking light triangles).

The Unit: A "Light Triangle"
- Radius (r): Amplitude of the Quantum State Vector (QSV)
- Angle (θ): The "tick" of the light clock (Angular Frequency)
- Area Formula: A = (1/2)r²θ

THE IMPLEMENTATION:
Instead of slicing a linear interval [0, 1) into rectangles, 
we slice a unit circle [0, 2π) into arc sectors (light triangles).

Higher frequency = More triangles = Sharper reality.

Advantages:
1. Continuous Wrap: Natural streaming without underflow/overflow.
2. Geometric Precision: Matches spinor/phason angular data.
3. Sector Summation: The integral IS the accumulated light triangles.
4. Derivative as Singularity: Each symbol is an instantaneous rotation (f'(t)).
5. Integral as Horizon: The Final Angle is the accumulated history (∫f'(t)dt).

Math:
The interval [θ_low, θ_high) is narrowed by each symbol (composed rotations).
The final compressed state is a single high-precision angle stored in φ-adic form.

This is not a replacement for calculus. It is its origin.

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass

try:
    from .phi_adic import PHI, encode_phi, decode_phi, PhiAdicNumber
    from .e8_lattice import Spinor
except ImportError:
    from phi_adic import PHI, encode_phi, decode_phi, PhiAdicNumber
    from e8_lattice import Spinor

@dataclass
class AngularSector:
    """
    Represents an arc sector on the unit circle.
    
    This is The Architect's Light Triangle:
    - theta_start, theta_end: The angular boundaries
    - width (θ): The "tick" of the light clock
    - Area: A = (1/2)r²θ where r=1 for unit circle
    """
    theta_start: float
    theta_end: float
    radius: float = 1.0  # Default unit circle
    
    @property
    def width(self) -> float:
        """Width of the arc in radians (the θ in Area = (1/2)r²θ)."""
        w = self.theta_end - self.theta_start
        if w < 0:
            w += 2 * np.pi
        return w

    @property
    def midpoint(self) -> float:
        """Midpoint angle of the arc."""
        m = self.theta_start + self.width / 2
        return m % (2 * np.pi)
    
    @property
    def light_triangle_area(self) -> float:
        """
        Calculate the Light Triangle area: A = (1/2)r²θ
        
        This is the fundamental unit of Quantum Information Holography.
        Each symbol added to the sequence creates a new light triangle.
        """
        return 0.5 * (self.radius ** 2) * self.width

class RadialArithmeticCoder:
    """
    Radial Arithmetic Coder using angular intervals and φ-adic precision.
    """
    def __init__(self, vocabulary_probs: Dict[Any, float]):
        self.probs = vocabulary_probs
        self.symbols = sorted(self.probs.keys())
        
        # Build cumulative probability mapping
        self.cum_probs = {}
        current = 0.0
        for s in self.symbols:
            low = current
            high = current + self.probs[s]
            self.cum_probs[s] = (low, high)
            current = high
            
    def encode(self, symbols: List[Any]) -> PhiAdicNumber:
        """
        Encode a sequence of symbols into a single high-precision φ-adic angle.
        
        THE LIGHT TRIANGLE INTEGRAL:
        Each symbol is a DERIVATIVE (f'(t)) - an instantaneous rotation.
        The Final Angle is the INTEGRAL (∫f'(t)dt) - the accumulated history.
        
        As we narrow the sector, we're stacking infinitely thin light triangles.
        Higher frequency (more symbols) = More triangles = Sharper encoding.
        """
        # Start with the full circle (The Singularity contains all possibilities)
        low = 0.0
        width = 1.0
        
        for s in symbols:
            if s not in self.cum_probs:
                # Use a default symbol or ignore
                continue
                    
            p_low, p_high = self.cum_probs[s]
            
            # Update interval (composed rotations)
            # This is MULTIPLICATION by composed rotation (from Axiom 8)
            # "Multiplication is composed rotation" - The Architect
            low = low + width * p_low
            width = width * (p_high - p_low)
            
        # The Final Angle is the midpoint of the final sector
        # This is The Horizon - where the Singularity's projection becomes visible
        final_norm = low + width / 2
        final_angle = final_norm * 2 * np.pi
        
        # Convert to φ-adic for holographic storage
        # Precision scales with -log2(width) because narrower sector = more information
        # This mirrors the Uncertainty Principle: Δθ × ΔL ≥ ℏ
        precision = int(-np.log2(max(width, 1e-300))) + 10
        return encode_phi(final_angle, max_precision=min(precision, 2048))

    def decode(self, phi_angle: PhiAdicNumber, length: int) -> List[Any]:
        """Decode the sequence from the final angle."""
        angle = phi_angle.to_float()
        val = (angle % (2 * np.pi)) / (2 * np.pi)
        
        decoded_symbols = []
        low = 0.0
        width = 1.0
        
        for _ in range(length):
            # Find which symbol's interval contains 'val'
            rel_val = (val - low) / width
            
            # Ensure rel_val is within [0, 1)
            rel_val = max(0.0, min(0.9999999999, rel_val))
            
            # Binary search for efficiency on large vocabularies
            found_symbol = self.symbols[0]
            for s in self.symbols:
                p_low, p_high = self.cum_probs[s]
                if p_low <= rel_val < p_high:
                    found_symbol = s
                    break
            
            decoded_symbols.append(found_symbol)
            
            # Update interval
            p_low, p_high = self.cum_probs[found_symbol]
            low = low + width * p_low
            width = width * (p_high - p_low)
            
        return decoded_symbols

def spinor_radial_update(spinor: Spinor, prob_low: float, prob_high: float) -> Spinor:
    """
    Update a spinor's phase and position using radial arithmetic.
    
    This treats the spinor as a vector whose phase represents the 'state'
    and whose position carries the 'accumulated geometry'.
    """
    # Addition is interference, Multiplication is composed rotation
    current_phase = spinor.phase
    interval_width = (prob_high - prob_low) * 2 * np.pi
    
    # New phase is shifted by the probability offset
    new_phase = (current_phase + prob_low * 2 * np.pi) % (2 * np.pi)
    
    # In Radial AC, the position (geometry) would also be transformed
    # using the sine/cosine 'shadows'.
    new_position = spinor.position * np.sqrt(prob_high - prob_low)
    
    return Spinor(new_position, new_phase)

def run_verification():
    """Verify Radial Arithmetic Coding."""
    print("=" * 60)
    print("RADIAL ARITHMETIC CODING (RAC) VERIFICATION")
    print("=" * 60)
    
    # Test vocabulary
    probs = {'A': 0.4, 'B': 0.3, 'C': 0.2, 'D': 0.1}
    coder = RadialArithmeticCoder(probs)
    
    test_seq = ['A', 'B', 'C', 'A', 'D']
    print(f"\nOriginal sequence: {test_seq}")
    
    # Encode
    phi_angle = coder.encode(test_seq)
    print(f"Final Angle (phi-adic): {phi_angle}")
    print(f"Final Angle (float): {phi_angle.to_float():.10f} rad")
    
    # Decode
    decoded = coder.decode(phi_angle, len(test_seq))
    print(f"Decoded sequence:  {decoded}")
    
    success = test_seq == decoded
    print(f"\nResult: {'SUCCESS' if success else 'FAILURE'}")
    
    # Trigonometric Projection Test
    print("\n--- Trigonometric Projection ---")
    angle = phi_angle.to_float()
    x = np.cos(angle)
    y = np.sin(angle)
    print(f"Angle: {angle:.4f}")
    print(f"Vector (Shadows): [{x:.4f}, {y:.4f}]")
    print(f"Reconstructed Angle: {np.arctan2(y, x):.4f}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_verification()
