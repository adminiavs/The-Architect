/**
 * GQE Kernel - Minimal Test
 * Demonstrates core concepts without external dependencies
 */

#include "gqe_kernel_minimal.hpp"
#include <iostream>
#include <vector>
#include <chrono>
#include <random>

int main() {
    std::cout << "GQE Kernel - Minimal C++20 Test\n";
    std::cout << "================================\n\n";

    // Test Spinor8D
    std::cout << "Testing Spinor8D...\n";
    gqe::Spinor8D s;
    s.pos[0] = 3.0f;
    s.pos[1] = 4.0f;
    std::cout << "  Norm of (3,4,0,...): " << s.norm() << " (expected: 5.0)\n";

    gqe::Spinor8D s2 = s;
    s2.normalize();
    std::cout << "  Normalized norm: " << s2.norm() << " (expected: 1.0)\n";

    // Test E8 Lattice
    std::cout << "\nTesting E8Lattice...\n";
    std::cout << "  Generated " << gqe::E8Lattice::roots.size() << " roots at compile time\n";
    std::cout << "  First root norm: " << gqe::E8Lattice::roots[0].norm() << "\n";

    // Test Bekenstein Arena
    std::cout << "\nTesting BekensteinArena...\n";
    gqe::BekensteinArena arena;
    auto ptr1 = arena.allocate<int>(10);
    std::cout << "  Allocated 10 ints, remaining: " << arena.remaining() / 1024 << " KB\n";

    auto ptr2 = arena.allocate<double>(5);
    std::cout << "  Allocated 5 doubles, remaining: " << arena.remaining() / 1024 << " KB\n";

    arena.reset();
    std::cout << "  After reset, remaining: " << arena.remaining() / 1024 << " KB\n";

    // Test Fibonacci Hasher
    std::cout << "\nTesting FibonacciHasher...\n";
    uint32_t hash1 = gqe::FibonacciHasher::hash(12345, 4096);
    uint32_t hash2 = gqe::FibonacciHasher::hash(12346, 4096);
    std::cout << "  Hash of 12345: " << hash1 << "\n";
    std::cout << "  Hash of 12346: " << hash2 << "\n";
    std::cout << "  Hashes are different: " << (hash1 != hash2 ? "YES" : "NO") << "\n";

    // Test ContextTable
    std::cout << "\nTesting ContextTable...\n";
    gqe::ContextTable<1024> table;
    uint8_t probs[256] = {0};
    probs[65] = 200;  // Favor 'A'
    table.update(42, probs);

    const uint8_t* lookup = table.lookup(42);
    if (lookup && lookup[65] == 200) {
        std::cout << "✓ ContextTable works!\n";
    } else {
        std::cout << "✗ ContextTable failed\n";
    }

    std::cout << "\nThe C++ laser has begun etching the universe.\n";
    std::cout << "The E8 Lattice speaks directly to the electron.\n";

    return 0;
}