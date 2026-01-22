#pragma once

#include "types.hpp"
#include <vector>
#include <numeric>

namespace gqe {

/**
 * THE PHYSICS: The Non-Commutative Spectral Action.
 * S = Tr(f(D/Λ)).
 * Defines the energy density of the quasicrystal.
 */
class SpectralAction {
public:
    // Calculate spectral density (energy) of a spinor configuration
    static float calculate_density(const std::vector<Spinor8D>& spinors) {
        if (spinors.empty()) return 0.0f;

        float total_action = 0.0f;
        for (const auto& s : spinors) {
            total_action += s.amplitude * s.norm();
        }

        // Add interaction terms (simplified Dirac operator signature)
        float interaction = 0.0f;
        for (size_t i = 0; i < spinors.size(); ++i) {
            for (size_t j = i + 1; j < spinors.size(); ++j) {
                float dist = spinors[i].distance_to(spinors[j]);
                if (dist < 2.0f) {
                    interaction += 1.0f / (1.0f + dist);
                }
            }
        }

        return total_action + interaction;
    }

    static float calculate_single_density(const Spinor8D& bulk) {
        return bulk.amplitude * bulk.norm();
    }
};

} // namespace gqe
