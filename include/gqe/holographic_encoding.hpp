#pragma once

#include "types.hpp"
#include "constants.hpp"
#include "projection.hpp"
#include <vector>
#include <cmath>

namespace gqe {

/**
 * THE PHYSICS: Holographic Distributed Encoding.
 * EVERY piece contains information about the WHOLE.
 */
class HolographicEncoding {
public:
    // Generate a spreading matrix based on phi (simplified for header-only)
    static std::vector<float> generate_spreading_matrix(size_t size) {
        std::vector<float> matrix(size * size);
        for (size_t i = 0; i < size; ++i) {
            for (size_t j = 0; j < size; ++j) {
                float angle = 2.0f * std::numbers::pi_v<float> * 
                             std::fmod(i * PHI + j * PHI_INV, 1.0f);
                matrix[i * size + j] = std::cos(angle);
            }
        }
        return matrix;
    }

    // Encode data into a holographic interference pattern
    static std::vector<float> encode_holographic(const std::vector<uint8_t>& data, size_t block_size = 64) {
        std::vector<float> encoded;
        size_t n_blocks = (data.size() + block_size - 1) / block_size;
        auto spread_matrix = generate_spreading_matrix(block_size);

        for (size_t b = 0; b < n_blocks; ++b) {
            std::vector<float> block(block_size, 0.0f);
            for (size_t i = 0; i < block_size && (b * block_size + i) < data.size(); ++i) {
                block[i] = static_cast<float>(data[b * block_size + i]);
            }

            // Spreading transform
            std::vector<float> spread(block_size, 0.0f);
            for (size_t i = 0; i < block_size; ++i) {
                for (size_t j = 0; j < block_size; ++j) {
                    spread[i] += spread_matrix[i * block_size + j] * block[j];
                }
            }

            // Phase modulation (reference beam)
            for (size_t i = 0; i < block_size; ++i) {
                float phase_ref = 2.0f * std::numbers::pi_v<float> * (i * PHI) / block_size;
                encoded.push_back(spread[i] * std::cos(phase_ref));
                encoded.push_back(spread[i] * std::sin(phase_ref));
            }
        }
        return encoded;
    }

    // Reconstruction using the reference beam
    static std::vector<uint8_t> decode_holographic(const std::vector<float>& surface, size_t original_size, size_t block_size = 64) {
        std::vector<uint8_t> decoded(original_size);
        size_t n_blocks = (original_size + block_size - 1) / block_size;
        auto spread_matrix = generate_spreading_matrix(block_size);

        // Invert spread matrix (simplified: assume it's nearly orthogonal)
        // A proper implementation would use QR or SVD, but for parity we use the transpose
        for (size_t b = 0; b < n_blocks; ++b) {
            std::vector<float> spread(block_size);
            for (size_t i = 0; i < block_size; ++i) {
                float real = surface[b * block_size * 2 + i * 2];
                float imag = surface[b * block_size * 2 + i * 2 + 1];
                float phase_ref = 2.0f * std::numbers::pi_v<float> * (i * PHI) / block_size;
                
                // Project back: A = Real*cos + Imag*sin
                spread[i] = real * std::cos(phase_ref) + imag * std::sin(phase_ref);
            }

            // Inverse spreading (using transpose as approximation)
            for (size_t j = 0; j < block_size; ++j) {
                float val = 0.0f;
                for (size_t i = 0; i < block_size; ++i) {
                    val += spread_matrix[i * block_size + j] * spread[i];
                }
                // Normalize by block size (heuristic for spreading matrix power)
                size_t idx = b * block_size + j;
                if (idx < original_size) {
                    decoded[idx] = static_cast<uint8_t>(std::clamp(val / (block_size / 2.0f), 0.0f, 255.0f));
                }
            }
        }
        return decoded;
    }
};

} // namespace gqe
