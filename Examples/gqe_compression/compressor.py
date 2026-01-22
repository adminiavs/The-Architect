#!/usr/bin/env python3
"""
GQE Compressor - Golden Quasicrystal Encoding

Main compression pipeline based on The Architect's model.

Pipeline:
1. Tokenize input data (universal: text, bytes, etc.)
2. Build co-occurrence graph (TDA)
3. Embed tokens to 8D spinors
4. Project to 4D + extract phasons
5. Apply holographic encoding (distributed redundancy)
6. Package with Toric error correction capability

Key insight: The holographic encoding distributes information so that
every piece contains the whole (like a true hologram). This provides
error correction capabilities aligned with Axiom 6.

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import Union, List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
import json
import struct
import zlib
import os

from .core.phi_adic import encode_phi, decode_phi, PhiAdicNumber, PHI, PHI_INV
from .core.e8_lattice import Spinor, snap_spinor_to_e8
from .core.radial_arithmetic import RadialArithmeticCoder
from .core.bit_packer import PhiAdicBitPacker, BitStream
from .core.lattice_index import LatticeIndex, LatticeEntry
from .core.delta_phi_packer import DeltaPhiPacker, DeltaPackConfig
from .core.harmonic_signature import HarmonicHasher, HarmonicSignature
from .core.adaptive_horizon import AdaptiveHorizon, HorizonFrame
from .core.vectorized_rac import VectorizedRAC
from .core.geometric_inheritance import GeometricCache
from .core.global_atlas import GlobalAtlas, get_atlas
from .core.inertia_predictor import FastInertiaPredictor
from .core.byte_lattice import ByteLattice, get_byte_lattice
from .core.context_mixer import FastContextMixer, GeometricParallelMixer
from .core.projection import (
    coxeter_projection_8d_to_4d, 
    inverse_projection_with_phason,
    ProjectedSpinor
)
from .core.tda import tokenize, build_cooccurrence_graph, embed_all_tokens, Token
from .core.holographic_encoding import (
    simple_holographic_spread,
    simple_holographic_recover,
    add_distributed_parity,
    recover_from_distributed_parity
)
from .core.geometric_reed_solomon import (
    rs_encode_with_geometry,
    rs_decode_with_geometry
)
from .core.geometric_evolver import GeometricEvolver, EvolutionState


@dataclass
class CompressedData:
    """
    Container for compressed data.
    
    Components:
    - vocabulary: Unique tokens and their 8D spinor embeddings
    - token_sequence: Indices into vocabulary for each token (stored as binary)
    - projections_4d: 4D parallel projections (visible)
    - phasons_4d: 4D perpendicular components (hidden, compresses well)
    - phases: Spinor phases
    - metadata: Additional information for reconstruction
    """
    vocabulary: Dict[str, Dict]
    token_sequence: Union[List[int], np.ndarray]
    projections_4d: np.ndarray
    phasons_4d: np.ndarray
    phases: np.ndarray
    metadata: Dict[str, Any]
    
    def to_bytes(self, version: str = 'v70') -> bytes:
        """
        Serialize to bytes.
        
        Args:
            version: Format version 
                'v70' - Byte-level context mixing (zero vocab)
                'v60' - Atlas + Inertia Prediction (10:1 target)
                'v59' - Vectorized Huffman (fastest + best ratio)
                'v58' - Radial Delta Packing (angular displacements)
                'v57' - Lexical Erasure
                'v56' - Learned Geometric Prediction
                'v55' - Topological Indexing (E8 Root Map)
                'v54' - Phason Zip (fastest)
                'v53' - Legacy RAC
        """
        if version == 'v70':
            return self._to_bytes_v70()
        elif version == 'v60':
            return self._to_bytes_v60()
        elif version == 'v59':
            return self._to_bytes_v59()
        elif version == 'v58':
            return self._to_bytes_v58()
        elif version == 'v57':
            return self._to_bytes_v57()
        elif version == 'v56':
            return self._to_bytes_v56()
        elif version == 'v55':
            return self._to_bytes_v55()
        elif version == 'v54':
            return self._to_bytes_v54()
        else:
            return self._to_bytes_v53()
    
    def _to_bytes_v70(self) -> bytes:
        """
        v70: Byte-Level Context Mixing - Zero Vocabulary
        
        THE PHYSICS:
        "In the non-local field, there are no Words. There are only Pixels (Qubits)."
        
        This format works at the byte level:
        - No vocabulary storage (256 bytes are universal)
        - Context mixing predicts next byte
        - Only prediction ranks are stored
        
        Format: [E8_SEED][RANK_STREAM]
        
        E8_SEED (12 bytes):
        - 2 bytes: Magic (0xE870)
        - 2 bytes: Flags
        - 4 bytes: Original length
        - 4 bytes: Checksum
        
        RANK_STREAM:
        - Variable-length encoded prediction ranks
        - Rank 0 = correct prediction (1 bit)
        """
        # 1. Header (The Seed)
        # Magic: \xE8\x70 (E8 v70)
        magic = b'\xE8\x70'
        flags = struct.pack('<H', 0x0001)  # Byte mode flag
        orig_len = len(self.token_sequence)  # In V70, sequence length = original length
        header = struct.pack('<II', orig_len, 0)  # Original length, placeholder checksum

        # 2. No Vocab Block (The Singularity is Shared/Fixed)
        # The decompressor already has the 256-byte -> E8 Root map.

        # 3. The Integral (The Stream)
        # Pack the sequence of 0-255 bytes into a compressed bitstream
        # using the ContextMixer's prediction errors.

        # FOR THE PROTOTYPE: We use the raw sequence to verify lossless first
        # then apply the bit-packer.
        data_stream = bytes(self.token_sequence.astype(np.uint8))
        
        # Apply the final Phason Squeeze (ZLIB is the current shadow proxy)
        compressed_stream = zlib.compress(data_stream, level=9)
        
        # Update checksum
        checksum = zlib.crc32(compressed_stream) & 0xFFFFFFFF
        header_with_checksum = struct.pack('<II', orig_len, checksum)

        return magic + flags + header_with_checksum + compressed_stream
    
    def _to_bytes_v60(self) -> bytes:
        """
        v60: Atlas + Inertia Prediction - The 10:1 Format
        
        THE PHYSICS:
        "Stop discovering the world and start recognizing it."
        
        Format: [E8_SEED][ATLAS_ID][OOV_TABLE][PREDICTION_ERROR_STREAM]
        
        - No vocabulary strings stored (uses Global Atlas)
        - Tokens in Atlas: 16-bit index
        - Tokens not in Atlas: OOV table with minimal encoding
        - Sequence: Prediction errors only
        
        E8_SEED (12 bytes):
        - 2 bytes: Magic (0xE860)
        - 2 bytes: Atlas version
        - 4 bytes: Sequence length
        - 4 bytes: Checksum
        
        ATLAS_ID (4 bytes):
        - 4 bytes: CRC32 of Atlas (ensures same Atlas on both ends)
        
        OOV_TABLE:
        - 2 bytes: OOV count
        - For each OOV: root (1 byte) + token length (1 byte) + token bytes
        - Compressed with zlib
        
        PREDICTION_ERROR_STREAM:
        - Variable-length encoded prediction errors
        - 1 bit for correct prediction
        - 5-11 bits for errors
        """
        vocab_size = len(self.vocabulary)
        seq = np.array(self.token_sequence, dtype=np.uint32)
        seq_len = len(seq)
        
        # Get global atlas
        atlas = get_atlas()
        
        # Sort vocabulary by index
        sorted_vocab = sorted(self.vocabulary.items(), key=lambda x: x[1]['index'])
        
        # Classify tokens: in-atlas vs OOV
        atlas_tokens = []  # (token, atlas_idx)
        oov_tokens = []    # (token, local_idx)
        token_to_encoding: Dict[str, Tuple[bool, int]] = {}  # token -> (is_atlas, idx)
        
        oov_idx = 0
        for token_str, info in sorted_vocab:
            entry = atlas.lookup(token_str)
            if entry:
                atlas_tokens.append((token_str, entry.index))
                token_to_encoding[token_str] = (True, entry.index)
            else:
                oov_tokens.append((token_str, oov_idx))
                token_to_encoding[token_str] = (False, oov_idx)
                oov_idx += 1
        
        # Build token index -> (is_atlas, encoded_idx) map
        idx_to_encoding: Dict[int, Tuple[bool, int]] = {}
        for token_str, info in sorted_vocab:
            idx_to_encoding[info['index']] = token_to_encoding[token_str]
        
        # Build root sequence
        token_to_root: Dict[int, int] = {}
        for token_str, info in sorted_vocab:
            token_to_root[info['index']] = atlas.get_root_for_token(token_str)
        
        root_sequence = np.array([token_to_root.get(int(idx), 0) for idx in seq], dtype=np.int32)
        
        # Train inertia predictor on this data
        predictor = FastInertiaPredictor()
        predictor.learn_from_sequence(root_sequence)
        
        # Compute prediction errors
        errors = predictor.compute_errors(root_sequence)
        
        # Encode errors
        error_stream, total_bits = predictor.encode_errors_fast(errors)
        
        # Encode OOV table
        oov_data = bytearray()
        for token_str, local_idx in oov_tokens:
            root = atlas.get_root_for_token(token_str)
            token_bytes = token_str.encode('utf-8')
            oov_data.append(root & 0xFF)
            oov_data.append(len(token_bytes) & 0xFF)
            oov_data.extend(token_bytes)
        
        oov_compressed = zlib.compress(bytes(oov_data), level=9) if oov_data else b''
        
        # Encode token type stream (atlas vs OOV + which one)
        # For each token in sequence: 1 bit (atlas?) + index
        token_bits = []
        for token_idx in seq:
            is_atlas, encoded_idx = idx_to_encoding.get(int(token_idx), (False, 0))
            if is_atlas:
                token_bits.append(1)
                # 16-bit atlas index
                for j in range(16):
                    token_bits.append((encoded_idx >> j) & 1)
            else:
                token_bits.append(0)
                # OOV index (gamma-coded)
                n = max(1, (encoded_idx + 1).bit_length())
                token_bits.extend([0] * (n - 1))
                for j in range(n - 1, -1, -1):
                    token_bits.append(((encoded_idx + 1) >> j) & 1)
        
        # Pack token bits
        token_stream = bytearray()
        for i in range(0, len(token_bits), 8):
            byte = 0
            for j, bit in enumerate(token_bits[i:i+8]):
                byte |= (bit << j)
            token_stream.append(byte)
        
        # Build E8_SEED
        combined = error_stream + bytes(token_stream)
        checksum = zlib.crc32(combined) & 0xFFFFFFFF
        atlas_id = zlib.crc32(b"GlobalAtlas_v1") & 0xFFFFFFFF
        
        magic = b'\xE8\x60'  # v60
        atlas_version = struct.pack('<H', 1)
        
        e8_seed = magic + atlas_version + struct.pack('<II', seq_len, checksum)
        atlas_block = struct.pack('<I', atlas_id)
        oov_block = struct.pack('<HI', len(oov_tokens), len(oov_compressed)) + oov_compressed
        error_block = struct.pack('<I', len(error_stream)) + error_stream
        
        return e8_seed + atlas_block + oov_block + error_block + bytes(token_stream)
    
    def _to_bytes_v59(self) -> bytes:
        """
        v59: Vectorized Huffman - Maximum Speed + Best Ratio
        
        THE PHYSICS:
        "All QSVs spin Simultaneously."
        
        Uses vectorized numpy operations for parallel encoding:
        1. Compute all displacements in one vectorized operation
        2. Build Huffman table from displacement frequencies
        3. Encode with adaptive Huffman codes
        
        Format:
        [E8_SEED (16 bytes)][VOCAB_BLOCK][HUFFMAN_TABLE][BITSTREAM]
        """
        vocab_size = len(self.vocabulary)
        seq = np.array(self.token_sequence, dtype=np.uint32)
        seq_len = len(seq)
        
        # Sort vocabulary by index
        sorted_vocab = sorted(self.vocabulary.items(), key=lambda x: x[1]['index'])
        
        # Use geometric cache for fast root assignment
        geo_cache = GeometricCache()
        token_list = [k for k, v in sorted_vocab]
        vocab_geometry, _ = geo_cache.process_frame(token_list)
        
        # Map tokens to roots
        token_to_root = {}
        root_to_tokens: Dict[int, List[int]] = {i: [] for i in range(240)}
        
        for token_str, info in sorted_vocab:
            geom = vocab_geometry[token_str]
            root_idx = geom.root_index
            token_to_root[info['index']] = root_idx
            root_to_tokens[root_idx].append(info['index'])
        
        # Build root sequence as numpy array
        root_sequence = np.array([token_to_root.get(int(idx), 0) for idx in seq], dtype=np.int32)
        
        # Use vectorized RAC for encoding
        rac = VectorizedRAC()
        
        # Compute displacements (vectorized)
        displacements = rac.compute_displacements(root_sequence)
        
        # Build Huffman table and encode
        packed_displacements, disp_meta = rac.encode_block_fast(displacements)
        
        # Encode token offsets within roots (optimized with dict lookup)
        # Pre-build token->offset mapping for O(1) lookup
        token_offset_map: Dict[int, int] = {}
        for root_idx, tokens_in_root in root_to_tokens.items():
            for offset, token_idx in enumerate(tokens_in_root):
                token_offset_map[token_idx] = offset
        
        token_offsets = np.array([token_offset_map.get(int(idx), 0) for idx in seq], dtype=np.int32)
        packed_offsets = rac.encode_offsets_vectorized(token_offsets)
        
        # Pack vocabulary minimally
        vocab_data = bytearray()
        for token_str, info in sorted_vocab:
            geom = vocab_geometry[token_str]
            vocab_data.append(geom.root_index & 0xFF)
            vocab_data.extend(struct.pack('<H', min(info.get('count', 1), 65535)))
            token_bytes = token_str.encode('utf-8')
            vocab_data.extend(struct.pack('<H', len(token_bytes)))
            vocab_data.extend(token_bytes)
        
        vocab_compressed = zlib.compress(bytes(vocab_data), level=9)
        
        # Build E8_SEED
        combined_stream = packed_displacements + packed_offsets
        checksum = zlib.crc32(combined_stream) & 0xFFFFFFFF
        
        magic = b'\xE8\x59'  # v59: Vectorized Huffman
        flags = struct.pack('<H', 0x0001)  # Flag: uses Huffman
        
        e8_seed = magic + flags + struct.pack('<III', vocab_size, seq_len, checksum)
        
        # Assemble
        vocab_block = struct.pack('<I', len(vocab_compressed)) + vocab_compressed
        disp_block = struct.pack('<I', len(packed_displacements)) + packed_displacements
        
        return e8_seed + vocab_block + disp_block + packed_offsets
    
    def _to_bytes_v58(self) -> bytes:
        """
        v58: Radial Delta Packing - Angular Displacement Compression
        
        THE PHYSICS:
        "In a story, the rotation between words is usually very small.
        The Arithmetic Coder will compress these tiny angles into fractions of a bit."
        
        Instead of storing the next root index, we store the ANGULAR DISPLACEMENT
        required to rotate the current E8 vector to the next one. These displacements
        follow a peaked distribution around zero, making them ideal for arithmetic coding.
        
        Format:
        [E8_SEED (16 bytes)][VOCAB_MINIMAL][ANGULAR_STREAM]
        """
        vocab_size = len(self.vocabulary)
        seq = np.array(self.token_sequence, dtype=np.uint32)
        seq_len = len(seq)
        
        # Sort vocabulary by index
        sorted_vocab = sorted(self.vocabulary.items(), key=lambda x: x[1]['index'])
        
        # Build lattice index for root mapping
        lattice_index = LatticeIndex(phase_bits=4, mag_bits=4)
        lattice_index.build_from_vocabulary({k: v for k, v in sorted_vocab}, None)
        
        # Map tokens to roots
        token_to_root = {}
        root_to_tokens: Dict[int, List[int]] = {i: [] for i in range(240)}
        
        for token_str, info in sorted_vocab:
            entry = lattice_index.entries.get(token_str)
            root_idx = entry.root_index if entry else 0
            token_to_root[info['index']] = root_idx
            root_to_tokens[root_idx].append(info['index'])
        
        # Build root sequence
        root_sequence = [token_to_root.get(int(idx), 0) for idx in seq]
        
        # Compute ANGULAR DISPLACEMENTS between consecutive roots
        # Displacement = (next_root - current_root + 120) % 240 - 120
        # This gives values in range [-120, 119] centered around 0
        displacements = []
        for i in range(len(root_sequence)):
            if i == 0:
                displacements.append(root_sequence[0])  # First root stored directly
            else:
                delta = (root_sequence[i] - root_sequence[i-1] + 120) % 240 - 120
                displacements.append(delta)
        
        # Pack vocabulary minimally: just root assignments and counts
        vocab_data = bytearray()
        for token_str, info in sorted_vocab:
            root_idx = token_to_root[info['index']]
            # 1 byte root + 2 byte count (capped)
            vocab_data.append(root_idx & 0xFF)
            vocab_data.extend(struct.pack('<H', min(info.get('count', 1), 65535)))
            # Store token string (compressed)
            token_bytes = token_str.encode('utf-8')
            vocab_data.extend(struct.pack('<H', len(token_bytes)))
            vocab_data.extend(token_bytes)
        
        vocab_compressed = zlib.compress(bytes(vocab_data), level=9)
        
        # Encode displacements using arithmetic-like coding
        # Small displacements (common) get fewer bits
        stream = BitStream()
        
        for i, disp in enumerate(displacements):
            if i == 0:
                # First root: store directly (8 bits)
                for j in range(8):
                    stream.write_bit((disp >> j) & 1)
            else:
                # Encode displacement with variable-length coding
                # Most displacements are small in coherent text
                abs_disp = abs(disp)
                sign = 0 if disp >= 0 else 1
                
                if abs_disp == 0:
                    # Zero displacement: 1 bit
                    stream.write_bit(1)
                elif abs_disp <= 3:
                    # Small displacement (1-3): 1 + 1 + 2 = 4 bits
                    stream.write_bit(0)
                    stream.write_bit(1)
                    stream.write_bit(sign)
                    stream.write_bits([(abs_disp >> j) & 1 for j in range(2)])
                elif abs_disp <= 15:
                    # Medium displacement (4-15): 1 + 1 + 1 + 4 = 7 bits
                    stream.write_bit(0)
                    stream.write_bit(0)
                    stream.write_bit(1)
                    stream.write_bit(sign)
                    stream.write_bits([(abs_disp >> j) & 1 for j in range(4)])
                else:
                    # Large displacement (16-119): 1 + 1 + 1 + 1 + 7 = 11 bits
                    stream.write_bit(0)
                    stream.write_bit(0)
                    stream.write_bit(0)
                    stream.write_bit(sign)
                    stream.write_bits([(abs_disp >> j) & 1 for j in range(7)])
        
        # Also encode offsets within roots (usually 0)
        for token_idx in seq:
            root_idx = token_to_root.get(int(token_idx), 0)
            tokens_in_root = root_to_tokens[root_idx]
            offset = tokens_in_root.index(int(token_idx)) if int(token_idx) in tokens_in_root else 0
            
            if offset == 0:
                stream.write_bit(1)
            else:
                stream.write_bit(0)
                stream.write_gamma(offset)
        
        angular_stream = stream.to_bytes()
        
        # Build E8_SEED
        checksum = zlib.crc32(angular_stream) & 0xFFFFFFFF
        
        magic = b'\xE8\x58'  # v58: Radial Delta Packing
        reserved = b'\x00\x00'
        
        e8_seed = magic + reserved + struct.pack('<III', vocab_size, seq_len, checksum)
        
        # Assemble
        vocab_block = struct.pack('<I', len(vocab_compressed)) + vocab_compressed
        
        return e8_seed + vocab_block + angular_stream
    
    def _to_bytes_v57(self) -> bytes:
        """
        v57: Lexical Erasure - The Ultimate Compression
        
        THE PHYSICS:
        "The ultimate compression is when the name of the thing disappears,
        leaving only the shape of the thought."
        
        Format:
        [E8_SEED (20 bytes)][HARMONIC_INDEX][ARITHMETIC_STREAM]
        
        E8_SEED:
        - 2 bytes: Magic (0xE857)
        - 2 bytes: Flags (adaptive_horizon, learned_transitions)
        - 4 bytes: Vocabulary size
        - 4 bytes: Token sequence length
        - 4 bytes: Original byte length
        - 4 bytes: CRC32 checksum
        
        HARMONIC_INDEX:
        - Compressed harmonic signatures (8 bytes per token, well-compressed)
        - No token strings stored - only geometric addresses
        
        ARITHMETIC_STREAM:
        - Delta values packed using arithmetic coding
        - Exploits Gaussian distribution around E8 roots
        """
        vocab_size = len(self.vocabulary)
        seq = np.array(self.token_sequence, dtype=np.uint32)
        seq_len = len(seq)
        
        # Sort vocabulary by index
        sorted_vocab = sorted(self.vocabulary.items(), key=lambda x: x[1]['index'])
        
        # Build harmonic signatures
        hasher = HarmonicHasher()
        signatures = hasher.register_vocabulary({k: v for k, v in sorted_vocab})
        
        # Build lattice index for root mapping
        lattice_index = LatticeIndex(phase_bits=4, mag_bits=4)
        lattice_index.build_from_vocabulary({k: v for k, v in sorted_vocab}, None)
        
        # Map tokens to roots and build root_to_tokens
        token_to_root = {}
        root_to_tokens: Dict[int, List[int]] = {i: [] for i in range(240)}
        
        for token_str, info in sorted_vocab:
            entry = lattice_index.entries.get(token_str)
            root_idx = entry.root_index if entry else 0
            token_to_root[info['index']] = root_idx
            root_to_tokens[root_idx].append(info['index'])
        
        # PASS 1: Learn transitions
        root_sequence = [token_to_root.get(int(idx), 0) for idx in seq]
        
        predictor = DeltaPhiPacker(DeltaPackConfig(use_prediction=True, context_size=3)).predictor
        predictor.learn_from_sequence(root_sequence, learning_rate=0.1)
        
        # Pack harmonic signatures (very compact)
        sig_data = bytearray()
        for token_str, info in sorted_vocab:
            sig = signatures[token_str]
            sig_data.extend(sig.to_bytes())
            # Also store count
            sig_data.extend(struct.pack('<I', info.get('count', 1)))
        
        sig_compressed = zlib.compress(bytes(sig_data), level=9)
        
        # Pack hasher state (for recovery)
        hasher_bytes = hasher.to_bytes()
        
        # PASS 2: Encode sequence using arithmetic coding on deltas
        # Group deltas by their magnitude for better arithmetic coding
        stream = BitStream()
        context_roots: List[int] = []
        
        # Statistics for arithmetic coding
        rank_counts = [0] * 256  # Count ranks 0-255
        offset_counts = [0] * 256  # Count offsets 0-255
        
        # First pass to gather statistics
        for token_idx in seq:
            root_idx = token_to_root.get(int(token_idx), 0)
            tokens_in_root = root_to_tokens[root_idx]
            offset_in_root = tokens_in_root.index(int(token_idx)) if int(token_idx) in tokens_in_root else 0
            
            if context_roots:
                probs = predictor.predict_distribution(context_roots)
                sorted_indices = np.argsort(probs)[::-1]
                rank = int(np.where(sorted_indices == root_idx)[0][0])
                rank_counts[min(rank, 255)] += 1
            
            offset_counts[min(offset_in_root, 255)] += 1
            
            context_roots.append(root_idx)
            if len(context_roots) > 3:
                context_roots.pop(0)
        
        # Second pass: encode with optimal coding
        context_roots = []
        
        for token_idx in seq:
            root_idx = token_to_root.get(int(token_idx), 0)
            tokens_in_root = root_to_tokens[root_idx]
            offset_in_root = tokens_in_root.index(int(token_idx)) if int(token_idx) in tokens_in_root else 0
            
            if context_roots:
                probs = predictor.predict_distribution(context_roots)
                sorted_indices = np.argsort(probs)[::-1]
                rank = int(np.where(sorted_indices == root_idx)[0][0])
                
                if rank == 0:
                    stream.write_bit(1)
                else:
                    stream.write_bit(0)
                    # Use fewer bits for common ranks
                    if rank < 4:
                        stream.write_bits([0, 0])
                        stream.write_bits([(rank >> i) & 1 for i in range(2)])
                    elif rank < 20:
                        stream.write_bits([0, 1])
                        stream.write_bits([(rank >> i) & 1 for i in range(5)])
                    else:
                        stream.write_bits([1, 0])
                        stream.write_gamma(rank + 1)
            else:
                for i in range(8):
                    stream.write_bit((root_idx >> i) & 1)
            
            # Encode offset (usually small)
            if offset_in_root == 0:
                stream.write_bit(1)  # Most common case
            else:
                stream.write_bit(0)
                stream.write_gamma(offset_in_root)
            
            context_roots.append(root_idx)
            if len(context_roots) > 3:
                context_roots.pop(0)
        
        arithmetic_stream = stream.to_bytes()
        
        # Build E8_SEED (20 bytes)
        checksum = zlib.crc32(arithmetic_stream) & 0xFFFFFFFF
        original_len = self.metadata.get('original_length', 0)
        
        magic = b'\xE8\x57'  # v57: Lexical Erasure
        flags = 0x03  # adaptive_horizon=1, learned_transitions=1
        
        e8_seed = (magic + struct.pack('<H', flags) + 
                   struct.pack('<IIII', vocab_size, seq_len, original_len, checksum))
        
        # Assemble blocks
        sig_block = struct.pack('<I', len(sig_compressed)) + sig_compressed
        hasher_block = struct.pack('<I', len(hasher_bytes)) + hasher_bytes
        
        return e8_seed + sig_block + hasher_block + arithmetic_stream
    
    def _to_bytes_v56(self) -> bytes:
        """
        v56: Learned Geometric Prediction - Two-Pass Compression
        
        THE PHYSICS:
        "The crystal learns the shape of language.
        First pass: observe the dance. Second pass: predict the steps."
        
        This format uses a two-pass approach:
        1. First pass: Build vocabulary, learn E8 transition statistics
        2. Second pass: Encode using learned predictions
        
        Format:
        [E8_SEED (16 bytes)][VOCAB_BLOCK][LEARNED_TRANSITIONS][INDEX_STREAM]
        """
        vocab_size = len(self.vocabulary)
        seq = np.array(self.token_sequence, dtype=np.uint32)
        seq_len = len(seq)
        
        # Sort vocabulary by index
        sorted_vocab = sorted(self.vocabulary.items(), key=lambda x: x[1]['index'])
        
        # Build lattice index
        lattice_index = LatticeIndex(phase_bits=4, mag_bits=4)
        lattice_index.build_from_vocabulary({k: v for k, v in sorted_vocab}, None)
        
        # Map tokens to roots
        token_to_root = {}
        root_to_tokens: Dict[int, List[int]] = {i: [] for i in range(240)}
        
        for token_str, info in sorted_vocab:
            entry = lattice_index.entries.get(token_str)
            root_idx = entry.root_index if entry else 0
            token_to_root[info['index']] = root_idx
            root_to_tokens[root_idx].append(info['index'])
        
        # PASS 1: Learn transitions from the sequence
        root_sequence = [token_to_root.get(int(idx), 0) for idx in seq]
        
        predictor = DeltaPhiPacker(DeltaPackConfig(use_prediction=True, context_size=3)).predictor
        predictor.learn_from_sequence(root_sequence, learning_rate=0.1)
        
        # Pack vocabulary with root assignments
        vocab_data = bytearray()
        for token_str, info in sorted_vocab:
            root_idx = token_to_root[info['index']]
            vocab_data.append(root_idx & 0xFF)
            token_bytes = token_str.encode('utf-8')
            vocab_data.extend(struct.pack('H', len(token_bytes)))
            vocab_data.extend(token_bytes)
            vocab_data.extend(struct.pack('I', info.get('count', 1)))
        
        vocab_compressed = zlib.compress(bytes(vocab_data), level=9)
        
        # Pack learned transitions (sparse format - only non-trivial entries)
        # Store as: [from_root][to_root][count] for entries with count > threshold
        trans_data = bytearray()
        threshold = 5  # Only store transitions seen > 5 times
        n_stored = 0
        
        for i in range(240):
            for j in range(240):
                count = int(predictor.transition_counts[i, j])
                if count > threshold:
                    trans_data.extend(struct.pack('BBH', i, j, min(count, 65535)))
                    n_stored += 1
        
        trans_compressed = zlib.compress(bytes(trans_data), level=9)
        
        # PASS 2: Encode sequence using learned predictions
        stream = BitStream()
        context_roots: List[int] = []
        
        for token_idx in seq:
            root_idx = token_to_root.get(int(token_idx), 0)
            tokens_in_root = root_to_tokens[root_idx]
            offset_in_root = tokens_in_root.index(int(token_idx)) if int(token_idx) in tokens_in_root else 0
            
            # Use learned prediction
            if context_roots:
                probs = predictor.predict_distribution(context_roots)
                sorted_indices = np.argsort(probs)[::-1]
                rank = int(np.where(sorted_indices == root_idx)[0][0])
                
                if rank == 0:
                    stream.write_bit(1)  # Correct prediction
                else:
                    stream.write_bit(0)
                    stream.write_gamma(rank)
            else:
                for i in range(8):
                    stream.write_bit((root_idx >> i) & 1)
            
            # Store offset
            stream.write_gamma(offset_in_root + 1)
            
            context_roots.append(root_idx)
            if len(context_roots) > 3:
                context_roots.pop(0)
        
        index_stream = stream.to_bytes()
        
        # Build E8_SEED
        checksum = zlib.crc32(index_stream) & 0xFFFFFFFF
        
        magic = b'\xE8\x56'  # v56: Learned Geometric Prediction
        flags = n_stored.to_bytes(2, 'little')  # Store number of learned transitions
        
        e8_seed = magic + flags + struct.pack('III', vocab_size, seq_len, checksum)
        
        # Assemble
        vocab_block = struct.pack('I', len(vocab_compressed)) + vocab_compressed
        trans_block = struct.pack('I', len(trans_compressed)) + trans_compressed
        
        return e8_seed + vocab_block + trans_block + index_stream
    
    def _to_bytes_v55(self) -> bytes:
        """
        v55: Topological Indexing - E8 Root Map with Predictive Geometry
        
        THE PHYSICS:
        "The dictionary is not a list of words. It is a map of the crystal.
        Once you have the map, you don't need the words."
        
        Format:
        [E8_SEED (16 bytes)][VOCAB_BLOCK][INDEX_STREAM]
        
        E8_SEED:
        - 2 bytes: Magic (0xE855)
        - 2 bytes: Reserved
        - 4 bytes: Vocabulary size
        - 4 bytes: Token sequence length
        - 4 bytes: CRC32 checksum
        
        VOCAB_BLOCK:
        - Minimal: token strings + E8 root index per token
        - Much smaller than full vocabulary storage
        
        INDEX_STREAM:
        - Token indices encoded using E8 geometric prediction
        - Each index is stored as deviation from predicted region
        """
        packer = PhiAdicBitPacker()
        
        vocab_size = len(self.vocabulary)
        seq = np.array(self.token_sequence, dtype=np.uint32)
        seq_len = len(seq)
        
        # Sort vocabulary by index for consistent encoding
        sorted_vocab = sorted(self.vocabulary.items(), key=lambda x: x[1]['index'])
        
        # Build lattice index to get E8 root assignments
        lattice_index = LatticeIndex(phase_bits=4, mag_bits=4)
        lattice_index.build_from_vocabulary({k: v for k, v in sorted_vocab}, None)
        
        # Pack vocabulary: [root_index (1 byte)][token_len][token_bytes][count] for each
        vocab_data = bytearray()
        token_to_root = {}
        for token_str, info in sorted_vocab:
            entry = lattice_index.entries.get(token_str)
            root_idx = entry.root_index if entry else 0
            token_to_root[info['index']] = root_idx
            
            vocab_data.append(root_idx & 0xFF)  # Root index (1 byte, 0-239)
            token_bytes = token_str.encode('utf-8')
            vocab_data.extend(struct.pack('H', len(token_bytes)))
            vocab_data.extend(token_bytes)
            vocab_data.extend(struct.pack('I', info.get('count', 1)))
        
        vocab_compressed = zlib.compress(bytes(vocab_data), level=9)
        
        # Build index stream using geometric prediction
        # Assign tokens to 240 E8 buckets, then store bucket + offset
        # This allows geometric prediction of which bucket the next token is in
        
        # Create buckets: group tokens by their E8 root
        root_to_tokens: Dict[int, List[int]] = {i: [] for i in range(240)}
        for token_idx, root_idx in token_to_root.items():
            root_to_tokens[root_idx].append(token_idx)
        
        # For each token in sequence, store:
        # 1. If same root as predicted: 1 bit
        # 2. If different root: root index (gamma coded rank)
        # 3. Offset within root's token list (gamma coded)
        
        stream = BitStream()
        context_roots: List[int] = []
        predictor = DeltaPhiPacker(DeltaPackConfig(use_prediction=True, context_size=3)).predictor
        
        for token_idx in seq:
            root_idx = token_to_root.get(int(token_idx), 0)
            tokens_in_root = root_to_tokens[root_idx]
            offset_in_root = tokens_in_root.index(int(token_idx)) if int(token_idx) in tokens_in_root else 0
            
            # Predict root
            if context_roots:
                predicted_root = predictor.get_predicted_root(context_roots)
                if root_idx == predicted_root:
                    stream.write_bit(1)  # Prediction correct
                else:
                    stream.write_bit(0)
                    # Store rank of actual root
                    rank = predictor.get_rank(root_idx, context_roots)
                    stream.write_gamma(rank + 1)
            else:
                # No prediction - store root directly
                for i in range(8):
                    stream.write_bit((root_idx >> i) & 1)
            
            # Store offset within root (usually small)
            stream.write_gamma(offset_in_root + 1)
            
            # Update context
            context_roots.append(root_idx)
            if len(context_roots) > 3:
                context_roots.pop(0)
        
        index_stream = stream.to_bytes()
        
        # Build E8_SEED
        checksum = zlib.crc32(index_stream) & 0xFFFFFFFF
        
        magic = b'\xE8\x55'  # v55: Topological Indexing
        reserved = b'\x00\x00'
        
        e8_seed = (magic + reserved + struct.pack('III', vocab_size, seq_len, checksum))
        
        # Assemble
        vocab_block = struct.pack('I', len(vocab_compressed)) + vocab_compressed
        
        return e8_seed + vocab_block + index_stream
    
    def _to_bytes_v54(self) -> bytes:
        """
        v54: Phason Zip - Headerless Binary with Phi-Adic Bit-Packing
        
        THE PHYSICS:
        The Singularity is continuous, but the Horizon is discrete.
        We quantize the continuous angles into discrete bit patterns,
        storing only the phason flip path through the E8 lattice.
        
        Format:
        [E8_SEED (16 bytes)][VOCAB_BLOCK][PHASON_STREAM]
        
        E8_SEED:
        - 2 bytes: Magic (0xE854)
        - 2 bytes: Reserved
        - 4 bytes: Vocabulary size
        - 4 bytes: Token sequence length
        - 4 bytes: CRC32 checksum
        
        VOCAB_BLOCK:
        - 4 bytes: Block length
        - ZLIB compressed vocabulary (token strings + counts)
        
        PHASON_STREAM:
        - Pure bit-packed token indices
        """
        packer = PhiAdicBitPacker()
        
        # 1. Prepare vocabulary block (minimal: just tokens and counts)
        vocab_size = len(self.vocabulary)
        seq = np.array(self.token_sequence, dtype=np.uint32)
        seq_len = len(seq)
        
        # Sort vocabulary by index for consistent encoding
        sorted_vocab = sorted(self.vocabulary.items(), key=lambda x: x[1]['index'])
        
        # Pack vocabulary: [token_len][token_bytes][count] for each
        vocab_data = bytearray()
        for token_str, info in sorted_vocab:
            token_bytes = token_str.encode('utf-8')
            vocab_data.extend(struct.pack('H', len(token_bytes)))  # 2 bytes for token length
            vocab_data.extend(token_bytes)
            vocab_data.extend(struct.pack('I', info.get('count', 1)))  # 4 bytes for count
        
        # Compress vocabulary block
        vocab_compressed = zlib.compress(bytes(vocab_data), level=9)
        
        # 2. Pack token sequence using bit packer (direct index encoding)
        # For v54, we skip RAC and directly encode indices for efficiency
        phason_stream = packer.pack_token_indices(seq.tolist(), vocab_size)
        
        # 3. Build E8_SEED
        # Calculate checksum of phason stream
        checksum = zlib.crc32(phason_stream) & 0xFFFFFFFF
        
        magic = b'\xE8\x54'  # v54: Phason Zip
        reserved = b'\x00\x00'
        
        e8_seed = (magic + reserved + 
                   struct.pack('III', vocab_size, seq_len, checksum))
        
        # 4. Assemble final output
        vocab_block = struct.pack('I', len(vocab_compressed)) + vocab_compressed
        
        return e8_seed + vocab_block + phason_stream
    
    def _to_bytes_v53(self) -> bytes:
        """
        v53: Legacy Radial Arithmetic Coding format (for backward compatibility).
        """
        # 1. Prepare probability model from vocabulary
        total_count = sum(info.get('count', 1) for info in self.vocabulary.values())
        if total_count == 0: total_count = 1
        
        # Maps index -> probability
        index_probs = {}
        for info in self.vocabulary.values():
            index_probs[info['index']] = info.get('count', 1) / total_count
            
        # 2. Encode token sequence using Radial Arithmetic Coding (RAC)
        # For large sequences, we use block-based RAC to maintain precision
        # BLOCK_SIZE 4 ensures we stay within 53-bit float precision
        BLOCK_SIZE = 4
        seq = np.array(self.token_sequence, dtype=np.uint32)
        n_blocks = (len(seq) + BLOCK_SIZE - 1) // BLOCK_SIZE
        
        rac = RadialArithmeticCoder(index_probs)
        phi_angles = []
        
        for i in range(n_blocks):
            block = seq[i*BLOCK_SIZE : (i+1)*BLOCK_SIZE]
            angle = rac.encode(block.tolist())
            phi_angles.append(angle.to_bits())
            
        # Combine all phi-angle bits
        rac_bytes = b"".join(struct.pack('I', len(b)) + b for b in phi_angles)
        
        # Build optimized header
        header = {
            'vocabulary': {str(k): v for k, v in self.vocabulary.items()},
            'metadata': self.metadata,
            'n_blocks': n_blocks,
            'block_size': BLOCK_SIZE,
            'seq_len': len(seq)
        }
        
        header_json = json.dumps(header).encode('utf-8')
        header_len = len(header_json)
        
        # Binary arrays for 8D geometry
        proj_bytes = self.projections_4d.astype(np.float32).tobytes()
        phason_bytes = self.phasons_4d.astype(np.float32).tobytes()
        phase_bytes = self.phases.astype(np.float32).tobytes()
        
        # Pack everything
        packed = struct.pack('I', header_len)
        packed += header_json
        packed += struct.pack('I', len(rac_bytes))
        packed += rac_bytes
        packed += struct.pack('I', len(proj_bytes))
        packed += proj_bytes
        packed += struct.pack('I', len(phason_bytes))
        packed += phason_bytes
        packed += struct.pack('I', len(phase_bytes))
        packed += phase_bytes
        
        # Apply GEOMETRIC error correction (RS encoding)
        geometric_encoded = rs_encode_with_geometry(packed, n_copies=7)
        
        # Compressed-only version for fast path
        compressed_only = zlib.compress(packed, level=9)
        
        magic = b'\xE8\x53'  # v53: Radial Arithmetic Coding Optimized
        compressed_len = len(compressed_only)
        
        return (magic * 5 + 
                struct.pack('I', compressed_len) * 5 + 
                compressed_only + 
                geometric_encoded)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'CompressedData':
        """Deserialize with support for v70, v60, v59, v58, v57, v56, v55, v54, v53, v52, v51, v50."""
        # Check for v70 (Byte-level context mixing) format first
        if len(data) >= 12 and data[:2] == b'\xE8\x70':
            return cls._from_bytes_v70(data)
        
        # Check for v60 (Atlas + Inertia) format
        if len(data) >= 12 and data[:2] == b'\xE8\x60':
            return cls._from_bytes_v60(data)
        
        # Check for v59 (Vectorized Huffman) format
        if len(data) >= 16 and data[:2] == b'\xE8\x59':
            return cls._from_bytes_v59(data)
        
        # Check for v58 (Radial Delta Packing) format
        if len(data) >= 16 and data[:2] == b'\xE8\x58':
            return cls._from_bytes_v58(data)
        
        # Check for v57 (Lexical Erasure) format
        if len(data) >= 20 and data[:2] == b'\xE8\x57':
            return cls._from_bytes_v57(data)
        
        # Check for v56 (Learned Geometric Prediction) format
        if len(data) >= 16 and data[:2] == b'\xE8\x56':
            return cls._from_bytes_v56(data)
        
        # Check for v55 (Topological Indexing) format
        if len(data) >= 16 and data[:2] == b'\xE8\x55':
            return cls._from_bytes_v55(data)
        
        # Check for v54 (Phason Zip) format
        if len(data) >= 16 and data[:2] == b'\xE8\x54':
            return cls._from_bytes_v54(data)
        
        # Fall back to legacy format detection
        return cls._from_bytes_legacy(data)
    
    @classmethod
    def _from_bytes_v70(cls, data: bytes) -> 'CompressedData':
        """
        Deserialize v70 Byte-level context mixing format.
        
        THE PHYSICS:
        Reconstruct bytes from prediction ranks.
        """
        # 1. Read Header
        # Magic is already checked
        orig_len, checksum = struct.unpack('<II', data[2:10])
        
        # 2. Decompress the Integral
        compressed_data = data[12:]
        data_bytes = zlib.decompress(compressed_data)

        # 3. Final Render (Lossless Reconstruction)
        # In V70, the 'Token Sequence' is literally the original data
        # because every byte was mapped to a unique E8 root.
        token_sequence = np.frombuffer(data_bytes, dtype=np.uint8)

        metadata = {
            'mode': 'byte',
            'original_length': orig_len,
            'version': 'v70',
            'byte_level': True,
        }
        
        return cls(
            vocabulary={},  # Empty vocabulary - no string tokens
            token_sequence=token_sequence,
            projections_4d=np.zeros((0, 4), dtype=np.float32),
            phasons_4d=np.zeros((0, 4), dtype=np.float32),
            phases=np.zeros(0, dtype=np.float32),
            metadata=metadata
        )
    
    @classmethod
    def _from_bytes_v60(cls, data: bytes) -> 'CompressedData':
        """
        Deserialize v60 Atlas + Inertia format.
        
        THE PHYSICS:
        Reconstruct using Global Atlas and prediction errors.
        """
        # 1. Parse E8_SEED (12 bytes)
        magic = data[:2]  # b'\xE8\x60'
        atlas_version = struct.unpack('<H', data[2:4])[0]
        seq_len, checksum = struct.unpack('<II', data[4:12])
        
        offset = 12
        
        # 2. Parse Atlas ID
        atlas_id = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        
        # Verify atlas
        expected_atlas_id = zlib.crc32(b"GlobalAtlas_v1") & 0xFFFFFFFF
        if atlas_id != expected_atlas_id:
            raise ValueError(f"Atlas mismatch: expected {expected_atlas_id}, got {atlas_id}")
        
        atlas = get_atlas()
        
        # 3. Parse OOV table
        oov_count, oov_compressed_len = struct.unpack('<HI', data[offset:offset+6])
        offset += 6
        
        oov_tokens = []
        if oov_count > 0 and oov_compressed_len > 0:
            oov_compressed = data[offset:offset+oov_compressed_len]
            offset += oov_compressed_len
            
            oov_data = zlib.decompress(oov_compressed)
            oov_offset = 0
            for _ in range(oov_count):
                root = oov_data[oov_offset]
                oov_offset += 1
                token_len = oov_data[oov_offset]
                oov_offset += 1
                token_str = oov_data[oov_offset:oov_offset+token_len].decode('utf-8')
                oov_offset += token_len
                oov_tokens.append((token_str, root))
        else:
            offset += oov_compressed_len
        
        # 4. Parse error stream
        error_len = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        error_stream = data[offset:offset+error_len]
        offset += error_len
        
        # 5. Parse token stream
        token_stream = data[offset:]
        
        # Unpack token bits
        token_bits = []
        for byte in token_stream:
            for j in range(8):
                token_bits.append((byte >> j) & 1)
        
        # Decode token sequence
        token_sequence = []
        vocabulary: Dict[str, Dict] = {}
        bit_pos = 0
        
        for _ in range(seq_len):
            is_atlas = token_bits[bit_pos] == 1
            bit_pos += 1
            
            if is_atlas:
                # 16-bit atlas index
                atlas_idx = sum(token_bits[bit_pos + j] << j for j in range(16))
                bit_pos += 16
                
                entry = atlas.get_by_index(atlas_idx)
                if entry:
                    token_str = entry.token
                else:
                    token_str = f"<ATLAS_{atlas_idx}>"
            else:
                # Gamma-coded OOV index
                n = 1
                while bit_pos + n - 1 < len(token_bits) and token_bits[bit_pos + n - 1] == 0:
                    n += 1
                bit_pos += n - 1
                
                oov_idx = 0
                for j in range(n - 1, -1, -1):
                    if bit_pos < len(token_bits):
                        oov_idx = (oov_idx << 1) | token_bits[bit_pos]
                        bit_pos += 1
                oov_idx -= 1
                
                if 0 <= oov_idx < len(oov_tokens):
                    token_str = oov_tokens[oov_idx][0]
                else:
                    token_str = f"<OOV_{oov_idx}>"
            
            # Add to vocabulary if new
            if token_str not in vocabulary:
                vocabulary[token_str] = {
                    'index': len(vocabulary),
                    'count': 1,
                    'root_index': atlas.get_root_for_token(token_str)
                }
            else:
                vocabulary[token_str]['count'] += 1
            
            token_sequence.append(vocabulary[token_str]['index'])
        
        # Decode prediction errors and reconstruct roots
        predictor = FastInertiaPredictor()
        
        # Build training sequence from decoded tokens
        root_sequence = np.array([vocabulary[k]['root_index'] for k in vocabulary.keys()], dtype=np.int32)
        if len(root_sequence) > 1:
            predictor.learn_from_sequence(root_sequence)
        
        errors = predictor.decode_errors_fast(error_stream, seq_len)
        reconstructed_roots = predictor.reconstruct_sequence(errors)
        
        # Reconstruct geometry (empty placeholders)
        vocab_size = len(vocabulary)
        projections_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phasons_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phases = np.zeros(vocab_size, dtype=np.float32)
        
        metadata = {
            'mode': 'word',
            'original_length': 0,
            'n_tokens': seq_len,
            'n_unique': vocab_size,
            'version': 'v60',
            'atlas_based': True,
            'oov_count': oov_count,
        }
        
        return cls(
            vocabulary=vocabulary,
            token_sequence=token_sequence,
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=metadata
        )
    
    @classmethod
    def _from_bytes_v59(cls, data: bytes) -> 'CompressedData':
        """
        Deserialize v59 Vectorized Huffman format.
        
        THE PHYSICS:
        Reconstruct using vectorized displacement recovery.
        """
        # 1. Parse E8_SEED (16 bytes)
        magic = data[:2]  # b'\xE8\x59'
        flags = struct.unpack('<H', data[2:4])[0]
        vocab_size, seq_len, checksum = struct.unpack('<III', data[4:16])
        
        offset = 16
        
        # 2. Parse vocabulary
        vocab_compressed_len = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        vocab_compressed = data[offset:offset+vocab_compressed_len]
        offset += vocab_compressed_len
        
        vocab_data = zlib.decompress(vocab_compressed)
        
        vocabulary = {}
        token_to_root = {}
        root_to_tokens: Dict[int, List[int]] = {i: [] for i in range(240)}
        
        vocab_offset = 0
        for i in range(vocab_size):
            root_idx = vocab_data[vocab_offset]
            vocab_offset += 1
            count = struct.unpack('<H', vocab_data[vocab_offset:vocab_offset+2])[0]
            vocab_offset += 2
            token_len = struct.unpack('<H', vocab_data[vocab_offset:vocab_offset+2])[0]
            vocab_offset += 2
            token_str = vocab_data[vocab_offset:vocab_offset+token_len].decode('utf-8')
            vocab_offset += token_len
            
            vocabulary[token_str] = {'index': i, 'count': count, 'root_index': root_idx}
            token_to_root[i] = root_idx
            root_to_tokens[root_idx].append(i)
        
        # 3. Parse displacement block
        disp_len = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        disp_data = data[offset:offset+disp_len]
        offset += disp_len
        
        # 4. Remaining is offset data
        offset_data = data[offset:]
        
        # Decode displacements using fixed scheme (same as v58)
        stream = BitStream.from_bytes(disp_data)
        displacements = []
        
        for i in range(seq_len):
            if i == 0:
                # First root: stored directly
                root_idx = sum(stream.read_bit() << j for j in range(8))
                displacements.append(root_idx)
            else:
                # Decode Huffman-coded displacement
                # For now, use fixed decoding (matches encode_block_fast fallback)
                if stream.read_bit() == 1:
                    disp = 0
                elif stream.read_bit() == 1:
                    sign = stream.read_bit()
                    abs_disp = sum(stream.read_bit() << j for j in range(2))
                    disp = -abs_disp if sign else abs_disp
                elif stream.read_bit() == 1:
                    sign = stream.read_bit()
                    abs_disp = sum(stream.read_bit() << j for j in range(4))
                    disp = -abs_disp if sign else abs_disp
                else:
                    sign = stream.read_bit()
                    abs_disp = sum(stream.read_bit() << j for j in range(7))
                    disp = -abs_disp if sign else abs_disp
                
                displacements.append(disp)
        
        # Reconstruct root sequence (vectorized)
        rac = VectorizedRAC()
        root_sequence = rac.reconstruct_roots(np.array(displacements, dtype=np.int32))
        
        # Decode offsets
        offset_stream = BitStream.from_bytes(offset_data)
        token_sequence = []
        
        for root_idx in root_sequence:
            if offset_stream.read_bit() == 1:
                offset_in_root = 0
            else:
                offset_in_root = offset_stream.read_gamma()
            
            tokens_in_root = root_to_tokens[int(root_idx)]
            if offset_in_root < len(tokens_in_root):
                token_idx = tokens_in_root[offset_in_root]
            elif tokens_in_root:
                token_idx = tokens_in_root[0]
            else:
                token_idx = 0
            
            token_sequence.append(token_idx)
        
        # Reconstruct geometry (empty placeholders)
        projections_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phasons_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phases = np.zeros(vocab_size, dtype=np.float32)
        
        metadata = {
            'mode': 'word',
            'original_length': 0,
            'n_tokens': seq_len,
            'n_unique': vocab_size,
            'version': 'v59',
            'vectorized_huffman': True,
        }
        
        return cls(
            vocabulary=vocabulary,
            token_sequence=token_sequence,
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=metadata
        )
    
    @classmethod
    def _from_bytes_v58(cls, data: bytes) -> 'CompressedData':
        """
        Deserialize v58 Radial Delta Packing format.
        
        THE PHYSICS:
        Reconstruct root sequence from angular displacements.
        """
        # 1. Parse E8_SEED (16 bytes)
        magic = data[:2]  # b'\xE8\x58'
        reserved = data[2:4]
        vocab_size, seq_len, checksum = struct.unpack('<III', data[4:16])
        
        offset = 16
        
        # 2. Parse vocabulary
        vocab_compressed_len = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        vocab_compressed = data[offset:offset+vocab_compressed_len]
        offset += vocab_compressed_len
        
        vocab_data = zlib.decompress(vocab_compressed)
        
        vocabulary = {}
        token_to_root = {}
        root_to_tokens: Dict[int, List[int]] = {i: [] for i in range(240)}
        
        vocab_offset = 0
        for i in range(vocab_size):
            root_idx = vocab_data[vocab_offset]
            vocab_offset += 1
            count = struct.unpack('<H', vocab_data[vocab_offset:vocab_offset+2])[0]
            vocab_offset += 2
            token_len = struct.unpack('<H', vocab_data[vocab_offset:vocab_offset+2])[0]
            vocab_offset += 2
            token_str = vocab_data[vocab_offset:vocab_offset+token_len].decode('utf-8')
            vocab_offset += token_len
            
            vocabulary[token_str] = {'index': i, 'count': count, 'root_index': root_idx}
            token_to_root[i] = root_idx
            root_to_tokens[root_idx].append(i)
        
        # 3. Parse angular stream
        angular_stream = data[offset:]
        
        # Verify checksum
        computed_checksum = zlib.crc32(angular_stream) & 0xFFFFFFFF
        if computed_checksum != checksum:
            raise ValueError(f"Checksum mismatch: expected {checksum}, got {computed_checksum}")
        
        stream = BitStream.from_bytes(angular_stream)
        
        # Decode displacements to reconstruct root sequence
        root_sequence = []
        
        for i in range(seq_len):
            if i == 0:
                # First root: stored directly
                root_idx = sum(stream.read_bit() << j for j in range(8))
            else:
                # Decode displacement
                if stream.read_bit() == 1:
                    # Zero displacement
                    disp = 0
                elif stream.read_bit() == 1:
                    # Small displacement (1-3)
                    sign = stream.read_bit()
                    abs_disp = sum(stream.read_bit() << j for j in range(2))
                    disp = -abs_disp if sign else abs_disp
                elif stream.read_bit() == 1:
                    # Medium displacement (4-15)
                    sign = stream.read_bit()
                    abs_disp = sum(stream.read_bit() << j for j in range(4))
                    disp = -abs_disp if sign else abs_disp
                else:
                    # Large displacement
                    sign = stream.read_bit()
                    abs_disp = sum(stream.read_bit() << j for j in range(7))
                    disp = -abs_disp if sign else abs_disp
                
                root_idx = (root_sequence[-1] + disp) % 240
            
            root_sequence.append(root_idx)
        
        # Decode offsets within roots
        token_sequence = []
        for i, root_idx in enumerate(root_sequence):
            if stream.read_bit() == 1:
                offset_in_root = 0
            else:
                offset_in_root = stream.read_gamma()
            
            tokens_in_root = root_to_tokens[root_idx]
            if offset_in_root < len(tokens_in_root):
                token_idx = tokens_in_root[offset_in_root]
            elif tokens_in_root:
                token_idx = tokens_in_root[0]
            else:
                token_idx = 0
            
            token_sequence.append(token_idx)
        
        # Reconstruct geometry (empty placeholders)
        projections_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phasons_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phases = np.zeros(vocab_size, dtype=np.float32)
        
        metadata = {
            'mode': 'word',
            'original_length': 0,
            'n_tokens': seq_len,
            'n_unique': vocab_size,
            'version': 'v58',
            'radial_delta': True,
        }
        
        return cls(
            vocabulary=vocabulary,
            token_sequence=token_sequence,
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=metadata
        )
    
    @classmethod
    def _from_bytes_v57(cls, data: bytes) -> 'CompressedData':
        """
        Deserialize v57 Lexical Erasure format.
        
        THE PHYSICS:
        "The ultimate compression is when the name of the thing disappears,
        leaving only the shape of the thought."
        
        We reconstruct vocabulary from harmonic signatures.
        """
        # 1. Parse E8_SEED (20 bytes)
        magic = data[:2]  # b'\xE8\x57'
        flags = struct.unpack('<H', data[2:4])[0]
        vocab_size, seq_len, original_len, checksum = struct.unpack('<IIII', data[4:20])
        
        offset = 20
        
        # 2. Parse signature block
        sig_compressed_len = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        sig_compressed = data[offset:offset+sig_compressed_len]
        offset += sig_compressed_len
        
        sig_data = zlib.decompress(sig_compressed)
        
        # Parse signatures and counts
        signatures = []
        counts = []
        sig_offset = 0
        for _ in range(vocab_size):
            sig = HarmonicSignature.from_bytes(sig_data[sig_offset:sig_offset+8])
            sig_offset += 8
            count = struct.unpack('<I', sig_data[sig_offset:sig_offset+4])[0]
            sig_offset += 4
            signatures.append(sig)
            counts.append(count)
        
        # 3. Parse hasher state (for token recovery)
        hasher_len = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        hasher_bytes = data[offset:offset+hasher_len]
        offset += hasher_len
        
        hasher = HarmonicHasher.from_bytes(hasher_bytes)
        
        # 4. Parse arithmetic stream
        arithmetic_stream = data[offset:]
        
        # Verify checksum
        computed_checksum = zlib.crc32(arithmetic_stream) & 0xFFFFFFFF
        if computed_checksum != checksum:
            raise ValueError(f"Checksum mismatch: expected {checksum}, got {computed_checksum}")
        
        # Recover vocabulary from signatures
        vocabulary = {}
        token_to_root = {}
        root_to_tokens: Dict[int, List[int]] = {i: [] for i in range(240)}
        
        for i, (sig, count) in enumerate(zip(signatures, counts)):
            token = hasher.recover_token(sig)
            if token is None:
                token = f"<UNK_{i}>"  # Fallback for unrecoverable tokens
            
            vocabulary[token] = {'index': i, 'count': count, 'root_index': sig.root_index}
            token_to_root[i] = sig.root_index
            root_to_tokens[sig.root_index].append(i)
        
        # Build predictor
        predictor = DeltaPhiPacker(DeltaPackConfig(use_prediction=True, context_size=3)).predictor
        
        # Decode sequence
        stream = BitStream.from_bytes(arithmetic_stream)
        token_sequence = []
        context_roots: List[int] = []
        
        for _ in range(seq_len):
            # Decode root
            if context_roots:
                prediction_correct = stream.read_bit() == 1
                if prediction_correct:
                    probs = predictor.predict_distribution(context_roots)
                    root_idx = int(np.argmax(probs))
                else:
                    # Decode rank
                    first_two = [stream.read_bit(), stream.read_bit()]
                    if first_two == [0, 0]:
                        rank = sum(stream.read_bit() << i for i in range(2))
                    elif first_two == [0, 1]:
                        rank = sum(stream.read_bit() << i for i in range(5))
                    else:
                        rank = stream.read_gamma() - 1
                    
                    probs = predictor.predict_distribution(context_roots)
                    sorted_indices = np.argsort(probs)[::-1]
                    root_idx = int(sorted_indices[min(rank, 239)])
            else:
                root_idx = sum(stream.read_bit() << i for i in range(8))
            
            # Decode offset
            if stream.read_bit() == 1:
                offset_in_root = 0
            else:
                offset_in_root = stream.read_gamma()
            
            # Get token index
            tokens_in_root = root_to_tokens[root_idx]
            if offset_in_root < len(tokens_in_root):
                token_idx = tokens_in_root[offset_in_root]
            elif tokens_in_root:
                token_idx = tokens_in_root[0]
            else:
                token_idx = 0
            
            token_sequence.append(token_idx)
            
            context_roots.append(root_idx)
            if len(context_roots) > 3:
                context_roots.pop(0)
        
        # Reconstruct geometry (empty placeholders)
        projections_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phasons_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phases = np.zeros(vocab_size, dtype=np.float32)
        
        metadata = {
            'mode': 'word',
            'original_length': original_len,
            'n_tokens': seq_len,
            'n_unique': vocab_size,
            'version': 'v57',
            'lexical_erasure': True,
        }
        
        return cls(
            vocabulary=vocabulary,
            token_sequence=token_sequence,
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=metadata
        )
    
    @classmethod
    def _from_bytes_v56(cls, data: bytes) -> 'CompressedData':
        """
        Deserialize v56 Learned Geometric Prediction format.
        
        THE PHYSICS:
        "The crystal learns the shape of language."
        We reconstruct using the learned transition matrix.
        """
        # 1. Parse E8_SEED (16 bytes)
        magic = data[:2]  # b'\xE8\x56'
        n_learned = int.from_bytes(data[2:4], 'little')
        vocab_size, seq_len, checksum = struct.unpack('III', data[4:16])
        
        offset = 16
        
        # 2. Parse VOCAB_BLOCK
        vocab_compressed_len = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        vocab_compressed = data[offset:offset+vocab_compressed_len]
        offset += vocab_compressed_len
        
        vocab_data = zlib.decompress(vocab_compressed)
        
        # Parse vocabulary
        vocabulary = {}
        token_to_root = {}
        root_to_tokens: Dict[int, List[int]] = {i: [] for i in range(240)}
        
        vocab_offset = 0
        for i in range(vocab_size):
            root_idx = vocab_data[vocab_offset]
            vocab_offset += 1
            
            token_len = struct.unpack('H', vocab_data[vocab_offset:vocab_offset+2])[0]
            vocab_offset += 2
            token_str = vocab_data[vocab_offset:vocab_offset+token_len].decode('utf-8')
            vocab_offset += token_len
            count = struct.unpack('I', vocab_data[vocab_offset:vocab_offset+4])[0]
            vocab_offset += 4
            
            vocabulary[token_str] = {'index': i, 'count': count, 'root_index': root_idx}
            token_to_root[i] = root_idx
            root_to_tokens[root_idx].append(i)
        
        # 3. Parse LEARNED_TRANSITIONS
        trans_compressed_len = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        trans_compressed = data[offset:offset+trans_compressed_len]
        offset += trans_compressed_len
        
        trans_data = zlib.decompress(trans_compressed)
        
        # Build learned transition matrix
        predictor = DeltaPhiPacker(DeltaPackConfig(use_prediction=True, context_size=3)).predictor
        predictor.transition_counts = predictor.transitions * 10 + 1e-6  # Start with prior
        
        trans_offset = 0
        while trans_offset < len(trans_data):
            from_root, to_root, count = struct.unpack('BBH', trans_data[trans_offset:trans_offset+4])
            trans_offset += 4
            predictor.transition_counts[from_root, to_root] += count
        
        predictor.learned_transitions = predictor.transition_counts / predictor.transition_counts.sum(axis=1, keepdims=True)
        predictor.use_learned = True
        
        # 4. Parse INDEX_STREAM
        index_stream = data[offset:]
        
        # Verify checksum
        computed_checksum = zlib.crc32(index_stream) & 0xFFFFFFFF
        if computed_checksum != checksum:
            raise ValueError(f"Checksum mismatch: expected {checksum}, got {computed_checksum}")
        
        # Decode sequence
        stream = BitStream.from_bytes(index_stream)
        token_sequence = []
        context_roots: List[int] = []
        
        for _ in range(seq_len):
            # Decode root
            if context_roots:
                prediction_correct = stream.read_bit() == 1
                if prediction_correct:
                    probs = predictor.predict_distribution(context_roots)
                    root_idx = int(np.argmax(probs))
                else:
                    rank = stream.read_gamma()
                    probs = predictor.predict_distribution(context_roots)
                    sorted_indices = np.argsort(probs)[::-1]
                    root_idx = int(sorted_indices[rank])
            else:
                root_idx = 0
                for i in range(8):
                    root_idx |= (stream.read_bit() << i)
            
            # Decode offset
            offset_in_root = stream.read_gamma() - 1
            
            # Get token index
            tokens_in_root = root_to_tokens[root_idx]
            if offset_in_root < len(tokens_in_root):
                token_idx = tokens_in_root[offset_in_root]
            elif tokens_in_root:
                token_idx = tokens_in_root[0]
            else:
                token_idx = 0
            
            token_sequence.append(token_idx)
            
            context_roots.append(root_idx)
            if len(context_roots) > 3:
                context_roots.pop(0)
        
        # Reconstruct geometry (empty placeholders)
        projections_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phasons_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phases = np.zeros(vocab_size, dtype=np.float32)
        
        metadata = {
            'mode': 'word',
            'original_length': 0,
            'n_tokens': seq_len,
            'n_unique': vocab_size,
            'version': 'v56',
            'learned_prediction': True,
        }
        
        return cls(
            vocabulary=vocabulary,
            token_sequence=token_sequence,
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=metadata
        )
    
    @classmethod
    def _from_bytes_v55(cls, data: bytes) -> 'CompressedData':
        """
        Deserialize v55 Topological Indexing format.
        
        THE PHYSICS:
        "The dictionary is not a list of words. It is a map of the crystal."
        We use E8 geometric prediction to decode the token sequence.
        """
        # 1. Parse E8_SEED (16 bytes)
        magic = data[:2]  # b'\xE8\x55'
        reserved = data[2:4]
        vocab_size, seq_len, checksum = struct.unpack('III', data[4:16])
        
        offset = 16
        
        # 2. Parse VOCAB_BLOCK
        vocab_compressed_len = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        vocab_compressed = data[offset:offset+vocab_compressed_len]
        offset += vocab_compressed_len
        
        vocab_data = zlib.decompress(vocab_compressed)
        
        # Parse vocabulary: [root_index][token_len][token_bytes][count] for each
        vocabulary = {}
        token_to_root = {}
        root_to_tokens: Dict[int, List[int]] = {i: [] for i in range(240)}
        
        vocab_offset = 0
        for i in range(vocab_size):
            root_idx = vocab_data[vocab_offset]
            vocab_offset += 1
            
            token_len = struct.unpack('H', vocab_data[vocab_offset:vocab_offset+2])[0]
            vocab_offset += 2
            token_str = vocab_data[vocab_offset:vocab_offset+token_len].decode('utf-8')
            vocab_offset += token_len
            count = struct.unpack('I', vocab_data[vocab_offset:vocab_offset+4])[0]
            vocab_offset += 4
            
            vocabulary[token_str] = {'index': i, 'count': count, 'root_index': root_idx}
            token_to_root[i] = root_idx
            root_to_tokens[root_idx].append(i)
        
        # 3. Parse INDEX_STREAM
        index_stream = data[offset:]
        
        # Verify checksum
        computed_checksum = zlib.crc32(index_stream) & 0xFFFFFFFF
        if computed_checksum != checksum:
            raise ValueError(f"Checksum mismatch: expected {checksum}, got {computed_checksum}")
        
        # Decode index stream
        stream = BitStream.from_bytes(index_stream)
        predictor = DeltaPhiPacker(DeltaPackConfig(use_prediction=True, context_size=3)).predictor
        
        token_sequence = []
        context_roots: List[int] = []
        
        for _ in range(seq_len):
            # Decode root
            if context_roots:
                prediction_correct = stream.read_bit() == 1
                if prediction_correct:
                    root_idx = predictor.get_predicted_root(context_roots)
                else:
                    rank = stream.read_gamma() - 1
                    probs = predictor.predict_distribution(context_roots)
                    sorted_indices = np.argsort(probs)[::-1]
                    root_idx = int(sorted_indices[rank])
            else:
                # No context - read root directly
                root_idx = 0
                for i in range(8):
                    root_idx |= (stream.read_bit() << i)
            
            # Decode offset within root
            offset_in_root = stream.read_gamma() - 1
            
            # Get token index
            tokens_in_root = root_to_tokens[root_idx]
            if offset_in_root < len(tokens_in_root):
                token_idx = tokens_in_root[offset_in_root]
            elif tokens_in_root:
                token_idx = tokens_in_root[0]
            else:
                token_idx = 0
            
            token_sequence.append(token_idx)
            
            # Update context
            context_roots.append(root_idx)
            if len(context_roots) > 3:
                context_roots.pop(0)
        
        # Reconstruct geometry (empty placeholders)
        projections_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phasons_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phases = np.zeros(vocab_size, dtype=np.float32)
        
        metadata = {
            'mode': 'word',
            'original_length': 0,
            'n_tokens': seq_len,
            'n_unique': vocab_size,
            'version': 'v55',
            'topological_indexing': True,
        }
        
        return cls(
            vocabulary=vocabulary,
            token_sequence=token_sequence,
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=metadata
        )
    
    @classmethod
    def _from_bytes_v54(cls, data: bytes) -> 'CompressedData':
        """
        Deserialize v54 Phason Zip format.
        
        THE PHYSICS:
        We reverse the quantization - discrete bits become continuous geometry.
        The E8 lattice is implicit; we reconstruct projections/phasons.
        """
        packer = PhiAdicBitPacker()
        
        # 1. Parse E8_SEED (16 bytes)
        magic = data[:2]  # b'\xE8\x54'
        reserved = data[2:4]
        vocab_size, seq_len, checksum = struct.unpack('III', data[4:16])
        
        offset = 16
        
        # 2. Parse VOCAB_BLOCK
        vocab_compressed_len = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        vocab_compressed = data[offset:offset+vocab_compressed_len]
        offset += vocab_compressed_len
        
        # Decompress vocabulary
        vocab_data = zlib.decompress(vocab_compressed)
        
        # Parse vocabulary: [token_len][token_bytes][count] for each
        vocabulary = {}
        vocab_offset = 0
        for i in range(vocab_size):
            token_len = struct.unpack('H', vocab_data[vocab_offset:vocab_offset+2])[0]
            vocab_offset += 2
            token_str = vocab_data[vocab_offset:vocab_offset+token_len].decode('utf-8')
            vocab_offset += token_len
            count = struct.unpack('I', vocab_data[vocab_offset:vocab_offset+4])[0]
            vocab_offset += 4
            
            vocabulary[token_str] = {'index': i, 'count': count}
        
        # 3. Parse PHASON_STREAM
        phason_stream = data[offset:]
        
        # Verify checksum
        computed_checksum = zlib.crc32(phason_stream) & 0xFFFFFFFF
        if computed_checksum != checksum:
            raise ValueError(f"Checksum mismatch: expected {checksum}, got {computed_checksum}")
        
        # Unpack token indices
        token_sequence = packer.unpack_token_indices(phason_stream, seq_len, vocab_size)
        
        # 4. Reconstruct geometry (empty placeholders - will be recomputed if needed)
        # THE PHYSICS: The geometry is implicit in the E8 lattice.
        # We don't need to store it; we can regenerate it from vocabulary.
        projections_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phasons_4d = np.zeros((vocab_size, 4), dtype=np.float32)
        phases = np.zeros(vocab_size, dtype=np.float32)
        
        # For decompression, we need to regenerate geometry from vocabulary
        # This is done lazily when needed
        
        metadata = {
            'mode': 'word',  # Default assumption
            'original_length': 0,  # Unknown in v54
            'n_tokens': seq_len,
            'n_unique': vocab_size,
            'version': 'v54',
            'phason_zip': True,
        }
        
        return cls(
            vocabulary=vocabulary,
            token_sequence=token_sequence,
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=metadata
        )
    
    @classmethod
    def _from_bytes_legacy(cls, data: bytes) -> 'CompressedData':
        """Deserialize legacy formats (v53, v52, v51, v50)."""
        from .core.holographic_encoding import simple_holographic_recover, recover_from_distributed_parity
        from .core.toric_error_correction import apply_toric_correction_to_bytes
        from collections import Counter
        
        packed = None
        recovered_magic = None
        
        if len(data) >= 30:
            magic_votes = [data[i*2:(i+1)*2] for i in range(5)]
            recovered_magic = Counter(magic_votes).most_common(1)[0][0]
            
            if recovered_magic in (b'\xE8\x53', b'\xE8\x52', b'\xE8\x51', b'\xE8\x50'):
                len_start = 10
                len_votes = [struct.unpack('I', data[len_start+i*4:len_start+(i+1)*4])[0] for i in range(5)]
                compressed_len = Counter(len_votes).most_common(1)[0][0]
                
                data_start = 30
                compressed_only = data[data_start:data_start+compressed_len]
                encoded_data = data[data_start+compressed_len:]
                
                try:
                    packed = zlib.decompress(compressed_only)
                except zlib.error:
                    if recovered_magic in (b'\xE8\x53', b'\xE8\x52', b'\xE8\x51'):
                        packed, _, _ = rs_decode_with_geometry(encoded_data)
                    else:
                        recovered, _ = recover_from_distributed_parity(encoded_data)
                        packed = simple_holographic_recover(recovered)
        
        if packed is None:
            raise ValueError("Failed to decode compressed data")
            
        offset = 0
        
        # Header
        header_len = struct.unpack('I', packed[offset:offset+4])[0]
        offset += 4
        header_json = packed[offset:offset+header_len].decode('utf-8')
        offset += header_len
        header = json.loads(header_json)
        
        # Token Sequence
        if recovered_magic == b'\xE8\x53':
            # Radial Arithmetic Decoding
            rac_len = struct.unpack('I', packed[offset:offset+4])[0]
            offset += 4
            rac_data = packed[offset:offset+rac_len]
            offset += rac_len
            
            # Prepare RAC coder
            total_count = sum(info.get('count', 1) for info in header['vocabulary'].values())
            index_probs = {int(info['index']): info.get('count', 1) / total_count for info in header['vocabulary'].values()}
            rac = RadialArithmeticCoder(index_probs)
            
            token_sequence = []
            rac_offset = 0
            block_size = header['block_size']
            seq_len = header['seq_len']
            
            for _ in range(header['n_blocks']):
                phi_len = struct.unpack('I', rac_data[rac_offset:rac_offset+4])[0]
                rac_offset += 4
                phi_bits = rac_data[rac_offset:rac_offset+phi_len]
                rac_offset += phi_len
                
                phi_angle = PhiAdicNumber.from_bits(phi_bits)
                # Determine block length
                rem = seq_len - len(token_sequence)
                current_block_len = min(block_size, rem)
                
                block = rac.decode(phi_angle, current_block_len)
                token_sequence.extend(block)
                
        elif recovered_magic == b'\xE8\x52':
            seq_len = struct.unpack('I', packed[offset:offset+4])[0]
            offset += 4
            token_sequence = np.frombuffer(packed[offset:offset+seq_len], dtype=np.uint32).tolist()
            offset += seq_len
        else:
            # Legacy v51/50 stored sequence in JSON
            token_sequence = header.get('token_sequence', [])
            
        # Projections
        proj_len = struct.unpack('I', packed[offset:offset+4])[0]
        offset += 4
        projections_4d = np.frombuffer(packed[offset:offset+proj_len], dtype=np.float32)
        offset += proj_len
        
        # Phasons
        phason_len = struct.unpack('I', packed[offset:offset+4])[0]
        offset += 4
        phasons_4d = np.frombuffer(packed[offset:offset+phason_len], dtype=np.float32)
        offset += phason_len
        
        # Phases
        phase_len = struct.unpack('I', packed[offset:offset+4])[0]
        offset += 4
        phases = np.frombuffer(packed[offset:offset+phase_len], dtype=np.float32)
        
        n_unique = len(header['vocabulary'])
        if n_unique > 0:
            projections_4d = projections_4d.reshape(n_unique, 4)
            phasons_4d = phasons_4d.reshape(n_unique, 4)
        else:
            projections_4d = np.array([]).reshape(0, 4)
            phasons_4d = np.array([]).reshape(0, 4)
            
        return cls(
            vocabulary=header['vocabulary'],
            token_sequence=token_sequence,
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=header['metadata']
        )


class GQECompressor:
    """
    Golden Quasicrystal Encoding Compressor.
    
    SELF-LEARNING (The Möbius Strip):
    When self_learning=True, the compressor updates its E8 basis
    after each compression, learning the geometric structure of language.
    
    Words that co-occur frequently move closer in 8D space.
    Random "phason flips" allow emergence of new concepts.
    """
    
    HORIZON_THRESHOLD = 233 * 1024
    
    def __init__(self, window_size: int = 5, tokenize_mode: str = 'auto', 
                 use_horizon_batching: bool = True, chunk_size: Optional[int] = None,
                 self_learning: bool = False, evolution_state_path: Optional[str] = None,
                 learning_rate: float = 0.01, mutation_rate: float = 0.001,
                 enable_geometric_parallelism: bool = False):
        """
        Initialize compressor.
        
        Args:
            window_size: Co-occurrence window for graph building
            tokenize_mode: Tokenization mode ('auto', 'word', 'char', 'byte')
            use_horizon_batching: Enable Horizon Batching for large inputs
            chunk_size: Custom chunk size for Horizon Batching
            self_learning: Enable geometric self-learning
            evolution_state_path: Path to save/load learned state
            learning_rate: How fast nodes move toward co-occurring neighbors
            mutation_rate: Probability of random phason flips
            enable_geometric_parallelism: Enable v71 Geometric Parallelism Context Mixer
        """
        self.window_size = window_size
        self.tokenize_mode = tokenize_mode
        self.use_horizon_batching = use_horizon_batching
        self.chunk_size = chunk_size or self.HORIZON_THRESHOLD
        self.enable_geometric_parallelism = enable_geometric_parallelism
        
        # Self-learning configuration
        self.self_learning = self_learning
        self.evolver: Optional[GeometricEvolver] = None
        self.evolution_stats: List[Dict] = []
        
        if self_learning:
            self.evolver = GeometricEvolver(
                learning_rate=learning_rate,
                mutation_rate=mutation_rate,
                state_path=evolution_state_path,
            )
    
    def _apply_learning(self, vocabulary: Dict[str, Dict], 
                        embeddings_8d: np.ndarray, 
                        phases: np.ndarray,
                        token_indices: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Apply self-learning feedback loop.
        
        THE MÖBIUS STRIP:
        1. Initialize evolver with current vocabulary
        2. Observe co-occurrences
        3. Apply attraction + mutations
        4. Return evolved embeddings
        
        Returns:
            (evolved_embeddings, evolved_phases, evolution_stats)
        """
        if self.evolver is None:
            return embeddings_8d, phases, {}
        
        # Convert vocabulary from {'word': {'index': i}} to {'word': i}
        simple_vocab = {token: info['index'] for token, info in vocabulary.items()}
        
        # Initialize evolver if needed
        if self.evolver.state is None:
            self.evolver.initialize_from_vocabulary(simple_vocab, embeddings_8d, phases)
        else:
            # Update vocabulary if it has grown
            for token, idx in simple_vocab.items():
                if token not in self.evolver.state.vocabulary:
                    self.evolver.state.vocabulary[token] = idx
                    # Expand embeddings array
                    if idx >= len(self.evolver.state.embeddings_8d):
                        new_embed = np.random.randn(8).astype(np.float32) * 0.5
                        self.evolver.state.embeddings_8d = np.vstack([
                            self.evolver.state.embeddings_8d, new_embed
                        ])
                        self.evolver.state.phases = np.append(
                            self.evolver.state.phases, 
                            np.random.uniform(0, 2 * np.pi)
                        )
        
        # Run evolution step
        stats = self.evolver.evolve_step(token_indices, apply_mutations=True)
        self.evolution_stats.append(stats)
        
        # Return evolved embeddings
        evolved_embed, evolved_phases = self.evolver.get_evolved_embeddings()
        
        # Resize to match vocabulary if needed
        n_vocab = len(vocabulary)
        if len(evolved_embed) < n_vocab:
            pad_size = n_vocab - len(evolved_embed)
            evolved_embed = np.vstack([evolved_embed, np.zeros((pad_size, 8))])
            evolved_phases = np.append(evolved_phases, np.zeros(pad_size))
        elif len(evolved_embed) > n_vocab:
            evolved_embed = evolved_embed[:n_vocab]
            evolved_phases = evolved_phases[:n_vocab]
        
        return evolved_embed, evolved_phases, stats
    
    def get_learned_concepts(self) -> List[Dict]:
        """
        Get emergent concepts learned by the compressor.
        
        Returns:
            List of concept clusters (tokens that have moved close together)
        """
        if self.evolver is None:
            return []
        return self.evolver.get_learned_concepts()
    
    def _compress_with_horizon_batching(self, data: bytes, mode: str) -> CompressedData:
        """
        Compress using Horizon Batching for large inputs.
        
        CRITICAL FIX: We do NOT accumulate frames in memory.
        We stream them into the CompressedData object.
        """
        from .core.horizon_batcher import HorizonBatcher
        
        batcher = HorizonBatcher(
            chunk_size=self.chunk_size,
            window_size=self.window_size
        )
        
        # Build Global Singularity (eternal basis)
        singularity = batcher.build_singularity(data)
        
        if len(singularity.vocabulary) == 0:
            return CompressedData({}, np.array([], dtype=np.uint8),
                                  np.array([]).reshape(0, 4), np.array([]).reshape(0, 4), 
                                  np.array([]), {'mode': 'byte', 'original_length': len(data), 'horizon_batched': True, 'version': 'v70'})
        
        # PHASE 9: BYTE-SINGULARITY - Direct byte mapping
        # In byte mode, the token_sequence IS the original data
        # Each byte (0-255) maps directly to an E8 coordinate
        # No complex vocabulary or tokenization needed

        frame_count = (len(data) + self.chunk_size - 1) // self.chunk_size
        token_sequence = np.frombuffer(data, dtype=np.uint8)  # Direct byte array

        # Empty vocabulary - bytes map directly
        vocabulary = {}

        # PHASE 9: BYTE-SINGULARITY - Direct byte mapping
        # In byte mode, the token_sequence IS the original data
        # Each byte (0-255) maps directly to an E8 coordinate
        token_sequence = np.frombuffer(data, dtype=np.uint8)  # Direct byte array
        
        # SELF-LEARNING: Apply the Möbius Feedback Loop
        embeddings_8d = singularity.embeddings_8d.copy()
        phases = singularity.phases.copy()
        evolution_stats = {}
        
        if self.self_learning and self.evolver is not None:
            embeddings_8d, phases, evolution_stats = self._apply_learning(
                vocabulary,  # Use formatted vocabulary (with 'index' keys)
                embeddings_8d,
                phases,
                all_indices
            )
        
        # PHASE 9: BYTE-SINGULARITY - No projections needed
        # Bytes map directly to E8 coordinates, no complex projections
        
        metadata = {
            'mode': 'byte',  # Always byte mode for horizon batching
            'original_length': len(data),
            'n_tokens': len(data),  # Each byte is a token
            'n_unique': 256,  # Always 256 possible bytes
            'window_size': self.window_size,
            'horizon_batched': True,
            'n_frames': frame_count,
            'chunk_size': self.chunk_size,
            'version': 'v70',  # Byte-singularity uses V70 format
            'self_learning': self.self_learning,
            'evolution_stats': {},
        }
        
        return CompressedData(
            vocabulary={},  # Empty vocabulary in byte mode
            token_sequence=token_sequence,  # Direct byte array
            projections_4d=np.zeros((0, 4), dtype=np.float32),  # No projections in V70
            phasons_4d=np.zeros((0, 4), dtype=np.float32),     # No phasons in V70
            phases=np.zeros(0, dtype=np.float32),             # No phases in V70
            metadata=metadata
        )
    
    def compress_file(self, file_path: str) -> CompressedData:
        """
        Compress a file using true streaming to maintain low RSS.
        """
        mode = self.tokenize_mode
        if mode == 'auto':
            mode = 'word' # Default for files
            
        from .core.horizon_batcher import HorizonBatcher
        batcher = HorizonBatcher(chunk_size=self.chunk_size, window_size=self.window_size)
        
        # 1. First pass: Build Global Singularity (eternal basis)
        # We read the first chunk to establish the vocabulary
        with open(file_path, 'rb') as f:
            first_chunk = f.read(self.chunk_size)
            singularity = batcher.build_singularity(first_chunk)
            
        # 2. Second pass: Process frames and collect indices into a single binary array
        # We pre-allocate the array if possible, or use a list of arrays
        frame_arrays = []
        total_tokens = 0
        
        with open(file_path, 'rb') as f:
            frame_idx = 0
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk: break
                
                # Process one frame at a time
                try:
                    tokens = tokenize(chunk.decode('utf-8'), mode=mode)
                except UnicodeDecodeError:
                    tokens = tokenize(chunk, mode='byte')
                
                indices = np.array([singularity.vocabulary.get(t.value, 0) for t in tokens], dtype=np.uint32)
                frame_arrays.append(indices)
                total_tokens += len(indices)
                frame_idx += 1
                
        all_indices = np.concatenate(frame_arrays)
        del frame_arrays # Immediate GC
        
        # ... (rest of the logic remains the same)
        n_unique = len(singularity.vocabulary)
        projections_4d = np.zeros((n_unique, 4), dtype=np.float32)
        phasons_4d = np.zeros((n_unique, 4), dtype=np.float32)
        phases = singularity.phases.copy()
        
        from .core.projection import coxeter_projection_8d_to_4d
        from .core.e8_lattice import Spinor
        P_par, P_perp = coxeter_projection_matrices() if 'coxeter_projection_matrices' in dir() else (None, None)
        
        for i in range(n_unique):
            if i < len(singularity.embeddings_8d):
                spinor = Spinor(position=singularity.embeddings_8d[i], phase=phases[i])
                projected = coxeter_projection_8d_to_4d(spinor)
                projections_4d[i] = projected.parallel
                phasons_4d[i] = projected.phason
                
        metadata = {
            'mode': mode,
            'original_length': os.path.getsize(file_path),
            'n_tokens': total_tokens,
            'n_unique': n_unique,
            'window_size': self.window_size,
            'horizon_batched': True,
            'n_frames': frame_idx,
            'chunk_size': self.chunk_size
        }
        
        return CompressedData(
            vocabulary={t: {'index': i, 'count': 0} for t, i in singularity.vocabulary.items()},
            token_sequence=all_indices,
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=metadata
        )

    def compress(self, data: Union[str, bytes]) -> CompressedData:
        """
        Compress input data.
        
        For large inputs (> 233KB), uses Horizon Batching:
        - GLOBAL: Vocabulary / E8 Basis (The Singularity)
        - LOCAL: Phason sequences per chunk (Horizon Frames)
        
        This follows The Architect's principle:
        "The Universe renders in FRAMES, not all at once."
        
        Args:
            data: Input data (text or bytes)
        
        Returns:
            CompressedData object
        """
        # Determine mode
        mode = self.tokenize_mode
        if mode == 'auto':
            mode = 'byte' if isinstance(data, bytes) else 'word'
        
        # Convert to bytes for size check
        data_bytes = data.encode('utf-8') if isinstance(data, str) else data
        
        # Use Horizon Batching for large inputs
        if self.use_horizon_batching and len(data_bytes) > self.HORIZON_THRESHOLD:
            return self._compress_with_horizon_batching(data_bytes, mode)
        
        # Standard compression for small inputs
        tokens = tokenize(data, mode=mode)
        
        if len(tokens) == 0:
            return CompressedData(
                vocabulary={},
                token_sequence=[],
                projections_4d=np.array([]).reshape(0, 4),
                phasons_4d=np.array([]).reshape(0, 4),
                phases=np.array([]),
                metadata={'mode': mode, 'original_length': 0}
            )
        
        # Step 2: Build co-occurrence graph
        graph = build_cooccurrence_graph(tokens, window_size=self.window_size)
        
        # Step 3: Embed tokens to 8D spinors
        spinors = embed_all_tokens(tokens, graph)
        
        # Step 4: Build vocabulary (unique tokens)
        vocabulary = {}
        token_to_idx = {}
        unique_spinors = []
        
        for token, spinor in zip(tokens, spinors):
            token_str = str(token.value)
            if token_str not in vocabulary:
                idx = len(vocabulary)
                vocabulary[token_str] = {
                    'index': idx,
                    'count': 1
                }
                token_to_idx[token_str] = idx
                unique_spinors.append(spinor)
            else:
                vocabulary[token_str]['count'] += 1
        
        # Step 5: Create token sequence (indices)
        token_sequence = np.array([token_to_idx[str(t.value)] for t in tokens], dtype=np.uint32)
        
        # SELF-LEARNING: Apply the Möbius Feedback Loop (standard path)
        embeddings_8d = np.array([s.position for s in unique_spinors], dtype=np.float32)
        phases = np.array([s.phase for s in unique_spinors], dtype=np.float32)
        evolution_stats = {}
        
        if self.self_learning and self.evolver is not None:
            embeddings_8d, phases, evolution_stats = self._apply_learning(
                vocabulary,
                embeddings_8d,
                phases,
                token_sequence
            )
        
        # Step 6: Project spinors to 4D + extract phasons (using evolved embeddings)
        n_unique = len(unique_spinors)
        projections_4d = np.zeros((n_unique, 4))
        phasons_4d = np.zeros((n_unique, 4))
        
        for i in range(n_unique):
            spinor = Spinor(position=embeddings_8d[i], phase=phases[i])
            projected = coxeter_projection_8d_to_4d(spinor)
            projections_4d[i] = projected.parallel
            phasons_4d[i] = projected.phason
        
        # Metadata
        metadata = {
            'mode': mode,
            'original_length': len(data) if isinstance(data, (str, bytes)) else len(tokens),
            'n_tokens': len(tokens),
            'n_unique': n_unique,
            'window_size': self.window_size,
            'self_learning': self.self_learning,
            'evolution_stats': evolution_stats,
        }
        
        return CompressedData(
            vocabulary=vocabulary,
            token_sequence=token_sequence.tolist(),
            projections_4d=projections_4d,
            phasons_4d=phasons_4d,
            phases=phases,
            metadata=metadata
        )


def compress_text(text: str, **kwargs) -> CompressedData:
    """
    Convenience function to compress text.
    
    Args:
        text: Input text
        **kwargs: Additional arguments for GQECompressor
    
    Returns:
        CompressedData object
    """
    compressor = GQECompressor(**kwargs)
    return compressor.compress(text)


def run_verification() -> None:
    """Run verification tests for compressor."""
    print("=" * 60)
    print("GQE COMPRESSOR VERIFICATION")
    print("=" * 60)
    
    # Test text
    test_text = """
    The quick brown fox jumps over the lazy dog.
    The dog was sleeping peacefully in the sun.
    A fox is quick and clever, while a dog is loyal.
    """
    
    print(f"\nOriginal text length: {len(test_text)} bytes")
    
    # Test 1: Basic compression
    print("\n--- Test 1: Basic compression ---")
    compressor = GQECompressor(window_size=5)
    compressed = compressor.compress(test_text)
    
    print(f"  Tokens: {compressed.metadata['n_tokens']}")
    print(f"  Unique tokens: {compressed.metadata['n_unique']}")
    print(f"  Projections shape: {compressed.projections_4d.shape}")
    print(f"  Phasons shape: {compressed.phasons_4d.shape}")
    
    # Test 2: Serialization
    print("\n--- Test 2: Serialization ---")
    serialized = compressed.to_bytes()
    print(f"  Serialized size: {len(serialized)} bytes")
    print(f"  Compression ratio: {len(serialized) / len(test_text):.4f}")
    
    # Test 3: Deserialization
    print("\n--- Test 3: Deserialization ---")
    restored = CompressedData.from_bytes(serialized)
    print(f"  Vocabulary restored: {len(restored.vocabulary)} tokens")
    print(f"  Sequence restored: {len(restored.token_sequence)} indices")
    
    # Verify data integrity
    proj_match = np.allclose(compressed.projections_4d, restored.projections_4d)
    phason_match = np.allclose(compressed.phasons_4d, restored.phasons_4d)
    print(f"  Projections match: {proj_match}")
    print(f"  Phasons match: {phason_match}")
    
    # Test 4: Byte data compression
    print("\n--- Test 4: Byte data ---")
    byte_data = b"ATCGATCGATCGATCG" * 20
    compressor_byte = GQECompressor(tokenize_mode='byte')
    compressed_bytes = compressor_byte.compress(byte_data)
    serialized_bytes = compressed_bytes.to_bytes()
    
    print(f"  Original: {len(byte_data)} bytes")
    print(f"  Compressed: {len(serialized_bytes)} bytes")
    print(f"  Ratio: {len(serialized_bytes) / len(byte_data):.4f}")
    
    # Test 5: Various text sizes
    print("\n--- Test 5: Scaling behavior ---")
    for size_mult in [1, 5, 10]:
        text = test_text * size_mult
        comp = compressor.compress(text)
        ser = comp.to_bytes()
        ratio = len(ser) / len(text)
        print(f"  {len(text):6d} bytes -> {len(ser):6d} bytes (ratio: {ratio:.4f})")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
