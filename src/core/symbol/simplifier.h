#pragma once

#include "expression.h"

namespace rc::symbol {

class Simplifier {
public:
    Expression::Ptr simplify(const Expression::Ptr& expr);
};

} // namespace rc::symbol
