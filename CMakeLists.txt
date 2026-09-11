cmake_minimum_required(VERSION 3.16)
project(research_core
    VERSION 0.2.0
    LANGUAGES CXX
    DESCRIPTION "大荒界-科研: Symbolic computation engine for differential geometry"
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ---------- Symbol engine ----------
add_library(symbol_engine STATIC
    src/core/symbol/expression.cpp
    src/core/symbol/parser.cpp
)
target_include_directories(symbol_engine PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src/core/symbol>
    $<INSTALL_INTERFACE:include/research_core/symbol>
)

# ---------- Tensor calculator ----------
add_library(tensor_calc STATIC
    src/core/tensor/tensor.cpp
    src/core/tensor/operations.cpp
)
target_include_directories(tensor_calc PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src/core/tensor>
    $<INSTALL_INTERFACE:include/research_core/tensor>
)
target_link_libraries(tensor_calc PUBLIC symbol_engine)

# ---------- Geometry core ----------
add_library(geometry_core STATIC
    src/core/geometry/geometry.cpp
)
target_include_directories(geometry_core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src/core/geometry>
    $<INSTALL_INTERFACE:include/research_core/geometry>
)
target_link_libraries(geometry_core PUBLIC tensor_calc)

# ---------- Convenience alias ----------
# Single target that pulls in everything
add_library(research_core::all ALIAS geometry_core)

# ---------- Install ----------
include(GNUInstallDirs)

install(TARGETS symbol_engine tensor_calc geometry_core
    EXPORT research_coreTargets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)

install(DIRECTORY
    src/core/symbol/
    src/core/tensor/
    src/core/geometry/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/research_core
    FILES_MATCHING PATTERN "*.h"
)

install(EXPORT research_coreTargets
    FILE research_coreTargets.cmake
    NAMESPACE research_core::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/research_core
)

# Version config
include(CMakePackageConfigHelpers)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/research_coreConfigVersion.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

configure_package_config_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake/research_coreConfig.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/research_coreConfig.cmake"
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/research_core
)

install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/research_coreConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/research_coreConfigVersion.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/research_core
)

# ---------- Tests ----------
option(BUILD_TESTS "Build tests" ON)
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests/cpp)
endif()

# ---------- Python bindings ----------
option(BUILD_PYTHON_BINDINGS "Build pybind11 bindings" ON)
if(BUILD_PYTHON_BINDINGS)
    # Static libs need fPIC when linked into a shared Python module
    set_target_properties(symbol_engine tensor_calc geometry_core
        PROPERTIES POSITION_INDEPENDENT_CODE ON)
    add_subdirectory(src/bindings)
endif()
