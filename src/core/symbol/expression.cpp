#include "expression.h"
#include <cmath>
#include <sstream>

namespace rc::symbol {

// Number
std::string Number::to_string() const {
    if (value_ == static_cast<int>(value_)) {
        return std::to_string(static_cast<int>(value_));
    }
    std::ostringstream oss;
    oss << value_;
    return oss.str();
}

bool Number::equals(const Expression& other) const {
    auto* p = dynamic_cast<const Number*>(&other);
    return p && p->value_ == value_;
}

Expression::Ptr Number::simplify() const { return clone(); }

Expression::Ptr Number::diff(const std::string&) const { return number(0); }

Expression::Ptr Number::clone() const { return std::make_shared<Number>(value_); }

// Symbol
std::string Symbol::to_string() const { return name_; }

bool Symbol::equals(const Expression& other) const {
    auto* p = dynamic_cast<const Symbol*>(&other);
    return p && p->name_ == name_;
}

Expression::Ptr Symbol::simplify() const { return clone(); }

Expression::Ptr Symbol::diff(const std::string& var) const {
    return number(name_ == var ? 1.0 : 0.0);
}

Expression::Ptr Symbol::clone() const { return std::make_shared<Symbol>(name_); }

double Symbol::evaluate(const std::unordered_map<std::string, double>& vars) const {
    auto it = vars.find(name_);
    if (it != vars.end()) return it->second;
    return 0.0; // undefined variables default to 0
}

// BinaryOp
std::string BinaryOp::to_string() const {
    std::string op;
    switch (op_) {
        case NodeType::Add: op = " + "; break;
        case NodeType::Mul: op = " * "; break;
        case NodeType::Pow: op = "^"; break;
        default: op = " ? "; break;
    }
    return "(" + lhs_->to_string() + op + rhs_->to_string() + ")";
}

bool BinaryOp::equals(const Expression& other) const {
    auto* p = dynamic_cast<const BinaryOp*>(&other);
    return p && p->op_ == op_ && lhs_->equals(*p->lhs_) && rhs_->equals(*p->rhs_);
}

Expression::Ptr BinaryOp::simplify() const {
    auto l = lhs_->simplify();
    auto r = rhs_->simplify();

    // Constant folding
    if (l->type() == NodeType::Number && r->type() == NodeType::Number) {
        auto lv = dynamic_cast<Number*>(l.get())->value();
        auto rv = dynamic_cast<Number*>(r.get())->value();
        switch (op_) {
            case NodeType::Add: return number(lv + rv);
            case NodeType::Mul: return number(lv * rv);
            case NodeType::Pow: return number(std::pow(lv, rv));
            default: break;
        }
    }

    // Identity simplification
    switch (op_) {
        case NodeType::Add:
            if (l->is_zero()) return r;
            if (r->is_zero()) return l;
            break;
        case NodeType::Mul:
            if (l->is_zero() || r->is_zero()) return number(0);
            if (l->is_one()) return r;
            if (r->is_one()) return l;
            break;
        case NodeType::Pow:
            if (r->is_zero()) return number(1);
            if (r->is_one()) return l;
            if (l->is_one()) return number(1);
            break;
        default:
            break;
    }

    return std::make_shared<BinaryOp>(op_, std::move(l), std::move(r));
}

Expression::Ptr BinaryOp::diff(const std::string& var) const {
    auto dl = lhs_->diff(var);
    auto dr = rhs_->diff(var);

    switch (op_) {
        case NodeType::Add:
            return add(dl, dr);
        case NodeType::Mul:
            // Product rule: (f*g)' = f'*g + f*g'
            return add(mul(dl, rhs_->clone()), mul(lhs_->clone(), dr));
        case NodeType::Pow: {
            // Power rule for f(x)^n: n * f(x)^(n-1) * f'(x)
            // General: f^g = f^g * (g'*ln(f) + g*f'/f)
            auto base = lhs_->clone();
            auto exp = rhs_->clone();
            auto n_minus_1 = add(exp->clone(), number(-1));
            return mul(
                mul(exp->clone(), pow(base->clone(), n_minus_1)),
                dl
            );
        }
        default:
            return number(0);
    }
}

Expression::Ptr BinaryOp::clone() const {
    return std::make_shared<BinaryOp>(op_, lhs_->clone(), rhs_->clone());
}

double BinaryOp::evaluate(const std::unordered_map<std::string, double>& vars) const {
    double l = lhs_->evaluate(vars);
    double r = rhs_->evaluate(vars);
    switch (op_) {
        case NodeType::Add: return l + r;
        case NodeType::Mul: return l * r;
        case NodeType::Pow: return std::pow(l, r);
        default: return 0.0;
    }
}

// Neg
std::string Neg::to_string() const { return "(-" + operand_->to_string() + ")"; }

bool Neg::equals(const Expression& other) const {
    auto* p = dynamic_cast<const Neg*>(&other);
    return p && operand_->equals(*p->operand_);
}

Expression::Ptr Neg::simplify() const {
    auto op = operand_->simplify();
    if (op->type() == NodeType::Number) {
        return number(-dynamic_cast<Number*>(op.get())->value());
    }
    return std::make_shared<Neg>(std::move(op));
}

Expression::Ptr Neg::diff(const std::string& var) const {
    return neg(operand_->diff(var));
}

Expression::Ptr Neg::clone() const {
    return std::make_shared<Neg>(operand_->clone());
}

double Neg::evaluate(const std::unordered_map<std::string, double>& vars) const {
    return -operand_->evaluate(vars);
}

// Func
std::string Func::to_string() const {
    std::string s = name_ + "(";
    for (size_t i = 0; i < args_.size(); ++i) {
        if (i > 0) s += ", ";
        s += args_[i]->to_string();
    }
    return s + ")";
}

bool Func::equals(const Expression& other) const {
    auto* p = dynamic_cast<const Func*>(&other);
    if (!p || p->name_ != name_ || p->args_.size() != args_.size()) return false;
    for (size_t i = 0; i < args_.size(); ++i) {
        if (!args_[i]->equals(*p->args_[i])) return false;
    }
    return true;
}

Expression::Ptr Func::simplify() const {
    std::vector<Ptr> simplified;
    simplified.reserve(args_.size());
    for (const auto& a : args_) {
        simplified.push_back(a->simplify());
    }
    return std::make_shared<Func>(name_, std::move(simplified));
}

Expression::Ptr Func::diff(const std::string& var) const {
    if (args_.size() != 1) return number(0);

    auto f = args_[0]->clone();
    auto df = args_[0]->diff(var);

    if (name_ == "sin") {
        return mul(func("cos", {f}), df);
    }
    if (name_ == "cos") {
        return neg(mul(func("sin", {f}), df));
    }
    if (name_ == "tan") {
        // d/dx tan(f) = sec^2(f) * f' = (1 + tan^2(f)) * f'
        return mul(add(number(1), pow(func("tan", {f}), number(2))), df);
    }
    if (name_ == "sinh") {
        return mul(func("cosh", {f}), df);
    }
    if (name_ == "cosh") {
        return mul(func("sinh", {f}), df);
    }
    if (name_ == "tanh") {
        // d/dx tanh(f) = (1 - tanh^2(f)) * f'
        return mul(add(number(1), neg(pow(func("tanh", {f}), number(2)))), df);
    }
    return number(0); // Default: treat as constant
}

Expression::Ptr Func::clone() const {
    std::vector<Ptr> cloned;
    cloned.reserve(args_.size());
    for (const auto& a : args_) {
        cloned.push_back(a->clone());
    }
    return std::make_shared<Func>(name_, std::move(cloned));
}

double Func::evaluate(const std::unordered_map<std::string, double>& vars) const {
    if (args_.empty()) {
        if (name_ == "pi") return M_PI;
        return 0.0;
    }
    double a = args_[0]->evaluate(vars);
    if (name_ == "sin") return std::sin(a);
    if (name_ == "cos") return std::cos(a);
    if (name_ == "tan") return std::tan(a);
    if (name_ == "sinh") return std::sinh(a);
    if (name_ == "cosh") return std::cosh(a);
    if (name_ == "tanh") return std::tanh(a);
    if (name_ == "exp") return std::exp(a);
    if (name_ == "log") return std::log(a);
    if (name_ == "asin") return std::asin(a);
    if (name_ == "acos") return std::acos(a);
    if (name_ == "atan") return std::atan(a);
    return 0.0;
}

} // namespace rc::symbol
