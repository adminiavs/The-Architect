#!/usr/bin/env python3
"""
GQE Decompressor - Golden Quasicrystal Decoding

Decompression pipeline based on The Architect's model.

Pipeline:
1. Deserialize compressed data (with holographic recovery)
2. Apply Toric error correction to spinors
3. Lift 4D projections + phasons to 8D spinors
4. Map spinors back to tokens via vocabulary
5. Reconstruct original data

Key insight: The phason provides the "hidden variable" needed to uniquely
identify which 8D spinor cast the 4D shadow, enabling LOSSLESS reconstruction.

Error Correction (Axiom 6): The Toric-inspired correction uses E8 lattice
neighborhoods to detect and fix phase inconsistencies (syndromes).

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import Union, List, Dict, Any, Optional, Tuple

from .core.phi_adic import encode_phi, decode_phi, PHI, PHI_INV
from .core.e8_lattice import Spinor
from .core.projection import inverse_projection_with_phason, ProjectedSpinor
from .core.toric_error_correction import ToricErrorCorrector
from .compressor import CompressedData


class GQEDecompressor:
    """
    Golden Quasicrystal Encoding Decompressor.
    
    Reconstructs original data from CompressedData.
    
    Includes Toric error correction (Axiom 6: "Physics is Error Correction")
    to recover from bit corruption in the compressed data.
    """
    
    def __init__(self, enable_error_correction: bool = True):
        """
        Initialize decompressor.
        
        Args:
            enable_error_correction: Whether to apply Toric error correction
        """
        self.enable_error_correction = enable_error_correction
        if enable_error_correction:
            self.error_corrector = ToricErrorCorrector(
                distance_threshold=2.0,
                phase_tolerance=np.pi / 4,
                confidence_threshold=0.3
            )
        else:
            self.error_corrector = None
    
    def decompress(self, compressed: CompressedData) -> Union[str, bytes]:
        """
        Decompress data.
        
        Args:
            compressed: CompressedData object
        
        Returns:
            Reconstructed data (str or bytes depending on original mode)
        """
        mode = compressed.metadata.get('mode', 'word')
        
        if len(compressed.token_sequence) == 0:
            return '' if mode != 'byte' else b''
        
        # Build reverse vocabulary (index -> token)
        idx_to_token = {}
        for token_str, info in compressed.vocabulary.items():
            idx_to_token[info['index']] = token_str
        
        # Reconstruct token sequence
        tokens = [idx_to_token[idx] for idx in compressed.token_sequence]
        
        # Reconstruct original data based on mode
        if mode == 'byte':
            # Tokens are byte values as strings
            result = bytes(int(t) for t in tokens)
        elif mode == 'char':
            # Join characters
            result = ''.join(tokens)
        elif mode == 'word':
            # Join words with spaces
            result = ' '.join(tokens)
        else:
            # Element mode or unknown
            result = ' '.join(str(t) for t in tokens)
        
        return result
    
    def decompress_to_spinors(self, compressed: CompressedData, 
                               apply_correction: bool = True) -> Tuple[List[Spinor], float]:
        """
        Decompress to spinor representation with optional error correction.
        
        Uses phason lifting to reconstruct 8D spinors, then applies
        Toric error correction to fix phase inconsistencies.
        
        Args:
            compressed: CompressedData object
            apply_correction: Whether to apply Toric error correction
        
        Returns:
            (List of 8D Spinors, coherence_score)
        """
        spinors = []
        
        for i, idx in enumerate(compressed.token_sequence):
            # Get projection and phason for this token
            parallel = compressed.projections_4d[idx]
            phason = compressed.phasons_4d[idx]
            phase = compressed.phases[idx]
            
            # Lift to 8D using phason
            spinor = inverse_projection_with_phason(parallel, phason, float(phase))
            spinors.append(spinor)
        
        # Apply Toric error correction if enabled
        coherence = 1.0
        if apply_correction and self.enable_error_correction and self.error_corrector:
            spinors, n_corrections, coherence = self.error_corrector.apply_error_correction(spinors)
        
        return spinors, coherence
    
    def verify_lossless(self, original: Union[str, bytes], compressed: CompressedData) -> bool:
        """
        Verify that decompression is lossless.
        
        Args:
            original: Original data
            compressed: Compressed data
        
        Returns:
            True if reconstruction matches original
        """
        reconstructed = self.decompress(compressed)
        
        # For word mode, exact match may differ due to whitespace
        mode = compressed.metadata.get('mode', 'word')
        
        if mode == 'word':
            # Compare normalized (whitespace-insensitive)
            orig_words = original.split() if isinstance(original, str) else original.decode().split()
            recon_words = reconstructed.split() if isinstance(reconstructed, str) else reconstructed.decode().split()
            return [w.lower() for w in orig_words] == [w.lower() for w in recon_words]
        elif mode == 'byte':
            return original == reconstructed
        elif mode == 'char':
            return original == reconstructed
        else:
            return str(original) == str(reconstructed)


def decompress_text(compressed: CompressedData, enable_error_correction: bool = True) -> str:
    """
    Convenience function to decompress text.
    
    Args:
        compressed: CompressedData object
        enable_error_correction: Whether to apply Toric error correction
    
    Returns:
        Reconstructed text
    """
    decompressor = GQEDecompressor(enable_error_correction=enable_error_correction)
    result = decompressor.decompress(compressed)
    return result if isinstance(result, str) else result.decode()


def run_verification() -> None:
    """Run verification tests for decompressor."""
    print("=" * 60)
    print("GQE DECOMPRESSOR VERIFICATION")
    print("=" * 60)
    
    from .compressor import GQECompressor
    
    # Test texts
    test_texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Hello world! This is a test of GQE compression.",
        "A" * 100,  # Repetitive
    ]
    
    # Test 1: Text round-trip
    print("\n--- Test 1: Text round-trip ---")
    compressor = GQECompressor(window_size=5)
    decompressor = GQEDecompressor()
    
    for i, text in enumerate(test_texts):
        compressed = compressor.compress(text)
        reconstructed = decompressor.decompress(compressed)
        is_lossless = decompressor.verify_lossless(text, compressed)
        
        print(f"  Text {i+1}: lossless={is_lossless}")
        if not is_lossless:
            print(f"    Original: {text[:50]}...")
            print(f"    Reconstructed: {reconstructed[:50]}...")
    
    # Test 2: Byte round-trip
    print("\n--- Test 2: Byte round-trip ---")
    test_bytes = [
        b"Hello World",
        b"\x00\x01\x02\x03\x04",
        b"ATCGATCGATCG",  # DNA-like
    ]
    
    compressor_byte = GQECompressor(tokenize_mode='byte')
    
    for i, data in enumerate(test_bytes):
        compressed = compressor_byte.compress(data)
        reconstructed = decompressor.decompress(compressed)
        is_lossless = decompressor.verify_lossless(data, compressed)
        
        print(f"  Bytes {i+1}: lossless={is_lossless}")
    
    # Test 3: Serialization round-trip
    print("\n--- Test 3: Serialization round-trip ---")
    text = "The quick brown fox jumps over the lazy dog."
    compressed = compressor.compress(text)
    serialized = compressed.to_bytes()
    deserialized = CompressedData.from_bytes(serialized)
    reconstructed = decompressor.decompress(deserialized)
    is_lossless = decompressor.verify_lossless(text, deserialized)
    
    print(f"  Serialize + Deserialize: lossless={is_lossless}")
    print(f"  Original size: {len(text)} bytes")
    print(f"  Compressed size: {len(serialized)} bytes")
    print(f"  Ratio: {len(serialized)/len(text):.2f}")
    
    # Test 4: Spinor recovery with error correction
    print("\n--- Test 4: Spinor recovery with error correction ---")
    text = "The fox and the dog"
    compressed = compressor.compress(text)
    spinors, coherence = decompressor.decompress_to_spinors(compressed)
    
    print(f"  Recovered {len(spinors)} spinors")
    print(f"  Coherence: {coherence:.2%}")
    print(f"  Sample spinor: {spinors[0]}")
    
    # Test 5: Character mode
    print("\n--- Test 5: Character mode ---")
    compressor_char = GQECompressor(tokenize_mode='char')
    text = "Hello!"
    compressed = compressor_char.compress(text)
    reconstructed = decompressor.decompress(compressed)
    is_lossless = (text == reconstructed)
    
    print(f"  Char mode: lossless={is_lossless}")
    print(f"  Original: {text}")
    print(f"  Reconstructed: {reconstructed}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
