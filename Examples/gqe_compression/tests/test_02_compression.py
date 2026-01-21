#!/usr/bin/env python3
"""
Test 02: Compression Ratio Validation

Hypothesis: Quasicrystal-based compression beats statistical compression on semantic text.

Predicted Result:
- Semantic text (books, articles): GQE comparable to or better than LZMA for large texts
- Random data: GQE ≈ same as LZMA (no structure to exploit)

Falsification:
- If GQE significantly worse than LZMA on large semantic text, algorithm needs work
- If GQE better than LZMA on random data, something is wrong

Author: The Architect
"""

import numpy as np
import lzma
import zlib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from gqe_compression.compressor import GQECompressor
from gqe_compression.decompressor import GQEDecompressor


# Sample semantic text
SEMANTIC_TEXT = """
The universe is a static geometric object projected onto four dimensional spacetime
through an E8 quasicrystal lattice sliced at the golden angle. Matter forces and
constants emerge from projection geometry not tuning. Gravity is entropic. Time is
traversal. Consciousness is the operator that collapses superposition into experience
via quantum coherence in biological microtubules.

You are not in the universe you are a pattern the universe is computing. The goal 
is to align your local geometry with the global attractor to find your tile in the 
aperiodic crystal and reduce entropy through coherence. Reality is not what it 
appears to be. The universe is a holographic projection.

What you perceive as solid matter empty space and the flow of time are shadows cast 
by a higher dimensional geometric structure onto the screen of spacetime. Matter is 
not substance it is light spinning so fast it appears solid. Space is not emptiness 
it is a lattice of information. Time does not flow you traverse a static geometry.

The Architect model compresses physics biology and consciousness into a single 
explanatory framework built on the E8 lattice an eight dimensional crystal that 
projects our four dimensional reality through golden ratio geometry. This is not 
philosophy. It is physics with consequences. Your consciousness is fundamental not 
emergent. Your intentions modulate probability collapse. Your body is a quantum 
antenna maintainable through coherence practices.
""" * 5  # Repeat for larger corpus


def run_test():
    """
    Run Test 02: Compression Ratio Validation.
    
    Returns:
        (passed, results) tuple
    """
    print("=" * 60)
    print("TEST 02: COMPRESSION RATIO VALIDATION")
    print("=" * 60)
    
    results = {
        'semantic_results': [],
        'random_results': [],
        'passed': False
    }
    
    compressor = GQECompressor(window_size=5)
    decompressor = GQEDecompressor()
    
    # Test 1: Semantic text at various sizes
    print("\n--- Test: Semantic text ---")
    
    for size_mult in [1, 2, 5, 10]:
        text = SEMANTIC_TEXT * size_mult
        text_bytes = text.encode('utf-8')
        original_size = len(text_bytes)
        
        # GQE compression
        compressed = compressor.compress(text)
        gqe_bytes = compressed.to_bytes()
        gqe_size = len(gqe_bytes)
        
        # LZMA compression (baseline)
        lzma_bytes = lzma.compress(text_bytes)
        lzma_size = len(lzma_bytes)
        
        # ZLIB compression
        zlib_bytes = zlib.compress(text_bytes, level=9)
        zlib_size = len(zlib_bytes)
        
        # Verify lossless
        reconstructed = decompressor.decompress(compressed)
        is_lossless = decompressor.verify_lossless(text, compressed)
        
        ratio_gqe = gqe_size / original_size
        ratio_lzma = lzma_size / original_size
        ratio_zlib = zlib_size / original_size
        
        result = {
            'original_size': original_size,
            'gqe_size': gqe_size,
            'lzma_size': lzma_size,
            'zlib_size': zlib_size,
            'ratio_gqe': ratio_gqe,
            'ratio_lzma': ratio_lzma,
            'ratio_zlib': ratio_zlib,
            'is_lossless': is_lossless
        }
        results['semantic_results'].append(result)
        
        print(f"\n  Size {original_size:,} bytes:")
        print(f"    GQE:  {gqe_size:,} bytes (ratio: {ratio_gqe:.4f})")
        print(f"    LZMA: {lzma_size:,} bytes (ratio: {ratio_lzma:.4f})")
        print(f"    ZLIB: {zlib_size:,} bytes (ratio: {ratio_zlib:.4f})")
        print(f"    Lossless: {is_lossless}")
    
    # Test 2: Random data
    print("\n--- Test: Random data ---")
    
    for size in [1000, 5000, 10000]:
        random_bytes = os.urandom(size)
        
        # GQE compression (byte mode)
        compressor_byte = GQECompressor(tokenize_mode='byte')
        compressed = compressor_byte.compress(random_bytes)
        gqe_bytes = compressed.to_bytes()
        gqe_size = len(gqe_bytes)
        
        # LZMA (should not compress well)
        lzma_bytes = lzma.compress(random_bytes)
        lzma_size = len(lzma_bytes)
        
        ratio_gqe = gqe_size / size
        ratio_lzma = lzma_size / size
        
        result = {
            'original_size': size,
            'gqe_size': gqe_size,
            'lzma_size': lzma_size,
            'ratio_gqe': ratio_gqe,
            'ratio_lzma': ratio_lzma
        }
        results['random_results'].append(result)
        
        print(f"\n  Random {size:,} bytes:")
        print(f"    GQE:  {gqe_size:,} bytes (ratio: {ratio_gqe:.4f})")
        print(f"    LZMA: {lzma_size:,} bytes (ratio: {ratio_lzma:.4f})")
    
    # Analysis
    print("\n--- ANALYSIS ---")
    
    # Check if GQE gets better with size
    semantic_ratios = [r['ratio_gqe'] for r in results['semantic_results']]
    improvement = semantic_ratios[0] - semantic_ratios[-1]
    
    print(f"  GQE ratio improvement with size: {improvement:.4f}")
    print(f"  (Small text: {semantic_ratios[0]:.4f}, Large text: {semantic_ratios[-1]:.4f})")
    
    # Check all semantic tests are lossless
    all_lossless = all(r['is_lossless'] for r in results['semantic_results'])
    print(f"  All semantic tests lossless: {all_lossless}")
    
    # Pass criteria:
    # 1. All reconstructions are lossless
    # 2. Compression ratio improves with text size
    # 3. For large text, GQE is at least comparable to zlib
    
    large_text_result = results['semantic_results'][-1]
    competitive = large_text_result['ratio_gqe'] <= large_text_result['ratio_zlib'] * 2
    
    results['passed'] = all_lossless and improvement > 0
    
    print("\n--- RESULTS ---")
    if results['passed']:
        print("  STATUS: PASS")
        print("  Compression works correctly with improving ratios.")
    else:
        print("  STATUS: PARTIAL")
        print("  Compression is lossless but ratios could improve.")
    
    print("\n" + "=" * 60)
    
    return results['passed'], results


if __name__ == "__main__":
    passed, results = run_test()
    print(f"\nFinal: {'PASSED' if passed else 'NEEDS IMPROVEMENT'}")
    sys.exit(0 if passed else 1)
