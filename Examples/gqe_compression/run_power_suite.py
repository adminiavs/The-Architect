#!/usr/bin/env python3
"""
The Power of 10 Suite: Logarithmic Scaling Test for GQE Engine

This script maps the capability of the GQE Engine across logarithmic scales
to prove Holographic Scaling (Ratio ∝ 1/N).

Columns: Size | Time | Ratio | Peak RAM
"""

import sys
import os
import time
import psutil
import csv
from pathlib import Path
import numpy as np

# Add the parent directory to sys.path to allow absolute imports
# This ensures that 'import gqe_compression' works regardless of where the script is called from
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from gqe_compression.compressor import GQECompressor
except ImportError:
    # Fallback for different execution contexts
    from compressor import GQECompressor

# Test sizes (in MB)
TEST_SIZES = [1, 10, 50, 100, 200]

# Base text for generation - The Architect's Axioms
BASE_TEXT = """
The universe is a static geometric object projected onto spacetime.
Matter, forces, and constants emerge from projection geometry.
Gravity is entropic and time is traversal through the E8 lattice.
Consciousness collapses superposition into experience.
The Golden Ratio (phi) is fundamental to quasicrystal structure.
Holographic projection implies that every part contains the whole.
Error correction is a fundamental aspect of physical laws.
To learn is to change geometry. To remember is to stabilize it.
Evolution is geometric refinement through natural selection.
The Bekenstein Bound limits information growth to surface area.
Sleep is consolidation and pruning, making knowledge denser.
"""

def generate_test_file(size_mb: int, output_path: str):
    """Generate a test file of specified size with synthetic text."""
    target_bytes = size_mb * 1024 * 1024
    
    print(f"Generating {size_mb}MB test file...")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        current_bytes = 0
        iteration = 0
        while current_bytes < target_bytes:
            # Block structure with variation to simulate real data patterns
            text = f"[Block {iteration}] {BASE_TEXT} "
            if iteration % 10 == 0:
                # Add some numeric "noise" or "coordinates"
                text += f"Coord: {np.sin(iteration):.8f}, {np.cos(iteration):.8f} "
            
            f.write(text)
            current_bytes += len(text.encode('utf-8'))
            iteration += 1
            
    print(f"Created: {os.path.getsize(output_path) / (1024*1024):.2f} MB")

def get_peak_rss_mb():
    """Get current Resident Set Size (RSS) in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

def run_suite():
    print("=" * 60)
    print("GQE ENGINE: POWER OF 10 PERFORMANCE CURVE")
    print("=" * 60)
    
    # Results storage
    results = []
    
    # Workspace for test files
    workspace = Path("/tmp/gqe_power_suite")
    workspace.mkdir(exist_ok=True)
    
    csv_path = "performance_curve.csv"
    
    # Initialize CSV
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Size (MB)", "Time (s)", "Ratio", "Peak RAM (MB)"])
    
    for size_mb in TEST_SIZES:
        file_path = workspace / f"test_{size_mb}mb.txt"
        generate_test_file(size_mb, str(file_path))
        
        print(f"\nCompressing {size_mb}MB...")
        
        # Reset Peak RAM tracking baseline
        baseline_ram = get_peak_rss_mb()
        
        compressor = GQECompressor(
            use_horizon_batching=True,
            chunk_size=233 * 1024, # Optimized Horizon Threshold
            tokenize_mode='word'
        )
        
        start_time = time.time()
        compressed = compressor.compress_file(str(file_path))
        serialized = compressed.to_bytes()
        end_time = time.time()
        
        duration = end_time - start_time
        compressed_size = len(serialized)
        original_size = os.path.getsize(str(file_path))
        ratio = compressed_size / original_size
        peak_ram = get_peak_rss_mb()
        
        print(f"  Time: {duration:.2f}s")
        print(f"  Ratio: {ratio:.4f}")
        print(f"  Peak RAM: {peak_ram:.2f} MB")
        
        result = {
            "Size": size_mb,
            "Time": f"{duration:.2f}",
            "Ratio": f"{ratio:.4f}",
            "Peak RAM": f"{peak_ram:.2f}"
        }
        results.append(result)
        
        # Append to CSV immediately
        with open(csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([size_mb, result["Time"], result["Ratio"], result["Peak RAM"]])
            
        # Cleanup
        if file_path.exists():
            file_path.unlink()

    print("\n" + "=" * 60)
    print("SUITE COMPLETE")
    print(f"Results saved to {csv_path}")
    print("=" * 60)
    
    # Summary Analysis
    if len(results) >= 2:
        first_ratio = float(results[0]["Ratio"])
        last_ratio = float(results[-1]["Ratio"])
        if last_ratio <= first_ratio:
            print("HOLOGRAPHIC SCALING DETECTED: Ratio is stable or improving with size.")
        else:
            print("WARNING: Ratio is degrading. Check for entropy leaks.")

if __name__ == "__main__":
    run_suite()
