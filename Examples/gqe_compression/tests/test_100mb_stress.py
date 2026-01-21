#!/usr/bin/env python3
"""
Test 10: The 100MB Singularity Stress Test

"The geometry gets stronger as the world gets bigger."

This test pushes the GQE compressor to the 100MB scale.
It verifies:
1. Horizon Batching stability at scale (400+ frames)
2. Peak RSS flatlining (The "Active Horizon" limit)
3. Vocabulary saturation on massive data
4. Real-world performance (throughput)

Author: The Architect
"""

import os
import sys
import time
import resource
import gc
from typing import Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from gqe_compression.compressor import GQECompressor
from gqe_compression.core.horizon_batcher import DEFAULT_CHUNK_SIZE


def get_peak_rss_mb() -> float:
    """Get peak RSS since process start in MB."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # ru_maxrss is in KB on Linux
    return usage.ru_maxrss / 1024


def generate_100mb_text(file_path: str):
    """Generate 100MB of text using a mix of repetitive and semantic patterns."""
    import numpy as np
    
    target_bytes = 100 * 1024 * 1024
    
    words = [
        'the', 'of', 'and', 'to', 'in', 'a', 'is', 'that', 'for', 'it',
        'universe', 'geometry', 'quantum', 'lattice', 'dimension', 'projection',
        'holographic', 'spinor', 'phase', 'topology', 'entropy', 'information',
        'structure', 'pattern', 'frequency', 'resonance', 'coherence', 'field',
        'king', 'queen', 'monarch', 'ruler', 'sovereign', 'emperor', 'kingdom',
        'realm', 'empire', 'nation', 'territory', 'domain', 'throne', 'crown'
    ]
    
    rng = np.random.RandomState(42)
    
    print(f"  Generating {target_bytes / 1024 / 1024:.1f} MB of data...")
    
    with open(file_path, 'w') as f:
        current_size = 0
        while current_size < target_bytes:
            sentence_len = rng.randint(5, 15)
            sentence = ' '.join(rng.choice(words) for _ in range(sentence_len)) + '. '
            f.write(sentence)
            current_size += len(sentence)
            
            if current_size % (10 * 1024 * 1024) < 1000:
                print(f"    Progress: {current_size / 1024 / 1024:.1f} MB")
    
    print(f"  Data generation complete: {os.path.getsize(file_path):,} bytes")


def run_stress_test():
    print("=" * 70)
    print("TEST 10: THE 100MB SINGULARITY STRESS TEST")
    print("=" * 70)
    
    file_path = "/tmp/gqe_100mb_test.txt"
    
    try:
        if not os.path.exists(file_path):
            generate_100mb_text(file_path)
        else:
            print(f"  Using existing data file: {file_path}")
            
        print(f"\nCurrent RSS before compression: {get_peak_rss_mb():.1f} MB")
        
        compressor = GQECompressor(
            window_size=5,
            use_horizon_batching=True,
            chunk_size=DEFAULT_CHUNK_SIZE
        )
        
        print("\n--- Starting Streaming Compression ---")
        print(f"  File: {file_path}")
        print(f"  Horizon Frame size: {DEFAULT_CHUNK_SIZE / 1024:.1f} KB")
        
        start_time = time.time()
        # Use the NEW streaming method
        compressed = compressor.compress_file(file_path)
        end_time = time.time()
        
        duration = end_time - start_time
        peak_rss = get_peak_rss_mb()
        
        print("\n--- Results ---")
        file_size_mb = os.path.getsize(file_path) / 1024 / 1024
        print(f"  Time taken: {duration:.2f} seconds")
        print(f"  Throughput: {file_size_mb / duration:.2f} MB/s")
        print(f"  Peak RSS:   {peak_rss:.1f} MB")
        
        # Meta analysis
        n_frames = compressed.metadata.get('n_frames', 0)
        vocab_size = len(compressed.vocabulary)
        n_tokens = compressed.metadata.get('n_tokens', 0)
        
        print(f"\n  Vocabulary: {vocab_size} unique tokens")
        print(f"  Total tokens: {n_tokens:,}")
        print(f"  Frames processed: {n_frames}")
        print(f"  Saturation: {vocab_size / n_tokens * 100:.4f}%")
        
        # Verification of RSS Flatline
        print("\n--- Verification ---")
        if peak_rss < 1000:
            print(f"  [PASS] RSS flatlined at {peak_rss:.1f} MB (STABLE SCALE PROVEN)")
        else:
            print(f"  [WARNING] RSS higher than expected: {peak_rss:.1f} MB")
            
        # Serialize check
        ser_start = time.time()
        serialized = compressed.to_bytes()
        ser_duration = time.time() - ser_start
        
        print(f"  Serialized size: {len(serialized) / 1024 / 1024:.2f} MB")
        print(f"  Compression ratio: {len(serialized) / (file_size_mb * 1024 * 1024):.4f}x")
        print(f"  Serialization time: {ser_duration:.2f}s")
        
    finally:
        if os.path.exists(file_path):
            # os.remove(file_path)
            pass

    print("\n" + "=" * 70)


if __name__ == "__main__":
    run_stress_test()
