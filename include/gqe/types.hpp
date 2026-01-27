#pragma once

#include <array>
#include <cmath>
#include <numeric>

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

    Spinor8D() : phase(0.0f), amplitude(1.0f) {
        std::fill(pos, pos + 8, 0.0f);
    }

    Spinor8D(const std::array<float, 8>& p, float ph = 0.0f, float amp = 1.0f) 
        : phase(ph), amplitude(amp) {
        std::copy(p.begin(), p.end(), pos);
    }

    float norm() const {
        float sum_sq = 0.0f;
        for (int i = 0; i < 8; ++i) sum_sq += pos[i] * pos[i];
        return std::sqrt(sum_sq);
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
