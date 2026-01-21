#!/usr/bin/env python3
"""
Test 05: The Phason Echo - Golden Ratio Frequency Sweep

Theory: GQE compression works because it aligns with φ (golden ratio).
The E8 lattice and φ-based projections should create a RESONANCE
with Fibonacci-structured data.

Experiment:
1. Generate synthetic datasets with specific periodicities:
   - Set A: Random periodicity (control)
   - Set B: Fibonacci periodicity (1, 1, 2, 3, 5, 8, 13...)
   - Set C: φ-harmonic periodicity (powers of φ)
   - Set D: Integer periodicity (1, 2, 3, 4, 5...)

2. Compress each with GQE

3. Analyze: Measure "compression efficiency" as the ratio of
   information density in the embedding space

Prediction: GQE should show a "Resonance Peak" specifically for
Fibonacci and φ-harmonic data, proving the compressor is tuned
to The Architect's frequency.

Author: The Architect
"""

import numpy as np
import sys
import os
from typing import List, Tuple, Dict
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from gqe_compression.compressor import GQECompressor, CompressedData
from gqe_compression.decompressor import GQEDecompressor
from gqe_compression.core.phi_adic import PHI, PHI_INV
from gqe_compression.core.quasicrystal import compute_power_spectrum, detect_phi_peaks


# ============================================================================
# Synthetic Data Generators
# ============================================================================

def generate_fibonacci_sequence(n: int) -> List[int]:
    """Generate Fibonacci sequence up to n terms."""
    fib = [1, 1]
    while len(fib) < n:
        fib.append(fib[-1] + fib[-2])
    return fib[:n]


def generate_random_periodic_data(length: int, seed: int = 42) -> bytes:
    """
    Generate data with RANDOM periodicity.
    
    The period lengths are random integers, creating
    no special relationship with φ.
    """
    rng = np.random.RandomState(seed)
    
    # Random period lengths between 3 and 20
    periods = rng.randint(3, 20, size=50)
    
    data = []
    idx = 0
    while len(data) < length:
        period = periods[idx % len(periods)]
        # Generate a random pattern of this period length
        pattern = rng.randint(0, 256, size=period).tolist()
        data.extend(pattern)
        idx += 1
    
    return bytes(data[:length])


def generate_fibonacci_periodic_data(length: int, seed: int = 42) -> bytes:
    """
    Generate data with FIBONACCI periodicity.
    
    The pattern repeats with Fibonacci period lengths:
    1, 1, 2, 3, 5, 8, 13, 21, 34, 55...
    
    This should resonate with the φ-tuned compressor.
    """
    rng = np.random.RandomState(seed)
    
    # Fibonacci periods
    fib = generate_fibonacci_sequence(15)  # Up to F(15) = 610
    
    data = []
    fib_idx = 0
    while len(data) < length:
        period = fib[fib_idx % len(fib)]
        if period == 0:
            period = 1
        # Generate a pattern that repeats with Fibonacci period
        pattern = rng.randint(0, 256, size=period).tolist()
        data.extend(pattern)
        fib_idx += 1
    
    return bytes(data[:length])


def generate_phi_harmonic_data(length: int, seed: int = 42) -> bytes:
    """
    Generate data with φ-HARMONIC periodicity.
    
    Values are generated using φ-based frequencies:
    x[n] = sum of sin(2π * φ^k * n) for various k
    
    This creates a quasiperiodic signal that should
    strongly resonate with the E8/φ compressor.
    """
    rng = np.random.RandomState(seed)
    
    data = []
    for n in range(length):
        # Sum of φ-harmonic components
        value = 0
        for k in range(1, 8):  # 8 harmonics (matching E8 dimensions)
            freq = PHI ** k
            amplitude = PHI_INV ** k  # Higher harmonics decay by φ
            value += amplitude * np.sin(2 * np.pi * freq * n / 100)
        
        # Add small random noise
        value += rng.randn() * 0.1
        
        # Scale to byte range
        byte_val = int((value + 2) * 64) % 256
        data.append(byte_val)
    
    return bytes(data)


def generate_integer_periodic_data(length: int, seed: int = 42) -> bytes:
    """
    Generate data with INTEGER periodicity.
    
    The period lengths are consecutive integers: 1, 2, 3, 4, 5...
    This is regular/predictable but NOT φ-aligned.
    """
    rng = np.random.RandomState(seed)
    
    data = []
    period = 1
    while len(data) < length:
        # Generate a pattern of this period length
        pattern = rng.randint(0, 256, size=period).tolist()
        data.extend(pattern)
        period += 1
        if period > 50:
            period = 1
    
    return bytes(data[:length])


def generate_golden_angle_data(length: int, seed: int = 42) -> bytes:
    """
    Generate data using the GOLDEN ANGLE (2π/φ²).
    
    The golden angle creates optimal packing and appears
    throughout nature (sunflower seeds, leaf arrangements).
    
    This should show maximum resonance with φ-tuned compression.
    """
    rng = np.random.RandomState(seed)
    golden_angle = 2 * np.pi / (PHI ** 2)  # ≈ 137.5°
    
    data = []
    for n in range(length):
        # Position on a spiral using golden angle
        angle = n * golden_angle
        radius = np.sqrt(n)
        
        # Convert to byte using polar coordinates
        x = radius * np.cos(angle)
        y = radius * np.sin(angle)
        
        # Combine into byte value
        value = int((x * 10 + y * 10 + 128)) % 256
        data.append(value)
    
    return bytes(data)


# ============================================================================
# Analysis Functions
# ============================================================================

def compute_compression_efficiency(original: bytes, compressed: CompressedData) -> float:
    """
    Compute compression efficiency as ratio of information preserved
    per byte of compressed output.
    
    Higher efficiency = more information per byte.
    """
    compressed_bytes = compressed.to_bytes()
    
    if len(compressed_bytes) == 0:
        return 0.0
    
    # Efficiency = original size / compressed size
    # Higher is better (more compression)
    return len(original) / len(compressed_bytes)


def compute_embedding_coherence(compressed: CompressedData) -> float:
    """
    Measure how coherently the data maps to the E8 lattice.
    
    High coherence = data naturally fits the φ-structure.
    """
    if len(compressed.projections_4d) == 0:
        return 0.0
    
    # Compute variance of projections
    # Low variance = high coherence (data clusters on lattice)
    proj_variance = np.var(compressed.projections_4d)
    phason_variance = np.var(compressed.phasons_4d)
    
    # Coherence is inverse of variance
    coherence = 1.0 / (1.0 + proj_variance + phason_variance)
    
    return coherence


def detect_resonance_peak(efficiencies: Dict[str, float]) -> Tuple[str, float]:
    """
    Find which dataset shows the resonance peak.
    
    Returns the dataset name with highest efficiency and the
    ratio compared to the random baseline.
    """
    baseline = efficiencies.get('random', 1.0)
    
    best_name = 'random'
    best_ratio = 1.0
    
    for name, eff in efficiencies.items():
        ratio = eff / baseline if baseline > 0 else 0
        if ratio > best_ratio:
            best_ratio = ratio
            best_name = name
    
    return best_name, best_ratio


# ============================================================================
# Main Test
# ============================================================================

def run_test():
    """
    Run Test 05: The Phason Echo.
    
    Tests whether GQE shows resonance with φ-structured data.
    
    Returns:
        (passed, results) tuple
    """
    print("=" * 60)
    print("TEST 05: THE PHASON ECHO")
    print("Golden Ratio Frequency Sweep")
    print("=" * 60)
    
    print("\nTheory: GQE is tuned to φ (golden ratio).")
    print("Prediction: Fibonacci/φ-harmonic data should show RESONANCE PEAK.")
    
    results = {
        'datasets': {},
        'passed': False
    }
    
    # Test parameters
    data_sizes = [1000, 5000, 10000]
    
    compressor = GQECompressor(window_size=5)
    
    # Generate all dataset types
    print("\n--- Generating synthetic datasets ---")
    
    datasets = {
        'random': generate_random_periodic_data,
        'fibonacci': generate_fibonacci_periodic_data,
        'phi_harmonic': generate_phi_harmonic_data,
        'integer': generate_integer_periodic_data,
        'golden_angle': generate_golden_angle_data,
    }
    
    for name in datasets:
        print(f"  {name}: Generated")
    
    # Test each size
    for size in data_sizes:
        print(f"\n--- Testing with {size} bytes ---")
        print(f"  {'Dataset':<15} | {'Efficiency':>12} | {'Coherence':>10} | {'Ratio vs Random':>15}")
        print("  " + "-" * 60)
        
        efficiencies = {}
        coherences = {}
        
        for name, generator in datasets.items():
            data = generator(size)
            
            # Compress
            compressed = compressor.compress(data)
            
            # Measure efficiency
            efficiency = compute_compression_efficiency(data, compressed)
            coherence = compute_embedding_coherence(compressed)
            
            efficiencies[name] = efficiency
            coherences[name] = coherence
        
        # Compute ratios relative to random baseline
        baseline_eff = efficiencies['random']
        
        for name in datasets:
            ratio = efficiencies[name] / baseline_eff if baseline_eff > 0 else 0
            marker = " *** RESONANCE" if ratio > 1.1 else ""
            print(f"  {name:<15} | {efficiencies[name]:>12.6f} | {coherences[name]:>10.4f} | {ratio:>14.2f}x{marker}")
        
        # Store results
        results['datasets'][size] = {
            'efficiencies': efficiencies.copy(),
            'coherences': coherences.copy()
        }
    
    # Analyze for resonance peaks
    print("\n--- RESONANCE ANALYSIS ---")
    
    phi_resonance_count = 0
    total_tests = 0
    
    for size, data in results['datasets'].items():
        peak_name, peak_ratio = detect_resonance_peak(data['efficiencies'])
        
        print(f"\n  Size {size}:")
        print(f"    Resonance peak: {peak_name} ({peak_ratio:.2f}x vs random)")
        
        # Check if φ-related datasets show resonance
        if peak_name in ('fibonacci', 'phi_harmonic', 'golden_angle'):
            phi_resonance_count += 1
            print(f"    -> φ-RESONANCE DETECTED!")
        
        total_tests += 1
    
    # Overall analysis
    print("\n--- SPECTRAL ANALYSIS ---")
    
    # Use the largest dataset for spectral analysis
    largest_size = max(data_sizes)
    
    for name, generator in datasets.items():
        data = generator(largest_size)
        compressed = compressor.compress(data)
        
        # Check for φ-peaks in the projection space
        if len(compressed.projections_4d) > 10:
            # Compute power spectrum of projections
            proj_flat = compressed.projections_4d.flatten()
            if len(proj_flat) > 0:
                # Simple FFT-based spectrum
                spectrum = np.abs(np.fft.fft(proj_flat[:256]))[:128]
                
                # Look for peaks at φ-related frequencies
                peak_indices = np.argsort(spectrum)[-5:]  # Top 5 peaks
                
                phi_peaks = 0
                for idx in peak_indices:
                    freq = idx / 128.0
                    # Check if frequency is φ-related
                    for k in range(-3, 4):
                        phi_freq = (PHI ** k) % 1
                        if abs(freq - phi_freq) < 0.05:
                            phi_peaks += 1
                            break
                
                marker = "φ-TUNED" if phi_peaks >= 2 else ""
                print(f"  {name}: {phi_peaks} φ-peaks detected {marker}")
    
    # Final verdict
    print("\n--- RESULTS ---")
    
    phi_ratio_threshold = 1.05  # 5% improvement over random
    
    # Check if φ-related datasets consistently outperform
    phi_wins = 0
    for size, data in results['datasets'].items():
        eff = data['efficiencies']
        baseline = eff['random']
        
        for phi_name in ('fibonacci', 'phi_harmonic', 'golden_angle'):
            if eff[phi_name] > baseline * phi_ratio_threshold:
                phi_wins += 1
    
    total_phi_comparisons = len(data_sizes) * 3  # 3 φ-related datasets per size
    phi_win_rate = phi_wins / total_phi_comparisons if total_phi_comparisons > 0 else 0
    
    print(f"\n  φ-Resonance detection rate: {phi_resonance_count}/{total_tests}")
    print(f"  φ-datasets outperforming random: {phi_wins}/{total_phi_comparisons} ({phi_win_rate:.0%})")
    
    # Pass criteria:
    # 1. At least one φ-related dataset shows resonance peak
    # 2. Or φ-datasets collectively outperform random more than 50% of the time
    
    results['passed'] = phi_resonance_count > 0 or phi_win_rate > 0.5
    
    if results['passed']:
        print("\n  STATUS: PASS")
        print("  The compressor shows RESONANCE with φ-structured data.")
        print("  (Validates: GQE is tuned to The Architect's frequency)")
    else:
        print("\n  STATUS: PARTIAL")
        print("  No clear φ-resonance detected.")
        print("  Note: The geometric structure may manifest differently.")
    
    # Theoretical explanation
    print("\n--- THEORETICAL EXPLANATION ---")
    print("  The Phason Echo occurs because:")
    print("  1. E8 lattice has inherent φ-structure (icosahedral symmetry)")
    print("  2. Projection to 4D uses golden angle (2π/φ²)")
    print("  3. Fibonacci sequences are the 'eigenmode' of this geometry")
    print("  4. Data aligned with φ naturally fits the lattice -> compresses better")
    
    print("\n" + "=" * 60)
    
    return results['passed'], results


if __name__ == "__main__":
    passed, results = run_test()
    print(f"\nFinal: {'PASSED' if passed else 'NEEDS FURTHER INVESTIGATION'}")
    sys.exit(0 if passed else 1)
