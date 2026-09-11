#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include "parser.h"

using namespace rc::symbol;

TEST_CASE("Parse integer", "[parser]") {
    Parser p;
    auto expr = p.parse("42");
    REQUIRE(expr->type() == NodeType::Number);
    REQUIRE(dynamic_cast<Number*>(expr.get())->value() == 42.0);
}

TEST_CASE("Parse decimal", "[parser]") {
    Parser p;
    auto expr = p.parse("3.14");
    REQUIRE(expr->type() == NodeType::Number);
    REQUIRE(dynamic_cast<Number*>(expr.get())->value() == Catch::Approx(3.14));
}

TEST_CASE("Parse symbol", "[parser]") {
    Parser p;
    auto expr = p.parse("x");
    REQUIRE(expr->type() == NodeType::Symbol);
    REQUIRE(expr->to_string() == "x");
}

TEST_CASE("Parse multi-char symbol", "[parser]") {
    Parser p;
    auto expr = p.parse("theta");
    REQUIRE(expr->type() == NodeType::Symbol);
    REQUIRE(expr->to_string() == "theta");
}

TEST_CASE("Parse addition", "[parser]") {
    Parser p;
    auto expr = p.parse("3 + 4");
    auto simplified = expr->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 7.0);
}

TEST_CASE("Parse subtraction", "[parser]") {
    Parser p;
    auto expr = p.parse("10 - 3");
    auto simplified = expr->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 7.0);
}

TEST_CASE("Parse multiplication", "[parser]") {
    Parser p;
    auto expr = p.parse("3 * 4");
    auto simplified = expr->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 12.0);
}

TEST_CASE("Parse division as inverse", "[parser]") {
    Parser p;
    auto expr = p.parse("6 / 3");
    auto simplified = expr->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == Catch::Approx(2.0));
}

TEST_CASE("Parse power", "[parser]") {
    Parser p;
    auto expr = p.parse("2 ^ 3");
    auto simplified = expr->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 8.0);
}

TEST_CASE("Parse parenthesized expression", "[parser]") {
    Parser p;
    auto expr = p.parse("(3 + 4) * 2");
    auto simplified = expr->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 14.0);
}

TEST_CASE("Operator precedence: * before +", "[parser]") {
    Parser p;
    auto expr = p.parse("2 + 3 * 4");
    auto simplified = expr->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 14.0);
}

TEST_CASE("Operator precedence: ^ before *", "[parser]") {
    Parser p;
    auto expr = p.parse("2 * 3 ^ 2");
    auto simplified = expr->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 18.0);
}

TEST_CASE("Unary minus", "[parser]") {
    Parser p;
    auto expr = p.parse("-5");
    auto simplified = expr->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == -5.0);
}

TEST_CASE("Unary minus in expression", "[parser]") {
    Parser p;
    auto expr = p.parse("3 + -2");
    auto simplified = expr->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 1.0);
}

TEST_CASE("Complex expression: (1-2*M/r)", "[parser]") {
    Parser p;
    auto expr = p.parse("1 - 2*M/r");
    // Should parse as 1 - ((2*M)/r)
    REQUIRE(expr->to_string() != "");
    // Test with M=1, r=4: 1 - 2/4 = 0.5
}

TEST_CASE("Function: sin", "[parser]") {
    Parser p;
    auto expr = p.parse("sin(x)");
    REQUIRE(expr->type() == NodeType::Func);
    REQUIRE(dynamic_cast<Func*>(expr.get())->name() == "sin");
}

TEST_CASE("Function: cos", "[parser]") {
    Parser p;
    auto expr = p.parse("cos(theta)");
    REQUIRE(expr->type() == NodeType::Func);
}

TEST_CASE("Function: sqrt as pow", "[parser]") {
    Parser p;
    auto expr = p.parse("sqrt(x)");
    REQUIRE(expr->type() == NodeType::Pow);
}

TEST_CASE("Nested function", "[parser]") {
    Parser p;
    auto expr = p.parse("sin(x)^2");
    REQUIRE(expr->type() == NodeType::Pow);
}

TEST_CASE("Complex: sin(theta)^2", "[parser]") {
    Parser p;
    auto expr = p.parse("sin(theta)^2");
    REQUIRE(expr->type() == NodeType::Pow);
    auto sin_part = dynamic_cast<BinaryOp*>(expr.get());
    REQUIRE(sin_part != nullptr);
}

TEST_CASE("Nested parentheses", "[parser]") {
    Parser p;
    auto expr = p.parse("((1 + 2) * (3 + 4))");
    auto simplified = expr->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 21.0);
}

TEST_CASE("Right-associative power", "[parser]") {
    Parser p;
    auto expr = p.parse("2^3^2");
    // 2^(3^2) = 2^9 = 512
    auto simplified = expr->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 512.0);
}

TEST_CASE("Division by expression", "[parser]") {
    Parser p;
    auto expr = p.parse("1 / (1 - 2*M/r)");
    REQUIRE(expr->type() == NodeType::Mul);  // a/b = a * b^(-1)
}

TEST_CASE("Parse error: unmatched paren", "[parser]") {
    Parser p;
    REQUIRE_THROWS_AS(p.parse("(1 + 2"), ParseError);
}

TEST_CASE("Parse error: empty input", "[parser]") {
    Parser p;
    REQUIRE_THROWS_AS(p.parse(""), ParseError);
}

TEST_CASE("Unknown function creates generic Func node", "[parser]") {
    Parser p;
    auto expr = p.parse("foo(x)");
    REQUIRE(expr->type() == NodeType::Func);
    REQUIRE(dynamic_cast<Func*>(expr.get())->name() == "foo");
}

TEST_CASE("Whitespace handling", "[parser]") {
    Parser p;
    auto expr = p.parse("  3  +  4  ");
    auto simplified = expr->simplify();
    REQUIRE(dynamic_cast<Number*>(simplified.get())->value() == 7.0);
}

TEST_CASE("Schwarzschild g_tt expression", "[parser]") {
    Parser p;
    auto expr = p.parse("-(1 - 2*M/r)");
    REQUIRE(expr != nullptr);
    // Should be a neg of an add
    REQUIRE(expr->type() == NodeType::Neg);
}

TEST_CASE("Schwarzschild g_rr expression", "[parser]") {
    Parser p;
    auto expr = p.parse("(1 - 2*M/r)^(-1)");
    REQUIRE(expr != nullptr);
    REQUIRE(expr->type() == NodeType::Pow);
}

TEST_CASE("FLRW scale factor expression", "[parser]") {
    Parser p;
    auto expr = p.parse("a(t)^2");
    REQUIRE(expr != nullptr);
    REQUIRE(expr->type() == NodeType::Pow);
}

TEST_CASE("Kerr delta expression", "[parser]") {
    Parser p;
    auto expr = p.parse("r^2 - 2*M*r + a^2");
    REQUIRE(expr != nullptr);
    // Should parse without error
    REQUIRE(expr->to_string() != "");
}
