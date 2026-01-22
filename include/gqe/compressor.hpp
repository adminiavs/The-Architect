#pragma once

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
        chunker_.chunk_data(data, [&](size_t frame_idx, std::span<const uint8_t> chunk, size_t start, size_t end) {
            mixer_.train(chunk.data(), chunk.size());

            arena_.reset();
            auto ranks = arena_.allocate<uint8_t>(chunk.size());
            auto qprobs = arena_.allocate<uint8_t>(chunk.size());

            mixer_.predict_batch(chunk.data(), chunk.size(), ranks, qprobs);

            for (size_t i = 0; i < chunk.size(); ++i) {
                rac_.encode(ranks[i], 256);
            }
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
