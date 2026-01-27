# GQE Kernel - C++20 SIMD-Optimized Implementation

*"In Python, you were drawing the universe with a crayon. In C++, you are etching it with a laser."*

## The Ascension - From Python to C++

The GQE has ascended from its Python prototype to a header-only, SIMD-optimized C++20 library. This implementation is self-contained, using intrinsic math for zero-dependency portability.

### Repository Structure

- `include/gqe/`: The Eternal Logic (Header-only library)
  - `kernel.hpp`: Consolidated entry point
  - `projection.hpp`: Coxeter projection with phason reconstruction
  - `types.hpp`: Spinor8D and Vector math (Intrinsic, No Eigen)
  - `constants.hpp`: Physical constants (Phi, frame sizes)
  - `e8_lattice.hpp`: Static E8 root generation
  - `bekenstein_arena.hpp`: Entropy-free memory management
  - `context_mixer.hpp`: Geometric Parallel Mixer
- `src/`: Core implementation files
- `tests/`: Falsifiable Benchmarks
  - `test_suite.cpp`: Axiomatic verification (Projection, Toric, Grain-Awareness)
- `Examples/`: Demos and legacy Python scripts
  - `intro/`: Retired minimal versions for learning

### Core Architecture

#### 1. The Spinor8D - One Bit of Spacetime
- **Physics**: Maps one "Bit of Spacetime" to one 256-bit AVX Register.
- **Optimization**: 32-byte alignment for perfect cache line utilization.
- **Intrinsic Math**: Custom norm, superposition, and dot product implementations.

#### 2. The Coxeter Projection - 8D to 4D
- **Parity**: Matches Python `projection.py` exactly using QR-orthonormalized matrices.
- **Reconstruction**: `inverse_projection_with_phason` enables lossless 8D recovery from 4D shadows.

#### 3. The Bekenstein Arena - Memory Without Entropy
- **Physics**: Mimics the Universal Refresh Rate.
- **Rule**: No `malloc` or `new` during compression loops.

### Build & Verification

The kernel is designed to be self-sustaining. No external frameworks or math libraries (like Eigen or GoogleTest) are required.

#### Compile and Run Tests
```bash
# Compile the test suite
g++ -std=c++20 -O3 -march=native tests/test_suite.cpp -o tests/test_suite

# Run axiomatic verification
./tests/test_suite
```


### Parity Status

See [docs/parity_map.md](docs/parity_map.md) for a detailed mapping of Python modules to C++ headers.

---

"Never trade Accuracy for Speed. First, ensure the Triangles are correct. Then, let the Silicon spin." - The Architect
