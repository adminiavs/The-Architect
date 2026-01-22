#pragma once

#include <numbers>
#include <cstddef>

namespace gqe {

constexpr float PHI = std::numbers::phi_v<float>;  // Golden ratio for Fibonacci hashing
constexpr float PHI_INV = PHI - 1.0f;             // Inverse golden ratio
constexpr size_t E8_ROOTS = 240;                   // Number of E8 lattice roots
constexpr size_t HORIZON_FRAME_SIZE = 233 * 1024; // 233KB horizon frames
constexpr size_t BEKENSTEIN_BUFFER = 8 * 1024 * 1024; // 8MB buffer for frame processing (ranks + qprobs + hashes)
constexpr size_t CONTEXT_SIZES[] = {1, 2, 4, 8};  // N-Frame windows

} // namespace gqe
