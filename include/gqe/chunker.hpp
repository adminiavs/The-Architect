#pragma once

#include "constants.hpp"
#include <array>
#include <span>
#include <algorithm>

namespace gqe {

/**
 * Grain-Aware Chunker - Prevents Boundary Entropy
 */
class GrainAwareChunker {
private:
    size_t chunk_size_;
    static constexpr std::array<uint8_t, 12> boundaries_ = {
        ' ', '\n', '\r', '\t', '.', ',', ';', ':', '!', '?', '-', '_'
    };

public:
    explicit GrainAwareChunker(size_t chunk_size = HORIZON_FRAME_SIZE)
        : chunk_size_(chunk_size) {}

    size_t find_boundary(std::span<const uint8_t> data, size_t target_end) const {
        size_t total_size = data.size();

        size_t forward_limit = std::min(target_end + 4096, total_size);
        for (size_t i = target_end; i < forward_limit; ++i) {
            if (is_boundary(data[i])) return i + 1;
        }

        size_t backward_limit = (target_end > 4096) ? target_end - 4096 : 0;
        for (size_t i = target_end - 1; i >= backward_limit && i < target_end; --i) {
            if (is_boundary(data[i])) return i + 1;
        }

        return target_end;
    }

    template<typename F>
    void chunk_data(std::span<const uint8_t> data, F&& callback) const {
        size_t total_size = data.size();
        size_t frame_index = 0;
        size_t start = 0;

        while (start < total_size) {
            size_t target_end = start + chunk_size_;
            size_t end = (target_end >= total_size) ? total_size : find_boundary(data, target_end);

            callback(frame_index, data.subspan(start, end - start), start, end);
            start = end;
            frame_index++;
        }
    }

private:
    bool is_boundary(uint8_t byte) const {
        for (uint8_t boundary : boundaries_) {
            if (byte == boundary) return true;
        }
        return false;
    }
};

} // namespace gqe
