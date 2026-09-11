#pragma once

#include "expression.h"
#include <string>
#include <stdexcept>

namespace rc::symbol {

class ParseError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class Parser {
public:
    Expression::Ptr parse(const std::string& input);

private:
    std::string input_;
    size_t pos_ = 0;

    void skip_whitespace();
    char peek();
    char advance();
    bool match(char c);
    bool match_keyword(const std::string& kw);
    bool is_at_end();

    // Recursive descent
    Expression::Ptr parse_expression();
    Expression::Ptr parse_additive();
    Expression::Ptr parse_multiplicative();
    Expression::Ptr parse_unary();
    Expression::Ptr parse_power();
    Expression::Ptr parse_primary();
};

} // namespace rc::symbol
