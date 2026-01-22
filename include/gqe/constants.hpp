#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <numbers>

namespace gqe {

constexpr float PHI = std::numbers::phi_v<float>;  // Golden ratio for Fibonacci hashing
constexpr float PHI_INV = PHI - 1.0f;             // Inverse golden ratio
constexpr size_t E8_ROOTS = 240;                   // Number of E8 lattice roots
constexpr size_t PRIMARY_GQE_STATES = 233;          // F13: Primary holographic map states
constexpr size_t PHASON_STATES = 23;                // Remainder treated as defects
constexpr size_t GQE_MAP_SIZE = PRIMARY_GQE_STATES; // legacy alias
constexpr size_t TOTAL_GQE_STATES = PRIMARY_GQE_STATES + PHASON_STATES;
constexpr size_t FIBONACCI_GRAIN = PRIMARY_GQE_STATES;            // F13: The fundamental grain size
constexpr size_t HORIZON_FRAME_SIZE = PRIMARY_GQE_STATES * 1024; // 233KB horizon frames
constexpr size_t BEKENSTEIN_BUFFER = 8 * 1024 * 1024; // 8MB buffer for frame processing (ranks + qprobs + hashes)
constexpr size_t GOLDEN_OVERLAP_STEP = 144 * 1024; // F12: new frame starts this far into previous
constexpr std::array<size_t, 7> CONTEXT_SIZES = {1, 2, 3, 5, 8, 13, 21};  // Fibonacci context windows
constexpr size_t CONTEXT_COUNT = CONTEXT_SIZES.size();

constexpr bool is_primary_byte(uint8_t value) {
    return value < PRIMARY_GQE_STATES;
}

constexpr size_t phason_index(uint8_t value) {
    return static_cast<size_t>(value) - PRIMARY_GQE_STATES;
}

} // namespace gqe
