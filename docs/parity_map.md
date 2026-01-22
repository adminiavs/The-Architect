# GQE Parity Map: Python to C++

This document maps the original Python prototype modules to the new SIMD-optimized C++20 implementation.

| Python File (gqe_compression/core/) | C++ Header (include/gqe/) | Parity Status | Key Functions |
|:--- |:--- |:--- |:--- |
| `types.py` | `types.hpp` | ✅ Complete | `Spinor8D`, `Vector4D`, `Vector8D` |
| `constants.py` | `constants.hpp` | ✅ Complete | `PHI`, `HORIZON_FRAME_SIZE` |
| `e8_lattice.py` | `e8_lattice.hpp` | ✅ Complete | `E8Lattice::roots` |
| `projection.py` | `projection.hpp` | ✅ Complete | `CoxeterProjection::project_with_phason`, `inverse_projection_with_phason` |
| `horizon_batcher.py` | `chunker.hpp` | ✅ Complete | `GrainAwareChunker::chunk_data` |
| `context_mixer.py` | `context_mixer.hpp` | 🟡 Partial | `GeometricParallelMixer::predict_batch`, `train` |
| `bit_packer.py` / `rac.py` | `circular_rac.hpp` | 🟡 Partial | `CircularRAC::encode` |
| `geometric_evolver.py` | `geometric_evolver.hpp` | 🧪 Skeleton | `GeometricEvolver::evolve` |
| `toric_error_correction.py` | `toric_error_correction.hpp` | 🧪 Skeleton | `ToricErrorCorrection::verify` |
| `holographic_encoding.py` | `holographic_encoding.hpp` | 🧪 Skeleton | `HolographicEncoding::encode` |
| `spectral_action.py` | `spectral_action.hpp` | 🧪 Skeleton | `SpectralAction::calculate_density` |
| `sleep_cycle.py` | `sleep_cycle.hpp` | 🧪 Skeleton | `SleepCycle::refresh` |

## Parity Definitions
- ✅ **Complete**: Functionality matches Python behavior exactly, including SIMD optimizations.
- 🟡 **Partial**: Core logic implemented, but some advanced features (e.g., adaptive weighting) are pending.
- 🧪 **Skeleton**: Architecture defined, interfaces mapped, but internal logic is a placeholder.

## Verification
Run the C++ test suite to verify parity:
```bash
g++ -std=c++20 -O3 -march=native tests/test_suite.cpp -o tests/test_suite && ./tests/test_suite
```
