#pragma once

#include "expression.h"

namespace rc::symbol {

class Differentiator {
public:
    Expression::Ptr diff(const Expression::Ptr& expr, const std::string& var);
};

} // namespace rc::symbol
