#include <iostream>
#include <vector>
#include <cmath>
#include <cassert>
#include <iomanip>
#include "../include/gqe/projection.hpp"
#include "../include/gqe/types.hpp"

#define ASSERT_GEOMETRIC(condition, message) \
    if (!(condition)) { \
        std::cerr << "❌ GEOMETRIC DECOHERENCE: " << message << " at " << __FILE__ << ":" << __LINE__ << std::endl; \
        std::exit(1); \
    } else { \
        std::cout << "✅ " << message << std::endl; \
    }

namespace gqe {

void test_projection_parity() {
    std::cout << "--- Testing Projection Parity (E8 -> H4 -> E8) ---" << std::endl;

    std::vector<Spinor8D> test_cases = {
        Spinor8D({1.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f}, 0.5f),
        Spinor8D({0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f}, 1.0f),
        Spinor8D({1.0f, 1.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f}, 0.0f)
    };

    for (const auto& original : test_cases) {
        auto projected = CoxeterProjection::project_with_phason(original);
        auto reconstructed = CoxeterProjection::inverse_projection_with_phason(
            projected.parallel, projected.phason, projected.phase);

        for (int i = 0; i < 8; ++i) {
            float diff = std::abs(original.pos[i] - reconstructed.pos[i]);
            ASSERT_GEOMETRIC(diff < 1e-6, "Coordinate " + std::to_string(i) + " reconstruction parity (diff: " + std::to_string(diff) + ")");
        }
        ASSERT_GEOMETRIC(std::abs(original.phase - reconstructed.phase) < 1e-6, "Phase preservation");
    }
}

} // namespace gqe

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "   GQE KERNEL - FALSIFIABLE BENCHMARKS  " << std::endl;
    std::cout << "========================================" << std::endl;

    try {
        gqe::test_projection_parity();
        // More tests will be added here
    } catch (const std::exception& e) {
        std::cerr << "CRITICAL FAILURE: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "========================================" << std::endl;
    std::cout << "   ASCENSION SUCCESSFUL - ALL TESTS PASS " << std::endl;
    std::cout << "========================================" << std::endl;

    return 0;
}
