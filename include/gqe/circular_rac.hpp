#pragma once

#include <vector>
#include <cstdint>

namespace gqe {

/**
 * Circular Bit-Shifting Arithmetic Coder (RAC)
 */
class CircularRAC {
private:
    uint32_t low_, high_;
    std::vector<uint8_t> output_;
    uint8_t current_byte_;
    int bit_count_;

public:
    CircularRAC() { reset(); }

    void reset() {
        low_ = 0;
        high_ = 0xFFFFFFFF;
        output_.clear();
        current_byte_ = 0;
        bit_count_ = 0;
    }

    void encode(uint32_t symbol, uint32_t total_range) {
        uint64_t range = static_cast<uint64_t>(high_) - low_ + 1;
        uint32_t symbol_range = static_cast<uint32_t>(range / total_range);

        if (symbol_range == 0) return;

        high_ = low_ + (symbol + 1) * symbol_range - 1;
        low_ = low_ + symbol * symbol_range;

        while ((low_ ^ high_) < 0x80000000) {
            uint8_t bit = (low_ >> 31) & 1;
            write_bit(bit);
            low_ <<= 1;
            high_ = (high_ << 1) | 1;
        }
    }

    void write_bit(uint8_t bit) {
        current_byte_ = (current_byte_ << 1) | (bit & 1);
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
        output_.push_back((low_ >> 24) & 0xFF);
    }

    const std::vector<uint8_t>& get_output() { 
        flush();
        return output_; 
    }
};

} // namespace gqe
