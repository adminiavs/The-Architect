#pragma once

#include "types.hpp"
#include "e8_lattice.hpp"
#include "phi_adic.hpp"
#include <vector>
#include <cmath>
#include <algorithm>

namespace gqe {

/**
 * THE PHYSICS: Delta-Phase Packer - Geometric Nuance Encoding.
 * Encodes the "nuance" between data and the nearest E8 root.
 */
class DeltaPhiPacker {
public:
    struct LatticeEntry {
        size_t root_index;
        float delta_phase;
        float delta_magnitude;
    };

    // Pack a sequence of lattice entries into a compressed stream
    static std::vector<uint8_t> pack_entries(const std::vector<LatticeEntry>& entries) {
        std::vector<uint8_t> packed;
        for (const auto& entry : entries) {
            // 1. Root index (8 bits for 240 roots)
            packed.push_back(static_cast<uint8_t>(entry.root_index));
            
            // 2. Quantized delta phase (4 bits)
            uint8_t phase_q = static_cast<uint8_t>((entry.delta_phase / (2.0f * std::numbers::pi_v<float>)) * 15.0f);
            
            // 3. Quantized delta magnitude (4 bits)
            uint8_t mag_q = static_cast<uint8_t>(std::clamp(entry.delta_magnitude * 15.0f, 0.0f, 15.0f));
            
            packed.push_back((phase_q << 4) | (mag_q & 0x0F));
        }
        return packed;
    }

    static std::vector<LatticeEntry> unpack_entries(const std::vector<uint8_t>& data) {
        std::vector<LatticeEntry> entries;
        for (size_t i = 0; i + 1 < data.size(); i += 2) {
            LatticeEntry entry;
            entry.root_index = data[i];
            uint8_t deltas = data[i+1];
            entry.delta_phase = (static_cast<float>(deltas >> 4) / 15.0f) * 2.0f * std::numbers::pi_v<float>;
            entry.delta_magnitude = static_cast<float>(deltas & 0x0F) / 15.0f;
            entries.push_back(entry);
        }
        return entries;
    }
};

/**
 * THE PHYSICS: Geometric Predictor.
 * Predicts the next E8 root based on geometric context and transition matrices.
 */
class GeometricPredictor {
private:
    float transitions_[240][240];

public:
    GeometricPredictor() {
        // Initialize transition matrix based on angular proximity
        const auto& roots = E8Lattice<>::roots;
        for (int i = 0; i < 240; ++i) {
            float sum = 0;
            for (int j = 0; j < 240; ++j) {
                // Similarity = dot product (for normalized roots)
                float similarity = 0;
                for (int k = 0; k < 8; ++k) similarity += roots[i].pos[k] * roots[j].pos[k];
                transitions_[i][j] = std::exp(similarity); // Softmax prior
                sum += transitions_[i][j];
            }
            for (int j = 0; j < 240; ++j) transitions_[i][j] /= sum;
        }
    }

    size_t predict_next(size_t current_root) {
        float max_prob = -1.0f;
        size_t best_root = 0;
        for (int j = 0; j < 240; ++j) {
            if (transitions_[current_root][j] > max_prob) {
                max_prob = transitions_[current_root][j];
                best_root = j;
            }
        }
        return best_root;
    }
};

} // namespace gqe
