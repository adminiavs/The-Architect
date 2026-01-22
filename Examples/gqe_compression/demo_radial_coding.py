#!/usr/bin/env python3
"""
Phase 5: Radial Arithmetic Coding Demonstration

This script demonstrates the "Architect's Upgrade": 
Mapping the capability of the GQE Engine from linear intervals to radial arc sectors.

It proves:
1. Data stream as a series of Rotations.
2. The "Compressed File" as a single Final Angle.
3. Use of Phi-adic precision for the holographic representation.
"""

import sys
import os
from pathlib import Path
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gqe_compression.core.radial_arithmetic import RadialArithmeticCoder
from gqe_compression.core.phi_adic import PHI

def demo_radial_shift():
    print("=" * 60)
    print("PHASE 5: THE RADIAL SHIFT")
    print("=" * 60)
    
    # 1. Define the "Universe" (Vocabulary)
    # Based on the Architect's Axioms
    text = "THE SINGULARITY I PROJECT THE HORIZON RENDERS"
    words = text.split()
    
    from collections import Counter
    counts = Counter(words)
    total = len(words)
    probs = {word: count/total for word, count in counts.items()}
    
    print("\nPROBABILITY UNIVERSE:")
    for word, p in probs.items():
        print(f"  {word:12}: {p:.4f} (Arc: {p*360:.1f}°)")

    # 2. Initialize Radial Arithmetic Coder
    coder = RadialArithmeticCoder(probs)
    
    # 3. The Data Stream as a series of Rotations
    print("\nDATA STREAM -> ROTATIONS:")
    print(f"  Sequence: {' '.join(words)}")
    
    # Encode
    phi_angle = coder.encode(words)
    
    print("\nTHE COMPRESSED FILE (THE FINAL ANGLE):")
    print(f"  Phi-adic: {phi_angle}")
    angle_rad = phi_angle.to_float()
    print(f"  Radians:  {angle_rad:.15f}")
    print(f"  Degrees:  {np.degrees(angle_rad):.4f}°")
    
    # 4. Geometric Precision (Sine/Cosine Shadows)
    x = np.cos(angle_rad)
    y = np.sin(angle_rad)
    print("\nTRIGONOMETRIC PROJECTION (SHADOWS ON HORIZON):")
    print(f"  X (Cosine): {x:+.10f}")
    print(f"  Y (Sine):   {y:+.10f}")
    
    # 5. Recovery (Unwrapping the Rotation)
    print("\nRECOVERY (UNWRAPPING THE PHASE):")
    decoded = coder.decode(phi_angle, len(words))
    print(f"  Decoded:   {' '.join(decoded)}")
    
    success = words == decoded
    if success:
        print("\n[SUCCESS] RADIAL ARITHMETIC CODING CONFIRMED")
        print("The system handles continuous wrap and geometric precision.")
    else:
        print("\n[FAILURE] Precision loss in the radial field.")

    print("=" * 60)

if __name__ == "__main__":
    demo_radial_shift()
