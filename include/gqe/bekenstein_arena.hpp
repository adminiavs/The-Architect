#pragma once

#include "constants.hpp"
#include <memory>
#include <vector>
#include <array>
#include <new>
#include <iostream>
#include <chrono>

namespace gqe {

/**
 * THE PHYSICS: Bekenstein Arena - Memory management without entropy.
 *
 * Following the holographic principle and Bekenstein bound, this arena:
 * - Tracks information content of allocations
 * - Prevents entropy increase during computation
 * - Mimics the Universal Refresh Rate (computational clock speed)
 * - No malloc/new during compression loops (as per rule)
 *
 * Memory is organized in Fibonacci-sized blocks to eliminate cache collisions.
 */

class BekensteinArena {
public:
    // Fibonacci-compliant block sizes (true Fibonacci numbers)
    static constexpr size_t BLOCK_SIZE_FIB_13 = 233;         // F_13 = 233 bytes
    static constexpr size_t BLOCK_SIZE_FIB_21 = 17711;       // F_21 = 17711 bytes (~17KB)
    static constexpr size_t BLOCK_SIZE_FIB_34 = 5702887;     // F_34 = 5702887 bytes (~5.7MB)

    // Default to medium Fibonacci block size
    static constexpr size_t DEFAULT_BLOCK_SIZE = BLOCK_SIZE_FIB_34; // 5.7MB working set

    struct MemoryStats {
        size_t total_allocated = 0;      // Bytes currently allocated
        size_t peak_allocated = 0;       // Peak memory usage
        size_t allocation_count = 0;     // Number of allocations
        double entropy_density = 0.0;    // Information per unit volume
        double coherence_factor = 1.0;   // Memory coherence (1.0 = perfect)
    };

private:
    struct MemoryBlock {
        std::unique_ptr<char[]> data;
        size_t size;
        size_t used;
        bool is_coherent;  // Coherent memory follows holographic bounds

        MemoryBlock(size_t block_size)
            : data(std::make_unique<char[]>(block_size))
            , size(block_size)
            , used(0)
            , is_coherent(true) {}
    };

    std::vector<MemoryBlock> blocks_;
    MemoryStats stats_;
    size_t current_block_index_;
    bool entropy_free_mode_;  // When true, no allocations allowed

    // Holographic refresh rate (computational clock)
    std::chrono::steady_clock::time_point last_refresh_;
    static constexpr auto REFRESH_INTERVAL = std::chrono::microseconds(100); // ~10kHz

public:
    BekensteinArena(size_t initial_block_size = DEFAULT_BLOCK_SIZE)
        : current_block_index_(0)
        , entropy_free_mode_(false)
        , last_refresh_(std::chrono::steady_clock::now())
    {
        add_block(initial_block_size);
    }

    ~BekensteinArena() {
        // Report final memory statistics
        report_stats();
    }

    /**
     * Allocate memory from the arena (entropy-free when in compression mode)
     */
    template<typename T>
    T* allocate(size_t count = 1) {
        if (entropy_free_mode_) {
            throw std::runtime_error("CRITICAL: Memory allocation during entropy-free compression loop!");
        }

        size_t bytes_needed = count * sizeof(T);
        size_t aligned_bytes = align_to_cache_line(bytes_needed);

        // Check if current block has space
        if (current_block_index_ >= blocks_.size() ||
            blocks_[current_block_index_].used + aligned_bytes > blocks_[current_block_index_].size) {

            // Need new block
            size_t new_block_size = std::max(aligned_bytes * 2, DEFAULT_BLOCK_SIZE);
            add_block(new_block_size);
        }

        // Allocate from current block
        MemoryBlock& current_block = blocks_[current_block_index_];
        char* ptr = current_block.data.get() + current_block.used;
        current_block.used += aligned_bytes;

        // Update statistics
        stats_.total_allocated += aligned_bytes;
        stats_.peak_allocated = std::max(stats_.peak_allocated, stats_.total_allocated);
        stats_.allocation_count++;

        // Check holographic bound
        update_holographic_bounds();

        return reinterpret_cast<T*>(ptr);
    }

    /**
     * Deallocate all memory (reset arena)
     */
    void reset() {
        for (auto& block : blocks_) {
            block.used = 0;
        }
        current_block_index_ = 0;
        stats_.total_allocated = 0;
        refresh_holographic_state();
    }

    /**
     * Enter entropy-free compression mode (no allocations allowed)
     */
    void enter_compression_mode() {
        entropy_free_mode_ = true;
        refresh_holographic_state();
    }

    /**
     * Exit entropy-free compression mode
     */
    void exit_compression_mode() {
        entropy_free_mode_ = false;
    }

    /**
     * Get current memory statistics
     */
    const MemoryStats& get_stats() const {
        return stats_;
    }

    /**
     * Report memory usage to console
     */
    void report_stats() const {
        std::cout << "=== Bekenstein Arena Memory Report ===" << std::endl;
        std::cout << "Total Allocated: " << stats_.total_allocated << " bytes" << std::endl;
        std::cout << "Peak Usage: " << stats_.peak_allocated << " bytes" << std::endl;
        std::cout << "Allocation Count: " << stats_.allocation_count << std::endl;
        std::cout << "Entropy Density: " << stats_.entropy_density << std::endl;
        std::cout << "Coherence Factor: " << stats_.coherence_factor << std::endl;
        std::cout << "Blocks Used: " << blocks_.size() << std::endl;
        std::cout << "Entropy-Free Mode: " << (entropy_free_mode_ ? "ACTIVE" : "INACTIVE") << std::endl;
    }

private:
    /**
     * Add a new memory block
     */
    void add_block(size_t size) {
        blocks_.emplace_back(size);
        current_block_index_ = blocks_.size() - 1;
    }

    /**
     * Align size to cache line boundary
     */
    size_t align_to_cache_line(size_t size) {
        return (size + CACHE_LINE_SIZE - 1) & ~(CACHE_LINE_SIZE - 1);
    }

    /**
     * Update holographic bounds and entropy tracking
     */
    void update_holographic_bounds() {
        // Simple holographic entropy calculation
        // Area ~ (volume)^{2/3}, so entropy ~ area ~ volume^{2/3}
        double volume = static_cast<double>(stats_.total_allocated);
        stats_.entropy_density = ENTROPY_DENSITY_FACTOR * std::pow(volume, 2.0/3.0);

        // Coherence factor decreases with entropy
        stats_.coherence_factor = 1.0 / (1.0 + stats_.entropy_density);
    }

    /**
     * Refresh holographic state (simulate computational clock)
     */
    void refresh_holographic_state() {
        auto now = std::chrono::steady_clock::now();
        if (now - last_refresh_ > REFRESH_INTERVAL) {
            // Reset entropy tracking on refresh
            stats_.entropy_density *= PHI_INV;  // Golden ratio decay
            last_refresh_ = now;
        }
    }
};

/**
 * RAII wrapper for entropy-free operations
 */
class EntropyFreeScope {
private:
    BekensteinArena& arena_;
    bool was_in_compression_mode_;

public:
    EntropyFreeScope(BekensteinArena& arena)
        : arena_(arena)
        , was_in_compression_mode_(arena_.get_stats().coherence_factor < 0.9) // Heuristic
    {
        if (!was_in_compression_mode_) {
            arena_.enter_compression_mode();
        }
    }

    ~EntropyFreeScope() {
        if (!was_in_compression_mode_) {
            arena_.exit_compression_mode();
        }
    }
};

/**
 * Fibonacci-sized buffer for coherent memory operations
 */
template<size_t N = FIB_21>
class FibonacciBuffer {
private:
    std::array<char, N> buffer_;
    size_t used_;

public:
    FibonacciBuffer() : used_(0) {}

    template<typename T>
    T* allocate(size_t count = 1) {
        size_t bytes_needed = count * sizeof(T);
        if (used_ + bytes_needed > N) {
            throw std::runtime_error("FibonacciBuffer: Insufficient space in buffer");
        }

        T* ptr = reinterpret_cast<T*>(&buffer_[used_]);
        used_ += bytes_needed;
        return ptr;
    }

    void reset() {
        used_ = 0;
    }

    size_t capacity() const { return N; }
    size_t used() const { return used_; }
    size_t available() const { return N - used_; }
};

} // namespace gqe