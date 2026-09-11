#include "geometry.h"
#include <stdexcept>
#include <sstream>
#include <cmath>

namespace rc::geometry {

// Manifold
Manifold::Manifold(std::string name, std::vector<std::string> coordinates)
    : name_(std::move(name)), coordinates_(std::move(coordinates)) {
    coord_symbols_.reserve(coordinates_.size());
    for (const auto& c : coordinates_) {
        coord_symbols_.push_back(symbol::symbol(c));
    }
}

symbol::Expression::Ptr Manifold::coord(int i) const {
    if (i < 0 || i >= dimension()) throw std::out_of_range("Coordinate index out of range");
    return coord_symbols_[i];
}

int Manifold::coord_index(const std::string& name) const {
    for (int i = 0; i < dimension(); ++i) {
        if (coordinates_[i] == name) return i;
    }
    return -1;
}

// Metric
Metric::Metric(Manifold::Ptr manifold,
               std::vector<std::vector<symbol::Expression::Ptr>> components)
    : manifold_(std::move(manifold)), components_(std::move(components)) {
    int n = manifold_->dimension();
    if (static_cast<int>(components_.size()) != n) {
        throw std::invalid_argument("Metric component rows != manifold dimension");
    }
    for (const auto& row : components_) {
        if (static_cast<int>(row.size()) != n) {
            throw std::invalid_argument("Metric component cols != manifold dimension");
        }
    }
}

const symbol::Expression::Ptr& Metric::g(int mu, int nu) const {
    return components_[mu][nu];
}

void Metric::compute_inverse() const {
    if (inverse_computed_) return;
    int n = dimension();

    // Build augmented matrix [g | I]
    // For symbolic computation, we use cofactor expansion (only practical for small n)
    // For 4x4 spacetime metrics (diagonal or block-diagonal), this is fine

    // Check if diagonal
    bool diagonal = true;
    for (int i = 0; i < n && diagonal; ++i) {
        for (int j = 0; j < n && diagonal; ++j) {
            if (i != j && !components_[i][j]->is_zero()) {
                diagonal = false;
            }
        }
    }

    inverse_cache_.resize(n, std::vector<symbol::Expression::Ptr>(n));

    if (diagonal) {
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                if (i == j) {
                    inverse_cache_[i][j] = symbol::pow(
                        components_[i][i]->clone(), symbol::number(-1))->simplify();
                } else {
                    inverse_cache_[i][j] = symbol::number(0);
                }
            }
        }
    } else {
        // General case: adjugate / determinant
        // Compute determinant via cofactor expansion
        // (For MVP, we handle 2x2 and general case)
        if (n == 2) {
            auto det = symbol::add(
                symbol::mul(components_[0][0]->clone(), components_[1][1]->clone()),
                symbol::neg(symbol::mul(components_[0][1]->clone(), components_[1][0]->clone()))
            )->simplify();
            auto det_inv = symbol::pow(det->clone(), symbol::number(-1))->simplify();
            inverse_cache_[0][0] = symbol::mul(components_[1][1]->clone(), det_inv)->simplify();
            inverse_cache_[0][1] = symbol::mul(symbol::number(-1),
                symbol::mul(components_[0][1]->clone(), det_inv))->simplify();
            inverse_cache_[1][0] = symbol::mul(symbol::number(-1),
                symbol::mul(components_[1][0]->clone(), det_inv))->simplify();
            inverse_cache_[1][1] = symbol::mul(components_[0][0]->clone(), det_inv)->simplify();
        } else {
            // General cofactor expansion (recursive, works for small n)
            // For MVP, we'll implement a basic version
            // TODO: Implement efficient symbolic matrix inverse for general case
            throw std::runtime_error(
                "General symbolic matrix inverse not yet implemented for n > 2 "
                "(diagonal metrics work for any dimension)");
        }
    }

    inverse_computed_ = true;
}

symbol::Expression::Ptr Metric::g_inv(int mu, int nu) const {
    compute_inverse();
    return inverse_cache_[mu][nu];
}

tensor::Tensor::Ptr Metric::covariant_tensor() const {
    int n = dimension();
    std::vector<int> dims(n, n);
    std::vector<tensor::Index> indices;
    for (int i = 0; i < n; ++i) {
        indices.push_back({manifold_->coordinates()[i], tensor::IndexType::Lower});
    }
    auto t = std::make_shared<tensor::Tensor>(n, dims, indices);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            t->at({i, j}) = components_[i][j]->clone();
        }
    }
    return t;
}

tensor::Tensor::Ptr Metric::inverse_metric_tensor() const {
    compute_inverse();
    int n = dimension();
    std::vector<int> dims(n, n);
    std::vector<tensor::Index> indices;
    for (int i = 0; i < n; ++i) {
        indices.push_back({manifold_->coordinates()[i], tensor::IndexType::Upper});
    }
    auto t = std::make_shared<tensor::Tensor>(n, dims, indices);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            t->at({i, j}) = inverse_cache_[i][j]->clone();
        }
    }
    return t;
}

tensor::Tensor::Ptr Metric::christoffel_symbols() const {
    int n = dimension();
    std::vector<int> dims = {n, n, n};
    auto safe_coord = [&](int i) -> const std::string& {
        return manifold_->coordinates()[i < n ? i : 0];
    };
    std::vector<tensor::Index> indices = {
        {safe_coord(0), tensor::IndexType::Upper},
        {safe_coord(1), tensor::IndexType::Lower},
        {safe_coord(2), tensor::IndexType::Lower},
    };
    auto Gamma = std::make_shared<tensor::Tensor>(3, dims, indices);

    // Gamma^mu_{nu rho} = (1/2) g^{mu sigma} (dg_{sigma nu}/dx^rho + dg_{sigma rho}/dx^nu - dg_{nu rho}/dx^sigma)
    for (int mu = 0; mu < n; ++mu) {
        for (int nu = 0; nu < n; ++nu) {
            for (int rho = 0; rho < n; ++rho) {
                symbol::Expression::Ptr sum = symbol::number(0);
                for (int sigma = 0; sigma < n; ++sigma) {
                    auto coord_rho = manifold_->coord(rho);
                    auto coord_nu = manifold_->coord(nu);
                    auto coord_sigma = manifold_->coord(sigma);

                    // dg_{sigma nu}/dx^rho
                    auto dg1 = components_[sigma][nu]->diff(manifold_->coordinates()[rho]);
                    // dg_{sigma rho}/dx^nu
                    auto dg2 = components_[sigma][rho]->diff(manifold_->coordinates()[nu]);
                    // dg_{nu rho}/dx^sigma
                    auto dg3 = components_[nu][rho]->diff(manifold_->coordinates()[sigma]);

                    auto bracket = symbol::add(
                        symbol::add(dg1, dg2),
                        symbol::neg(dg3)
                    )->simplify();

                    auto term = symbol::mul(g_inv(mu, sigma)->clone(), bracket)->simplify();
                    sum = symbol::add(sum, term)->simplify();
                }
                Gamma->at({mu, nu, rho}) = symbol::mul(symbol::number(0.5), sum)->simplify();
            }
        }
    }

    return Gamma;
}

tensor::Tensor::Ptr Metric::riemann_tensor() const {
    auto Gamma = christoffel_symbols();
    int n = dimension();

    std::vector<int> dims = {n, n, n, n};
    auto safe_coord = [&](int i) -> const std::string& {
        return manifold_->coordinates()[i < n ? i : 0];
    };
    std::vector<tensor::Index> indices = {
        {safe_coord(0), tensor::IndexType::Upper},
        {safe_coord(1), tensor::IndexType::Lower},
        {safe_coord(2), tensor::IndexType::Lower},
        {safe_coord(3), tensor::IndexType::Lower},
    };
    auto R = std::make_shared<tensor::Tensor>(4, dims, indices);

    // R^mu_{nu rho sigma} = d_rho Gamma^mu_{nu sigma} - d_sigma Gamma^mu_{nu rho}
    //                      + Gamma^mu_{lambda rho} Gamma^lambda_{nu sigma}
    //                      - Gamma^mu_{lambda sigma} Gamma^lambda_{nu rho}
    for (int mu = 0; mu < n; ++mu) {
        for (int nu = 0; nu < n; ++nu) {
            for (int rho = 0; rho < n; ++rho) {
                for (int sigma = 0; sigma < n; ++sigma) {
                    // d_rho Gamma^mu_{nu sigma}
                    auto dg1 = Gamma->at({mu, nu, sigma})->diff(manifold_->coordinates()[rho]);
                    // d_sigma Gamma^mu_{nu rho}
                    auto dg2 = Gamma->at({mu, nu, rho})->diff(manifold_->coordinates()[sigma]);

                    auto result = symbol::add(dg1, symbol::neg(dg2));

                    // + Gamma^mu_{lambda rho} Gamma^lambda_{nu sigma}
                    for (int lambda = 0; lambda < n; ++lambda) {
                        auto term1 = symbol::mul(
                            Gamma->at({mu, lambda, rho})->clone(),
                            Gamma->at({lambda, nu, sigma})->clone()
                        );
                        result = symbol::add(result, term1);
                    }

                    // - Gamma^mu_{lambda sigma} Gamma^lambda_{nu rho}
                    for (int lambda = 0; lambda < n; ++lambda) {
                        auto term2 = symbol::mul(
                            Gamma->at({mu, lambda, sigma})->clone(),
                            Gamma->at({lambda, nu, rho})->clone()
                        );
                        result = symbol::add(result, symbol::neg(term2));
                    }

                    R->at({mu, nu, rho, sigma}) = result->simplify();
                }
            }
        }
    }

    return R;
}

tensor::Tensor::Ptr Metric::ricci_tensor() const {
    auto R = riemann_tensor();
    int n = dimension();

    // R_{nu sigma} = R^mu_{nu mu sigma} (contract mu with first index)
    // We need to sum over mu (upper index) with the third lower index
    std::vector<int> dims = {n, n};
    std::vector<tensor::Index> indices = {
        {manifold_->coordinates()[0], tensor::IndexType::Lower},
        {manifold_->coordinates()[1], tensor::IndexType::Lower},
    };
    auto Ric = std::make_shared<tensor::Tensor>(2, dims, indices);

    for (int nu = 0; nu < n; ++nu) {
        for (int sigma = 0; sigma < n; ++sigma) {
            symbol::Expression::Ptr sum = symbol::number(0);
            for (int mu = 0; mu < n; ++mu) {
                // R^mu_{nu mu sigma}
                sum = symbol::add(sum, R->at({mu, nu, mu, sigma}))->simplify();
            }
            Ric->at({nu, sigma}) = sum;
        }
    }

    return Ric;
}

symbol::Expression::Ptr Metric::scalar_curvature() const {
    auto Ric = ricci_tensor();
    int n = dimension();

    // R = g^{mu nu} R_{mu nu}
    symbol::Expression::Ptr R = symbol::number(0);
    for (int mu = 0; mu < n; ++mu) {
        for (int nu = 0; nu < n; ++nu) {
            auto term = symbol::mul(g_inv(mu, nu)->clone(), Ric->at({mu, nu})->clone());
            R = symbol::add(R, term)->simplify();
        }
    }

    return R;
}

tensor::Tensor::Ptr Metric::einstein_tensor() const {
    auto Ric = ricci_tensor();
    auto R = scalar_curvature();
    int n = dimension();

    std::vector<int> dims = {n, n};
    auto safe_coord = [&](int i) -> const std::string& {
        return manifold_->coordinates()[i < n ? i : 0];
    };
    std::vector<tensor::Index> indices = {
        {safe_coord(0), tensor::IndexType::Lower},
        {safe_coord(1), tensor::IndexType::Lower},
    };
    auto G = std::make_shared<tensor::Tensor>(2, dims, indices);

    // G_{mu nu} = R_{mu nu} - (1/2) g_{mu nu} R
    for (int mu = 0; mu < n; ++mu) {
        for (int nu = 0; nu < n; ++nu) {
            auto half_g_R = symbol::mul(
                symbol::number(0.5),
                symbol::mul(components_[mu][nu]->clone(), R->clone())
            );
            G->at({mu, nu}) = symbol::add(Ric->at({mu, nu})->clone(), symbol::neg(half_g_R))->simplify();
        }
    }

    return G;
}

symbol::Expression::Ptr Metric::kretschmann_scalar() const {
    auto R_mixed = riemann_tensor();  // R^mu_{nu rho sigma}
    int n = dimension();

    // K = R_{mu nu rho sigma} R^{mu nu rho sigma}
    // Compute R_{mu nu rho sigma} = g_{mu a} R^a_{nu rho sigma} for diagonal metric
    // Then K = sum_{mu nu rho sigma} (R_{mu nu rho sigma})^2 * g^{mu mu} g^{nu nu} g^{rho rho} g^{sigma sigma}
    //        = sum (g_{mu mu} R^mu_{nu rho sigma})^2 / (g_{mu mu} g_{nu nu} g_{rho rho} g_{sigma sigma})
    //        = sum (R^mu_{nu rho sigma})^2 * g_{mu mu} / (g_{nu nu} g_{rho rho} g_{sigma sigma})

    symbol::Expression::Ptr K = symbol::number(0);

    for (int mu = 0; mu < n; ++mu) {
        for (int nu = 0; nu < n; ++nu) {
            for (int rho = 0; rho < n; ++rho) {
                for (int sigma = 0; sigma < n; ++sigma) {
                    auto R_comp = R_mixed->at({mu, nu, rho, sigma});
                    if (R_comp->is_zero()) continue;

                    // R_{mu nu rho sigma} = g_{mu mu} * R^mu_{nu rho sigma} (diagonal)
                    auto R_lower = symbol::mul(components_[mu][mu]->clone(), R_comp->clone());

                    // R^{mu nu rho sigma} = g^{mu mu} g^{nu nu} g^{rho rho} g^{sigma sigma} R_{mu nu rho sigma}
                    auto R_upper = symbol::mul(
                        symbol::mul(g_inv(mu, mu), g_inv(nu, nu)),
                        symbol::mul(g_inv(rho, rho), symbol::mul(g_inv(sigma, sigma), R_lower->clone()))
                    );

                    K = symbol::add(K, symbol::mul(R_lower, R_upper))->simplify();
                }
            }
        }
    }

    return K;
}

} // namespace rc::geometry
