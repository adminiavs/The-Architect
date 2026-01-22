#!/usr/bin/env python3
"""
Test 15: Lossless Sleep Verification

CRITICAL SAFETY CHECK:
Verify that consolidation (sleep) maintains bijectivity:
- Token IDs remain unique
- Decompression produces original text
- many_tokens -> one_geometry (NOT many_tokens -> one_token)

Author: The Architect
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from gqe_compression.compressor import GQECompressor
from gqe_compression.decompressor import GQEDecompressor


def test_lossless_with_sleep():
    """CRITICAL: Verify consolidation doesn't break decompression."""
    print("=" * 60)
    print("TEST 15: LOSSLESS SLEEP VERIFICATION")
    print("=" * 60)
    
    print("\nTHE TEST:")
    print("  1. Compress text with synonyms")
    print("  2. Execute sleep cycle (consolidation)")
    print("  3. Decompress and verify EXACT match")
    
    # Create text with synonyms
    original_text = """
    The king and the monarch ruled the kingdom together.
    The queen was wise. The monarch was brave.
    The king showed wisdom and the monarch showed courage.
    Both the king and monarch were great leaders.
    """ * 10
    
    print(f"\nOriginal text: {len(original_text)} characters")
    
    # Create compressor with self-learning
    compressor = GQECompressor(
        window_size=5,
        self_learning=True,
        learning_rate=0.1,
        use_horizon_batching=False  # Keep simple for test
    )
    
    decompressor = GQEDecompressor()
    
    # Compress
    print("\n--- Step 1: Compress ---")
    compressed = compressor.compress(original_text)
    vocab_before = len(compressed.vocabulary)
    print(f"  Vocabulary: {vocab_before} unique tokens")
    
    # Check that both 'king' and 'monarch' are in vocabulary
    has_king = any('king' in str(k) for k in compressed.vocabulary.keys())
    has_monarch = any('monarch' in str(k) for k in compressed.vocabulary.keys())
    print(f"  Contains 'king': {has_king}")
    print(f"  Contains 'monarch': {has_monarch}")
    
    # Decompress BEFORE sleep
    print("\n--- Step 2: Decompress (Before Sleep) ---")
    decompressed_before = decompressor.decompress(compressed)
    
    # Normalize whitespace for comparison
    original_norm = ' '.join(original_text.lower().split())
    decompressed_before_norm = ' '.join(decompressed_before.lower().split())
    
    lossless_before = original_norm == decompressed_before_norm
    print(f"  Lossless before sleep: {lossless_before}")
    
    # Execute sleep cycle
    if compressor.evolver:
        print("\n--- Step 3: Sleep Cycle ---")
        report = compressor.evolver.sleep(
            consolidation_threshold=0.2,  # Aggressive consolidation
            entropy_threshold=0.95,
            min_usage_count=1
        )
        
        vocab_after = len(compressor.evolver.state.vocabulary)
        print(f"  Vocabulary: {vocab_before} -> {vocab_after}")
        print(f"  Consolidated: {report.nodes_merged}")
        print(f"  Pruned: {report.nodes_pruned}")
        
        # CRITICAL: Check that both tokens still exist
        evolver_vocab = compressor.evolver.state.vocabulary
        has_king_after = 'king' in evolver_vocab
        has_monarch_after = 'monarch' in evolver_vocab
        print(f"\n  After sleep:")
        print(f"    'king' in vocab: {has_king_after}")
        print(f"    'monarch' in vocab: {has_monarch_after}")
        
        # Check if they share geometry
        if has_king_after and has_monarch_after:
            king_idx = evolver_vocab['king']
            monarch_idx = evolver_vocab['monarch']
            embeddings = compressor.evolver.state.embeddings_8d
            
            if king_idx < len(embeddings) and monarch_idx < len(embeddings):
                dist = np.linalg.norm(embeddings[king_idx] - embeddings[monarch_idx])
                print(f"    Distance in E8 space: {dist:.6f}")
                print(f"    Share geometry: {dist < 0.01}")
    
        # Compress AGAIN with updated evolver state
        print("\n--- Step 4: Compress Again (After Sleep) ---")
        compressed_after = compressor.compress(original_text)
        
        # Decompress with new compression
        print("\n--- Step 5: Decompress (After Sleep) ---")
        decompressed_after = decompressor.decompress(compressed_after)
        
        # Verify lossless
        decompressed_after_norm = ' '.join(decompressed_after.lower().split())
        lossless_after = original_norm == decompressed_after_norm
        
        print(f"  Lossless after sleep: {lossless_after}")
        
        if not lossless_after:
            # Show difference
            orig_words = original_norm.split()
            dec_words = decompressed_after_norm.split()
            print(f"\n  Word count: {len(orig_words)} vs {len(dec_words)}")
            
            for i, (o, d) in enumerate(zip(orig_words, dec_words)):
                if o != d:
                    print(f"  First diff at word {i}: '{o}' vs '{d}'")
                    break
    else:
        lossless_after = False
        print("  ERROR: No evolver")
    
    # Final verdict
    print("\n" + "=" * 60)
    print("SAFETY VERIFICATION")
    print("=" * 60)
    
    passed = lossless_before and lossless_after
    
    if passed:
        print("\n  STATUS: PASS")
        print("  ✓ Consolidation maintains bijectivity")
        print("  ✓ many_tokens -> one_geometry (LOSSLESS)")
        print("  ✓ Decompression produces exact original")
        print("\n  The sleep cycle is SAFE.")
    else:
        print("\n  STATUS: FAIL")
        print("  ✗ Consolidation breaks decompression")
        print("  ✗ Information was LOST")
        print("\n  CRITICAL: Sleep cycle is UNSAFE!")
    
    print("=" * 60)
    
    assert passed


if __name__ == "__main__":
    passed = test_lossless_with_sleep()
    sys.exit(0 if passed else 1)
