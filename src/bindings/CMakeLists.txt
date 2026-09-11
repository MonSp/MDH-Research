find_package(pybind11 REQUIRED)

pybind11_add_module(_research_core bindings.cpp)
target_link_libraries(_research_core PRIVATE research_core)
