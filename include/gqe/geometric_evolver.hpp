#pragma once

#include "types.hpp"
#include <vector>
#include <random>

namespace gqe {

/**
 * THE PHYSICS: Self-Learning through the Möbius Strip.
 * Learning is not "adding weights" - it is RESHAPING the geometric substrate.
 */
class GeometricEvolver {
private:
    float learning_rate_;
    float mutation_rate_;

public:
    GeometricEvolver(float lr = 0.01f, float mr = 0.001f) 
        : learning_rate_(lr), mutation_rate_(mr) {}

    // Möbius feedback loop: attract co-occurring tokens
    void evolve(std::vector<Spinor8D>& embeddings, 
                const std::vector<std::pair<size_t, size_t>>& cooccurrences) {
        for (const auto& [i, j] : cooccurrences) {
            if (i >= embeddings.size() || j >= embeddings.size()) continue;
            
            // Move spinors closer in 8D space
            for (int k = 0; k < 8; ++k) {
                float diff = embeddings[j].pos[k] - embeddings[i].pos[k];
                embeddings[i].pos[k] += learning_rate_ * diff;
                embeddings[j].pos[k] -= learning_rate_ * diff;
            }
            
            // Phase attraction
            float phase_diff = embeddings[j].phase - embeddings[i].phase;
            embeddings[i].phase += learning_rate_ * phase_diff;
            embeddings[j].phase -= learning_rate_ * phase_diff;
        }

        // Apply phason flips (mutations)
        std::mt19937 rng(42);
        std::uniform_real_distribution<float> dist(0, 1);
        for (auto& s : embeddings) {
            if (dist(rng) < mutation_rate_) {
                int axis = std::uniform_int_distribution<int>(0, 7)(rng);
                s.pos[axis] *= -1.0f; // Simplified phason flip
            }
        }
    }

    // Single spinor evolution
    static void evolve_single(Spinor8D& spinor, float delta_time) {
        spinor.phase += delta_time;
    }
};

} // namespace gqe
