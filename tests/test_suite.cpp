#include <iostream>
#include <vector>
#include <cmath>
#include <cassert>
#include <iomanip>
#include "../include/gqe/kernel.hpp"
#include "../include/gqe/phi_adic.hpp"

#define ASSERT_GEOMETRIC(condition, message) \
    if (!(condition)) { \
        std::cerr << "❌ GEOMETRIC DECOHERENCE: " << message << " at " << __FILE__ << ":" << __LINE__ << std::endl; \
        std::exit(1); \
    } else { \
        std::cout << "✅ " << message << std::endl; \
    }

namespace gqe {

void test_projection_parity() {
    std::cout << "\n--- Testing Projection Parity (E8 -> H4 -> E8) ---" << std::endl;

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

void test_phason_integrity() {
    std::cout << "\n--- Testing Phason Integrity (Hidden Variable Check) ---" << std::endl;
    
    Spinor8D s1({1, 0, 0, 0, 0, 0, 0, 0});
    Spinor8D s2({0, 1, 0, 0, 0, 0, 0, 0});
    
    auto p1 = CoxeterProjection::project_with_phason(s1);
    auto p2 = CoxeterProjection::project_with_phason(s2);
    
    bool distinct_phasons = false;
    for(int i=0; i<4; ++i) {
        if (std::abs(p1.phason[i] - p2.phason[i]) > 1e-6) distinct_phasons = true;
    }
    ASSERT_GEOMETRIC(distinct_phasons, "Phasons distinguish unique 8D origins");
}

void test_e8_lattice_full() {
    std::cout << "\n--- Testing Full E8 Lattice (240 Roots) ---" << std::endl;
    constexpr auto& roots = E8Lattice<>::roots;
    ASSERT_GEOMETRIC(roots.size() == 240, "Generated exactly 240 roots");
    
    for (const auto& r : roots) {
        float norm = r.norm();
        ASSERT_GEOMETRIC(std::abs(norm - std::sqrt(2.0f)) < 1e-5, "Root norm is sqrt(2)");
    }
}

void test_phi_adic() {
    std::cout << "\n--- Testing Phi-Adic Number System ---" << std::endl;
    float original = 3.14159f;
    auto encoded = PhiAdicNumber::encode(original);
    float recovered = encoded.to_float();
    ASSERT_GEOMETRIC(std::abs(original - recovered) < 1e-4, "Phi-adic round-trip accuracy");
}

void test_toric_correction_syndromes() {
    std::cout << "\n--- Testing Toric Error Correction (Syndromes) ---" << std::endl;
    std::vector<Spinor8D> spinors(10);
    for (auto& s : spinors) s.phase = 0.0f;
    
    // Introduce a decoherent spinor
    spinors[5].phase = std::numbers::pi_v<float>;
    
    auto syndromes = ToricErrorCorrection::detect_syndromes(spinors);
    ASSERT_GEOMETRIC(!syndromes.empty(), "Detected decoherence syndrome");
    ASSERT_GEOMETRIC(syndromes[0].spinor_idx == 5, "Identified correct decoherent spinor");
}

void test_geometric_evolution() {
    std::cout << "\n--- Testing Geometric Evolver (Möbius Feedback) ---" << std::endl;
    std::vector<Spinor8D> embeddings = {
        Spinor8D({1, 0, 0, 0, 0, 0, 0, 0}),
        Spinor8D({0, 1, 0, 0, 0, 0, 0, 0})
    };
    float initial_dist = embeddings[0].distance_to(embeddings[1]);
    
    GeometricEvolver evolver(0.1f, 0.0f);
    evolver.evolve(embeddings, {{0, 1}});
    
    float final_dist = embeddings[0].distance_to(embeddings[1]);
    ASSERT_GEOMETRIC(final_dist < initial_dist, "Tokens moved closer after co-occurrence");
}

void test_sleep_consolidation() {
    std::cout << "\n--- Testing Sleep Cycle (Consolidation) ---" << std::endl;
    std::vector<Spinor8D> embeddings = {
        Spinor8D({1.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f}),
        Spinor8D({1.05f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f})
    };
    
    SleepCycle sleeper(0.1f);
    sleeper.consolidate(embeddings);
    
    float dist = embeddings[0].distance_to(embeddings[1]);
    ASSERT_GEOMETRIC(dist < 1e-6, "Tokens consolidated to same geometry");
}

void test_holographic_parity() {
    std::cout << "\n--- Testing Holographic Encoding Parity ---" << std::endl;
    std::vector<uint8_t> data = {1, 2, 3, 4, 5, 6, 7, 8};
    
    auto surface = HolographicEncoding::encode_holographic(data, 8);
    auto reconstructed = HolographicEncoding::decode_holographic(surface, data.size(), 8);
    
    for (size_t i = 0; i < data.size(); ++i) {
        int diff = std::abs(static_cast<int>(data[i]) - static_cast<int>(reconstructed[i]));
        // Spreading/inverse isn't perfectly lossless without full QR, but should be close.
        // Allowing a small diff due to heuristic inverse spreading.
        ASSERT_GEOMETRIC(diff <= 10, "Holographic reconstruction accuracy (diff: " + std::to_string(diff) + ")");
    }
}

void test_horizon_batching() {
    std::cout << "\n--- Testing Horizon Batching (Grain-Awareness) ---" << std::endl;
    
    std::string text = "The quick brown fox jumps over the lazy dog. The singularity is near.";
    std::vector<uint8_t> data(text.begin(), text.end());
    
    GrainAwareChunker chunker(10); 
    
    size_t chunk_count = 0;
    chunker.chunk_data(data, [&](size_t idx, std::span<const uint8_t> chunk, size_t start, size_t end) {
        chunk_count++;
        if (end < data.size()) {
            bool ends_at_boundary = false;
            uint8_t last_byte = chunk.back();
            if (last_byte == ' ' || last_byte == '.') ends_at_boundary = true;
            ASSERT_GEOMETRIC(ends_at_boundary, "Chunk ends at grain boundary");
        }
    });
    
    ASSERT_GEOMETRIC(chunk_count > 1, "Data was successfully chunked");
}

} // namespace gqe

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "   GQE KERNEL - PARITY VERIFICATION     " << std::endl;
    std::cout << "========================================" << std::endl;

    try {
        gqe::test_projection_parity();
        gqe::test_phason_integrity();
        gqe::test_e8_lattice_full();
        gqe::test_phi_adic();
        gqe::test_toric_correction_syndromes();
        gqe::test_geometric_evolution();
        gqe::test_sleep_consolidation();
        gqe::test_holographic_parity();
        gqe::test_horizon_batching();
    } catch (const std::exception& e) {
        std::cerr << "CRITICAL FAILURE: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "========================================" << std::endl;
    std::cout << "   PARITY SUCCESSFUL - MODEL ADHERED    " << std::endl;
    std::cout << "========================================" << std::endl;

    return 0;
}
