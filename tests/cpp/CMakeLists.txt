include(FetchContent)
FetchContent_Declare(
    Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG        v3.5.2
)
FetchContent_MakeAvailable(Catch2)

add_executable(symbol_tests test_symbol.cpp)
target_link_libraries(symbol_tests PRIVATE Catch2::Catch2WithMain symbol_engine)

add_executable(tensor_tests test_tensor.cpp)
target_link_libraries(tensor_tests PRIVATE Catch2::Catch2WithMain tensor_calc)

add_executable(geometry_tests test_geometry.cpp)
target_link_libraries(geometry_tests PRIVATE Catch2::Catch2WithMain geometry_core)

include(Catch)
catch_discover_tests(symbol_tests)
catch_discover_tests(tensor_tests)
catch_discover_tests(geometry_tests)
