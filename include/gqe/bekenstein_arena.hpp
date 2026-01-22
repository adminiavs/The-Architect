#pragma once

#include "constants.hpp"
#include <memory>
#include <cstdint>
#include <type_traits>

namespace gqe {

/**
 * THE PHYSICS: This mimics the Universal Refresh Rate.
 * The "Memory" is a fixed surface that updates frame-by-frame.
 * This prevents "Memory Leaks" (Entropy Accumulation).
 */
class BekensteinArena {
private:
    std::unique_ptr<uint8_t[]> buffer_;
    size_t buffer_size_;
    size_t offset_;

public:
    BekensteinArena(size_t size = BEKENSTEIN_BUFFER)
        : buffer_(std::make_unique<uint8_t[]>(size))
        , buffer_size_(size)
        , offset_(0) {}

    // Reset for new frame (no deallocation)
    inline void reset() { offset_ = 0; }

    // Allocate from arena (no malloc/new)
    template<typename T>
    inline T* allocate(size_t count = 1) {
        static_assert(std::is_trivially_copyable_v<T>,
                     "Arena allocation requires trivially copyable types");

        size_t bytes_needed = count * sizeof(T);
        size_t aligned_offset = (offset_ + alignof(T) - 1) & ~(alignof(T) - 1);

        if (aligned_offset + bytes_needed > buffer_size_) {
            throw std::bad_alloc(); // Frame too large for arena
        }

        T* ptr = reinterpret_cast<T*>(&buffer_[aligned_offset]);
        offset_ = aligned_offset + bytes_needed;
        return ptr;
    }

    // Get remaining space
    inline size_t remaining() const {
        return buffer_size_ - offset_;
    }
};

} // namespace gqe
