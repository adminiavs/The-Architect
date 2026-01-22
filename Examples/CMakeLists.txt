cmake_minimum_required(VERSION 3.20)
project(GQE_Kernel VERSION 1.0.0 LANGUAGES CXX)

# Require C++20
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Optimization flags - etching the universe with a laser
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native -mtune=native")

# Enable LTO (Link Time Optimization)
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)

# SIMD and vectorization flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -mavx512f -mavx512bw -mavx512dq")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -mavx2 -mfma")

# Enable fast math (careful with floating point precision)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -ffast-math -funroll-loops")

# Warning flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Wpedantic")

# Find required dependencies
find_package(Eigen3 3.4 REQUIRED)

# Create the main library (header-only)
add_library(gqe_kernel INTERFACE)
target_include_directories(gqe_kernel INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>
)
target_link_libraries(gqe_kernel INTERFACE Eigen3::Eigen)

# Create benchmark executable
add_executable(gqe_benchmark benchmark.cpp)
target_link_libraries(gqe_benchmark PRIVATE gqe_kernel)

# Create test executable
add_executable(gqe_test test.cpp)
target_link_libraries(gqe_test PRIVATE gqe_kernel)

# Install headers
install(FILES gqe_kernel.hpp
    DESTINATION include
)

# Install targets
install(TARGETS gqe_kernel
    EXPORT GQEKerneTargets
    INCLUDES DESTINATION include
)

# Generate and install config files
include(CMakePackageConfigHelpers)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/GQEKerneConfigVersion.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

configure_package_config_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/GQEKerneConfig.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/GQEKerneConfig.cmake"
    INSTALL_DESTINATION lib/cmake/GQEKerne
)

install(EXPORT GQEKerneTargets
    FILE GQEKerneTargets.cmake
    NAMESPACE GQEKerne::
    DESTINATION lib/cmake/GQEKerne
)

install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/GQEKerneConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/GQEKerneConfigVersion.cmake"
    DESTINATION lib/cmake/GQEKerne
)