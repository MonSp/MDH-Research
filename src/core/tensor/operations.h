#pragma once

#include "tensor.h"

namespace rc::tensor {

class TensorOperations {
public:
    // Tensor product (outer product)
    static Tensor::Ptr tensor_product(const Tensor::Ptr& a, const Tensor::Ptr& b);

    // Contraction of two tensors on specified indices
    static Tensor::Ptr contract(const Tensor::Ptr& a, int a_idx,
                                 const Tensor::Ptr& b, int b_idx);
};

} // namespace rc::tensor
