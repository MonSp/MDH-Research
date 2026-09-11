#include "differentiator.h"

namespace rc::symbol {

Expression::Ptr Differentiator::diff(const Expression::Ptr& expr, const std::string& var) {
    return expr->diff(var);
}

} // namespace rc::symbol
