#include "parser.h"
#include <cctype>
#include <cmath>
#include <sstream>

namespace rc::symbol {

void Parser::skip_whitespace() {
    while (pos_ < input_.size() && std::isspace(input_[pos_])) ++pos_;
}

char Parser::peek() {
    skip_whitespace();
    if (pos_ >= input_.size()) return '\0';
    return input_[pos_];
}

char Parser::advance() {
    skip_whitespace();
    if (pos_ >= input_.size()) return '\0';
    return input_[pos_++];
}

bool Parser::match(char c) {
    if (peek() == c) {
        advance();
        return true;
    }
    return false;
}

bool Parser::match_keyword(const std::string& kw) {
    skip_whitespace();
    if (pos_ + kw.size() > input_.size()) return false;
    if (input_.substr(pos_, kw.size()) != kw) return false;
    // Must not be followed by alphanumeric (to avoid partial match)
    char next = (pos_ + kw.size() < input_.size()) ? input_[pos_ + kw.size()] : '\0';
    if (std::isalnum(next) || next == '_') return false;
    pos_ += kw.size();
    return true;
}

bool Parser::is_at_end() {
    skip_whitespace();
    return pos_ >= input_.size();
}

Expression::Ptr Parser::parse(const std::string& input) {
    input_ = input;
    pos_ = 0;
    auto result = parse_expression();
    if (!is_at_end()) {
        throw ParseError("Unexpected character at position " + std::to_string(pos_) +
                         ": '" + std::string(1, input_[pos_]) + "'");
    }
    return result;
}

// expression = additive
Expression::Ptr Parser::parse_expression() {
    return parse_additive();
}

// additive = multiplicative (('+' | '-') multiplicative)*
Expression::Ptr Parser::parse_additive() {
    auto left = parse_multiplicative();
    while (true) {
        if (match('+')) {
            auto right = parse_multiplicative();
            left = add(std::move(left), std::move(right));
        } else if (match('-')) {
            auto right = parse_multiplicative();
            left = add(std::move(left), neg(std::move(right)));
        } else {
            break;
        }
    }
    return left;
}

// multiplicative = unary (('*' | '/') unary)*
Expression::Ptr Parser::parse_multiplicative() {
    auto left = parse_unary();
    while (true) {
        if (match('*')) {
            auto right = parse_unary();
            left = mul(std::move(left), std::move(right));
        } else if (match('/')) {
            auto right = parse_unary();
            left = mul(std::move(left), pow(std::move(right), number(-1)));
        } else {
            break;
        }
    }
    return left;
}

// unary = '-' unary | power
Expression::Ptr Parser::parse_unary() {
    if (match('-')) {
        auto operand = parse_unary();
        // Optimize: -number -> -number
        if (operand->type() == NodeType::Number) {
            return number(-dynamic_cast<Number*>(operand.get())->value());
        }
        return neg(std::move(operand));
    }
    if (match('+')) {
        return parse_unary();
    }
    return parse_power();
}

// power = primary ('^' unary)?   (right-associative)
Expression::Ptr Parser::parse_power() {
    auto base = parse_primary();
    if (match('^')) {
        auto exp = parse_unary();  // right-associative: 2^3^2 = 2^(3^2)
        return pow(std::move(base), std::move(exp));
    }
    return base;
}

// primary = number | symbol_or_func | '(' expression ')'
Expression::Ptr Parser::parse_primary() {
    skip_whitespace();
    if (pos_ >= input_.size()) {
        throw ParseError("Unexpected end of expression");
    }

    char c = input_[pos_];

    // Parenthesized expression
    if (c == '(') {
        advance();
        auto expr = parse_expression();
        if (!match(')')) {
            throw ParseError("Expected ')' at position " + std::to_string(pos_));
        }
        return expr;
    }

    // Number
    if (std::isdigit(c) || c == '.') {
        size_t start = pos_;
        while (pos_ < input_.size() && (std::isdigit(input_[pos_]) || input_[pos_] == '.')) {
            ++pos_;
        }
        // Handle scientific notation: 1e-3, 2.5E10
        if (pos_ < input_.size() && (input_[pos_] == 'e' || input_[pos_] == 'E')) {
            ++pos_;
            if (pos_ < input_.size() && (input_[pos_] == '+' || input_[pos_] == '-')) ++pos_;
            while (pos_ < input_.size() && std::isdigit(input_[pos_])) ++pos_;
        }
        std::string num_str = input_.substr(start, pos_ - start);
        try {
            double val = std::stod(num_str);
            return number(val);
        } catch (...) {
            throw ParseError("Invalid number: " + num_str);
        }
    }

    // Symbol or function
    if (std::isalpha(c) || c == '_') {
        size_t start = pos_;
        while (pos_ < input_.size() && (std::isalnum(input_[pos_]) || input_[pos_] == '_')) {
            ++pos_;
        }
        std::string name = input_.substr(start, pos_ - start);

        // Check if it's a function call
        if (peek() == '(') {
            advance();  // consume '('
            std::vector<Expression::Ptr> args;
            if (peek() != ')') {
                args.push_back(parse_expression());
                while (match(',')) {
                    args.push_back(parse_expression());
                }
            }
            if (!match(')')) {
                throw ParseError("Expected ')' after function arguments at position " +
                                 std::to_string(pos_));
            }

            // Built-in functions
            if (name == "sin" || name == "cos" || name == "tan" ||
                name == "sqrt" || name == "exp" || name == "log" ||
                name == "asin" || name == "acos" || name == "atan") {
                if (args.size() != 1) {
                    throw ParseError(name + "() requires exactly 1 argument");
                }
                if (name == "sqrt") {
                    return pow(std::move(args[0]), number(0.5));
                }
                if (name == "exp") {
                    return func("exp", std::move(args));
                }
                return func(name, std::move(args));
            }

            // Generic function — allow any name
            return func(name, std::move(args));
        }

        // Known constants
        if (name == "pi") return func("pi", {});
        if (name == "Pi") return func("pi", {});
        if (name == "e" && (pos_ >= input_.size() || !std::isdigit(input_[pos_]))) {
            return func("exp", {number(1)});
        }

        // Regular symbol
        return symbol(name);
    }

    throw ParseError(std::string("Unexpected character: '") + c + "' at position " +
                     std::to_string(pos_));
}

} // namespace rc::symbol
