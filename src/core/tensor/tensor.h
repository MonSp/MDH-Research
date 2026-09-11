#pragma once

#include "expression.h"
#include <vector>
#include <string>
#include <initializer_list>

namespace rc::tensor {

enum class IndexType { Upper, Lower };

struct Index {
    std::string label;
    IndexType type;
};

class Tensor {
public:
    using Ptr = std::shared_ptr<Tensor>;

    Tensor(int rank, std::vector<int> dimensions, std::vector<Index> indices);
    ~Tensor() = default;

    int rank() const { return rank_; }
    const std::vector<int>& dimensions() const { return dimensions_; }
    const std::vector<Index>& indices() const { return indices_; }

    // Access components
    symbol::Expression::Ptr& at(const std::vector<int>& position);
    const symbol::Expression::Ptr& at(const std::vector<int>& position) const;

    // Set all components
    void set_components(const std::vector<symbol::Expression::Ptr>& components);

    // Index operations
    Ptr raise_index(int pos) const;
    Ptr lower_index(int pos) const;
    Ptr contract(int upper_pos, int lower_pos) const;

    // Output
    std::string to_string() const;
    std::string to_latex() const;

private:
    int rank_;
    std::vector<int> dimensions_;
    std::vector<Index> indices_;
    std::vector<symbol::Expression::Ptr> components_;

    int flat_index(const std::vector<int>& position) const;
};

} // namespace rc::tensor

namespace rc {
using TensorPtr = std::shared_ptr<tensor::Tensor>;
}
