find_package(pybind11 REQUIRED)

pybind11_add_module(_research_core bindings.cpp)
target_include_directories(_research_core PRIVATE ${CMAKE_SOURCE_DIR}/src/core)
target_link_libraries(_research_core PRIVATE geometry_core)
