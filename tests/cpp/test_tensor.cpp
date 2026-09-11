#include <catch2/catch_test_macros.hpp>
#include "tensor.h"
#include "operations.h"

using namespace rc::tensor;
using namespace rc::symbol;

TEST_CASE("Tensor creation", "[tensor]") {
    std::vector<int> dims = {3, 3};
    std::vector<Index> indices = {
        {"mu", IndexType::Lower},
        {"nu", IndexType::Lower},
    };
    auto t = Tensor(2, dims, indices);

    REQUIRE(t.rank() == 2);
    REQUIRE(t.dimensions() == dims);
}

TEST_CASE("Tensor component access", "[tensor]") {
    std::vector<int> dims = {2, 2};
    std::vector<Index> indices = {
        {"i", IndexType::Lower},
        {"j", IndexType::Lower},
    };
    auto t = Tensor(2, dims, indices);

    t.at({0, 0}) = number(1);
    t.at({0, 1}) = number(2);
    t.at({1, 0}) = number(3);
    t.at({1, 1}) = number(4);

    REQUIRE(t.at({0, 0})->equals(*number(1)));
    REQUIRE(t.at({1, 1})->equals(*number(4)));
}

TEST_CASE("Tensor index out of bounds", "[tensor]") {
    std::vector<int> dims = {2, 2};
    std::vector<Index> indices = {
        {"i", IndexType::Lower},
        {"j", IndexType::Lower},
    };
    auto t = Tensor(2, dims, indices);

    REQUIRE_THROWS_AS(t.at({2, 0}), std::out_of_range);
    REQUIRE_THROWS_AS(t.at({0, -1}), std::out_of_range);
}

TEST_CASE("Tensor raise/lower index", "[tensor]") {
    std::vector<int> dims = {2, 2};
    std::vector<Index> indices = {
        {"mu", IndexType::Lower},
        {"nu", IndexType::Lower},
    };
    auto t = Tensor(2, dims, indices);
    t.at({0, 0}) = number(1);
    t.at({1, 1}) = number(2);

    auto raised = t.raise_index(0);
    REQUIRE(raised->indices()[0].type == IndexType::Upper);
    REQUIRE(raised->indices()[1].type == IndexType::Lower);
    REQUIRE(raised->at({0, 0})->equals(*number(1)));
}

TEST_CASE("Tensor contraction", "[tensor]") {
    // 2x2 identity-like tensor with one upper, one lower index
    std::vector<int> dims = {2, 2};
    std::vector<Index> indices = {
        {"mu", IndexType::Upper},
        {"nu", IndexType::Lower},
    };
    auto t = Tensor(2, dims, indices);
    t.at({0, 0}) = number(1);
    t.at({0, 1}) = number(0);
    t.at({1, 0}) = number(0);
    t.at({1, 1}) = number(1);

    // Contract: sum of diagonal = 2
    auto scalar = t.contract(0, 1);
    REQUIRE(scalar->rank() == 0);
    // For rank-0 tensor, we need to access the single element
    // The flat index for {} is 0
    REQUIRE(scalar->at({})->equals(*number(2)));
}

TEST_CASE("Tensor product", "[tensor]") {
    std::vector<int> dims_a = {2};
    std::vector<Index> indices_a = {{"i", IndexType::Lower}};
    auto a = std::make_shared<Tensor>(1, dims_a, indices_a);
    a->at({0}) = number(1);
    a->at({1}) = number(2);

    std::vector<int> dims_b = {2};
    std::vector<Index> indices_b = {{"j", IndexType::Lower}};
    auto b = std::make_shared<Tensor>(1, dims_b, indices_b);
    b->at({0}) = number(3);
    b->at({1}) = number(4);

    auto product = TensorOperations::tensor_product(a, b);
    REQUIRE(product->rank() == 2);
    REQUIRE(product->at({0, 0})->equals(*number(3)));
    REQUIRE(product->at({0, 1})->equals(*number(4)));
    REQUIRE(product->at({1, 0})->equals(*number(6)));
    REQUIRE(product->at({1, 1})->equals(*number(8)));
}

TEST_CASE("Tensor to_string", "[tensor]") {
    std::vector<int> dims = {2, 2};
    std::vector<Index> indices = {
        {"mu", IndexType::Upper},
        {"nu", IndexType::Lower},
    };
    auto t = Tensor(2, dims, indices);
    auto s = t.to_string();
    REQUIRE(s.find("^mu") != std::string::npos);
    REQUIRE(s.find("_nu") != std::string::npos);
}
