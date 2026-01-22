#!/usr/bin/env python3
"""
Geometric Inheritance - The Phason Cache

THE PHYSICS:
"A new frame should inherit the lattice of the previous frame
and only update the Topological Defects."

This module implements hot-loading of E8 basis between frames,
eliminating redundant TDA calculations for continuous text streams.

Key Concepts:
- Frame Inheritance: New frames start from previous frame's state
- Defect Detection: Only recalculate where topology changes
- Cache Coherence: Maintain consistent vocabulary across frames

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
import hashlib

try:
    from .phi_adic import PHI, PHI_INV
    from .e8_lattice import Spinor, generate_e8_roots
except ImportError:
    from phi_adic import PHI, PHI_INV
    from e8_lattice import Spinor, generate_e8_roots


@dataclass
class TokenGeometry:
    """Cached geometric data for a token."""
    root_index: int
    delta_phase: float
    delta_magnitude: float
    embedding: np.ndarray = field(default_factory=lambda: np.zeros(8))
    last_seen_frame: int = 0


@dataclass 
class FrameState:
    """State of the E8 lattice at a particular frame."""
    frame_id: int
    vocabulary: Dict[str, TokenGeometry]
    root_distribution: np.ndarray  # Count per root
    entropy: float
    
    def copy(self) -> 'FrameState':
        """Deep copy for inheritance."""
        return FrameState(
            frame_id=self.frame_id,
            vocabulary={k: TokenGeometry(
                root_index=v.root_index,
                delta_phase=v.delta_phase,
                delta_magnitude=v.delta_magnitude,
                embedding=v.embedding.copy(),
                last_seen_frame=v.last_seen_frame
            ) for k, v in self.vocabulary.items()},
            root_distribution=self.root_distribution.copy(),
            entropy=self.entropy
        )


class GeometricCache:
    """
    Cache for E8 geometric computations across frames.
    
    THE PHYSICS:
    The lattice persists between frames. New tokens cause
    "topological defects" that must be recalculated, but
    existing tokens retain their geometric addresses.
    """
    
    def __init__(self, max_frames: int = 100):
        self.max_frames = max_frames
        self.e8_roots = generate_e8_roots()
        self.root_spinors = [Spinor(root) for root in self.e8_roots]
        
        # Frame history
        self._frame_states: List[FrameState] = []
        self._current_frame_id = 0
        
        # Global token cache (persists across all frames)
        self._global_cache: Dict[str, TokenGeometry] = {}
        
        # Statistics
        self._cache_hits = 0
        self._cache_misses = 0
    
    def _compute_token_geometry(self, token: str) -> TokenGeometry:
        """
        Compute geometric properties for a new token.
        
        THE PHYSICS:
        Hash the token to find its natural E8 root,
        then compute the "defect" from that root.
        """
        # Use hash to find root index
        h = hashlib.sha256(token.encode('utf-8')).digest()
        root_index = int.from_bytes(h[:2], 'little') % 240
        
        # Compute delta phase from token characteristics
        char_sum = sum(ord(c) for c in token)
        delta_phase = (char_sum * PHI) % (2 * np.pi) - np.pi
        
        # Compute delta magnitude (how far from ideal root)
        delta_magnitude = (len(token) * PHI_INV) % 1.0
        
        # Create pseudo-embedding from token
        embedding = np.zeros(8)
        for i, c in enumerate(token[:8]):
            embedding[i] = (ord(c) - 64) / 64.0
        
        return TokenGeometry(
            root_index=root_index,
            delta_phase=delta_phase,
            delta_magnitude=delta_magnitude,
            embedding=embedding,
            last_seen_frame=self._current_frame_id
        )
    
    def get_token_geometry(self, token: str) -> TokenGeometry:
        """
        Get geometry for a token, using cache if available.
        
        THE PHYSICS:
        Check the cache first. If the token was seen before,
        its geometric address is already known.
        """
        if token in self._global_cache:
            self._cache_hits += 1
            geom = self._global_cache[token]
            geom.last_seen_frame = self._current_frame_id
            return geom
        
        self._cache_misses += 1
        geom = self._compute_token_geometry(token)
        self._global_cache[token] = geom
        return geom
    
    def process_frame(self, tokens: List[str]) -> Tuple[Dict[str, TokenGeometry], Dict]:
        """
        Process a frame of tokens, inheriting from previous state.
        
        Returns:
            (vocabulary_geometry, frame_stats)
        """
        self._current_frame_id += 1
        
        # Find unique tokens
        unique_tokens = set(tokens)
        
        # Check which are new vs cached
        new_tokens = [t for t in unique_tokens if t not in self._global_cache]
        cached_tokens = [t for t in unique_tokens if t in self._global_cache]
        
        # Get geometry for all tokens
        vocab_geometry = {}
        root_counts = np.zeros(240, dtype=np.int32)
        
        for token in unique_tokens:
            geom = self.get_token_geometry(token)
            vocab_geometry[token] = geom
            root_counts[geom.root_index] += 1
        
        # Compute frame entropy
        probs = root_counts[root_counts > 0] / root_counts.sum()
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        
        # Store frame state
        state = FrameState(
            frame_id=self._current_frame_id,
            vocabulary=vocab_geometry,
            root_distribution=root_counts,
            entropy=entropy
        )
        
        self._frame_states.append(state)
        if len(self._frame_states) > self.max_frames:
            self._frame_states.pop(0)
        
        stats = {
            'frame_id': self._current_frame_id,
            'total_tokens': len(tokens),
            'unique_tokens': len(unique_tokens),
            'new_tokens': len(new_tokens),
            'cached_tokens': len(cached_tokens),
            'cache_hit_rate': len(cached_tokens) / len(unique_tokens) if unique_tokens else 0,
            'entropy': entropy,
            'global_cache_size': len(self._global_cache),
        }
        
        return vocab_geometry, stats
    
    def get_defects(self, prev_frame_id: int, current_frame_id: int) -> Set[str]:
        """
        Find topological defects between two frames.
        
        THE PHYSICS:
        Defects are tokens that changed their geometric position
        or are new to the current frame.
        """
        if prev_frame_id >= len(self._frame_states):
            return set()
        
        prev_state = self._frame_states[prev_frame_id]
        current_state = self._frame_states[current_frame_id] if current_frame_id < len(self._frame_states) else None
        
        if current_state is None:
            return set()
        
        # New tokens are defects
        prev_tokens = set(prev_state.vocabulary.keys())
        current_tokens = set(current_state.vocabulary.keys())
        
        return current_tokens - prev_tokens
    
    def inherit_and_update(self, 
                           new_tokens: List[str],
                           parent_frame_id: Optional[int] = None) -> Tuple[Dict[str, TokenGeometry], Dict]:
        """
        Inherit from a previous frame and update with new tokens.
        
        THE PHYSICS:
        Hot-load the previous frame's E8 basis.
        Only compute geometry for new tokens (defects).
        """
        self._current_frame_id += 1
        
        # Start from previous state if available
        if parent_frame_id is not None and parent_frame_id < len(self._frame_states):
            base_state = self._frame_states[parent_frame_id].copy()
            base_state.frame_id = self._current_frame_id
        else:
            base_state = FrameState(
                frame_id=self._current_frame_id,
                vocabulary={},
                root_distribution=np.zeros(240, dtype=np.int32),
                entropy=0.0
            )
        
        # Find new tokens (defects)
        unique_new = set(new_tokens)
        defects = unique_new - set(base_state.vocabulary.keys())
        
        # Update only for defects
        for token in defects:
            geom = self.get_token_geometry(token)
            base_state.vocabulary[token] = geom
            base_state.root_distribution[geom.root_index] += 1
        
        # Update counts for existing tokens
        for token in unique_new & set(base_state.vocabulary.keys()):
            base_state.vocabulary[token].last_seen_frame = self._current_frame_id
        
        # Recompute entropy
        counts = base_state.root_distribution
        probs = counts[counts > 0] / counts.sum() if counts.sum() > 0 else np.array([1.0])
        base_state.entropy = -np.sum(probs * np.log2(probs + 1e-10))
        
        self._frame_states.append(base_state)
        if len(self._frame_states) > self.max_frames:
            self._frame_states.pop(0)
        
        stats = {
            'frame_id': self._current_frame_id,
            'parent_frame': parent_frame_id,
            'inherited_tokens': len(unique_new) - len(defects),
            'new_defects': len(defects),
            'total_vocabulary': len(base_state.vocabulary),
            'entropy': base_state.entropy,
        }
        
        return base_state.vocabulary, stats
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics."""
        total = self._cache_hits + self._cache_misses
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': self._cache_hits / total if total > 0 else 0,
            'global_cache_size': len(self._global_cache),
            'frame_count': len(self._frame_states),
        }
    
    def clear(self):
        """Clear all cached state."""
        self._frame_states = []
        self._global_cache = {}
        self._current_frame_id = 0
        self._cache_hits = 0
        self._cache_misses = 0


def run_verification():
    """Verify the geometric inheritance functionality."""
    import time
    
    print("=" * 60)
    print("GEOMETRIC INHERITANCE VERIFICATION")
    print("=" * 60)
    
    cache = GeometricCache()
    
    # Test 1: Basic token geometry
    print("\n--- Test 1: Token Geometry ---")
    tokens = ["King", "Queen", "Royal", "Castle"]
    for token in tokens:
        geom = cache.get_token_geometry(token)
        print(f"  {token}: root={geom.root_index}, phase={geom.delta_phase:.3f}")
    
    # Test 2: Cache behavior
    print("\n--- Test 2: Cache Behavior ---")
    # Request same tokens again
    for token in tokens:
        _ = cache.get_token_geometry(token)
    
    stats = cache.get_cache_stats()
    print(f"  Hits: {stats['cache_hits']}, Misses: {stats['cache_misses']}")
    print(f"  Hit rate: {stats['hit_rate']:.1%}")
    
    # Test 3: Frame processing
    print("\n--- Test 3: Frame Processing ---")
    frame1_tokens = ["The", "quick", "brown", "fox", "jumps"]
    frame2_tokens = ["The", "lazy", "dog", "sleeps"]
    frame3_tokens = ["The", "quick", "dog", "runs"]
    
    _, stats1 = cache.process_frame(frame1_tokens)
    print(f"  Frame 1: {stats1['unique_tokens']} unique, {stats1['new_tokens']} new")
    
    _, stats2 = cache.process_frame(frame2_tokens)
    print(f"  Frame 2: {stats2['unique_tokens']} unique, {stats2['new_tokens']} new")
    
    _, stats3 = cache.process_frame(frame3_tokens)
    print(f"  Frame 3: {stats3['unique_tokens']} unique, {stats3['new_tokens']} new")
    
    # Test 4: Large-scale performance
    print("\n--- Test 4: Large-Scale Performance ---")
    cache.clear()
    
    # Simulate processing 100 frames of 1000 tokens each
    np.random.seed(42)
    vocab_pool = [f"word_{i}" for i in range(5000)]
    
    start = time.time()
    for frame_id in range(100):
        # Each frame has some overlap with previous
        frame_tokens = np.random.choice(vocab_pool, 1000)
        _, _ = cache.process_frame(list(frame_tokens))
    
    elapsed = time.time() - start
    stats = cache.get_cache_stats()
    
    print(f"  100 frames processed in {elapsed*1000:.1f}ms")
    print(f"  Final cache size: {stats['global_cache_size']}")
    print(f"  Overall hit rate: {stats['hit_rate']:.1%}")
    
    # Test 5: Inheritance mode
    print("\n--- Test 5: Inheritance Mode ---")
    cache.clear()
    
    # Process first frame fully
    _, _ = cache.process_frame(["The", "quick", "brown", "fox"])
    
    # Inherit from first frame
    _, inherit_stats = cache.inherit_and_update(
        ["The", "quick", "lazy", "dog"],
        parent_frame_id=0
    )
    
    print(f"  Inherited tokens: {inherit_stats['inherited_tokens']}")
    print(f"  New defects: {inherit_stats['new_defects']}")
    print(f"  Total vocabulary: {inherit_stats['total_vocabulary']}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
