cmake_minimum_required(VERSION 3.16)
project(research_core VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Symbol engine
add_library(symbol_engine STATIC
    src/core/symbol/expression.cpp
    src/core/symbol/simplifier.cpp
    src/core/symbol/differentiator.cpp
)
target_include_directories(symbol_engine PUBLIC src/core/symbol)

# Tensor calculator
add_library(tensor_calc STATIC
    src/core/tensor/tensor.cpp
    src/core/tensor/operations.cpp
    src/core/tensor/index.cpp
)
target_include_directories(tensor_calc PUBLIC src/core/tensor)
target_link_libraries(tensor_calc PUBLIC symbol_engine)

# Geometry core
add_library(geometry_core STATIC
    src/core/geometry/geometry.cpp
)
target_include_directories(geometry_core PUBLIC src/core/geometry)
target_link_libraries(geometry_core PUBLIC tensor_calc)

# Main library
add_library(research_core STATIC
    src/core/research_core.cpp
)
target_include_directories(research_core PUBLIC src/core)
target_link_libraries(research_core PUBLIC geometry_core)

# Tests
option(BUILD_TESTS "Build tests" ON)
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests/cpp)
endif()

# Python bindings
option(BUILD_PYTHON_BINDINGS "Build pybind11 bindings" ON)
if(BUILD_PYTHON_BINDINGS)
    add_subdirectory(src/bindings)
endif()
