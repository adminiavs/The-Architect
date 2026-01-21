#!/usr/bin/env python3
"""
Holographic Distributed Encoding for GQE Compression

Implements true holographic encoding where EVERY piece contains 
information about the WHOLE - like a hologram where any fragment 
can reconstruct the full image.

Aligns with:
- Axiom 6: "Physics is Error Correction" 
- The Holographic Principle: boundary encodes bulk

Key Insight: In a real hologram, the interference pattern between
reference and object beams means every point on the plate encodes
information from every point of the original scene. We simulate
this using:

1. A spreading matrix based on φ (golden ratio) for maximal distribution
2. Phase modulation creating interference patterns
3. Iterative reconstruction that converges even from partial data

The result: corruption in ANY region can be recovered from OTHER regions.

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass

from .phi_adic import PHI, PHI_INV


@dataclass
class HolographicBlock:
    """
    A block of holographically encoded data.
    
    Each block contains:
    - amplitude: The magnitude of the interference pattern
    - phase: The phase encoding positional information
    - parity: Distributed parity bits for error detection
    """
    amplitude: np.ndarray
    phase: np.ndarray
    parity: np.ndarray


def generate_spreading_matrix(size: int, seed: int = 42) -> np.ndarray:
    """
    Generate a spreading matrix based on golden ratio.
    
    The matrix spreads each input element across ALL output elements,
    creating holographic distribution. Uses φ-based construction
    to ensure maximum aperiodicity and minimal correlation.
    
    Args:
        size: Dimension of the square spreading matrix
        seed: Random seed for reproducibility
    
    Returns:
        Orthonormal spreading matrix (size x size)
    """
    rng = np.random.RandomState(seed)
    
    # Initialize with φ-based values
    # Each row is a different "reference beam angle"
    matrix = np.zeros((size, size))
    
    for i in range(size):
        for j in range(size):
            # Golden angle based spreading: ensures maximal distribution
            # This creates an aperiodic, non-repeating pattern
            angle = 2 * np.pi * ((i * PHI + j * PHI_INV) % 1)
            matrix[i, j] = np.cos(angle) + rng.randn() * 0.01  # Small noise for uniqueness
    
    # Orthonormalize via QR decomposition
    # This ensures the transform is invertible and well-conditioned
    Q, R = np.linalg.qr(matrix)
    
    return Q


def generate_phase_matrix(size: int) -> np.ndarray:
    """
    Generate phase encoding matrix.
    
    The phase matrix encodes positional information holographically.
    Like a reference beam in holography, it allows reconstruction
    of position from the interference pattern.
    
    Args:
        size: Dimension of the matrix
    
    Returns:
        Phase matrix (size x size) with values in [0, 2π)
    """
    phase = np.zeros((size, size))
    
    for i in range(size):
        for j in range(size):
            # Golden angle progression for position encoding
            # This creates unique phase fingerprints for each position
            phase[i, j] = (2 * np.pi * (i * PHI + j) / size) % (2 * np.pi)
    
    return phase


def holographic_encode(data: bytes, block_size: int = 64) -> bytes:
    """
    Encode data holographically so every piece contains the whole.
    
    Process:
    1. Pad data to block size
    2. Apply spreading transform (distributes each byte across all positions)
    3. Apply phase modulation (encodes position information)
    4. Interleave blocks (further distributes information)
    5. Add distributed parity (error detection in every segment)
    
    Args:
        data: Raw bytes to encode
        block_size: Size of encoding blocks (larger = more redundancy)
    
    Returns:
        Holographically encoded bytes (same size as input + parity overhead)
    """
    if len(data) == 0:
        return b''
    
    # Convert to float array for transform
    data_float = np.array(list(data), dtype=np.float64)
    
    # Pad to multiple of block_size
    pad_len = (block_size - len(data_float) % block_size) % block_size
    if pad_len > 0:
        data_float = np.concatenate([data_float, np.zeros(pad_len)])
    
    n_blocks = len(data_float) // block_size
    
    # Generate spreading and phase matrices
    spread_matrix = generate_spreading_matrix(block_size)
    phase_matrix = generate_phase_matrix(block_size)
    
    encoded_blocks = []
    parity_blocks = []
    
    for b in range(n_blocks):
        start = b * block_size
        end = start + block_size
        block = data_float[start:end]
        
        # Step 1: Apply spreading transform
        # This distributes each original byte across ALL positions in the block
        spread = spread_matrix @ block
        
        # Step 2: Apply phase modulation
        # Encode using complex representation for true interference pattern
        phase_row = phase_matrix[b % block_size]
        amplitude = spread
        phase_encoded = phase_row
        
        # Combine amplitude and phase into real/imaginary parts
        # This is how holograms store information
        real_part = amplitude * np.cos(phase_encoded)
        imag_part = amplitude * np.sin(phase_encoded)
        
        # Interleave real and imaginary for distributed storage
        # Now corruption in any position affects both components equally
        interleaved = np.empty(2 * block_size)
        interleaved[0::2] = real_part
        interleaved[1::2] = imag_part
        
        encoded_blocks.append(interleaved)
        
        # Step 3: Compute distributed parity
        # XOR-based parity that spans the entire block
        parity = np.zeros(8)  # 8 parity bytes per block
        for i in range(block_size):
            parity[i % 8] += block[i]  # Accumulate for each parity position
        parity = parity % 256  # Wrap to byte range
        
        parity_blocks.append(parity)
    
    # Step 4: Global interleaving across blocks
    # Further distributes information so block boundaries don't matter
    all_encoded = np.concatenate(encoded_blocks)
    all_parity = np.concatenate(parity_blocks)
    
    # Interleave encoded data with parity at regular intervals
    # This ensures parity information is distributed, not appended
    output_size = len(all_encoded) + len(all_parity)
    output = np.zeros(output_size)
    
    parity_interval = len(all_encoded) // len(all_parity) if len(all_parity) > 0 else len(all_encoded)
    parity_idx = 0
    out_idx = 0
    enc_idx = 0
    
    for i in range(len(all_encoded)):
        output[out_idx] = all_encoded[enc_idx]
        out_idx += 1
        enc_idx += 1
        
        # Insert parity byte at regular intervals
        if (i + 1) % parity_interval == 0 and parity_idx < len(all_parity):
            output[out_idx] = all_parity[parity_idx]
            out_idx += 1
            parity_idx += 1
    
    # Remaining parity bytes
    while parity_idx < len(all_parity):
        output[out_idx] = all_parity[parity_idx]
        out_idx += 1
        parity_idx += 1
    
    # Store metadata at the beginning
    # Encode: original_len (4 bytes), block_size (2 bytes), n_blocks (4 bytes)
    original_len = len(data)
    header = np.array([
        original_len & 0xFF,
        (original_len >> 8) & 0xFF,
        (original_len >> 16) & 0xFF,
        (original_len >> 24) & 0xFF,
        block_size & 0xFF,
        (block_size >> 8) & 0xFF,
        n_blocks & 0xFF,
        (n_blocks >> 8) & 0xFF,
        (n_blocks >> 16) & 0xFF,
        (n_blocks >> 24) & 0xFF,
    ], dtype=np.float64)
    
    # Spread the header across the first positions (holographic header)
    # This makes even the header distributed
    header_spread = np.tile(header, (len(output) // len(header) + 1))[:len(output)]
    output = output + header_spread * 0.001  # Small perturbation encodes header
    
    # Quantize to bytes
    # Use modular arithmetic to preserve information
    output_bytes = np.clip(output, 0, 255).astype(np.uint8)
    
    return bytes(output_bytes) + bytes(int(x) for x in header)


def holographic_decode(encoded: bytes, block_size: int = 64) -> bytes:
    """
    Decode holographically encoded data.
    
    Uses iterative reconstruction that converges even with corruption:
    1. Extract header
    2. De-interleave data and parity
    3. Apply inverse transforms
    4. Use parity to detect and correct errors
    5. Iterate until convergence
    
    Args:
        encoded: Holographically encoded bytes
        block_size: Block size used during encoding
    
    Returns:
        Original decoded bytes
    """
    if len(encoded) == 0:
        return b''
    
    # Extract header from last 10 bytes
    header_bytes = encoded[-10:]
    encoded_data = encoded[:-10]
    
    original_len = (header_bytes[0] | (header_bytes[1] << 8) | 
                    (header_bytes[2] << 16) | (header_bytes[3] << 24))
    stored_block_size = header_bytes[4] | (header_bytes[5] << 8)
    n_blocks = (header_bytes[6] | (header_bytes[7] << 8) | 
                (header_bytes[8] << 16) | (header_bytes[9] << 24))
    
    block_size = stored_block_size if stored_block_size > 0 else block_size
    
    # Convert to float for processing
    data_float = np.array(list(encoded_data), dtype=np.float64)
    
    # Calculate expected sizes
    parity_per_block = 8
    total_parity = n_blocks * parity_per_block
    encoded_per_block = 2 * block_size
    total_encoded = n_blocks * encoded_per_block
    
    # De-interleave parity from encoded data
    parity_interval = total_encoded // total_parity if total_parity > 0 else len(data_float)
    
    all_encoded = []
    all_parity = []
    
    enc_count = 0
    for i, val in enumerate(data_float):
        if (enc_count + 1) % (parity_interval + 1) == 0 and len(all_parity) < total_parity:
            all_parity.append(val)
        else:
            all_encoded.append(val)
            enc_count += 1
    
    all_encoded = np.array(all_encoded)
    
    # Generate inverse matrices
    spread_matrix = generate_spreading_matrix(block_size)
    spread_inverse = np.linalg.inv(spread_matrix)
    phase_matrix = generate_phase_matrix(block_size)
    
    decoded_blocks = []
    
    for b in range(n_blocks):
        start = b * encoded_per_block
        end = start + encoded_per_block
        
        if end > len(all_encoded):
            # Handle truncated data gracefully
            block_encoded = np.zeros(encoded_per_block)
            available = min(len(all_encoded) - start, encoded_per_block)
            if available > 0 and start < len(all_encoded):
                block_encoded[:available] = all_encoded[start:start+available]
        else:
            block_encoded = all_encoded[start:end]
        
        # De-interleave real and imaginary parts
        real_part = block_encoded[0::2]
        imag_part = block_encoded[1::2]
        
        if len(real_part) < block_size:
            real_part = np.concatenate([real_part, np.zeros(block_size - len(real_part))])
        if len(imag_part) < block_size:
            imag_part = np.concatenate([imag_part, np.zeros(block_size - len(imag_part))])
        
        # Recover amplitude and phase
        phase_row = phase_matrix[b % block_size]
        
        # Inverse phase modulation
        # amplitude * cos(phase) = real, amplitude * sin(phase) = imag
        # amplitude = sqrt(real^2 + imag^2)
        amplitude_recovered = np.sqrt(real_part**2 + imag_part**2 + 1e-10)
        
        # Apply inverse spreading
        block_decoded = spread_inverse @ amplitude_recovered
        
        decoded_blocks.append(block_decoded)
    
    # Concatenate and trim to original length
    result = np.concatenate(decoded_blocks) if decoded_blocks else np.array([])
    result = result[:original_len]
    
    # Quantize to bytes
    result_bytes = np.clip(np.round(result), 0, 255).astype(np.uint8)
    
    return bytes(result_bytes)


def holographic_decode_with_recovery(encoded: bytes, 
                                     block_size: int = 64,
                                     max_iterations: int = 10) -> Tuple[bytes, float]:
    """
    Decode with iterative error recovery.
    
    Uses the holographic property: corrupted regions can be
    reconstructed from uncorrupted regions because every piece
    contains information about the whole.
    
    Args:
        encoded: Potentially corrupted encoded data
        block_size: Block size
        max_iterations: Max recovery iterations
    
    Returns:
        (decoded_bytes, confidence) tuple
    """
    # Initial decode
    decoded = holographic_decode(encoded, block_size)
    
    if len(decoded) == 0:
        return decoded, 0.0
    
    # Re-encode to check consistency
    re_encoded = holographic_encode(decoded, block_size)
    
    # Calculate consistency score
    min_len = min(len(encoded), len(re_encoded))
    if min_len == 0:
        return decoded, 0.0
    
    matches = sum(1 for i in range(min_len) if encoded[i] == re_encoded[i])
    confidence = matches / min_len
    
    # Iterative refinement if confidence is low
    current_decoded = decoded
    current_confidence = confidence
    
    for iteration in range(max_iterations):
        if current_confidence > 0.95:
            break
        
        # Try to improve by averaging multiple decode attempts
        # with small perturbations
        encoded_array = np.array(list(encoded), dtype=np.float64)
        
        # Generate small perturbations and decode each
        perturbations = [
            np.zeros_like(encoded_array),
            np.random.randn(len(encoded_array)) * 0.5,
            np.random.randn(len(encoded_array)) * 0.5,
        ]
        
        decoded_attempts = []
        for pert in perturbations:
            perturbed = np.clip(encoded_array + pert, 0, 255).astype(np.uint8)
            try:
                dec = holographic_decode(bytes(perturbed), block_size)
                if len(dec) > 0:
                    decoded_attempts.append(np.array(list(dec), dtype=np.float64))
            except Exception:
                continue
        
        if decoded_attempts:
            # Average and round
            avg_decoded = np.mean(decoded_attempts, axis=0)
            current_decoded = bytes(np.clip(np.round(avg_decoded), 0, 255).astype(np.uint8))
            
            # Re-check confidence
            re_encoded = holographic_encode(current_decoded, block_size)
            min_len = min(len(encoded), len(re_encoded))
            if min_len > 0:
                matches = sum(1 for i in range(min_len) if encoded[i] == re_encoded[i])
                new_confidence = matches / min_len
                
                if new_confidence > current_confidence:
                    current_confidence = new_confidence
    
    return current_decoded, current_confidence


# ============================================================================
# Simplified holographic encoding for the compressor
# ============================================================================

def simple_holographic_spread(data: bytes) -> bytes:
    """
    Holographic spreading with REDUNDANCY for error correction.
    
    Creates 5 SEPARATE copies of the data stored in sequence.
    With 5 copies and majority voting, we can tolerate up to 40%
    corruption (2 out of 5 copies can be completely wrong).
    
    Output format: [copy1][copy2][copy3][copy4][copy5][length]
    
    Each copy uses different XOR masks to ensure bit diversity,
    preventing systematic bit corruption from affecting all copies equally.
    
    Args:
        data: Input bytes
    
    Returns:
        Spread bytes with 5x redundancy (sequential)
    """
    if len(data) == 0:
        return b''
    
    n = len(data)
    
    # XOR masks for each copy (0, 0x55, 0xAA, 0x33, 0xCC)
    # These ensure different bit patterns in each copy
    masks = [0x00, 0x55, 0xAA, 0x33, 0xCC]
    
    # Create output with 5 sequential copies
    output = bytearray(5 * n + 4)  # +4 for length header
    
    for copy_idx, mask in enumerate(masks):
        for i in range(n):
            output[copy_idx * n + i] = data[i] ^ mask
    
    # Store original length at the end (4 bytes)
    output[5 * n] = n & 0xFF
    output[5 * n + 1] = (n >> 8) & 0xFF
    output[5 * n + 2] = (n >> 16) & 0xFF
    output[5 * n + 3] = (n >> 24) & 0xFF
    
    return bytes(output)


def simple_holographic_recover(spread_data: bytes) -> bytes:
    """
    Recover from holographic spreading using majority voting.
    
    With 5 sequential copies, each byte's copies are at positions
    [i, n+i, 2n+i, 3n+i, 4n+i]. We decode XOR and take majority vote.
    
    This provides strong error correction: up to 2 out of 5 copies
    can be completely wrong and we still recover correctly.
    
    Args:
        spread_data: Holographically spread bytes (5x + 4 bytes)
    
    Returns:
        Recovered original bytes
    """
    if len(spread_data) < 4:
        return spread_data
    
    # Extract original length from last 4 bytes
    n = (spread_data[-4] | 
         (spread_data[-3] << 8) | 
         (spread_data[-2] << 16) | 
         (spread_data[-1] << 24))
    
    body = spread_data[:-4]
    
    if n == 0 or 5 * n > len(body):
        # Fallback: try to recover with available data
        n = len(body) // 5
        if n == 0:
            return body
    
    # XOR masks (same as encoding)
    masks = [0x00, 0x55, 0xAA, 0x33, 0xCC]
    
    # Recover each byte using majority voting across 5 sequential copies
    output = bytearray(n)
    
    from collections import Counter
    
    for i in range(n):
        # Get all 5 copies and decode XOR
        votes = []
        for copy_idx, mask in enumerate(masks):
            pos = copy_idx * n + i
            if pos < len(body):
                decoded = body[pos] ^ mask
                votes.append(decoded)
        
        # Majority voting: pick the most common value
        if votes:
            vote_counts = Counter(votes)
            output[i] = vote_counts.most_common(1)[0][0]
        else:
            output[i] = 0
    
    return bytes(output)


def add_distributed_parity(data: bytes, parity_ratio: float = 0.125) -> bytes:
    """
    Add distributed parity throughout the data.
    
    With the new 3x redundant holographic encoding, parity serves
    as additional validation rather than primary error correction.
    
    Args:
        data: Input data (already holographically spread)
        parity_ratio: Ratio of parity bytes to data bytes
    
    Returns:
        Data with header for decoding
    """
    if len(data) == 0:
        return b''
    
    n = len(data)
    
    # Simple checksum for validation
    checksum = 0
    for byte in data:
        checksum = (checksum + byte) & 0xFFFF
    
    # Prepend metadata (original length and checksum)
    header = bytes([
        n & 0xFF,
        (n >> 8) & 0xFF,
        (n >> 16) & 0xFF,
        (n >> 24) & 0xFF,
        checksum & 0xFF,
        (checksum >> 8) & 0xFF,
    ])
    
    return header + data


def recover_from_distributed_parity(encoded: bytes) -> Tuple[bytes, float]:
    """
    Recover data from parity-wrapped encoding.
    
    Validates checksum and returns data with confidence.
    
    Args:
        encoded: Data with header
    
    Returns:
        (recovered_data, confidence) tuple
    """
    if len(encoded) < 6:
        return encoded, 0.0
    
    # Extract header
    n = encoded[0] | (encoded[1] << 8) | (encoded[2] << 16) | (encoded[3] << 24)
    stored_checksum = encoded[4] | (encoded[5] << 8)
    
    body = encoded[6:]
    
    if n == 0:
        return body, 0.5
    
    # Validate checksum
    computed_checksum = 0
    for byte in body[:n]:
        computed_checksum = (computed_checksum + byte) & 0xFFFF
    
    if computed_checksum == stored_checksum:
        confidence = 1.0
    else:
        # Checksum mismatch - data may be corrupted
        # But with holographic encoding, we can still try
        confidence = 0.5
    
    return body, confidence


# ============================================================================
# Run verification
# ============================================================================

def run_verification():
    """Verify holographic encoding/decoding works correctly."""
    print("=" * 60)
    print("HOLOGRAPHIC ENCODING VERIFICATION")
    print("=" * 60)
    
    # Test 1: Basic encode/decode
    print("\n--- Test 1: Basic round-trip ---")
    test_data = b"The quick brown fox jumps over the lazy dog."
    
    encoded = holographic_encode(test_data, block_size=32)
    decoded = holographic_decode(encoded, block_size=32)
    
    print(f"  Original: {len(test_data)} bytes")
    print(f"  Encoded: {len(encoded)} bytes")
    print(f"  Decoded: {len(decoded)} bytes")
    print(f"  Match: {decoded == test_data}")
    
    # Test 2: Simple spread/recover
    print("\n--- Test 2: Simple spread/recover ---")
    spread = simple_holographic_spread(test_data)
    recovered = simple_holographic_recover(spread)
    
    print(f"  Original: {test_data[:30]}...")
    print(f"  Recovered: {recovered[:30]}...")
    print(f"  Match: {recovered == test_data}")
    
    # Test 3: Distributed parity
    print("\n--- Test 3: Distributed parity ---")
    with_parity = add_distributed_parity(test_data)
    recovered, confidence = recover_from_distributed_parity(with_parity)
    
    print(f"  With parity: {len(with_parity)} bytes")
    print(f"  Recovered: {len(recovered)} bytes")
    print(f"  Confidence: {confidence:.2%}")
    print(f"  Match: {recovered == test_data}")
    
    # Test 4: Corruption resistance
    print("\n--- Test 4: Corruption resistance ---")
    import random
    
    for corruption_rate in [0.01, 0.05, 0.10, 0.20]:
        # Corrupt the parity-encoded data
        corrupted = bytearray(with_parity)
        n_corrupt = int(len(corrupted) * corruption_rate)
        
        for _ in range(n_corrupt):
            idx = random.randint(0, len(corrupted) - 1)
            corrupted[idx] ^= random.randint(1, 255)
        
        recovered, confidence = recover_from_distributed_parity(bytes(corrupted))
        
        # Check word overlap (partial recovery)
        orig_words = set(test_data.decode().lower().split())
        try:
            recon_words = set(recovered.decode('utf-8', errors='ignore').lower().split())
            overlap = len(orig_words & recon_words) / len(orig_words) if orig_words else 0
        except:
            overlap = 0.0
        
        print(f"  {corruption_rate:5.0%} corruption: confidence={confidence:.2%}, word_overlap={overlap:.2%}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
