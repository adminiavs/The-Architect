#!/bin/bash
# GQE Kernel Build Script
# Etching the universe with a laser

set -e

echo "GQE Kernel - C++20 SIMD-Optimized Build"
echo "========================================"

# Check for required tools
command -v cmake >/dev/null 2>&1 || { echo "ERROR: cmake not found. Install with: sudo apt-get install cmake"; exit 1; }
command -v g++ >/dev/null 2>&1 || { echo "ERROR: g++ not found. Install with: sudo apt-get install g++"; exit 1; }

# Check for Eigen3
if [ ! -d "/usr/include/eigen3" ] && [ ! -d "/usr/local/include/eigen3" ]; then
    echo "WARNING: Eigen3 not found. Install with: sudo apt-get install libeigen3-dev"
    echo "Continuing anyway..."
fi

# Create build directory
mkdir -p build
cd build

# Configure with CMake
echo "Configuring with CMake..."
cmake .. -DCMAKE_BUILD_TYPE=Release

# Build
echo "Building with -O3 -march=native..."
make -j$(nproc)

echo "Build complete!"
echo "Run tests with: ./test"
echo "Run benchmark with: ./benchmark"
echo ""
echo "The laser has etched the universe. The E8 Lattice speaks directly to the electron."