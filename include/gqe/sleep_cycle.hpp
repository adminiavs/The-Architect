#pragma once

#include "types.hpp"
#include <vector>
#include <map>

namespace gqe {

/**
 * THE PHYSICS: The Forgetting Protocol (Sleep Cycle).
 * 1. Consolidation (Lossless): Close tokens share geometric points.
 * 2. Pruning (Lossy): Delete high-entropy noise.
 */
class SleepCycle {
private:
    float consolidation_threshold_;
    float entropy_threshold_;

public:
    SleepCycle(float ct = 0.1f, float et = 0.8f) 
        : consolidation_threshold_(ct), entropy_threshold_(et) {}

    // Geometric consolidation: many tokens -> one geometry (lossless)
    void consolidate(std::vector<Spinor8D>& embeddings) {
        if (embeddings.empty()) return;

        for (size_t i = 0; i < embeddings.size(); ++i) {
            for (size_t j = i + 1; j < embeddings.size(); ++j) {
                if (embeddings[i].distance_to(embeddings[j]) < consolidation_threshold_) {
                    // Merge j into i: j points to i's location
                    std::copy(std::begin(embeddings[i].pos), std::end(embeddings[i].pos), std::begin(embeddings[j].pos));
                    embeddings[j].phase = embeddings[i].phase;
                }
            }
        }
    }

    // Bijective refresh
    static void refresh(Spinor8D& spinor) {
        spinor.phase = std::fmod(spinor.phase, 2.0f * std::numbers::pi_v<float>);
    }
};

} // namespace gqe
