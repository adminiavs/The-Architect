"""
Core mathematical modules for GQE Compression.

Modules:
- phi_adic: Golden ratio number system (Proof 02)
- e8_lattice: Spinor operations on E8 lattice (Concept 03, Lexicon)
- projection: Bulk→Brane projection with Phason (Concept 04)
- quasicrystal: Aperiodic tiling detection (Concept 03)
- spectral_action: Compression via spectral encoding (Mech 02)
- tda: Topological Data Analysis for universal embedding
"""

from .phi_adic import encode_phi, decode_phi, PHI, PHI_INV
from .e8_lattice import Spinor, generate_e8_roots, spinor_distance
from .projection import coxeter_projection_8d_to_4d, inverse_projection_with_phason
from .quasicrystal import compute_power_spectrum, detect_phi_peaks, compute_aperiodicity_score
from .tda import build_cooccurrence_graph, embed_token_to_spinor

__all__ = [
    # Constants
    'PHI', 'PHI_INV',
    # phi_adic
    'encode_phi', 'decode_phi',
    # e8_lattice
    'Spinor', 'generate_e8_roots', 'spinor_distance',
    # projection
    'coxeter_projection_8d_to_4d', 'inverse_projection_with_phason',
    # quasicrystal
    'compute_power_spectrum', 'detect_phi_peaks', 'compute_aperiodicity_score',
    # tda
    'build_cooccurrence_graph', 'embed_token_to_spinor',
]
