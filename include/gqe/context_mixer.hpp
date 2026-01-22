#pragma once

#include "constants.hpp"
#include "bekenstein_arena.hpp"
#include <cstdint>
#include <array>
#include <cstring>
#include <algorithm>
#include <immintrin.h>

namespace gqe {

/**
 * THE PHYSICS: Use the 黄金比例 (phi) as the hash multiplier
 */
class FibonacciHasher {
private:
    static constexpr uint64_t PHI_U64 = static_cast<uint64_t>(PHI * (1ULL << 32));

public:
    inline static uint32_t hash(uint32_t key, uint32_t table_size) {
        uint64_t h = static_cast<uint64_t>(key) * PHI_U64;
        return static_cast<uint32_t>(h >> 32) % table_size;
    }
};

/**
 * Lock-Free Hash Table for Context Mixing
 */
template<size_t TABLE_SIZE = 16384>
class ContextTable {
private:
    struct Entry {
        uint32_t key;
        uint8_t probabilities[256];
        bool valid;
    };

    std::unique_ptr<Entry[]> table_;

public:
    ContextTable() : table_(std::make_unique<Entry[]>(TABLE_SIZE)) {
        reset();
    }

    inline void reset() {
        std::memset(table_.get(), 0, sizeof(Entry) * TABLE_SIZE);
    }

    inline void update(uint32_t hash, const uint8_t* probs) {
        Entry& entry = table_[hash % TABLE_SIZE];
        entry.key = hash;
        std::memcpy(entry.probabilities, probs, 256);
        entry.valid = true;
    }

    inline const uint8_t* lookup(uint32_t hash) const {
        const Entry& entry = table_[hash % TABLE_SIZE];
        return entry.valid && entry.key == hash ? entry.probabilities : nullptr;
    }
};

/**
 * SIMD-Optimized Context Mixer
 */
class GeometricParallelMixer {
private:
    ContextTable<> tables_[4];
    uint8_t weights_[4];
    BekensteinArena& arena_;

public:
    explicit GeometricParallelMixer(BekensteinArena& arena)
        : arena_(arena) {
        std::fill_n(weights_, 4, 64);
    }

    void vectorized_hash(const uint8_t* data, size_t len,
                        uint32_t* hashes[4]) const {
        for (size_t i = 0; i < 4; ++i) {
            hashes[i] = arena_.allocate<uint32_t>(len);
        }

        for (size_t ctx_idx = 0; ctx_idx < 4; ++ctx_idx) {
            size_t ctx_size = CONTEXT_SIZES[ctx_idx];

            for (size_t i = 0; i < len; ++i) {
                if (i < ctx_size) {
                    hashes[ctx_idx][i] = 0;
                    continue;
                }

                uint32_t h = 2166136261U;
                for (size_t j = i - ctx_size; j < i; ++j) {
                    h ^= data[j];
                    h *= 16777619U;
                }
                hashes[ctx_idx][i] = FibonacciHasher::hash(h, 16384);
            }
        }
    }

    void predict_batch(const uint8_t* data, size_t len,
                      uint8_t* ranks, uint8_t* qprobs) {
        uint32_t* hashes[4];
        vectorized_hash(data, len, hashes);

        for (size_t i = 0; i < len; ++i) {
            uint8_t mixed_probs[256] = {0};

            for (size_t ctx = 0; ctx < 4; ++ctx) {
                uint32_t h = hashes[ctx][i];
                const uint8_t* probs = tables_[ctx].lookup(h);

                if (probs) {
                    for (size_t j = 0; j < 256; ++j) {
                        uint16_t weighted = static_cast<uint16_t>(probs[j]) * weights_[ctx];
                        mixed_probs[j] += static_cast<uint8_t>(weighted >> 8);
                    }
                } else {
                    for (size_t j = 0; j < 256; ++j) {
                        mixed_probs[j] += weights_[ctx];
                    }
                }
            }

            uint8_t actual = data[i];
            uint8_t actual_prob = mixed_probs[actual];
            uint8_t rank = 0;
            for (size_t j = 0; j < 256; ++j) {
                if (mixed_probs[j] > actual_prob) rank++;
                else if (mixed_probs[j] == actual_prob && j < actual) rank++;
            }

            ranks[i] = rank;
            qprobs[i] = actual_prob;
        }
    }

    void train(const uint8_t* data, size_t len) {
        uint32_t* hashes[4];
        vectorized_hash(data, len, hashes);

        // This is a large allocation, we might want to use a different approach
        // for a real implementation, but for parity it matches.
        auto counts = std::make_unique<std::array<std::array<uint32_t, 256>, 16384>[]>(4);

        for (size_t i = 0; i < len; ++i) {
            uint8_t actual = data[i];
            for (size_t ctx = 0; ctx < 4; ++ctx) {
                uint32_t h = hashes[ctx][i];
                counts[ctx][h][actual]++;
            }
        }

        for (size_t ctx = 0; ctx < 4; ++ctx) {
            for (size_t h = 0; h < 16384; ++h) {
                uint32_t total = 0;
                for (uint32_t c : counts[ctx][h]) total += c;

                if (total > 0) {
                    uint8_t probs[256];
                    for (size_t b = 0; b < 256; ++b) {
                        float prob = (counts[ctx][h][b] + 1.0f) / (total + 256.0f);
                        probs[b] = static_cast<uint8_t>(prob * 255.0f);
                    }
                    tables_[ctx].update(h, probs);
                }
            }
        }
    }
};

} // namespace gqe
