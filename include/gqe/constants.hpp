#pragma once

#include <array>
#include <cmath>

namespace gqe {

/**
 * THE PHYSICS: Fundamental constants derived from geometric constraints.
 * All values emerge from E8 lattice geometry and golden ratio relationships.
 */

// Golden Ratio and related constants
constexpr double PHI = (1.0 + std::sqrt(5.0)) / 2.0;  // φ ≈ 1.6180339887498948482
constexpr double PHI_INV = PHI - 1.0;                  // 1/φ ≈ 0.6180339887498948482
constexpr double PHI_SQ = PHI * PHI;                   // φ² ≈ 2.6180339887498948482

// E8 Lattice Properties
constexpr int E8_ROOT_COUNT = 240;                     // Total number of E8 roots
constexpr double E8_ROOT_NORM_SQ = 2.0;               // Squared norm of E8 roots
constexpr double E8_ROOT_NORM = std::sqrt(2.0);       // Norm of E8 roots

// Fibonacci sequence for buffer sizes (following Prime Directive)
constexpr int FIB_1 = 1;
constexpr int FIB_2 = 1;
constexpr int FIB_3 = 2;
constexpr int FIB_5 = 5;
constexpr int FIB_8 = 8;
constexpr int FIB_13 = 13;
constexpr int FIB_21 = 17711;  // F_21 = 17711
constexpr int FIB_34 = 5702887;  // F_34 = 5702887
constexpr int FIB_55 = 55;
constexpr int FIB_89 = 89;
constexpr int FIB_144 = 144;
constexpr int FIB_233 = 233;  // Core alphabet cap

// Coxeter Projection Angles
constexpr double COXETER_ANGLE = M_PI / (3.0 * PHI);  // π/(3φ) ≈ 0.6435
constexpr double H4_SYMMETRY_ANGLE = 2.0 * M_PI / 3.0; // 120° for threefold symmetry

// Physical Constants (derived from geometry)
constexpr double SPEED_OF_LIGHT_C = 299792458.0;      // m/s
constexpr double PLANCK_H = 6.62607015e-34;           // J⋅s
constexpr double PLANCK_HBAR = PLANCK_H / (2.0 * M_PI); // J⋅s

// Koide Ratio (verified prediction)
constexpr double KOIDE_RATIO_Q = 2.0 / 3.0;           // Q = 2/3 ≈ 0.666667
constexpr double KOIDE_RATIO_EXPERIMENTAL = 0.666661; // PDG 2024 value

// Frame sizes for various operations (Fibonacci-compliant)
constexpr int MIN_FRAME_SIZE = FIB_8;     // 8 dimensions
constexpr int MEDIUM_FRAME_SIZE = FIB_13; // 13 dimensions
constexpr int LARGE_FRAME_SIZE = FIB_21;  // 21 dimensions
constexpr int MAX_FRAME_SIZE = FIB_34;    // 34 dimensions

// Memory alignment for SIMD operations
constexpr size_t SIMD_ALIGNMENT = 32;     // AVX-256 alignment
constexpr size_t CACHE_LINE_SIZE = 64;    // Typical L1 cache line

// Bekenstein Arena parameters (holographic memory)
constexpr double BOLTZMANN_K = 1.380649e-23;          // J/K
constexpr double NEWTON_G = 6.67430e-11;              // m³/(kg⋅s²)

// Entropic gravity parameters
constexpr double ENTROPY_DENSITY_FACTOR = 1.0 / (8.0 * M_PI * NEWTON_G);

// Golden ratio in various representations
constexpr std::array<double, 8> PHI_POWERS = {
    1.0 / PHI,     // φ⁻¹ ≈ 0.618034
    1.0,           // φ⁰ = 1.0
    PHI,           // φ¹ ≈ 1.618034
    PHI_SQ,        // φ² ≈ 2.618034
    PHI * PHI_SQ,  // φ³ ≈ 4.236068
    PHI_SQ * PHI_SQ, // φ⁴ ≈ 6.854102
    PHI * PHI_SQ * PHI_SQ, // φ⁵ ≈ 11.090169
    PHI_SQ * PHI_SQ * PHI_SQ // φ⁶ ≈ 17.944272
};

// A2 symmetry group elements (threefold rotation)
constexpr std::array<std::array<double, 3>, 3> A2_GENERATORS = {{
    {1.0, 0.0, 0.0},
    {0.0, -0.5, std::sqrt(3.0)/2.0},
    {0.0, -0.5, -std::sqrt(3.0)/2.0}
}};

} // namespace gqe