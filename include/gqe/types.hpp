#pragma once

#include <array>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <immintrin.h>

namespace gqe {

/**
 * THE PHYSICS: Norm calculation and geometric operations in the E8 Lattice.
 */
struct Vector8D {
    std::array<float, 8> data;

    float norm() const {
        float sum = 0;
        for (float x : data) sum += x * x;
        return std::sqrt(sum);
    }

    Vector8D operator+(const Vector8D& other) const {
        Vector8D res;
        for (int i = 0; i < 8; ++i) res.data[i] = data[i] + other.data[i];
        return res;
    }

    float dot(const Vector8D& other) const {
        float res = 0;
        for (int i = 0; i < 8; ++i) res = std::fma(data[i], other.data[i], res);
        return res;
    }
};

/**
 * THE PHYSICS: This maps one "Bit of Spacetime" to one 256-bit AVX Register.
 */
struct alignas(32) Spinor8D {
    float pos[8];      // The E8 Root Coordinates
    float phase;       // The Internal Twist
    float amplitude;   // Information Intensity

    // Default constructor
    constexpr Spinor8D() : pos{}, phase(0.0f), amplitude(1.0f) {}

    // Constructor from array
    constexpr Spinor8D(const std::array<float, 8>& p, float ph = 0.0f, float amp = 1.0f)
        : phase(ph), amplitude(amp) {
        std::copy(p.begin(), p.end(), pos);
    }

    // SIMD-optimized operations
    inline __m256 get_pos_simd() const {
        return _mm256_load_ps(pos);
    }

    inline void set_pos_simd(__m256 v) {
        _mm256_store_ps(pos, v);
    }

    // Euclidean norm (SIMD accelerated)
    inline float norm() const {
        __m256 v = get_pos_simd();
        __m256 sq = _mm256_mul_ps(v, v);
        // Horizontal add
        __m128 hi = _mm256_extractf128_ps(sq, 1);
        __m128 lo = _mm256_castps256_ps128(sq);
        __m128 sum = _mm_add_ps(lo, hi);
        sum = _mm_hadd_ps(sum, sum);
        sum = _mm_hadd_ps(sum, sum);
        return std::sqrt(_mm_cvtss_f32(sum));
    }

    // Euclidean distance in position space
    inline float distance_to(const Spinor8D& other) const {
        __m256 v1 = get_pos_simd();
        __m256 v2 = other.get_pos_simd();
        __m256 diff = _mm256_sub_ps(v1, v2);
        __m256 sq = _mm256_mul_ps(diff, diff);
        __m128 hi = _mm256_extractf128_ps(sq, 1);
        __m128 lo = _mm256_castps256_ps128(sq);
        __m128 sum = _mm_add_ps(lo, hi);
        sum = _mm_hadd_ps(sum, sum);
        sum = _mm_hadd_ps(sum, sum);
        float euclidean_sq = _mm_cvtss_f32(sum);

        // Phase difference (normalized to [-PI, PI])
        float phase_diff = phase - other.phase;
        while (phase_diff > std::numbers::pi_v<float>) phase_diff -= 2.0f * std::numbers::pi_v<float>;
        while (phase_diff < -std::numbers::pi_v<float>) phase_diff += 2.0f * std::numbers::pi_v<float>;
        float phase_comp = std::abs(phase_diff) / std::numbers::pi_v<float>;

        // Combined distance: sqrt(dist_sq + phase_comp_sq)
        return std::sqrt(euclidean_sq + phase_comp * phase_comp);
    }

    // Compute interference factor in [-1, +1]
    inline float compute_interference(const Spinor8D& other) const {
        return std::cos(phase - other.phase);
    }

    // Normalize (SIMD accelerated)
    inline Spinor8D& normalize() {
        float n = norm();
        if (n > 0.0f) {
            __m256 v = get_pos_simd();
            __m256 inv_n = _mm256_set1_ps(1.0f / n);
            set_pos_simd(_mm256_mul_ps(v, inv_n));
        }
        return *this;
    }
};

/**
 * Vector4D for 4D projections.
 */
struct alignas(16) Vector4D {
    float coords[4];
    constexpr Vector4D() : coords{0, 0, 0, 0} {}
    constexpr Vector4D(float x, float y, float z, float w) : coords{x, y, z, w} {}
};

} // namespace gqe
