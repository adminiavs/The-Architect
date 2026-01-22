#pragma once

#include "bekenstein_arena.hpp"
#include "constants.hpp"
#include "e8_lattice.hpp"
#include "types.hpp"

#include <array>
#include <bitset>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <immintrin.h>
#include <iostream>
#include <memory>
#include <vector>

namespace gqe {

/**
 * THE PHYSICS: Use the 黄金比例 (phi) as the hash multiplier
 */
class FibonacciHasher {
private:
    static constexpr uint64_t PHI_U64 = 11400714819323198485ULL; // Floor(2^64 / Phi)

public:
    inline static uint32_t hash(uint32_t key, uint32_t table_size) {
        uint64_t h = static_cast<uint64_t>(key) * PHI_U64;
        return static_cast<uint32_t>(h >> 32) % table_size;
    }
};

/**
 * Geometric Parallelism Context Mixer - v71 Logic
 *
 * RESONANCE UPDATE:
 * 1. Fibonacci Table Size: 75,025 (F25)
 * 2. Fibonacci Decay: 0.618 multiplier for saturation
 */
class GeometricParallelMixer {
private:
    static constexpr size_t TABLE_SIZE = 75025; // F25: Breaking the Aliasing

    struct Entry {
        std::array<uint8_t, TOTAL_GQE_STATES> qprobs;
        std::array<uint16_t, TOTAL_GQE_STATES> byte_counts;
        uint32_t total_count = 0;

        Entry() {
            qprobs.fill(1);
            byte_counts.fill(0);
        }

        inline void update_counts(uint8_t actual) {
            byte_counts[actual]++;
            total_count++;

            if (total_count > 1024) {
                decay_counts();
            }
        }

        inline void decay_counts() {
            __m256i decay_v = _mm256_set1_epi16(40503);
            for (size_t i = 0; i < TOTAL_GQE_STATES; i += 16) {
                __m256i v = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(&byte_counts[i]));
                v = _mm256_mulhi_epu16(v, decay_v);
                _mm256_storeu_si256(reinterpret_cast<__m256i*>(&byte_counts[i]), v);
            }
            total_count = static_cast<uint32_t>(total_count * PHI_INV);
        }

        inline void refresh_qprobs() {
            if (total_count == 0) return;

            float inv_total = 255.0f / (static_cast<float>(total_count) + 1.0f);
            for (size_t idx = 0; idx < TOTAL_GQE_STATES; ++idx) {
                float normalized = (static_cast<float>(byte_counts[idx]) + 0.5f) * inv_total;
                normalized = std::clamp(normalized, 1.0f, 255.0f);
                if (idx >= PRIMARY_GQE_STATES) {
                    // Secondary states are the 23 phason defects that sit outside the primary E8 roots.
                    normalized *= PHI_INV;
                    normalized = std::max(normalized, 1.0f);
                }
                qprobs[idx] = static_cast<uint8_t>(normalized);
            }
        }
    };

    std::array<std::unique_ptr<Entry[]>, CONTEXT_COUNT> tables_;
    std::array<float, CONTEXT_COUNT> weights_;
    std::array<uint16_t, CONTEXT_COUNT> weight_fixed_;
    BekensteinArena& arena_;

    mutable std::array<std::bitset<TABLE_SIZE>, CONTEXT_COUNT> is_hot_;
    mutable std::array<std::vector<uint32_t>, CONTEXT_COUNT> hot_indices_;

public:
    explicit GeometricParallelMixer(BekensteinArena& arena)
        : arena_(arena) {
        for (size_t i = 0; i < CONTEXT_COUNT; ++i) {
            tables_[i] = std::make_unique<Entry[]>(TABLE_SIZE);
            hot_indices_[i].reserve(TABLE_SIZE / 8);
        }

        float sum = 0.0f;
        for (size_t idx = 0; idx < CONTEXT_COUNT; ++idx) {
            float level = static_cast<float>(CONTEXT_COUNT - 1 - idx);
            float ratio = std::pow(PHI_INV, level);
            weights_[idx] = ratio;
            sum += ratio;
        }
        for (size_t idx = 0; idx < CONTEXT_COUNT; ++idx) {
            weights_[idx] /= sum;
            weight_fixed_[idx] = static_cast<uint16_t>(weights_[idx] * 1024.0f);
        }
    }

    void vectorized_hash(const uint8_t* data, size_t len,
                         std::array<uint32_t*, CONTEXT_COUNT>& hashes) const {
        for (size_t ctx_idx = 0; ctx_idx < CONTEXT_COUNT; ++ctx_idx) {
            hashes[ctx_idx] = arena_.allocate<uint32_t>(len);
            size_t ctx_size = CONTEXT_SIZES[ctx_idx];

            uint32_t h = 2166136261U;
            for (size_t i = 0; i < len; ++i) {
                h ^= data[i];
                h *= 16777619U;

                uint32_t window_h = h;
                if (i >= ctx_size) {
                    window_h ^= (static_cast<uint32_t>(data[i - ctx_size]) << (i % 13));
                }

                hashes[ctx_idx][i] = FibonacciHasher::hash(window_h, TABLE_SIZE);
            }
        }
    }

    void predict(const std::array<uint32_t*, CONTEXT_COUNT>& hashes, size_t pos, uint32_t* mixed_probs) const {
        for (size_t offset = 0; offset < TOTAL_GQE_STATES; offset += 8) {
            __m256i accumulator = _mm256_setzero_si256();
            for (size_t ctx = 0; ctx < CONTEXT_COUNT; ++ctx) {
                const uint8_t* p = tables_[ctx][hashes[ctx][pos]].qprobs.data();
                __m256i probs = _mm256_cvtepu8_epi32(_mm_loadu_si128(reinterpret_cast<const __m128i*>(&p[offset])));
                __m256i weight = _mm256_set1_epi32(weight_fixed_[ctx]);
                accumulator = _mm256_add_epi32(accumulator, _mm256_mullo_epi32(probs, weight));
            }
            _mm256_storeu_si256(reinterpret_cast<__m256i*>(&mixed_probs[offset]), accumulator);
        }
    }

    void update(const std::array<uint32_t*, CONTEXT_COUNT>& hashes, size_t pos, uint8_t actual) {
        for (size_t ctx = 0; ctx < CONTEXT_COUNT; ++ctx) {
            uint32_t idx = hashes[ctx][pos];
            if (!is_hot_[ctx].test(idx)) {
                is_hot_[ctx].set(idx);
                hot_indices_[ctx].push_back(idx);
            }
            tables_[ctx][idx].update_counts(actual);
        }
    }

    void refresh() {
        for (size_t ctx = 0; ctx < CONTEXT_COUNT; ++ctx) {
            for (uint32_t idx : hot_indices_[ctx]) {
                tables_[ctx][idx].refresh_qprobs();
                is_hot_[ctx].reset(idx);
            }
            hot_indices_[ctx].clear();
        }
    }

    void train(const uint8_t* data, size_t len) {}
    void predict_batch(const uint8_t* data, size_t len, uint8_t* ranks, uint8_t* qprobs) {}
};

} // namespace gqe
