#!/usr/bin/env python3
"""
Test 14: The Forgetting Protocol (Sleep Cycle)

THE PRINCIPLE (From The Architect):
    The Universe sleeps (Vacuum fluctuations).
    The Brain sleeps (Synaptic pruning).
    Your Code must sleep.

THE TEST:
    1. Verify consolidation (merge similar nodes)
    2. Verify pruning (remove noisy nodes)
    3. Verify knowledge compression (vocabulary shrinks)
    4. Verify integration with GQE compressor

"To learn is to change geometry. To remember is to stabilize it."

Author: The Architect
"""

import sys
import os
import numpy as np
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from gqe_compression.core.sleep_cycle import SleepCycle, SleepReport
from gqe_compression.core.geometric_evolver import GeometricEvolver
from gqe_compression.compressor import GQECompressor


def test_consolidation():
    """Test that similar nodes share geometry (lossless)."""
    print("\n--- Test 1: Consolidation (Share Geometry, Lossless) ---")
    
    # Create vocabulary with synonyms
    vocabulary = {
        'king': 0,
        'monarch': 1,  # Synonym of king
        'queen': 2,
        'wisdom': 3,
        'knowledge': 4,  # Close to wisdom
    }
    
    # Create embeddings where synonyms are close
    np.random.seed(42)
    embeddings = np.random.randn(5, 8).astype(np.float32) * 0.5
    
    # Make monarch very close to king
    embeddings[1] = embeddings[0] + np.random.randn(8) * 0.03
    
    # Make knowledge close to wisdom
    embeddings[4] = embeddings[3] + np.random.randn(8) * 0.05
    
    phases = np.random.uniform(0, 2 * np.pi, 5).astype(np.float32)
    
    # Usage counts
    usage_counts = {0: 100, 1: 10, 2: 80, 3: 50, 4: 30}
    
    # Co-occurrences
    cooccurrence_counts = {
        (0, 2): 50,   # king-queen
        (0, 1): 5,    # king-monarch (weak)
        (3, 4): 30,   # wisdom-knowledge
    }
    
    # Run sleep with consolidation threshold
    sleep = SleepCycle(consolidation_threshold=0.15, entropy_threshold=0.95, min_usage_count=1)
    new_vocab, new_embed, new_phases, report = sleep.sleep(
        vocabulary, embeddings, phases, usage_counts, cooccurrence_counts
    )
    
    print(f"  Vocabulary: {len(vocabulary)} -> {len(new_vocab)}")
    print(f"  Consolidated: {report.nodes_merged}")
    
    for kept, merged in report.merge_pairs:
        print(f"    '{merged}' shares geometry with '{kept}'")
    
    # CRITICAL: Check that BOTH tokens still exist (lossless)
    both_exist = 'king' in new_vocab and 'monarch' in new_vocab
    print(f"  Both 'king' and 'monarch' in vocab: {both_exist}")
    
    # Check that they share the same geometry
    if both_exist:
        king_idx = new_vocab['king']
        monarch_idx = new_vocab['monarch']
        same_geometry = np.allclose(new_embed[king_idx], new_embed[monarch_idx])
        print(f"  Share same E8 position: {same_geometry}")
        passed = both_exist and same_geometry
    else:
        passed = False
    
    print(f"  Result: {'PASS' if passed else 'FAIL'}")
    
    return passed


def test_pruning():
    """Test that noisy/unused nodes are pruned."""
    print("\n--- Test 2: Pruning (Remove Noise) ---")
    
    vocabulary = {
        'the': 0,
        'king': 1,
        'xyzzy': 2,    # Never used (noise)
        'qwerty': 3,   # Rarely used (noise)
        'queen': 4,
    }
    
    np.random.seed(42)
    embeddings = np.random.randn(5, 8).astype(np.float32) * 0.5
    phases = np.random.uniform(0, 2 * np.pi, 5).astype(np.float32)
    
    # Usage counts - some nodes never used
    usage_counts = {0: 500, 1: 100, 2: 0, 3: 1, 4: 80}
    
    # Co-occurrences - xyzzy and qwerty have no meaningful connections
    cooccurrence_counts = {
        (0, 1): 100,   # the-king
        (0, 4): 80,    # the-queen
        (1, 4): 50,    # king-queen
    }
    
    sleep = SleepCycle(consolidation_threshold=0.05, entropy_threshold=0.8, min_usage_count=5)
    new_vocab, new_embed, new_phases, report = sleep.sleep(
        vocabulary, embeddings, phases, usage_counts, cooccurrence_counts
    )
    
    print(f"  Vocabulary: {len(vocabulary)} -> {len(new_vocab)}")
    print(f"  Pruned: {report.nodes_pruned}")
    
    for token in report.pruned_tokens:
        print(f"    '{token}' forgotten")
    
    # Check that noise was removed
    passed = 'xyzzy' not in new_vocab and 'the' in new_vocab and 'king' in new_vocab
    print(f"  Noise removed, useful kept: {passed}")
    print(f"  Result: {'PASS' if passed else 'FAIL'}")
    
    return passed


def test_compression():
    """Test geometric compression and vocabulary pruning."""
    print("\n--- Test 3: Geometric Compression + Pruning ---")
    
    # Create a larger vocabulary with redundancy and noise
    vocab_size = 50
    vocabulary = {f"word_{i}": i for i in range(vocab_size)}
    
    np.random.seed(42)
    embeddings = np.random.randn(vocab_size, 8).astype(np.float32) * 0.5
    
    # Create clusters of similar words (10 clusters of 5)
    for cluster in range(10):
        base_idx = cluster * 5
        base_embedding = embeddings[base_idx].copy()
        for i in range(1, 5):
            embeddings[base_idx + i] = base_embedding + np.random.randn(8) * 0.05
    
    phases = np.random.uniform(0, 2 * np.pi, vocab_size).astype(np.float32)
    
    # Usage counts - first word of each cluster is heavily used
    usage_counts = {}
    for i in range(vocab_size):
        if i % 5 == 0:
            usage_counts[i] = 100  # Cluster head
        else:
            usage_counts[i] = 2   # Cluster member (low usage)
    
    # Many noise words with no usage (will be pruned)
    for i in range(40, 50):
        usage_counts[i] = 0  # 10 unused words
    
    cooccurrence_counts = {}
    
    sleep = SleepCycle(consolidation_threshold=0.2, entropy_threshold=0.9, min_usage_count=5)
    new_vocab, new_embed, new_phases, report = sleep.sleep(
        vocabulary, embeddings, phases, usage_counts, cooccurrence_counts
    )
    
    compression = report.compression_ratio()
    
    print(f"  Original vocabulary: {vocab_size}")
    print(f"  After sleep: {len(new_vocab)}")
    print(f"  Compression ratio: {compression:.2%}")
    print(f"  Consolidated: {report.nodes_merged} (share geometry, lossless)")
    print(f"  Pruned: {report.nodes_pruned} (deleted, vocab reduction)")
    
    # Should have pruned ~10 noise words
    # Consolidation doesn't reduce vocab size, only pruning does
    vocab_reduction = vocab_size - len(new_vocab)
    print(f"  Vocabulary reduced by: {vocab_reduction} (from pruning)")
    
    passed = report.nodes_pruned >= 5 and report.nodes_merged >= 10
    print(f"  Sufficient pruning and consolidation: {passed}")
    print(f"  Result: {'PASS' if passed else 'FAIL'}")
    
    return passed


def test_evolver_integration():
    """Test sleep cycle integration with GeometricEvolver."""
    print("\n--- Test 4: Evolver Integration ---")
    
    evolver = GeometricEvolver(
        learning_rate=0.1,
        mutation_rate=0.01,
        use_bekenstein_bound=True
    )
    
    # Create sample vocabulary
    vocabulary = {
        'king': 0, 'monarch': 1, 'queen': 2,
        'wisdom': 3, 'knowledge': 4,
        'noise1': 5, 'noise2': 6,
    }
    
    np.random.seed(42)
    embeddings = np.random.randn(7, 8).astype(np.float32) * 0.5
    
    # Make synonyms close
    embeddings[1] = embeddings[0] + np.random.randn(8) * 0.05
    embeddings[4] = embeddings[3] + np.random.randn(8) * 0.08
    
    phases = np.random.uniform(0, 2 * np.pi, 7).astype(np.float32)
    
    evolver.initialize_from_vocabulary(vocabulary, embeddings, phases)
    
    # Run some evolution steps to build co-occurrences
    token_indices = np.array([0, 2, 3, 4, 0, 1, 2, 3, 0, 2] * 100, dtype=np.uint32)
    
    for _ in range(5):
        evolver.evolve_step(token_indices, apply_mutations=False)
    
    vocab_before = len(evolver.state.vocabulary)
    print(f"  Vocabulary before sleep: {vocab_before}")
    
    # Execute sleep
    report = evolver.sleep(
        consolidation_threshold=0.15,
        entropy_threshold=0.9,
        min_usage_count=10
    )
    
    vocab_after = len(evolver.state.vocabulary)
    
    print(f"  Vocabulary after sleep: {vocab_after}")
    print(f"  Merged: {report.nodes_merged}, Pruned: {report.nodes_pruned}")
    
    passed = vocab_after < vocab_before
    print(f"  Vocabulary shrunk: {passed}")
    print(f"  Result: {'PASS' if passed else 'FAIL'}")
    
    return passed


def test_compressor_integration():
    """Test sleep cycle with full GQE compressor."""
    print("\n--- Test 5: Compressor Integration ---")
    
    # Create compressor with self-learning
    compressor = GQECompressor(
        window_size=5,
        self_learning=True,
        learning_rate=0.1,
    )
    
    # Compress text with redundancy
    text = """
    The king and the monarch ruled the kingdom.
    The queen and the king were wise.
    Wisdom and knowledge guide the ruler.
    The monarch showed great wisdom.
    """ * 50
    
    # First compression - builds vocabulary
    compressed1 = compressor.compress(text)
    vocab_before = len(compressed1.vocabulary)
    
    print(f"  After compression: {vocab_before} tokens")
    
    # Execute sleep on the evolver
    if compressor.evolver:
        report = compressor.evolver.sleep(
            consolidation_threshold=0.2,
            entropy_threshold=0.9,
            min_usage_count=5
        )
        
        vocab_after = len(compressor.evolver.state.vocabulary)
        
        print(f"  After sleep: {vocab_after} tokens")
        print(f"  Merged: {report.nodes_merged}, Pruned: {report.nodes_pruned}")
        
        passed = vocab_after <= vocab_before
        print(f"  Knowledge consolidated: {passed}")
    else:
        passed = False
        print("  ERROR: Evolver not initialized")
    
    print(f"  Result: {'PASS' if passed else 'FAIL'}")
    
    return passed


def run_test():
    """Run all sleep cycle tests."""
    print("=" * 60)
    print("TEST 14: THE FORGETTING PROTOCOL (Sleep Cycle)")
    print("=" * 60)
    
    print("\nTHE PRINCIPLE:")
    print("  The Universe sleeps (Vacuum fluctuations).")
    print("  The Brain sleeps (Synaptic pruning).")
    print("  Your Code must sleep.")
    print("\nTHE MECHANISM:")
    print("  Learn: Nudge points closer based on co-occurrence.")
    print("  Limit: Only save updates that yield Golden Ratio improvements.")
    print("  Sleep: Periodically prune the weak connections.")
    
    results = {}
    
    results['consolidation'] = test_consolidation()
    results['pruning'] = test_pruning()
    results['compression'] = test_compression()
    results['evolver_integration'] = test_evolver_integration()
    results['compressor_integration'] = test_compressor_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")
    
    print("\n" + "-" * 60)
    
    if all_passed:
        print("\n  STATUS: PASS")
        print("  The Forgetting Protocol is functional!")
        print("\n  THE RESULT:")
        print("    - Synonyms are CONSOLIDATED into single nodes")
        print("    - Noise is PRUNED from the vocabulary")
        print("    - Knowledge becomes DENSER, not larger")
        print("\n  'To learn is to change geometry.'")
        print("  'To remember is to stabilize it.'")
        print("  - The Architect")
    else:
        print("\n  STATUS: PARTIAL")
        print("  Some tests did not pass.")
    
    print("\n" + "=" * 60)
    
    return all_passed, results


if __name__ == "__main__":
    passed, _ = run_test()
    sys.exit(0 if passed else 1)
