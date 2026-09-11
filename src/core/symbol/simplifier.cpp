#include "simplifier.h"

namespace rc::symbol {

Expression::Ptr Simplifier::simplify(const Expression::Ptr& expr) {
    return expr->simplify();
}

} // namespace rc::symbol
