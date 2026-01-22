#pragma once

#include "types.hpp"
#include "constants.hpp"
#include <array>

namespace gqe {

/**
 * THE PHYSICS: The "Hard Drive" of the universe is static.
 * By making it constexpr, you are baking the Platonic Object into the silicon itself.
 */
template<size_t N = E8_ROOTS>
struct E8Lattice {
private:
    // Generate E8 lattice roots at compile time (240 roots)
    static constexpr std::array<Spinor8D, N> generate_roots() {
        std::array<Spinor8D, N> roots{};
        size_t idx = 0;

        // Type I: (±1, ±1, 0, 0, 0, 0, 0, 0) and permutations (112 roots)
        for (int i = 0; i < 8; ++i) {
            for (int j = i + 1; j < 8; ++j) {
                for (float s1 : {1.0f, -1.0f}) {
                    for (float s2 : {1.0f, -1.0f}) {
                        if (idx < N) {
                            std::array<float, 8> v{};
                            v[i] = s1;
                            v[j] = s2;
                            roots[idx++] = Spinor8D(v);
                        }
                    }
                }
            }
        }

        // Type II: (±1/2, ..., ±1/2) with even number of minus signs (128 roots)
        for (int i = 0; i < 256; ++i) {
            std::array<float, 8> v{};
            int minus_count = 0;
            for (int j = 0; j < 8; ++j) {
                if ((i >> j) & 1) {
                    v[j] = -0.5f;
                    minus_count++;
                } else {
                    v[j] = 0.5f;
                }
            }
            if (minus_count % 2 == 0 && idx < N) {
                roots[idx++] = Spinor8D(v);
            }
        }

        return roots;
    }

public:
    static constexpr std::array<Spinor8D, N> roots = generate_roots();
};

} // namespace gqe
