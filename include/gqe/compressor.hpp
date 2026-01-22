#pragma once

#include <array>
#include <iomanip>
#include <iostream>
#include "bekenstein_arena.hpp"
#include "context_mixer.hpp"
#include "circular_rac.hpp"
#include "chunker.hpp"
#include <span>

namespace gqe {

/**
 * Main GQE Compressor with Grain-Aware Chunking
 */
class GQECompressor {
private:
    BekensteinArena arena_;
    GeometricParallelMixer mixer_;
    CircularRAC rac_;
    GrainAwareChunker chunker_;

public:
    GQECompressor(size_t chunk_size = HORIZON_FRAME_SIZE)
        : mixer_(arena_), chunker_(chunk_size) {}

    std::vector<uint8_t> compress(std::span<const uint8_t> data) {
        rac_.reset();
        const size_t total_size = data.size();
        const size_t monitor_step = 1024 * 1024;
        const double total_mb = static_cast<double>(total_size) / static_cast<double>(monitor_step);

        chunker_.chunk_data(data, [&](size_t frame_idx, std::span<const uint8_t> chunk, size_t start, size_t end) {
            arena_.reset();
            
            // 1. Precompute all context hashes for the frame
            std::array<uint32_t*, CONTEXT_COUNT> hashes;
            mixer_.vectorized_hash(chunk.data(), chunk.size(), hashes);

            // 2. Continuous Learning + Phason Squeeze
            alignas(32) uint32_t mixed_probs[TOTAL_GQE_STATES];
            for (size_t i = 0; i < chunk.size(); ++i) {
                size_t absolute_pos = start + i;
                if (absolute_pos != 0 && (absolute_pos % monitor_step == 0)) {
                    double progress = (static_cast<double>(absolute_pos) / static_cast<double>(total_size)) * 100.0;
                    std::cout << "[Horizon] Rendering Frame: " << (absolute_pos / monitor_step) << "MB / "
                              << std::fixed << std::setprecision(1) << total_mb << "MB (" << progress
                              << "%)" << std::endl;
                }

                // Capture the holographic distribution
                mixer_.predict(hashes, i, mixed_probs);
                
                // Weighted Sector Slicing (SIMD-optimized)
                rac_.encode(chunk[i], mixed_probs);
                
                // Update synaptic links
                mixer_.update(hashes, i, chunk[i]);

                // RESONANCE UPDATE: Fibonacci Block Processing (F13)
                // We refresh the "Shutter Speed" every 233 bytes.
                if ((i + 1) % FIBONACCI_GRAIN == 0) {
                    mixer_.refresh();
                }
            }

            // Ensure any remaining hot entries are refreshed
            mixer_.refresh();
        });

        return rac_.get_output();
    }

    struct Stats {
        size_t original_size;
        size_t compressed_size;
        float ratio;
        float bits_per_byte;
    };

    Stats get_stats() const {
        return Stats{0, 0, 0.0f, 0.0f};
    }
};

} // namespace gqe
