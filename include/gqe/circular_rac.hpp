#pragma once

#include <vector>
#include <cstdint>
#include <immintrin.h>
#include <numeric>

namespace gqe {

/**
 * Circular Bit-Shifting Arithmetic Coder (RAC)
 * 
 * THE PHYSICS:
 * Narrowing the sectors based on holographic probabilities.
 */
class CircularRAC {
private:
    static constexpr uint64_t RANGE_BITS = 55;
    static constexpr uint64_t RANGE_MASK = (1ULL << RANGE_BITS) - 1;
    static constexpr uint64_t HALF_RANGE = 1ULL << (RANGE_BITS - 1);
    static constexpr uint64_t FIRST_QUARTER = 1ULL << (RANGE_BITS - 2);
    static constexpr uint64_t THIRD_QUARTER = FIRST_QUARTER * 3;

    uint64_t low_, high_;
    uint32_t underflow_count_;
    std::vector<uint8_t> output_;
    uint8_t current_byte_;
    int bit_count_;

public:
    CircularRAC() { reset(); }

    void reset() {
        low_ = 0;
        high_ = RANGE_MASK;
        underflow_count_ = 0;
        output_.clear();
        current_byte_ = 0;
        bit_count_ = 0;
    }

    /**
     * THE PHYSICS: Weighted Sector Slicing
     * Use SIMD (AVX2) to calculate the cumulative sum of probabilities.
     */
    void encode(uint8_t actual, const uint32_t* distribution) {
        __m256i sum_v = _mm256_setzero_si256();
        __m256i low_sum_v = _mm256_setzero_si256();
        
        // Process 256 values in 32 iterations of 8-way SIMD
        for (int i = 0; i < 256; i += 8) {
            __m256i v = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(&distribution[i]));
            sum_v = _mm256_add_epi32(sum_v, v);
            
            // Masked addition for low_cdf
            if (i < actual) {
                if (i + 8 <= actual) {
                    low_sum_v = _mm256_add_epi32(low_sum_v, v);
                } else {
                    // Optimized mask for the last partial chunk
                    static const int32_t mask_data[16] = {
                        -1, -1, -1, -1, -1, -1, -1, -1,
                         0,  0,  0,  0,  0,  0,  0,  0
                    };
                    __m256i mask = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(&mask_data[8 - (actual - i)]));
                    low_sum_v = _mm256_add_epi32(low_sum_v, _mm256_and_si256(v, mask));
                }
            }
        }
        
        // Fast horizontal add
        auto hsum = []( __m256i v) {
            __m128i vlow = _mm256_castsi256_si128(v);
            __m128i vhigh = _mm256_extracti128_si256(v, 1);
            vlow = _mm_add_epi32(vlow, vhigh);
            __m128i shuf = _mm_shuffle_epi32(vlow, _MM_SHUFFLE(1, 0, 3, 2));
            vlow = _mm_add_epi32(vlow, shuf);
            shuf = _mm_shuffle_epi32(vlow, _MM_SHUFFLE(2, 3, 0, 1));
            vlow = _mm_add_epi32(vlow, shuf);
            return static_cast<uint32_t>(_mm_cvtsi128_si32(vlow));
        };

        uint32_t total_sum = hsum(sum_v);
        uint32_t low_cdf = hsum(low_sum_v);
        uint32_t high_cdf = low_cdf + distribution[actual];

        encode_range(low_cdf, high_cdf, total_sum);
    }

    void encode_range(uint32_t low_count, uint32_t high_count, uint32_t total_sum) {
        if (total_sum == 0) return;

        // THE PHYSICS: Narrowing the Sectors
        // We use 64-bit precision to compute the new range boundaries.
        // This ensures the "range" actually shrinks even when it's small relative to total_sum.
        uint64_t range = high_ - low_ + 1;
        
        uint64_t new_high = low_ + ((range * high_count) / total_sum) - 1;
        uint64_t new_low = low_ + ((range * low_count) / total_sum);
        
        new_high &= RANGE_MASK;
        new_low &= RANGE_MASK;
        
        // Safeguard: Ensure the range doesn't collapse to zero due to rounding
        if (new_high <= new_low) {
            new_high = new_low + 1;
        }
        
        high_ = new_high;
        low_ = new_low;

        // Renormalization: Output bits and shift range
        for (;;) {
            if ((low_ & HALF_RANGE) == (high_ & HALF_RANGE)) {
                uint8_t bit = static_cast<uint8_t>((low_ & HALF_RANGE) >> (RANGE_BITS - 1));
                write_bit(bit);
                while (underflow_count_ > 0) {
                    write_bit(!bit);
                    underflow_count_--;
                }
            } else if (low_ >= FIRST_QUARTER && high_ < THIRD_QUARTER) {
                // MSB differs, but the range sits in the middle half (01..10..)
                underflow_count_++;
                low_ -= FIRST_QUARTER;
                high_ -= FIRST_QUARTER;
            } else {
                // Range is large enough to continue
                break;
            }
            
            low_ = (low_ << 1) & RANGE_MASK;
            high_ = ((high_ << 1) & RANGE_MASK) | 1;
        }
    }

    void encode(uint32_t symbol, uint32_t total_range) {
        encode_range(symbol, symbol + 1, total_range);
    }

    void write_bit(uint8_t bit) {
        current_byte_ = static_cast<uint8_t>((current_byte_ << 1) | (bit & 1));
        bit_count_++;
        if (bit_count_ == 8) {
            output_.push_back(current_byte_);
            current_byte_ = 0;
            bit_count_ = 0;
        }
    }

    void flush() {
        if (bit_count_ > 0) {
            output_.push_back(current_byte_ << (8 - bit_count_));
            current_byte_ = 0;
            bit_count_ = 0;
        }
        // Push remaining range bits to ensure uniqueness
        output_.push_back(static_cast<uint8_t>((low_ >> (RANGE_BITS - 8)) & 0xFF));
    }

    const std::vector<uint8_t>& get_output() { 
        flush();
        return output_; 
    }
};

} // namespace gqe
