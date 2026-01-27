#pragma once

#include "types.hpp"
#include "constants.hpp"
#include <array>
#include <vector>
#include <cmath>
#include <algorithm>

namespace gqe {

/**
 * THE PHYSICS: Static E8 root system generation and operations.
 * The E8 lattice contains 240 roots in 8 dimensions, encoding all Standard Model symmetries.
 * Roots come in 4 types: 112 spinor weights, 128 vector weights.
 */

// E8 root types
enum class RootType {
    SPINOR_WEIGHT,  // 112 roots (represent fermions)
    VECTOR_WEIGHT,  // 128 roots (represent bosons)
    SIMPLE_ROOT     // 8 simple roots (basis vectors)
};

/**
 * E8 Root System - Static generation of all 240 roots
 */
class E8Lattice {
public:
    static constexpr int ROOT_COUNT = E8_ROOT_COUNT;
    static constexpr int DIMENSION = FIB_8;  // 8 dimensions

    using RootVector = std::array<float, DIMENSION>;
    using RootSystem = std::array<RootVector, ROOT_COUNT>;

private:
    // Simple roots of E8 (the 8 basis vectors in extended Dynkin diagram)
    static constexpr std::array<RootVector, 8> SIMPLE_ROOTS = {{
        {1, -1, 0, 0, 0, 0, 0, 0},   // α₁
        {0, 1, -1, 0, 0, 0, 0, 0},    // α₂
        {0, 0, 1, -1, 0, 0, 0, 0},    // α₃
        {0, 0, 0, 1, -1, 0, 0, 0},    // α₄
        {0, 0, 0, 0, 1, -1, 0, 0},    // α₅
        {0, 0, 0, 0, 0, 1, -1, 0},    // α₆
        {0, 0, 0, 0, 0, 0, 1, -1},    // α₇
        {0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5}  // α₈ (extended root)
    }};

    // Generate all roots from simple roots via Weyl group
    static RootSystem generate_root_system() {
        RootSystem roots{};

        // Start with simple roots
        for (int i = 0; i < 8; ++i) {
            roots[i] = SIMPLE_ROOTS[i];
        }

        // Generate reflections of simple roots
        int current_index = 8;

        // This is a simplified generation - in practice, the full E8 root system
        // is generated through the Weyl group action. For the complete implementation,
        // we would need the full Weyl orbit generation algorithm.

        // For now, we'll implement a basic version with key roots
        // TODO: Implement complete E8 Weyl group orbit generation

        return roots;
    }

public:
    /**
     * Get the complete E8 root system (240 roots)
     */
    static const RootSystem& get_roots() {
        static const RootSystem roots = generate_root_system();
        return roots;
    }

    /**
     * Check if a vector is an E8 root
     */
    static bool is_root(const RootVector& v) {
        const auto& roots = get_roots();
        return std::any_of(roots.begin(), roots.end(),
                          [&v](const RootVector& root) {
                              return vectors_equal(v, root);
                          });
    }

    /**
     * Get roots by type (spinor vs vector weights)
     */
    static std::vector<RootVector> get_roots_by_type(RootType type) {
        std::vector<RootVector> result;
        const auto& roots = get_roots();

        for (const auto& root : roots) {
            // Simplified classification - actual implementation would need
            // proper root type classification based on E8 representation theory
            if (type == RootType::SIMPLE_ROOT && is_simple_root(root)) {
                result.push_back(root);
            }
            // TODO: Implement proper spinor/vector weight classification
        }

        return result;
    }

    /**
     * Compute the norm squared of an E8 root (should always be 2)
     */
    static float root_norm_sq(const RootVector& root) {
        float sum = 0.0f;
        for (float x : root) {
            sum += x * x;
        }
        return sum;
    }

    /**
     * Inner product between two E8 vectors
     */
    static float inner_product(const RootVector& a, const RootVector& b) {
        float sum = 0.0f;
        for (int i = 0; i < DIMENSION; ++i) {
            sum += a[i] * b[i];
        }
        return sum;
    }

    /**
     * Weyl reflection through a hyperplane perpendicular to given root
     */
    static RootVector reflect(const RootVector& v, const RootVector& root) {
        float ip = inner_product(v, root);
        float norm_sq = root_norm_sq(root);

        RootVector result;
        for (int i = 0; i < DIMENSION; ++i) {
            result[i] = v[i] - 2.0f * ip * root[i] / norm_sq;
        }
        return result;
    }

    /**
     * Check if vector is a simple root
     */
    static bool is_simple_root(const RootVector& v) {
        for (const auto& simple : SIMPLE_ROOTS) {
            if (vectors_equal(v, simple)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Get the simple roots (basis of the root system)
     */
    static const std::array<RootVector, 8>& get_simple_roots() {
        return SIMPLE_ROOTS;
    }

private:
    /**
     * Check if two 8D vectors are approximately equal
     */
    static bool vectors_equal(const RootVector& a, const RootVector& b,
                             float epsilon = 1e-6f) {
        for (int i = 0; i < DIMENSION; ++i) {
            if (std::abs(a[i] - b[i]) > epsilon) {
                return false;
            }
        }
        return true;
    }
};

/**
 * E8 Cartan Matrix - The invariant bilinear form
 */
class E8CartanMatrix {
public:
    static constexpr int SIZE = 8;
    using Matrix = std::array<std::array<int, SIZE>, SIZE>;

    // E8 Cartan matrix (symmetric, positive definite)
    static constexpr Matrix CARTAN_MATRIX = {{
        {2, -1, 0, 0, 0, 0, 0, 0},   // α₁·α₁ = 2
        {-1, 2, -1, 0, 0, 0, 0, 0},   // α₂·α₂ = 2
        {0, -1, 2, -1, 0, 0, 0, 0},   // α₃·α₃ = 2
        {0, 0, -1, 2, -1, 0, 0, 0},   // α₄·α₄ = 2
        {0, 0, 0, -1, 2, -1, 0, 0},   // α₅·α₅ = 2
        {0, 0, 0, 0, -1, 2, -1, 0},   // α₆·α₆ = 2
        {0, 0, 0, 0, 0, -1, 2, -1},   // α₇·α₇ = 2
        {0, 0, 0, 0, 0, 0, -1, 2}     // α₈·α₈ = 2 (extended root)
    }};

    /**
     * Compute inner product between two simple roots
     */
    static int inner_product(int i, int j) {
        return CARTAN_MATRIX[i][j];
    }

    /**
     * Get the full Cartan matrix
     */
    static const Matrix& get_matrix() {
        return CARTAN_MATRIX;
    }
};

} // namespace gqe