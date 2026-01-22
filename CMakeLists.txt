cmake_minimum_required(VERSION 3.20)
project(TheArchitect GQE)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Optimization flags for the laser etching
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    add_compile_options(-O3 -march=native -Wall -Wextra)
endif()

# Header-only library
add_library(gqe_kernel INTERFACE)
target_include_directories(gqe_kernel INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# Benchmark executable
add_executable(benchmark src/benchmark.cpp)
target_link_libraries(benchmark PRIVATE gqe_kernel)

# Test suite
add_executable(test_suite tests/test_suite.cpp)
target_link_libraries(test_suite PRIVATE gqe_kernel)

# Installation (optional, but good for completeness)
install(DIRECTORY include/ DESTINATION include)
