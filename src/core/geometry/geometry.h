#pragma once

#include "../tensor/tensor.h"
#include <string>
#include <vector>
#include <memory>

namespace rc::geometry {

class Manifold {
public:
    using Ptr = std::shared_ptr<Manifold>;

    Manifold(std::string name, std::vector<std::string> coordinates);

    const std::string& name() const { return name_; }
    int dimension() const { return static_cast<int>(coordinates_.size()); }
    const std::vector<std::string>& coordinates() const { return coordinates_; }

    // Get symbol for coordinate i
    symbol::Expression::Ptr coord(int i) const;
    int coord_index(const std::string& name) const;

private:
    std::string name_;
    std::vector<std::string> coordinates_;
    std::vector<symbol::Expression::Ptr> coord_symbols_;
};

class Metric {
public:
    using Ptr = std::shared_ptr<Metric>;

    Metric(Manifold::Ptr manifold,
           std::vector<std::vector<symbol::Expression::Ptr>> components);

    const Manifold::Ptr& manifold() const { return manifold_; }
    int dimension() const { return manifold_->dimension(); }

    // Access metric components g_{mu nu}
    const symbol::Expression::Ptr& g(int mu, int nu) const;

    // Inverse metric g^{mu nu}
    symbol::Expression::Ptr g_inv(int mu, int nu) const;

    // Compute inverse metric tensor
    tensor::Tensor::Ptr inverse_metric_tensor() const;

    // As covariant tensor
    tensor::Tensor::Ptr covariant_tensor() const;

    // Christoffel symbols Gamma^mu_{nu rho}
    tensor::Tensor::Ptr christoffel_symbols() const;

    // Riemann curvature tensor R^mu_{nu rho sigma}
    tensor::Tensor::Ptr riemann_tensor() const;

    // Ricci tensor R_{mu nu}
    tensor::Tensor::Ptr ricci_tensor() const;

    // Scalar curvature R
    symbol::Expression::Ptr scalar_curvature() const;

    // Einstein tensor G_{mu nu} = R_{mu nu} - (1/2) g_{mu nu} R
    tensor::Tensor::Ptr einstein_tensor() const;

private:
    Manifold::Ptr manifold_;
    std::vector<std::vector<symbol::Expression::Ptr>> components_;
    mutable std::vector<std::vector<symbol::Expression::Ptr>> inverse_cache_;
    mutable bool inverse_computed_ = false;

    void compute_inverse() const;
    int flat_idx(int mu, int nu) const { return mu * dimension() + nu; }
};

} // namespace rc::geometry
