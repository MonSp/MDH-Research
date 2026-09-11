#include "operations.h"

namespace rc::tensor {

Tensor::Ptr TensorOperations::tensor_product(const Tensor::Ptr& a, const Tensor::Ptr& b) {
    int new_rank = a->rank() + b->rank();
    std::vector<int> new_dims;
    std::vector<Index> new_indices;

    for (int i = 0; i < a->rank(); ++i) {
        new_dims.push_back(a->dimensions()[i]);
        new_indices.push_back(a->indices()[i]);
    }
    for (int i = 0; i < b->rank(); ++i) {
        new_dims.push_back(b->dimensions()[i]);
        new_indices.push_back(b->indices()[i]);
    }

    auto result = std::make_shared<Tensor>(new_rank, new_dims, new_indices);

    // Iterate over all positions
    int total = 1;
    for (int d : new_dims) total *= d;

    for (int flat = 0; flat < total; ++flat) {
        int tmp = flat;
        std::vector<int> pos(new_rank);
        for (int i = new_rank - 1; i >= 0; --i) {
            pos[i] = tmp % new_dims[i];
            tmp /= new_dims[i];
        }

        std::vector<int> a_pos(a->rank()), b_pos(b->rank());
        for (int i = 0; i < a->rank(); ++i) a_pos[i] = pos[i];
        for (int i = 0; i < b->rank(); ++i) b_pos[i] = pos[a->rank() + i];

        result->at(pos) = symbol::mul(a->at(a_pos), b->at(b_pos))->simplify();
    }

    return result;
}

Tensor::Ptr TensorOperations::contract(const Tensor::Ptr& a, int a_idx,
                                         const Tensor::Ptr& b, int b_idx) {
    // First take tensor product, then contract
    auto product = tensor_product(a, b);
    // The b index in the product is at position a->rank() + b_idx
    return product->contract(a_idx, a->rank() + b_idx);
}

} // namespace rc::tensor
