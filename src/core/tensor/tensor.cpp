#include "tensor.h"
#include <sstream>
#include <stdexcept>
#include <numeric>

namespace rc::tensor {

Tensor::Tensor(int rank, std::vector<int> dimensions, std::vector<Index> indices)
    : rank_(rank), dimensions_(std::move(dimensions)), indices_(std::move(indices)) {
    int total = 1;
    for (int d : dimensions_) total *= d;
    components_.resize(total, symbol::number(0));
}

int Tensor::flat_index(const std::vector<int>& position) const {
    if (static_cast<int>(position.size()) != rank_) {
        throw std::invalid_argument("Position dimension mismatch");
    }
    int idx = 0;
    for (int i = 0; i < rank_; ++i) {
        if (position[i] < 0 || position[i] >= dimensions_[i]) {
            throw std::out_of_range("Index out of bounds");
        }
        idx = idx * dimensions_[i] + position[i];
    }
    return idx;
}

symbol::Expression::Ptr& Tensor::at(const std::vector<int>& position) {
    return components_[flat_index(position)];
}

const symbol::Expression::Ptr& Tensor::at(const std::vector<int>& position) const {
    return components_[flat_index(position)];
}

void Tensor::set_components(const std::vector<symbol::Expression::Ptr>& components) {
    if (static_cast<int>(components.size()) != static_cast<int>(components_.size())) {
        throw std::invalid_argument("Component count mismatch");
    }
    components_ = components;
}

Tensor::Ptr Tensor::raise_index(int pos) const {
    auto result = std::make_shared<Tensor>(rank_, dimensions_, indices_);
    result->components_ = components_;
    if (pos >= 0 && pos < rank_) {
        result->indices_[pos].type = IndexType::Upper;
    }
    return result;
}

Tensor::Ptr Tensor::lower_index(int pos) const {
    auto result = std::make_shared<Tensor>(rank_, dimensions_, indices_);
    result->components_ = components_;
    if (pos >= 0 && pos < rank_) {
        result->indices_[pos].type = IndexType::Lower;
    }
    return result;
}

Tensor::Ptr Tensor::contract(int upper_pos, int lower_pos) const {
    if (upper_pos < 0 || upper_pos >= rank_ || lower_pos < 0 || lower_pos >= rank_) {
        throw std::out_of_range("Contraction index out of range");
    }
    if (indices_[upper_pos].type != IndexType::Upper ||
        indices_[lower_pos].type != IndexType::Lower) {
        throw std::invalid_argument("Contraction requires one upper and one lower index");
    }
    if (dimensions_[upper_pos] != dimensions_[lower_pos]) {
        throw std::invalid_argument("Contraction dimensions must match");
    }

    int new_rank = rank_ - 2;
    std::vector<int> new_dims;
    std::vector<Index> new_indices;
    for (int i = 0; i < rank_; ++i) {
        if (i != upper_pos && i != lower_pos) {
            new_dims.push_back(dimensions_[i]);
            new_indices.push_back(indices_[i]);
        }
    }

    auto result = std::make_shared<Tensor>(new_rank, new_dims, new_indices);
    int d = dimensions_[upper_pos];

    // Iterate over all positions in the result tensor
    std::vector<int> result_pos(new_rank, 0);
    int total = 1;
    for (int dim : new_dims) total *= dim;

    for (int flat = 0; flat < total; ++flat) {
        // Decompose flat index
        int tmp = flat;
        for (int i = new_rank - 1; i >= 0; --i) {
            result_pos[i] = tmp % new_dims[i];
            tmp /= new_dims[i];
        }

        // Sum over contracted index
        symbol::Expression::Ptr sum = symbol::number(0);
        for (int k = 0; k < d; ++k) {
            std::vector<int> src_pos(rank_);
            int ri = 0;
            for (int i = 0; i < rank_; ++i) {
                if (i == upper_pos) {
                    src_pos[i] = k;
                } else if (i == lower_pos) {
                    src_pos[i] = k;
                } else {
                    src_pos[i] = result_pos[ri++];
                }
            }
            sum = symbol::add(sum, at(src_pos));
        }
        result->at(result_pos) = sum->simplify();
    }

    return result;
}

std::string Tensor::to_string() const {
    std::ostringstream oss;
    oss << "Tensor(rank=" << rank_ << ", indices=[";
    for (size_t i = 0; i < indices_.size(); ++i) {
        if (i > 0) oss << ", ";
        oss << (indices_[i].type == IndexType::Upper ? "^" : "_") << indices_[i].label;
    }
    oss << "])";
    return oss.str();
}

std::string Tensor::to_latex() const {
    std::ostringstream oss;
    oss << "T^{";
    bool first = true;
    for (const auto& idx : indices_) {
        if (idx.type == IndexType::Upper) {
            if (!first) oss << " ";
            oss << idx.label;
            first = false;
        }
    }
    oss << "}_{";
    first = true;
    for (const auto& idx : indices_) {
        if (idx.type == IndexType::Lower) {
            if (!first) oss << " ";
            oss << idx.label;
            first = false;
        }
    }
    oss << "}";
    return oss.str();
}

} // namespace rc::tensor
