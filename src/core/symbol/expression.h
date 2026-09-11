#pragma once

#include <string>
#include <memory>
#include <vector>
#include <functional>
#include <unordered_map>

namespace rc::symbol {

enum class NodeType {
    Number,
    Symbol,
    Add,
    Mul,
    Pow,
    Neg,
    Func,
};

// Forward declare all classes
class Expression;
class Number;
class Symbol;
class BinaryOp;
class Neg;
class Func;

using ExprPtr = std::shared_ptr<Expression>;

class Expression : public std::enable_shared_from_this<Expression> {
public:
    using Ptr = std::shared_ptr<Expression>;

    virtual ~Expression() = default;
    virtual NodeType type() const = 0;
    virtual std::string to_string() const = 0;
    virtual bool equals(const Expression& other) const = 0;
    virtual Ptr simplify() const = 0;
    virtual Ptr diff(const std::string& var) const = 0;
    virtual Ptr clone() const = 0;
    virtual bool is_zero() const { return false; }
    virtual bool is_one() const { return false; }
    // Numerical evaluation: substitute variable values and compute
    virtual double evaluate(const std::unordered_map<std::string, double>& vars) const = 0;
};

class Number : public Expression {
public:
    explicit Number(double value) : value_(value) {}
    NodeType type() const override { return NodeType::Number; }
    double value() const { return value_; }
    std::string to_string() const override;
    bool equals(const Expression& other) const override;
    Ptr simplify() const override;
    Ptr diff(const std::string& var) const override;
    Ptr clone() const override;
    bool is_zero() const override { return value_ == 0.0; }
    bool is_one() const override { return value_ == 1.0; }
    double evaluate(const std::unordered_map<std::string, double>&) const override { return value_; }

private:
    double value_;
};

class Symbol : public Expression {
public:
    explicit Symbol(std::string name) : name_(std::move(name)) {}
    NodeType type() const override { return NodeType::Symbol; }
    const std::string& name() const { return name_; }
    std::string to_string() const override;
    bool equals(const Expression& other) const override;
    Ptr simplify() const override;
    Ptr diff(const std::string& var) const override;
    Ptr clone() const override;
    double evaluate(const std::unordered_map<std::string, double>& vars) const override;

private:
    std::string name_;
};

class BinaryOp : public Expression {
public:
    BinaryOp(NodeType op, Ptr lhs, Ptr rhs) : op_(op), lhs_(std::move(lhs)), rhs_(std::move(rhs)) {}
    NodeType type() const override { return op_; }
    const Ptr& lhs() const { return lhs_; }
    const Ptr& rhs() const { return rhs_; }
    std::string to_string() const override;
    bool equals(const Expression& other) const override;
    Ptr simplify() const override;
    Ptr diff(const std::string& var) const override;
    Ptr clone() const override;
    double evaluate(const std::unordered_map<std::string, double>& vars) const override;

private:
    NodeType op_;
    Ptr lhs_, rhs_;
};

class Neg : public Expression {
public:
    explicit Neg(Ptr operand) : operand_(std::move(operand)) {}
    NodeType type() const override { return NodeType::Neg; }
    const Ptr& operand() const { return operand_; }
    std::string to_string() const override;
    bool equals(const Expression& other) const override;
    Ptr simplify() const override;
    Ptr diff(const std::string& var) const override;
    Ptr clone() const override;
    double evaluate(const std::unordered_map<std::string, double>& vars) const override;

private:
    Ptr operand_;
};

class Func : public Expression {
public:
    Func(std::string name, std::vector<Ptr> args)
        : name_(std::move(name)), args_(std::move(args)) {}
    NodeType type() const override { return NodeType::Func; }
    const std::string& name() const { return name_; }
    const std::vector<Ptr>& args() const { return args_; }
    std::string to_string() const override;
    bool equals(const Expression& other) const override;
    Ptr simplify() const override;
    Ptr diff(const std::string& var) const override;
    Ptr clone() const override;
    double evaluate(const std::unordered_map<std::string, double>& vars) const override;

private:
    std::string name_;
    std::vector<Ptr> args_;
};

// Factory functions (defined after all classes are complete)
inline ExprPtr number(double v) { return std::make_shared<Number>(v); }
inline ExprPtr symbol(const std::string& name) { return std::make_shared<Symbol>(name); }
inline ExprPtr add(Expression::Ptr a, Expression::Ptr b) { return std::make_shared<BinaryOp>(NodeType::Add, std::move(a), std::move(b)); }
inline ExprPtr mul(Expression::Ptr a, Expression::Ptr b) { return std::make_shared<BinaryOp>(NodeType::Mul, std::move(a), std::move(b)); }
inline ExprPtr pow(Expression::Ptr base, Expression::Ptr exp) { return std::make_shared<BinaryOp>(NodeType::Pow, std::move(base), std::move(exp)); }
inline ExprPtr neg(Expression::Ptr a) { return std::make_shared<Neg>(std::move(a)); }
inline ExprPtr func(const std::string& name, std::vector<Expression::Ptr> args) { return std::make_shared<Func>(name, std::move(args)); }

} // namespace rc::symbol

namespace rc {
using ExprPtr = std::shared_ptr<symbol::Expression>;
}
