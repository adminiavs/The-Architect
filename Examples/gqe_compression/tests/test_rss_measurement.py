#!/usr/bin/env python3
"""
RSS Measurement Test: The Falsifiable Proof

"Theory is the map. Measurement is the territory."

This test measures ACTUAL process memory (RSS - Resident Set Size)
directly from the OS kernel, not theoretical calculations.

THE TEST:
    Case A (Standard): Load full 10MB graph - predict crash/massive RAM
    Case B (Horizon): Load in 233KB chunks - predict stable ~50-100MB RSS

THE MEASUREMENT:
    Peak RSS from /proc/self/status (Linux) or resource.getrusage()
    This is the ground truth - what the kernel actually allocated.

Author: The Architect
"""

import os
import sys
import gc
import time
import resource
import subprocess
from typing import Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def get_rss_mb() -> float:
    """
    Get current RSS (Resident Set Size) in MB.
    
    Reads directly from /proc/self/status on Linux.
    This is the ACTUAL memory allocated by the kernel.
    """
    try:
        # Linux: Read from /proc/self/status
        with open('/proc/self/status', 'r') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    # Format: "VmRSS:    12345 kB"
                    parts = line.split()
                    rss_kb = int(parts[1])
                    return rss_kb / 1024.0  # Convert to MB
    except FileNotFoundError:
        pass
    
    # Fallback: use resource module
    # Note: ru_maxrss is in KB on Linux, bytes on macOS
    usage = resource.getrusage(resource.RUSAGE_SELF)
    if sys.platform == 'darwin':
        return usage.ru_maxrss / 1024 / 1024  # bytes to MB
    else:
        return usage.ru_maxrss / 1024  # KB to MB


def get_peak_rss_mb() -> float:
    """
    Get peak RSS since process start.
    """
    usage = resource.getrusage(resource.RUSAGE_SELF)
    if sys.platform == 'darwin':
        return usage.ru_maxrss / 1024 / 1024
    else:
        return usage.ru_maxrss / 1024


def generate_test_data(size_mb: float) -> str:
    """Generate test data of specified size in MB."""
    import numpy as np
    
    target_bytes = int(size_mb * 1024 * 1024)
    
    words = [
        'the', 'of', 'and', 'to', 'in', 'a', 'is', 'that', 'for', 'it',
        'universe', 'geometry', 'quantum', 'lattice', 'dimension', 'projection',
        'holographic', 'spinor', 'phase', 'topology', 'entropy', 'information',
        'structure', 'pattern', 'frequency', 'resonance', 'coherence', 'field',
        'king', 'queen', 'monarch', 'ruler', 'sovereign', 'emperor', 'kingdom',
        'realm', 'empire', 'nation', 'territory', 'domain', 'throne', 'crown'
    ]
    
    rng = np.random.RandomState(42)
    text_parts = []
    current_size = 0
    
    while current_size < target_bytes:
        sentence_len = rng.randint(5, 15)
        sentence = ' '.join(rng.choice(words) for _ in range(sentence_len)) + '.'
        text_parts.append(sentence)
        current_size += len(sentence) + 1
    
    return ' '.join(text_parts)[:target_bytes]


def run_compression_in_subprocess(data_file: str, use_horizon: bool) -> Tuple[float, float, bool]:
    """
    Run compression in a subprocess to get clean RSS measurement.
    
    Returns:
        (peak_rss_mb, duration_sec, success)
    """
    script = f'''
import sys
sys.path.insert(0, "{os.path.dirname(os.path.dirname(os.path.dirname(__file__)))}")

import resource
import time

def get_peak_rss_mb():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_maxrss / 1024  # KB to MB on Linux

# Read test data
with open("{data_file}", "r") as f:
    text = f.read()

print(f"Data size: {{len(text)}} bytes", file=sys.stderr)
print(f"RSS before: {{get_peak_rss_mb():.1f}} MB", file=sys.stderr)

from gqe_compression.compressor import GQECompressor

compressor = GQECompressor(
    window_size=5, 
    use_horizon_batching={use_horizon}
)

start = time.time()
try:
    compressed = compressor.compress(text)
    duration = time.time() - start
    success = True
except MemoryError:
    duration = time.time() - start
    success = False

peak_rss = get_peak_rss_mb()
print(f"RSS after: {{peak_rss:.1f}} MB", file=sys.stderr)
print(f"Duration: {{duration:.2f}}s", file=sys.stderr)

# Output format: peak_rss,duration,success
print(f"{{peak_rss}},{{duration}},{{1 if success else 0}}")
'''
    
    try:
        result = subprocess.run(
            [sys.executable, '-c', script],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        
        # Print stderr for debugging
        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                print(f"    {line}")
        
        # Parse output
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(',')
            peak_rss = float(parts[0])
            duration = float(parts[1])
            success = int(parts[2]) == 1
            return peak_rss, duration, success
        else:
            return 0, 0, False
            
    except subprocess.TimeoutExpired:
        print("    TIMEOUT (> 5 minutes)")
        return 0, 300, False
    except Exception as e:
        print(f"    ERROR: {e}")
        return 0, 0, False


def run_test():
    """
    Run the RSS Measurement Test.
    
    This is the FALSIFIABLE PROOF of Horizon Batching.
    """
    print("=" * 70)
    print("RSS MEASUREMENT TEST: THE FALSIFIABLE PROOF")
    print("=" * 70)
    
    print("\n'Theory is the map. Measurement is the territory.'")
    print()
    print("This test measures ACTUAL process memory (RSS) from the OS kernel.")
    print("Not theoretical calculations - REAL memory allocation.")
    
    # Test sizes
    test_sizes_mb = [1, 5, 10]
    
    results = {
        'standard': [],
        'horizon': [],
        'passed': False
    }
    
    # Create temporary data files
    print("\n--- Generating test data ---")
    data_files = {}
    for size_mb in test_sizes_mb:
        print(f"  Generating {size_mb}MB test data...")
        data = generate_test_data(size_mb)
        
        data_file = f"/tmp/gqe_test_{size_mb}mb.txt"
        with open(data_file, 'w') as f:
            f.write(data)
        data_files[size_mb] = data_file
        print(f"    Saved to {data_file} ({len(data):,} bytes)")
    
    # Run tests
    print("\n" + "=" * 70)
    print("CASE A: STANDARD (No Horizon Batching)")
    print("Prediction: High RSS, possibly crash on large inputs")
    print("=" * 70)
    
    for size_mb in test_sizes_mb:
        print(f"\n  [{size_mb}MB] Standard compression:")
        peak_rss, duration, success = run_compression_in_subprocess(
            data_files[size_mb], 
            use_horizon=False
        )
        
        results['standard'].append({
            'size_mb': size_mb,
            'peak_rss_mb': peak_rss,
            'duration_sec': duration,
            'success': success
        })
        
        status = "SUCCESS" if success else "FAILED"
        print(f"    Result: {status}")
        print(f"    Peak RSS: {peak_rss:.1f} MB")
        print(f"    Duration: {duration:.2f}s")
    
    print("\n" + "=" * 70)
    print("CASE B: HORIZON BATCHING (233KB chunks)")
    print("Prediction: Stable RSS ~50-100MB regardless of input size")
    print("=" * 70)
    
    for size_mb in test_sizes_mb:
        print(f"\n  [{size_mb}MB] Horizon batching:")
        peak_rss, duration, success = run_compression_in_subprocess(
            data_files[size_mb], 
            use_horizon=True
        )
        
        results['horizon'].append({
            'size_mb': size_mb,
            'peak_rss_mb': peak_rss,
            'duration_sec': duration,
            'success': success
        })
        
        status = "SUCCESS" if success else "FAILED"
        print(f"    Result: {status}")
        print(f"    Peak RSS: {peak_rss:.1f} MB")
        print(f"    Duration: {duration:.2f}s")
    
    # Cleanup
    for data_file in data_files.values():
        try:
            os.remove(data_file)
        except:
            pass
    
    # Analysis
    print("\n" + "=" * 70)
    print("RESULTS: RSS COMPARISON")
    print("=" * 70)
    
    print(f"\n  {'Size':<10} | {'Standard RSS':>15} | {'Horizon RSS':>15} | {'Reduction':>12}")
    print("  " + "-" * 60)
    
    reductions = []
    for i, size_mb in enumerate(test_sizes_mb):
        std = results['standard'][i]
        hz = results['horizon'][i]
        
        std_rss = std['peak_rss_mb']
        hz_rss = hz['peak_rss_mb']
        
        if hz_rss > 0:
            reduction = std_rss / hz_rss
            reductions.append(reduction)
        else:
            reduction = 0
        
        std_str = f"{std_rss:.1f} MB" if std['success'] else "FAILED"
        hz_str = f"{hz_rss:.1f} MB" if hz['success'] else "FAILED"
        red_str = f"{reduction:.1f}x" if reduction > 0 else "N/A"
        
        print(f"  {size_mb}MB       | {std_str:>15} | {hz_str:>15} | {red_str:>12}")
    
    # Final analysis
    print("\n--- ANALYSIS ---")
    
    # Check if horizon RSS is stable (doesn't grow linearly with input)
    horizon_rss_values = [r['peak_rss_mb'] for r in results['horizon'] if r['success']]
    standard_rss_values = [r['peak_rss_mb'] for r in results['standard'] if r['success']]
    
    # Calculate RSS growth rate
    hz_growth = 0
    std_growth = 0
    growth_reduction = 0
    
    if len(horizon_rss_values) >= 2:
        hz_growth = (horizon_rss_values[-1] - horizon_rss_values[0]) / (test_sizes_mb[-1] - test_sizes_mb[0])
        std_growth = (standard_rss_values[-1] - standard_rss_values[0]) / (test_sizes_mb[-1] - test_sizes_mb[0]) if len(standard_rss_values) >= 2 else float('inf')
        
        print(f"\n  Standard RSS growth: {std_growth:.1f} MB per MB input")
        print(f"  Horizon RSS growth:  {hz_growth:.1f} MB per MB input")
        
        # Horizon should have much lower growth rate
        growth_reduction = std_growth / hz_growth if hz_growth > 0 else float('inf')
        print(f"  Growth rate reduction: {growth_reduction:.1f}x")
    
    # Check if horizon RSS stays within bounds
    max_horizon_rss = max(horizon_rss_values) if horizon_rss_values else 0
    print(f"\n  Maximum Horizon RSS: {max_horizon_rss:.1f} MB")
    print(f"  Horizon RSS stable: {'YES' if max_horizon_rss < 200 else 'NO'} (threshold: 200MB)")
    
    # Average reduction
    if reductions:
        avg_reduction = sum(reductions) / len(reductions)
        print(f"  Average RSS reduction: {avg_reduction:.1f}x")
    
    # Pass criteria
    print("\n--- VERDICT ---")
    
    # Pass if:
    # 1. All horizon tests succeeded
    # 2. Growth rate reduced by at least 1.5x
    # 3. RSS reduction > 1.2x on largest test
    
    all_horizon_success = all(r['success'] for r in results['horizon'])
    growth_rate_improved = growth_reduction > 1.5
    good_reduction = reductions[-1] > 1.2 if reductions else False  # Check largest test
    
    results['passed'] = all_horizon_success and (growth_rate_improved or good_reduction)
    results['growth_reduction'] = growth_reduction
    
    if results['passed']:
        print("\n  STATUS: PASS")
        print("  HORIZON BATCHING PROVEN WITH REAL RSS MEASUREMENTS!")
        print()
        print("  Evidence (from OS kernel, not theory):")
        print(f"    - All horizon compressions succeeded: YES")
        print(f"    - Growth rate reduction: {growth_reduction:.1f}x")
        print(f"    - RSS reduction on 10MB: {reductions[-1]:.1f}x")
        print(f"    - Standard 10MB RSS: {standard_rss_values[-1]:.1f} MB")
        print(f"    - Horizon 10MB RSS:  {horizon_rss_values[-1]:.1f} MB")
        print()
        print("  THE KEY FINDING:")
        print(f"    Standard grows at {std_growth:.1f} MB per MB input")
        print(f"    Horizon grows at  {hz_growth:.1f} MB per MB input")
        print(f"    -> Horizon's memory footprint grows {growth_reduction:.1f}x SLOWER")
        print()
        print("  'The territory matches the map.'")
        print("  Horizon Batching works in REALITY, not just THEORY.")
    else:
        print("\n  STATUS: PARTIAL")
        print(f"    - All horizon success: {all_horizon_success}")
        print(f"    - Growth rate improved (> 1.5x): {growth_rate_improved}")
        print(f"    - Good reduction on largest: {good_reduction}")
    
    print("\n" + "=" * 70)
    
    return results['passed'], results


if __name__ == "__main__":
    passed, results = run_test()
    print(f"\nFinal: {'PASSED' if passed else 'NEEDS INVESTIGATION'}")
    sys.exit(0 if passed else 1)
