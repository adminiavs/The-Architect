#!/usr/bin/env python3
"""
Adaptive Horizon - Dynamic Batching Based on Local Entropy

THE PHYSICS:
"The Shutter Control" - The window size adapts to the information density.

- Low Entropy (predictable): Expand horizon to 1MB+ (fewer frame headers)
- High Entropy (chaotic): Shrink horizon to 64KB (more frequent resets)

This minimizes overhead by using large frames for repetitive content
and small frames for complex content.

Key Concepts:
- Entropy Estimation: Sliding window character/token frequency analysis
- Fibonacci Sizing: Horizon sizes follow Fibonacci sequence for golden scaling
- Smooth Transitions: Gradual horizon changes to avoid boundary artifacts

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import List, Tuple, Iterator, Optional
from dataclasses import dataclass
from collections import Counter
import math

try:
    from .phi_adic import PHI, PHI_INV
except ImportError:
    from phi_adic import PHI, PHI_INV


# Fibonacci-based horizon sizes (in bytes)
HORIZON_SIZES = [
    8 * 1024,      # 8KB - Minimum (high entropy)
    13 * 1024,     # 13KB
    21 * 1024,     # 21KB
    34 * 1024,     # 34KB
    55 * 1024,     # 55KB
    89 * 1024,     # 89KB
    144 * 1024,    # 144KB
    233 * 1024,    # 233KB - Default
    377 * 1024,   # 377KB
    610 * 1024,    # 610KB
    987 * 1024,    # 987KB
    1597 * 1024,   # 1.56MB - Maximum (low entropy)
]


@dataclass
class HorizonFrame:
    """
    A single frame with adaptive size.
    
    Attributes:
        data: The chunk of data
        start_offset: Position in original data
        entropy_score: Local entropy (0-1, higher = more complex)
        horizon_size: Size of this frame in bytes
    """
    data: str
    start_offset: int
    entropy_score: float
    horizon_size: int
    
    @property
    def end_offset(self) -> int:
        return self.start_offset + len(self.data)


class EntropyEstimator:
    """
    Estimates local entropy of text using character frequency analysis.
    
    THE PHYSICS:
    High entropy = Many unique characters, unpredictable
    Low entropy = Few unique characters, repetitive patterns
    """
    
    def __init__(self, window_size: int = 4096):
        self.window_size = window_size
    
    def estimate(self, text: str) -> float:
        """
        Estimate Shannon entropy of text.
        
        Returns value in [0, 1] where:
        0 = Completely predictable (single character repeated)
        1 = Maximum entropy (uniform distribution)
        """
        if not text:
            return 0.0
        
        # Character frequency
        freq = Counter(text)
        total = len(text)
        
        # Shannon entropy
        entropy = 0.0
        for count in freq.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        
        # Normalize to [0, 1] (max entropy for ASCII is ~7 bits)
        max_entropy = math.log2(min(len(freq), 256))
        if max_entropy > 0:
            normalized = entropy / max_entropy
        else:
            normalized = 0.0
        
        return min(1.0, normalized)
    
    def estimate_sliding(self, text: str, position: int) -> float:
        """
        Estimate entropy in a sliding window around position.
        """
        start = max(0, position - self.window_size // 2)
        end = min(len(text), position + self.window_size // 2)
        return self.estimate(text[start:end])


class AdaptiveHorizon:
    """
    Dynamically adjusts horizon (chunk) size based on local entropy.
    
    THE PHYSICS:
    The horizon is like a "shutter" on a camera.
    - Fast shutter (small horizon) for fast-moving (high entropy) content
    - Slow shutter (large horizon) for static (low entropy) content
    
    ADAPTIVE SHUTTER:
    Checks entropy every 10KB. If the score is stable, doubles the chunk size.
    This reduces "Geometric Re-alignments" (overhead) and makes the
    "Phason Stream" more continuous.
    """
    
    # Check entropy stability every 10KB
    STABILITY_CHECK_INTERVAL = 10 * 1024
    # Threshold for considering entropy "stable"
    STABILITY_THRESHOLD = 0.1
    
    def __init__(self, 
                 min_size: int = 8 * 1024,
                 max_size: int = 1597 * 1024,
                 entropy_window: int = 4096,
                 smooth_factor: float = 0.3):
        """
        Initialize adaptive horizon.
        
        Args:
            min_size: Minimum horizon size (high entropy)
            max_size: Maximum horizon size (low entropy)
            entropy_window: Window size for entropy estimation
            smooth_factor: How quickly horizon size changes (0-1)
        """
        self.min_size = min_size
        self.max_size = max_size
        self.estimator = EntropyEstimator(entropy_window)
        self.smooth_factor = smooth_factor
        
        # Filter to valid Fibonacci sizes
        self.sizes = [s for s in HORIZON_SIZES if min_size <= s <= max_size]
        if not self.sizes:
            self.sizes = [min_size]
        
        # Track entropy history for stability detection
        self._entropy_history: List[float] = []
        self._stable_count = 0
    
    def _entropy_to_size(self, entropy: float) -> int:
        """
        Map entropy score to horizon size.
        
        High entropy -> Small horizon
        Low entropy -> Large horizon
        """
        # Invert: high entropy = small size
        size_index = int((1 - entropy) * (len(self.sizes) - 1))
        size_index = max(0, min(size_index, len(self.sizes) - 1))
        return self.sizes[size_index]
    
    def _smooth_transition(self, current_size: int, target_size: int) -> int:
        """
        Smooth transition between horizon sizes.
        
        Uses golden ratio for natural transitions.
        """
        # Find indices
        if current_size not in self.sizes:
            return target_size
        
        current_idx = self.sizes.index(current_size)
        target_idx = self.sizes.index(target_size) if target_size in self.sizes else current_idx
        
        # Move one step at a time (Fibonacci stepping)
        if target_idx > current_idx:
            new_idx = min(current_idx + 1, len(self.sizes) - 1)
        elif target_idx < current_idx:
            new_idx = max(current_idx - 1, 0)
        else:
            new_idx = current_idx
        
        return self.sizes[new_idx]
    
    def _is_entropy_stable(self, current_entropy: float) -> bool:
        """
        Check if entropy has been stable over recent history.
        
        THE PHYSICS:
        Stable entropy = predictable content = can use larger horizon.
        """
        self._entropy_history.append(current_entropy)
        
        # Keep only recent history
        if len(self._entropy_history) > 10:
            self._entropy_history.pop(0)
        
        if len(self._entropy_history) < 3:
            return False
        
        # Check variance in recent entropy
        recent = self._entropy_history[-3:]
        variance = max(recent) - min(recent)
        
        return variance < self.STABILITY_THRESHOLD
    
    def _double_size(self, current_size: int) -> int:
        """
        Double the horizon size (within bounds).
        
        THE PHYSICS:
        Stable content allows us to "open the shutter" wider,
        reducing frame overhead.
        """
        # Find current index
        if current_size not in self.sizes:
            return current_size
        
        idx = self.sizes.index(current_size)
        # Move to next Fibonacci size (approximately doubles)
        new_idx = min(idx + 2, len(self.sizes) - 1)
        return self.sizes[new_idx]
    
    def split(self, data: str) -> List[HorizonFrame]:
        """
        Split data into adaptive horizon frames with stability detection.
        
        THE PHYSICS:
        The data is divided according to its local "energy" (entropy).
        High-energy regions get small frames, low-energy get large frames.
        
        ADAPTIVE SHUTTER:
        Every 10KB, if entropy is stable, double the frame size.
        This creates a "continuous phason stream" for predictable content.
        """
        if not data:
            return []
        
        frames = []
        offset = 0
        current_size = self.sizes[len(self.sizes) // 2]  # Start with middle size
        last_stability_check = 0
        
        # Reset stability tracking
        self._entropy_history = []
        self._stable_count = 0
        
        while offset < len(data):
            # Estimate local entropy
            entropy = self.estimator.estimate_sliding(data, offset)
            
            # Check stability every 10KB
            if offset - last_stability_check >= self.STABILITY_CHECK_INTERVAL:
                if self._is_entropy_stable(entropy):
                    self._stable_count += 1
                    # After 2 consecutive stable checks, double the size
                    if self._stable_count >= 2:
                        current_size = self._double_size(current_size)
                        self._stable_count = 0
                else:
                    self._stable_count = 0
                    # Entropy changed - reset to base size
                    target_size = self._entropy_to_size(entropy)
                    current_size = self._smooth_transition(current_size, target_size)
                
                last_stability_check = offset
            else:
                # Normal entropy-based sizing
                target_size = self._entropy_to_size(entropy)
                current_size = self._smooth_transition(current_size, target_size)
            
            # Extract frame
            frame_end = min(offset + current_size, len(data))
            frame_data = data[offset:frame_end]
            
            frames.append(HorizonFrame(
                data=frame_data,
                start_offset=offset,
                entropy_score=entropy,
                horizon_size=current_size
            ))
            
            offset = frame_end
        
        return frames
    
    def iter_frames(self, data: str) -> Iterator[HorizonFrame]:
        """
        Iterate over frames without storing all in memory.
        
        Useful for very large files.
        """
        offset = 0
        current_size = self.sizes[len(self.sizes) // 2]
        
        while offset < len(data):
            entropy = self.estimator.estimate_sliding(data, offset)
            target_size = self._entropy_to_size(entropy)
            current_size = self._smooth_transition(current_size, target_size)
            
            frame_end = min(offset + current_size, len(data))
            frame_data = data[offset:frame_end]
            
            yield HorizonFrame(
                data=frame_data,
                start_offset=offset,
                entropy_score=entropy,
                horizon_size=current_size
            )
            
            offset = frame_end


def analyze_entropy_profile(data: str, num_samples: int = 100) -> List[Tuple[int, float]]:
    """
    Analyze entropy profile across a document.
    
    Returns list of (position, entropy) tuples.
    """
    estimator = EntropyEstimator(window_size=4096)
    step = max(1, len(data) // num_samples)
    
    profile = []
    for pos in range(0, len(data), step):
        entropy = estimator.estimate_sliding(data, pos)
        profile.append((pos, entropy))
    
    return profile


def run_verification():
    """Verify the adaptive horizon functionality."""
    print("=" * 60)
    print("ADAPTIVE HORIZON VERIFICATION")
    print("=" * 60)
    
    # Test 1: Entropy estimation
    print("\n--- Test 1: Entropy Estimation ---")
    estimator = EntropyEstimator()
    
    test_cases = [
        ("aaaaaaaaaa", "Single char repeated"),
        ("abcdefghij", "All unique chars"),
        ("the quick brown fox jumps over the lazy dog", "Natural text"),
        ("<xml><tag>value</tag></xml>", "XML markup"),
        ("01010101010101010101", "Binary pattern"),
    ]
    
    for text, desc in test_cases:
        entropy = estimator.estimate(text)
        print(f"  {desc}: entropy={entropy:.3f}")
    
    # Test 2: Entropy to size mapping
    print("\n--- Test 2: Entropy to Size Mapping ---")
    horizon = AdaptiveHorizon()
    
    for entropy in [0.0, 0.25, 0.5, 0.75, 1.0]:
        size = horizon._entropy_to_size(entropy)
        print(f"  Entropy {entropy:.2f} -> Size {size / 1024:.0f}KB")
    
    # Test 3: Adaptive splitting on synthetic data
    print("\n--- Test 3: Adaptive Splitting ---")
    
    # Create test data with varying entropy
    low_entropy = "the " * 10000  # Repetitive
    high_entropy = "".join(chr(32 + (i * 7) % 95) for i in range(10000))  # More random
    mixed = low_entropy + high_entropy + low_entropy
    
    frames = horizon.split(mixed)
    
    print(f"  Input size: {len(mixed)} bytes")
    print(f"  Number of frames: {len(frames)}")
    print(f"  Frame sizes:")
    
    size_counts = Counter(f.horizon_size for f in frames)
    for size, count in sorted(size_counts.items()):
        print(f"    {size / 1024:.0f}KB: {count} frames")
    
    # Test 4: Profile analysis
    print("\n--- Test 4: Entropy Profile ---")
    profile = analyze_entropy_profile(mixed, num_samples=10)
    
    for pos, entropy in profile:
        region = "LOW" if entropy < 0.5 else "HIGH"
        print(f"  Position {pos:6d}: entropy={entropy:.3f} [{region}]")
    
    # Test 5: Memory efficiency
    print("\n--- Test 5: Iterator Mode ---")
    frame_count = 0
    total_data = 0
    
    for frame in horizon.iter_frames(mixed):
        frame_count += 1
        total_data += len(frame.data)
    
    print(f"  Frames iterated: {frame_count}")
    print(f"  Total data: {total_data} bytes")
    print(f"  Match original: {'PASS' if total_data == len(mixed) else 'FAIL'}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
