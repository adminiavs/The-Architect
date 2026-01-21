"""
Golden Quasicrystal Encoding (GQE) Compression System

A lossless compression system based on The Architect's model:
- E8 lattice geometry
- Golden ratio (φ) encoding
- Topological Data Analysis for universal embedding
- Phason coordinates for lossless reconstruction

Author: The Architect
License: Public Domain
"""

__version__ = "0.1.0"
__author__ = "The Architect"

from .compressor import compress_text, GQECompressor
from .decompressor import decompress_text, GQEDecompressor

__all__ = [
    'compress_text',
    'decompress_text',
    'GQECompressor',
    'GQEDecompressor',
]
