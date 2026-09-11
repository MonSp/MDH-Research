#include <catch2/catch_test_macros.hpp>
#include "expression.h"

using namespace rc::symbol;

TEST_CASE("Number creation and properties", "[symbol]") {
    auto n = number(42.0);
    REQUIRE(n->type() == NodeType::Number);
    REQUIRE(n->to_string() == "42");
    REQUIRE_FALSE(n->is_zero());
    REQUIRE_FALSE(n->is_one());

    auto zero = number(0.0);
    REQUIRE(zero->is_zero());

    auto one = number(1.0);
    REQUIRE(one->is_one());
}

TEST_CASE("Symbol creation and properties", "[symbol]") {
    auto x = symbol("x");
    REQUIRE(x->type() == NodeType::Symbol);
    REQUIRE(x->to_string() == "x");
}

TEST_CASE("Symbol equality", "[symbol]") {
    auto x1 = symbol("x");
    auto x2 = symbol("x");
    auto y = symbol("y");

    REQUIRE(x1->equals(*x2));
    REQUIRE_FALSE(x1->equals(*y));
}

TEST_CASE("Number equality", "[symbol]") {
    auto a = number(3.0);
    auto b = number(3.0);
    auto c = number(4.0);

    REQUIRE(a->equals(*b));
    REQUIRE_FALSE(a->equals(*c));
}

TEST_CASE("Addition simplification", "[symbol]") {
    auto sum = add(number(3), number(4));
    auto simplified = sum->simplify();
    REQUIRE(simplified->type() == NodeType::Number);
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 7.0);
}

TEST_CASE("Multiplication simplification", "[symbol]") {
    auto prod = mul(number(3), number(4));
    auto simplified = prod->simplify();
    REQUIRE(simplified->type() == NodeType::Number);
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 12.0);
}

TEST_CASE("Power simplification", "[symbol]") {
    auto p = pow(number(2), number(3));
    auto simplified = p->simplify();
    REQUIRE(simplified->type() == NodeType::Number);
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 8.0);
}

TEST_CASE("Identity simplifications", "[symbol]") {
    auto x = symbol("x");

    // x + 0 = x
    auto sum_zero = add(x->clone(), number(0));
    REQUIRE(sum_zero->simplify()->equals(*x));

    // x * 1 = x
    auto mul_one = mul(x->clone(), number(1));
    REQUIRE(mul_one->simplify()->equals(*x));

    // x * 0 = 0
    auto mul_zero = mul(x->clone(), number(0));
    REQUIRE(mul_zero->simplify()->is_zero());
}

TEST_CASE("Differentiation of symbol", "[symbol]") {
    auto x = symbol("x");
    auto y = symbol("y");

    // dx/dx = 1
    auto dx = x->diff("x");
    REQUIRE(dx->is_one());

    // dy/dx = 0
    auto dy = y->diff("x");
    REQUIRE(dy->is_zero());
}

TEST_CASE("Differentiation of number", "[symbol]") {
    auto n = number(42);
    auto dn = n->diff("x");
    REQUIRE(dn->is_zero());
}

TEST_CASE("Product rule", "[symbol]") {
    // d/dx (x * x) = x + x (simplified from 1*x + x*1)
    auto x = symbol("x");
    auto expr = mul(x->clone(), x->clone());
    auto deriv = expr->diff("x");
    auto simplified = deriv->simplify();

    // Simplifier correctly reduces 1*x -> x
    REQUIRE(simplified->to_string() == "(x + x)");
}

TEST_CASE("Function creation", "[symbol]") {
    auto x = symbol("x");
    auto sin_x = func("sin", {x->clone()});
    REQUIRE(sin_x->to_string() == "sin(x)");

    auto sin_dx = sin_x->diff("x");
    REQUIRE(sin_dx->to_string() == "(cos(x) * 1)");
}

TEST_CASE("Expression clone", "[symbol]") {
    auto x = symbol("x");
    auto expr = add(x->clone(), number(5));
    auto cloned = expr->clone();

    REQUIRE(expr->equals(*cloned));
    REQUIRE(expr.get() != cloned.get());
}

TEST_CASE("Neg", "[symbol]") {
    auto x = symbol("x");
    auto neg_x = neg(x->clone());
    REQUIRE(neg_x->to_string() == "(-x)");

    auto simplified = neg(number(3))->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == -3.0);
}
