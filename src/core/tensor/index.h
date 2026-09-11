#pragma once

#include "tensor.h"

namespace rc::tensor {

class IndexHelper {
public:
    static std::string type_string(IndexType t) {
        return t == IndexType::Upper ? "upper" : "lower";
    }

    static bool is_contractible(const Index& a, const Index& b) {
        return (a.type == IndexType::Upper && b.type == IndexType::Lower) ||
               (a.type == IndexType::Lower && b.type == IndexType::Upper);
    }
};

} // namespace rc::tensor
