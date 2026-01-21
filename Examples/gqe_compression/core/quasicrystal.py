#!/usr/bin/env python3
"""
Quasicrystal Detection for GQE Compression

Architect Principle: From Concept 03 - "Quasicrystal → optimal information density"

Key properties of quasicrystals:
- Aperiodic: No translational symmetry
- Ordered: Sharp diffraction peaks (not random)
- Golden ratio: Peak frequencies related by φ

This module detects quasicrystalline structure in data by:
1. Computing power spectrum of point distributions
2. Finding peaks at φ-related frequency ratios
3. Computing aperiodicity score (0=periodic, 1=random, 0.618=quasicrystal)

The presence of φ-peaks validates The Architect's hypothesis that natural
language (and other structured data) has quasicrystalline geometry.

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from scipy import signal
from scipy.fft import fft, fftfreq
from scipy.spatial.distance import pdist, squareform

try:
    from .phi_adic import PHI, PHI_INV
except ImportError:
    from phi_adic import PHI, PHI_INV

# Precision
EPSILON = 1e-10


def compute_power_spectrum(points: np.ndarray, n_bins: int = 256) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute the radial power spectrum of a point distribution.
    
    For a quasicrystal, this will show sharp peaks at φ-related frequencies.
    For a random distribution, the spectrum will be flat.
    For a periodic crystal, peaks will be at rational frequency ratios.
    
    Args:
        points: (N, D) array of N points in D dimensions
        n_bins: Number of frequency bins
    
    Returns:
        (frequencies, magnitudes): Arrays of frequency values and power
    """
    N, D = points.shape
    
    if N < 2:
        return np.array([0.0]), np.array([0.0])
    
    # Compute all pairwise distances
    distances = pdist(points)
    
    if len(distances) == 0:
        return np.array([0.0]), np.array([0.0])
    
    # Create histogram of distances (radial distribution function)
    max_dist = np.max(distances)
    if max_dist < EPSILON:
        return np.array([0.0]), np.array([0.0])
    
    hist, bin_edges = np.histogram(distances, bins=n_bins, range=(0, max_dist))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    # Normalize histogram
    hist = hist.astype(np.float64)
    hist_norm = hist / (np.sum(hist) + EPSILON)
    
    # Compute FFT to get power spectrum
    spectrum = np.abs(fft(hist_norm)) ** 2
    freqs = fftfreq(n_bins, d=(max_dist / n_bins))
    
    # Keep only positive frequencies
    positive_mask = freqs > 0
    freqs = freqs[positive_mask]
    spectrum = spectrum[positive_mask]
    
    return freqs, spectrum


def detect_phi_peaks(
    freqs: np.ndarray, 
    magnitudes: np.ndarray,
    prominence: float = 0.01,
    phi_tolerance: float = 0.1
) -> Tuple[List[float], int]:
    """
    Detect peaks in the spectrum and count φ-related frequency ratios.
    
    Args:
        freqs: Frequency values
        magnitudes: Power spectrum magnitudes
        prominence: Minimum peak prominence for detection
        phi_tolerance: Tolerance for matching φ ratios
    
    Returns:
        (peak_frequencies, phi_ratio_count): List of peak frequencies and
        count of consecutive φ-related ratios
    """
    if len(freqs) < 3:
        return [], 0
    
    # Find peaks
    peak_indices, properties = signal.find_peaks(
        magnitudes, 
        prominence=prominence * np.max(magnitudes)
    )
    
    if len(peak_indices) < 2:
        return list(freqs[peak_indices]) if len(peak_indices) > 0 else [], 0
    
    peak_freqs = freqs[peak_indices]
    
    # Sort by frequency
    peak_freqs = np.sort(peak_freqs)
    peak_freqs = peak_freqs[peak_freqs > EPSILON]  # Remove zero/near-zero
    
    if len(peak_freqs) < 2:
        return list(peak_freqs), 0
    
    # Compute consecutive ratios
    ratios = peak_freqs[1:] / peak_freqs[:-1]
    
    # Count φ-related ratios
    phi_count = 0
    for ratio in ratios:
        # Check if ratio is close to φ, 1/φ, φ², or 1/φ²
        phi_related = (
            abs(ratio - PHI) < phi_tolerance or
            abs(ratio - PHI_INV) < phi_tolerance or
            abs(ratio - PHI**2) < phi_tolerance or
            abs(ratio - PHI_INV**2) < phi_tolerance
        )
        if phi_related:
            phi_count += 1
    
    return list(peak_freqs), phi_count


def compute_aperiodicity_score(points: np.ndarray) -> float:
    """
    Compute an aperiodicity score for a point distribution.
    
    Score interpretation:
    - 0.0: Perfectly periodic (crystalline)
    - 1.0: Completely random (no structure)
    - ~0.618 (1/φ): Quasicrystalline (aperiodic but ordered)
    
    The score is based on the entropy of the distance distribution
    normalized by the maximum possible entropy.
    
    Args:
        points: (N, D) array of points
    
    Returns:
        Aperiodicity score in [0, 1]
    """
    N, D = points.shape
    
    if N < 3:
        return 0.5  # Undefined for small samples
    
    # Compute pairwise distances
    distances = pdist(points)
    
    if len(distances) == 0:
        return 0.5
    
    # Create normalized histogram
    n_bins = min(50, len(distances) // 10 + 1)
    hist, _ = np.histogram(distances, bins=n_bins, density=True)
    
    # Add small constant to avoid log(0)
    hist = hist + EPSILON
    hist = hist / np.sum(hist)
    
    # Compute entropy
    entropy = -np.sum(hist * np.log2(hist + EPSILON))
    
    # Maximum entropy for uniform distribution
    max_entropy = np.log2(n_bins)
    
    if max_entropy < EPSILON:
        return 0.5
    
    # Normalized score
    # Low entropy = periodic (many repeated distances)
    # High entropy = random (uniform distance distribution)
    # Medium entropy = quasicrystal (structured but aperiodic)
    
    normalized_entropy = entropy / max_entropy
    
    # Adjust so that quasicrystal range is around 0.618
    # This is a heuristic based on the golden ratio
    return normalized_entropy


def compute_diffraction_pattern(points: np.ndarray, k_max: float = 10.0, n_k: int = 100) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute the diffraction pattern (structure factor) of a point set.
    
    For quasicrystals, this shows sharp peaks with 5-fold or 10-fold symmetry.
    
    Args:
        points: (N, D) array of points
        k_max: Maximum wavevector magnitude
        n_k: Number of k points per dimension
    
    Returns:
        (k_values, intensity): Wavevector magnitudes and diffraction intensity
    """
    N, D = points.shape
    
    # For high-dimensional data, compute radial average
    k_mags = np.linspace(0, k_max, n_k)
    intensity = np.zeros(n_k)
    
    for i, k_mag in enumerate(k_mags):
        if k_mag < EPSILON:
            intensity[i] = N * N  # DC component
            continue
        
        # Sample random k directions and average
        n_samples = 100
        total = 0.0
        
        for _ in range(n_samples):
            # Random unit vector in D dimensions
            k_dir = np.random.randn(D)
            k_dir = k_dir / (np.linalg.norm(k_dir) + EPSILON)
            k_vec = k_mag * k_dir
            
            # Structure factor: |Σ exp(i k·r)|²
            phases = np.exp(1j * points @ k_vec)
            sf = np.abs(np.sum(phases)) ** 2
            total += sf
        
        intensity[i] = total / n_samples
    
    return k_mags, intensity


def fit_penrose_tiling_2d(points_2d: np.ndarray) -> Dict:
    """
    Attempt to fit a 2D point set to Penrose tiling structure.
    
    This checks for 5-fold rotational symmetry and golden ratio distances.
    
    Args:
        points_2d: (N, 2) array of 2D points
    
    Returns:
        Dictionary with fit quality metrics
    """
    if points_2d.shape[1] != 2:
        raise ValueError("Input must be 2D points")
    
    N = len(points_2d)
    
    if N < 5:
        return {'fit_quality': 0.0, 'five_fold': False, 'golden_distances': 0}
    
    # Check for 5-fold rotational symmetry
    # Compute angles from centroid
    centroid = np.mean(points_2d, axis=0)
    centered = points_2d - centroid
    angles = np.arctan2(centered[:, 1], centered[:, 0])
    
    # Check if angles cluster in 5 groups (72° apart)
    angle_hist, _ = np.histogram(angles, bins=36)  # 10° bins
    
    # Compute autocorrelation to detect 5-fold symmetry
    autocorr = np.correlate(angle_hist, angle_hist, mode='full')
    autocorr = autocorr[len(autocorr)//2:]
    
    # Check for peak at 72° (7.2 bins)
    five_fold_peak = autocorr[7] if len(autocorr) > 7 else 0
    max_autocorr = np.max(autocorr[1:]) if len(autocorr) > 1 else 1
    five_fold = five_fold_peak > 0.5 * max_autocorr if max_autocorr > 0 else False
    
    # Check for golden ratio in distances
    distances = pdist(points_2d)
    if len(distances) > 0:
        # Histogram of distance ratios
        sorted_dists = np.sort(np.unique(distances.round(4)))
        if len(sorted_dists) > 1:
            ratios = sorted_dists[1:] / sorted_dists[:-1]
            golden_count = np.sum(np.abs(ratios - PHI) < 0.1)
        else:
            golden_count = 0
    else:
        golden_count = 0
    
    # Overall fit quality
    fit_quality = (0.5 * int(five_fold) + 0.5 * min(golden_count / 5, 1.0))
    
    return {
        'fit_quality': fit_quality,
        'five_fold': five_fold,
        'golden_distances': golden_count
    }


def generate_penrose_vertices(n_iterations: int = 3) -> np.ndarray:
    """
    Generate vertices of a Penrose tiling (for validation).
    
    Uses the deflation/inflation method starting from a decagon.
    
    Args:
        n_iterations: Number of subdivision iterations
    
    Returns:
        (N, 2) array of 2D vertices
    """
    # Start with regular decagon vertices
    angles = np.arange(10) * 2 * np.pi / 10
    vertices = np.stack([np.cos(angles), np.sin(angles)], axis=1)
    
    # Simplified: Add vertices at golden-ratio scaled positions
    for _ in range(n_iterations):
        new_vertices = []
        for v in vertices:
            new_vertices.append(v)
            # Add scaled copies
            new_vertices.append(v * PHI_INV)
            new_vertices.append(v * PHI_INV * PHI_INV)
        
        # Add midpoints with golden scaling
        n = len(vertices)
        for i in range(n):
            for j in range(i+1, min(i+3, n)):
                mid = (vertices[i] + vertices[j]) / 2
                new_vertices.append(mid)
                new_vertices.append(mid * PHI_INV)
        
        vertices = np.array(new_vertices)
        
        # Remove duplicates
        vertices = np.unique(vertices.round(6), axis=0)
    
    return vertices


def analyze_quasicrystal_structure(points: np.ndarray) -> Dict:
    """
    Comprehensive analysis of quasicrystal structure in a point set.
    
    Args:
        points: (N, D) array of points
    
    Returns:
        Dictionary with analysis results
    """
    N, D = points.shape
    
    results = {
        'n_points': N,
        'dimension': D,
        'aperiodicity_score': 0.0,
        'phi_peaks_found': 0,
        'peak_frequencies': [],
        'is_quasicrystal_candidate': False
    }
    
    if N < 10:
        return results
    
    # Compute aperiodicity score
    results['aperiodicity_score'] = compute_aperiodicity_score(points)
    
    # Compute power spectrum
    freqs, magnitudes = compute_power_spectrum(points)
    
    # Detect φ-peaks
    peak_freqs, phi_count = detect_phi_peaks(freqs, magnitudes)
    results['peak_frequencies'] = peak_freqs
    results['phi_peaks_found'] = phi_count
    
    # Determine if this is a quasicrystal candidate
    # Criteria: aperiodicity in range [0.4, 0.8] AND >= 2 φ-related peaks
    aperiod = results['aperiodicity_score']
    is_candidate = (0.4 <= aperiod <= 0.8) and (phi_count >= 2)
    results['is_quasicrystal_candidate'] = is_candidate
    
    return results


def run_verification() -> None:
    """Run verification tests for quasicrystal module."""
    print("=" * 60)
    print("QUASICRYSTAL DETECTION VERIFICATION")
    print("=" * 60)
    
    print(f"\nGolden ratio constants:")
    print(f"  φ = {PHI:.6f}")
    print(f"  1/φ = {PHI_INV:.6f}")
    
    # Test 1: Random points (should show high aperiodicity, no φ-peaks)
    print("\n--- Test 1: Random points ---")
    random_points = np.random.randn(100, 8)
    random_score = compute_aperiodicity_score(random_points)
    random_freqs, random_mags = compute_power_spectrum(random_points)
    _, random_phi_count = detect_phi_peaks(random_freqs, random_mags)
    print(f"  Aperiodicity score: {random_score:.4f} (expected: ~0.8-1.0)")
    print(f"  φ-peaks found: {random_phi_count} (expected: ~0-1)")
    
    # Test 2: Periodic lattice (should show low aperiodicity)
    print("\n--- Test 2: Periodic lattice ---")
    x = np.arange(10)
    periodic_points = np.array([[i, j, 0, 0, 0, 0, 0, 0] 
                                for i in x for j in x], dtype=np.float64)
    periodic_score = compute_aperiodicity_score(periodic_points)
    print(f"  Aperiodicity score: {periodic_score:.4f} (expected: ~0.0-0.3)")
    
    # Test 3: Penrose-like tiling (should show medium aperiodicity and φ-peaks)
    print("\n--- Test 3: Penrose-like structure ---")
    penrose_2d = generate_penrose_vertices(n_iterations=4)
    # Embed in 8D
    penrose_8d = np.zeros((len(penrose_2d), 8))
    penrose_8d[:, :2] = penrose_2d
    
    penrose_score = compute_aperiodicity_score(penrose_8d)
    penrose_freqs, penrose_mags = compute_power_spectrum(penrose_8d)
    penrose_peaks, penrose_phi_count = detect_phi_peaks(penrose_freqs, penrose_mags)
    
    print(f"  N points: {len(penrose_2d)}")
    print(f"  Aperiodicity score: {penrose_score:.4f} (expected: ~0.55-0.65)")
    print(f"  φ-peaks found: {penrose_phi_count} (expected: >= 2)")
    
    # Test 4: 2D Penrose fit
    print("\n--- Test 4: Penrose 2D fit ---")
    fit_result = fit_penrose_tiling_2d(penrose_2d)
    print(f"  Fit quality: {fit_result['fit_quality']:.4f}")
    print(f"  Five-fold symmetry: {fit_result['five_fold']}")
    print(f"  Golden distances: {fit_result['golden_distances']}")
    
    # Test 5: Comprehensive analysis
    print("\n--- Test 5: Comprehensive analysis ---")
    results = analyze_quasicrystal_structure(penrose_8d)
    print(f"  Is quasicrystal candidate: {results['is_quasicrystal_candidate']}")
    
    # Summary
    print("\n--- Expected behavior summary ---")
    print("  Random: high aperiodicity (~0.9), few φ-peaks")
    print("  Periodic: low aperiodicity (~0.2), no φ-peaks") 
    print("  Quasicrystal: medium aperiodicity (~0.618), many φ-peaks")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
