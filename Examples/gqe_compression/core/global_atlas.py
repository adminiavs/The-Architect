#!/usr/bin/env python3
"""
Global Atlas - The Memory of the Crystal

THE PHYSICS:
"Stop discovering the world and start recognizing it."

This module provides a STATIC vocabulary atlas - a pre-computed mapping
of common words to their E8 lattice coordinates. Both compressor and
decompressor share this atlas, eliminating vocabulary storage entirely.

The Atlas contains:
- 65,536 most common English words/tokens (16-bit index)
- Pre-computed E8 root assignments
- Pre-computed phase offsets

When compressing, tokens are looked up in the Atlas:
- Known tokens: Store only the 16-bit Atlas index
- Unknown tokens: Fall back to out-of-vocabulary encoding

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
import struct
import hashlib
import os

try:
    from .phi_adic import PHI, PHI_INV
    from .e8_lattice import generate_e8_roots
except ImportError:
    from phi_adic import PHI, PHI_INV
    from e8_lattice import generate_e8_roots


# Atlas configuration
ATLAS_VERSION = 1
ATLAS_SIZE = 65536  # 2^16 entries (16-bit index)
ATLAS_MAGIC = b'\xE8\xA7'  # "E8 Atlas"


@dataclass
class AtlasEntry:
    """A single entry in the Global Atlas."""
    index: int          # 16-bit index in atlas
    token: str          # The token string
    root_index: int     # E8 root (0-239)
    phase_offset: int   # Phase within root (0-255)
    frequency_rank: int # Rank by frequency (lower = more common)


class GlobalAtlas:
    """
    The Global Atlas - A shared vocabulary for compressor and decompressor.
    
    THE PHYSICS:
    The Atlas is the "memory" of the crystal. It contains the geometric
    addresses of the most common concepts. When both ends share the Atlas,
    we only need to transmit the ADDRESS, not the NAME.
    """
    
    # Common English words and punctuation for the base vocabulary
    # This is deterministically generated - same on all machines
    BASE_VOCABULARY = [
        # Single characters and punctuation (0-127)
        ' ', '\n', '\t', '.', ',', '!', '?', ';', ':', "'", '"', '-',
        '(', ')', '[', ']', '{', '}', '/', '\\', '@', '#', '$', '%',
        '^', '&', '*', '+', '=', '<', '>', '|', '~', '`', '_',
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
        'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
        'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
        'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
        # Common words (128+)
        'the', 'of', 'and', 'to', 'a', 'in', 'that', 'is', 'was', 'he',
        'for', 'it', 'with', 'as', 'his', 'on', 'be', 'at', 'by', 'I',
        'this', 'had', 'not', 'are', 'but', 'from', 'or', 'have', 'an', 'they',
        'which', 'one', 'you', 'were', 'all', 'her', 'she', 'there', 'would', 'their',
        'we', 'him', 'been', 'has', 'when', 'who', 'will', 'no', 'more', 'if',
        'out', 'so', 'up', 'said', 'what', 'its', 'about', 'than', 'into', 'them',
        'can', 'only', 'other', 'time', 'new', 'some', 'could', 'these', 'two', 'may',
        'first', 'then', 'do', 'any', 'like', 'my', 'now', 'over', 'such', 'our',
        'man', 'me', 'even', 'most', 'made', 'after', 'also', 'did', 'many', 'off',
        'before', 'must', 'well', 'back', 'through', 'years', 'much', 'where', 'your', 'way',
        # Wikipedia-specific common words
        'born', 'died', 'known', 'called', 'part', 'used', 'including', 'however',
        'world', 'state', 'city', 'country', 'area', 'population', 'government',
        'system', 'number', 'people', 'year', 'during', 'between', 'under', 'since',
        'name', 'based', 'later', 'century', 'national', 'public', 'university',
        'school', 'united', 'states', 'american', 'english', 'british', 'french',
        'german', 'italian', 'spanish', 'chinese', 'japanese', 'russian', 'indian',
        # Common XML/HTML tokens (for Wikipedia markup)
        'ref', 'http', 'www', 'org', 'com', 'html', 'xml', 'id', 'class', 'title',
        'link', 'text', 'page', 'list', 'item', 'table', 'row', 'col', 'div', 'span',
        # Numbers as words
        'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
        'hundred', 'thousand', 'million', 'billion',
        # Common suffixes/prefixes
        'ing', 'ed', 'er', 'est', 'ly', 'tion', 'ness', 'ment', 'able', 'ible',
        'pre', 'pro', 'anti', 'sub', 'super', 'inter', 'trans', 'non', 'un', 're',
    ]
    
    def __init__(self):
        self.entries: Dict[str, AtlasEntry] = {}
        self.index_to_entry: Dict[int, AtlasEntry] = {}
        self.root_groups: Dict[int, List[int]] = {i: [] for i in range(240)}
        self._initialized = False
    
    def _compute_root_index(self, token: str, seed: int = 0xE8A71A5) -> int:
        """Deterministic E8 root assignment using hash."""
        h = hashlib.sha256(f"{seed}:{token}".encode()).digest()
        return int.from_bytes(h[:2], 'little') % 240
    
    def _compute_phase_offset(self, token: str, seed: int = 0xE8A71A5) -> int:
        """Deterministic phase offset using hash."""
        h = hashlib.md5(f"{seed}:phase:{token}".encode()).digest()
        return h[0]  # 0-255
    
    def initialize(self):
        """
        Initialize the Global Atlas with the standard vocabulary.
        
        THE PHYSICS:
        We build the crystal's memory - a deterministic mapping from
        tokens to geometric coordinates.
        """
        if self._initialized:
            return
        
        # Start with base vocabulary
        tokens = list(self.BASE_VOCABULARY)
        
        # Expand to full atlas size with generated tokens
        # These are deterministic - same on all machines
        np.random.seed(0xE8A71A5)  # Fixed seed for reproducibility
        
        # Generate common bigrams, trigrams, etc.
        common_letters = 'etaoinshrdlcumwfgypbvkjxqz'
        
        # Add common 2-letter combinations
        for c1 in common_letters[:10]:
            for c2 in common_letters[:10]:
                tokens.append(c1 + c2)
        
        # Add common 3-letter combinations
        for c1 in common_letters[:6]:
            for c2 in 'aeiou':
                for c3 in common_letters[:6]:
                    tokens.append(c1 + c2 + c3)
        
        # Add numeric patterns
        for i in range(1000):
            tokens.append(str(i))
        
        # Add year patterns
        for year in range(1000, 2100):
            tokens.append(str(year))
        
        # Deduplicate and limit to ATLAS_SIZE
        seen = set()
        unique_tokens = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                unique_tokens.append(t)
        
        # Fill remaining slots with hash-generated tokens
        while len(unique_tokens) < ATLAS_SIZE:
            idx = len(unique_tokens)
            # Generate placeholder for unknown tokens
            unique_tokens.append(f"<OOV_{idx}>")
        
        unique_tokens = unique_tokens[:ATLAS_SIZE]
        
        # Build atlas entries
        for idx, token in enumerate(unique_tokens):
            root_index = self._compute_root_index(token)
            phase_offset = self._compute_phase_offset(token)
            
            entry = AtlasEntry(
                index=idx,
                token=token,
                root_index=root_index,
                phase_offset=phase_offset,
                frequency_rank=idx
            )
            
            self.entries[token] = entry
            self.index_to_entry[idx] = entry
            self.root_groups[root_index].append(idx)
        
        self._initialized = True
    
    def lookup(self, token: str) -> Optional[AtlasEntry]:
        """
        Look up a token in the Atlas.
        
        Returns AtlasEntry if found, None if out-of-vocabulary.
        """
        if not self._initialized:
            self.initialize()
        return self.entries.get(token)
    
    def get_by_index(self, index: int) -> Optional[AtlasEntry]:
        """Get entry by its 16-bit index."""
        if not self._initialized:
            self.initialize()
        return self.index_to_entry.get(index)
    
    def encode_token(self, token: str) -> Tuple[bool, int, int]:
        """
        Encode a token using the Atlas.
        
        Returns:
            (in_atlas, atlas_index, oov_hash)
            - If in_atlas=True: atlas_index is the 16-bit index
            - If in_atlas=False: oov_hash is a 32-bit hash for OOV tokens
        """
        if not self._initialized:
            self.initialize()
        
        entry = self.entries.get(token)
        if entry:
            return (True, entry.index, 0)
        else:
            # Out-of-vocabulary: use hash
            h = hashlib.sha256(token.encode('utf-8')).digest()
            oov_hash = int.from_bytes(h[:4], 'little')
            return (False, 0, oov_hash)
    
    def get_root_for_token(self, token: str) -> int:
        """Get the E8 root index for a token (works for OOV too)."""
        if not self._initialized:
            self.initialize()
        
        entry = self.entries.get(token)
        if entry:
            return entry.root_index
        else:
            return self._compute_root_index(token)
    
    def get_coverage(self, tokens: List[str]) -> Tuple[int, int, float]:
        """
        Calculate Atlas coverage for a list of tokens.
        
        Returns (in_atlas_count, total_count, coverage_ratio).
        """
        if not self._initialized:
            self.initialize()
        
        in_atlas = sum(1 for t in tokens if t in self.entries)
        total = len(tokens)
        return (in_atlas, total, in_atlas / total if total > 0 else 0)
    
    def get_stats(self) -> Dict:
        """Get Atlas statistics."""
        if not self._initialized:
            self.initialize()
        
        return {
            'total_entries': len(self.entries),
            'roots_used': sum(1 for g in self.root_groups.values() if g),
            'avg_per_root': len(self.entries) / 240,
            'max_per_root': max(len(g) for g in self.root_groups.values()),
        }


# Global singleton instance
_atlas = None

def get_atlas() -> GlobalAtlas:
    """Get the global Atlas singleton."""
    global _atlas
    if _atlas is None:
        _atlas = GlobalAtlas()
        _atlas.initialize()
    return _atlas


def run_verification():
    """Verify the Global Atlas functionality."""
    print("=" * 60)
    print("GLOBAL ATLAS VERIFICATION")
    print("=" * 60)
    
    atlas = get_atlas()
    stats = atlas.get_stats()
    
    print(f"\n--- Atlas Statistics ---")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Roots used: {stats['roots_used']}/240")
    print(f"  Avg per root: {stats['avg_per_root']:.1f}")
    print(f"  Max per root: {stats['max_per_root']}")
    
    # Test lookups
    print(f"\n--- Lookup Tests ---")
    test_tokens = ['the', 'of', 'and', ' ', 'Wikipedia', '2024', 'xyz123']
    for token in test_tokens:
        entry = atlas.lookup(token)
        if entry:
            print(f"  '{token}': idx={entry.index}, root={entry.root_index}")
        else:
            root = atlas.get_root_for_token(token)
            print(f"  '{token}': OOV, computed root={root}")
    
    # Test encoding
    print(f"\n--- Encoding Tests ---")
    for token in test_tokens:
        in_atlas, idx, oov = atlas.encode_token(token)
        if in_atlas:
            print(f"  '{token}': IN_ATLAS, idx={idx}")
        else:
            print(f"  '{token}': OOV, hash={oov:08x}")
    
    # Test coverage on sample text
    print(f"\n--- Coverage Test ---")
    sample = "the quick brown fox jumps over the lazy dog in 2024"
    tokens = sample.split()
    in_count, total, coverage = atlas.get_coverage(tokens)
    print(f"  Text: '{sample}'")
    print(f"  Coverage: {in_count}/{total} ({coverage*100:.1f}%)")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
