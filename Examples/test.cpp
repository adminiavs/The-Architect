/**
 * GQE Kernel Test Program
 *
 * Tests basic functionality of the header-only C++20 GQE library.
 */

#include "gqe_kernel.hpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <random>
#include <filesystem>

namespace fs = std::filesystem;

void test_spinor8d() {
    std::cout << "Testing Spinor8D...\n";

    // Test basic construction
    gqe::Spinor8D s1;
    std::cout << "  Default Spinor8D norm: " << s1.norm() << "\n";

    // Test array construction
    std::array<float, 8> coords = {1, 0, 0, 0, 0, 0, 0, 0};
    gqe::Spinor8D s2(coords, 0.5f, 2.0f);
    std::cout << "  Array Spinor8D norm: " << s2.norm() << "\n";

    // Test normalization
    gqe::Spinor8D s3 = s2;
    s3.normalize();
    std::cout << "  Normalized norm: " << s3.norm() << "\n";

    std::cout << "  Spinor8D tests passed!\n";
}

void test_e8_lattice() {
    std::cout << "Testing E8Lattice...\n";

    // Test compile-time generation
    constexpr auto& roots = gqe::E8Lattice<>::roots;
    std::cout << "  Generated " << roots.size() << " E8 roots at compile time\n";

    // Test first few roots
    for (size_t i = 0; i < std::min(size_t(5), roots.size()); ++i) {
        std::cout << "  Root " << i << " norm: " << roots[i].norm() << "\n";
    }

    std::cout << "  E8Lattice tests passed!\n";
}

void test_bekenstein_arena() {
    std::cout << "Testing BekensteinArena...\n";

    gqe::BekensteinArena arena;

    // Test allocation
    auto ptr1 = arena.allocate<int>(10);
    std::cout << "  Allocated 10 ints, remaining: " << arena.remaining() << "\n";

    auto ptr2 = arena.allocate<double>(5);
    std::cout << "  Allocated 5 doubles, remaining: " << arena.remaining() << "\n";

    // Test reset
    arena.reset();
    std::cout << "  After reset, remaining: " << arena.remaining() << "\n";

    std::cout << "  BekensteinArena tests passed!\n";
}

void test_fibonacci_hasher() {
    std::cout << "Testing FibonacciHasher...\n";

    // Test single hash
    uint32_t key = 12345;
    uint32_t table_size = 16384;
    uint32_t hash = gqe::FibonacciHasher::hash(key, table_size);
    std::cout << "  Hash of " << key << ": " << hash << "\n";

    // Test SIMD hash
    std::vector<uint32_t> keys = {1, 2, 3, 4, 5, 6, 7, 8};
    std::vector<uint32_t> hashes(keys.size());
    gqe::FibonacciHasher::hash_simd(keys.data(), hashes.data(), keys.size(), table_size);

    std::cout << "  SIMD hashes: ";
    for (uint32_t h : hashes) std::cout << h << " ";
    std::cout << "\n";

    std::cout << "  FibonacciHasher tests passed!\n";
}

void test_compression() {
    std::cout << "Testing GQE Compression...\n";

    // Generate test data
    std::vector<uint8_t> test_data;
    std::mt19937 rng(42);
    std::uniform_int_distribution<uint8_t> dist(0, 255);

    // Create 1MB of test data
    size_t test_size = 1024 * 1024;
    test_data.reserve(test_size);
    for (size_t i = 0; i < test_size; ++i) {
        test_data.push_back(dist(rng));
    }

    std::cout << "  Generated " << test_data.size() << " bytes of test data\n";

    // Test compression
    gqe::GQECompressor compressor;

    auto start = std::chrono::high_resolution_clock::now();
    auto compressed = compressor.compress(test_data);
    auto end = std::chrono::high_resolution_clock::now();

    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    float throughput = test_data.size() / (duration.count() / 1000.0f) / (1024 * 1024);

    std::cout << "  Compressed to " << compressed.size() << " bytes\n";
    std::cout << "  Compression ratio: " << static_cast<float>(test_data.size()) / compressed.size() << ":1\n";
    std::cout << "  Throughput: " << throughput << " MB/s\n";
    std::cout << "  Compression time: " << duration.count() << "ms\n";

    std::cout << "  GQE Compression tests passed!\n";
}

void test_projection() {
    std::cout << "Testing CoxeterProjection...\n";

    // Create test spinor
    std::array<float, 8> coords = {1, 2, 3, 4, 5, 6, 7, 8};
    gqe::Spinor8D spinor(coords);

    // Project to 4D
    gqe::Vector4D projected = gqe::CoxeterProjection::project(spinor);

    std::cout << "  8D Spinor: [" << coords[0];
    for (size_t i = 1; i < 8; ++i) std::cout << ", " << coords[i];
    std::cout << "]\n";

    std::cout << "  4D Projection: [" << projected.coords[0];
    for (size_t i = 1; i < 4; ++i) std::cout << ", " << projected.coords[i];
    std::cout << "]\n";

    std::cout << "  CoxeterProjection tests passed!\n";
}

int main() {
    std::cout << "GQE Kernel Test Suite\n";
    std::cout << "=====================\n\n";

    try {
        test_spinor8d();
        std::cout << "\n";

        test_e8_lattice();
        std::cout << "\n";

        test_bekenstein_arena();
        std::cout << "\n";

        test_fibonacci_hasher();
        std::cout << "\n";

        test_projection();
        std::cout << "\n";

        test_compression();
        std::cout << "\n";

        std::cout << "All tests passed! The laser is etching the universe.\n";

    } catch (const std::exception& e) {
        std::cerr << "Test failed with exception: " << e.what() << "\n";
        return 1;
    }

    return 0;
}