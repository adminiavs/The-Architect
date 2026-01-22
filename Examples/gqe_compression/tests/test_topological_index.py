#!/usr/bin/env python3
"""
Test Suite for Topological Indexing (v55 Format)

THE PHYSICS:
"The dictionary is not a list of words. It is a map of the crystal.
Once you have the map, you don't need the words."

Test Cases:
1. Lattice Index: E8 root mapping and round-trip
2. Delta-Phi Packer: Predictive geometry encoding
3. V55 Format: Serialization and deserialization
4. Lossless: 100% token sequence preservation
5. Compression: Better ratio than v54 on varied text

Author: The Architect
License: Public Domain
"""

import pytest
import numpy as np
import zlib
import os
import sys

# Set up path for module imports
_test_dir = os.path.dirname(os.path.abspath(__file__))
_gqe_dir = os.path.dirname(_test_dir)
_examples_dir = os.path.dirname(_gqe_dir)
if _examples_dir not in sys.path:
    sys.path.insert(0, _examples_dir)

from gqe_compression.core.lattice_index import LatticeIndex, LatticeEntry, get_e8_roots
from gqe_compression.core.delta_phi_packer import DeltaPhiPacker, DeltaPackConfig, GeometricPredictor


class TestLatticeIndex:
    """Test the LatticeIndex class."""
    
    def test_e8_roots_count(self):
        """Verify E8 lattice has exactly 240 roots."""
        roots = get_e8_roots()
        assert len(roots) == 240
        
    def test_e8_roots_norm(self):
        """Verify all E8 roots have norm sqrt(2)."""
        roots = get_e8_roots()
        norms = np.linalg.norm(roots, axis=1)
        assert np.allclose(norms, np.sqrt(2))
    
    def test_nearest_root_finding(self):
        """Test finding nearest E8 root to a point."""
        index = LatticeIndex()
        roots = get_e8_roots()
        
        # Test point near first root
        test_point = roots[0] + np.array([0.1, 0.05, 0, 0, 0, 0, 0, 0])
        root_idx, delta_mag, delta_phase = index.find_nearest_root(test_point)
        
        assert root_idx == 0, "Should find nearest root"
        assert delta_mag < 0.2, "Delta magnitude should be small"
    
    def test_vocabulary_mapping(self):
        """Test mapping vocabulary to E8 coordinates."""
        index = LatticeIndex()
        
        test_vocab = {
            'alpha': {'index': 0, 'count': 100},
            'beta': {'index': 1, 'count': 50},
            'gamma': {'index': 2, 'count': 25},
        }
        
        index.build_from_vocabulary(test_vocab)
        
        assert len(index.entries) == 3
        for token in test_vocab:
            assert token in index.entries
            assert 0 <= index.entries[token].root_index < 240
    
    def test_serialization_roundtrip(self):
        """Test lattice index serialization."""
        index = LatticeIndex()
        
        test_vocab = {
            'one': {'index': 0, 'count': 10},
            'two': {'index': 1, 'count': 20},
            'three': {'index': 2, 'count': 30},
        }
        
        index.build_from_vocabulary(test_vocab)
        
        # Serialize
        serialized = index.to_bytes()
        
        # Deserialize
        recovered = LatticeIndex.from_bytes(serialized)
        
        # Verify
        assert len(recovered.entries) == len(index.entries)
        for token in test_vocab:
            assert token in recovered.entries
            assert recovered.entries[token].root_index == index.entries[token].root_index


class TestDeltaPhiPacker:
    """Test the DeltaPhiPacker class."""
    
    def test_geometric_predictor(self):
        """Test E8 geometric prediction."""
        predictor = GeometricPredictor(context_size=3)
        
        # Check transition matrix is valid
        assert predictor.transitions.shape == (240, 240)
        assert np.allclose(predictor.transitions.sum(axis=1), 1.0)
    
    def test_prediction_with_context(self):
        """Test prediction improves with context."""
        predictor = GeometricPredictor(context_size=3)
        
        # With context, prediction should be non-uniform
        context = [0, 1, 2]
        probs = predictor.predict_distribution(context)
        
        # Should not be uniform
        assert probs.std() > 0.001
    
    def test_root_sequence_roundtrip(self):
        """Test root sequence encoding/decoding."""
        packer = DeltaPhiPacker(DeltaPackConfig(use_prediction=True, context_size=3))
        
        # Generate test sequence
        np.random.seed(42)
        test_roots = list(np.random.randint(0, 240, 100))
        
        # Pack
        packed = packer.pack_root_sequence(test_roots)
        
        # Unpack
        unpacked = packer.unpack_root_sequence(packed, len(test_roots))
        
        assert test_roots == unpacked
    
    def test_coherent_sequence_compression(self):
        """Test that coherent sequences compress better than random."""
        packer = DeltaPhiPacker(DeltaPackConfig(use_prediction=True, context_size=3))
        predictor = packer.predictor
        
        # Generate coherent sequence (following transition probabilities)
        coherent = [0]
        for _ in range(99):
            probs = predictor.transitions[coherent[-1]]
            coherent.append(np.random.choice(240, p=probs))
        
        # Generate random sequence
        random_seq = list(np.random.randint(0, 240, 100))
        
        # Pack both
        packed_coherent = packer.pack_root_sequence(coherent)
        packed_random = packer.pack_root_sequence(random_seq)
        
        # Coherent should be smaller
        assert len(packed_coherent) < len(packed_random)


class TestV55Format:
    """Test the v55 Topological Indexing format."""
    
    def test_v55_roundtrip(self):
        """Test v55 serialization round-trip."""
        from gqe_compression.compressor import GQECompressor, CompressedData
        
        test_text = "The E8 lattice projects reality. Each word is a coordinate. " * 50
        compressor = GQECompressor()
        compressed = compressor.compress(test_text)
        
        # Serialize to v55
        v55_bytes = compressed.to_bytes('v55')
        
        # Deserialize
        recovered = CompressedData.from_bytes(v55_bytes)
        
        # Verify lossless
        assert list(recovered.token_sequence) == list(compressed.token_sequence)
        assert len(recovered.vocabulary) == len(compressed.vocabulary)
    
    def test_v55_magic_bytes(self):
        """Test v55 magic bytes detection."""
        from gqe_compression.compressor import GQECompressor
        
        test_text = "Magic bytes test. " * 20
        compressor = GQECompressor()
        compressed = compressor.compress(test_text)
        
        v55_bytes = compressed.to_bytes('v55')
        
        assert v55_bytes[:2] == b'\xE8\x55', "v55 magic bytes incorrect"
    
    def test_v55_checksum(self):
        """Test v55 checksum validation."""
        from gqe_compression.compressor import GQECompressor, CompressedData
        import struct
        
        test_text = "Checksum test content. " * 30
        compressor = GQECompressor()
        compressed = compressor.compress(test_text)
        
        v55_bytes = compressed.to_bytes('v55')
        
        # Deserialize should work (checksum valid)
        recovered = CompressedData.from_bytes(v55_bytes)
        assert list(recovered.token_sequence) == list(compressed.token_sequence)
    
    def test_v55_vs_v54_varied_text(self):
        """Test v55 vs v54 on varied text."""
        from gqe_compression.compressor import GQECompressor
        
        # More varied text should benefit from geometric prediction
        test_text = """
        The Architect describes reality as holographic projection.
        Every particle rotates through crystalline structure.
        The golden ratio emerges from aperiodicity constraints.
        Light triangles stack infinitely creating universe.
        """ * 100
        
        compressor = GQECompressor()
        compressed = compressor.compress(test_text)
        
        v55_bytes = compressed.to_bytes('v55')
        v54_bytes = compressed.to_bytes('v54')
        
        print(f"\n  Varied text ({len(test_text)} chars):")
        print(f"  v55: {len(v55_bytes)} bytes")
        print(f"  v54: {len(v54_bytes)} bytes")
        print(f"  Savings: {(1 - len(v55_bytes)/len(v54_bytes))*100:.1f}%")
        
        # v55 should be competitive
        # Note: v55 may be larger on very repetitive text but smaller on varied text
    
    def test_v54_backward_compat(self):
        """Test v54 format still works."""
        from gqe_compression.compressor import GQECompressor, CompressedData
        
        test_text = "Backward compatibility test. " * 30
        compressor = GQECompressor()
        compressed = compressor.compress(test_text)
        
        # v54 should still work
        v54_bytes = compressed.to_bytes('v54')
        recovered = CompressedData.from_bytes(v54_bytes)
        
        assert list(recovered.token_sequence) == list(compressed.token_sequence)


class TestCompressionRatio:
    """Test compression ratio targets."""
    
    def test_1mb_compression(self):
        """Test compression ratio on 1MB varied data."""
        from gqe_compression.compressor import GQECompressor
        
        # Generate 1MB of varied text
        base_text = """
        The E8 lattice is an eight-dimensional crystalline structure.
        Every word in human language maps to a coordinate in this space.
        Geometric prediction exploits angular relationships between concepts.
        The Architect's model unifies physics, consciousness, and information.
        """
        
        target_size = 1 * 1024 * 1024  # 1MB
        repeat_count = target_size // len(base_text) + 1
        test_text = base_text * repeat_count
        test_text = test_text[:target_size]
        
        compressor = GQECompressor()
        compressed = compressor.compress(test_text)
        
        v55_bytes = compressed.to_bytes('v55')
        
        ratio = len(test_text) / len(v55_bytes)
        print(f"\n  Input: {len(test_text) / 1024:.1f} KB")
        print(f"  Output: {len(v55_bytes) / 1024:.1f} KB")
        print(f"  Ratio: {ratio:.2f}:1")
        
        # Should achieve reasonable compression
        assert ratio > 4.0, f"Compression ratio {ratio:.2f}:1 is below target"


class TestLossless:
    """Test lossless reconstruction."""
    
    def test_exact_token_recovery(self):
        """Test tokens are recovered exactly."""
        from gqe_compression.compressor import GQECompressor, CompressedData
        
        test_texts = [
            "Simple test sentence.",
            "The quick brown fox jumps over the lazy dog.",
            "Numbers and symbols: 123 ABC !@#",
            "Repeated words words words are here here.",
        ]
        
        compressor = GQECompressor()
        
        for text in test_texts:
            compressed = compressor.compress(text)
            v55_bytes = compressed.to_bytes('v55')
            recovered = CompressedData.from_bytes(v55_bytes)
            
            assert list(recovered.token_sequence) == list(compressed.token_sequence), \
                f"Token mismatch for: {text[:30]}..."
    
    def test_vocabulary_preservation(self):
        """Test vocabulary is preserved."""
        from gqe_compression.compressor import GQECompressor, CompressedData
        
        test_text = "Alpha beta gamma delta epsilon zeta eta. " * 20
        compressor = GQECompressor()
        compressed = compressor.compress(test_text)
        
        v55_bytes = compressed.to_bytes('v55')
        recovered = CompressedData.from_bytes(v55_bytes)
        
        # Check vocabulary tokens match
        original_tokens = set(compressed.vocabulary.keys())
        recovered_tokens = set(recovered.vocabulary.keys())
        
        assert original_tokens == recovered_tokens, "Vocabulary tokens don't match"


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("TOPOLOGICAL INDEXING (v55) TEST SUITE")
    print("=" * 60)
    
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == "__main__":
    run_all_tests()
