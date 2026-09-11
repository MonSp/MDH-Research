#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "symbol/expression.h"
#include "symbol/parser.h"
#include "tensor/tensor.h"
#include "geometry/geometry.h"

namespace py = pybind11;
using namespace rc::symbol;
using namespace rc::tensor;
using namespace rc::geometry;

// Helper: create a Metric from a diagonal vector of expression strings
static Metric::Ptr metric_from_diagonal(
    Manifold::Ptr manifold, const std::vector<std::string>& diag_strs) {
    int n = manifold->dimension();
    if (static_cast<int>(diag_strs.size()) != n) {
        throw std::invalid_argument("Diagonal length must match manifold dimension");
    }
    Parser parser;
    std::vector<std::vector<Expression::Ptr>> components(n);
    for (int i = 0; i < n; ++i) {
        components[i].resize(n);
        for (int j = 0; j < n; ++j) {
            components[i][j] = (i == j) ? parser.parse(diag_strs[i]) : number(0);
        }
    }
    return std::make_shared<Metric>(std::move(manifold), std::move(components));
}

PYBIND11_MODULE(_research_core, m) {
    m.doc() = "大荒界-科研 符号计算核心";
    m.attr("version") = "0.2.0";

    // ---- Top-level parse convenience ----
    m.def("parse", [](const std::string& expr) {
        Parser p;
        return p.parse(expr);
    }, py::arg("expression"), "Parse a symbolic expression string");

    // ---- Symbol module ----
    auto sym = m.def_submodule("symbol", "符号表达式引擎");

    py::class_<Expression, std::shared_ptr<Expression>>(sym, "Expression")
        .def("to_string", &Expression::to_string)
        .def("simplify", &Expression::simplify)
        .def("diff", &Expression::diff, py::arg("var"))
        .def("is_zero", &Expression::is_zero)
        .def("is_one", &Expression::is_one)
        .def("evaluate", &Expression::evaluate, py::arg("variables"),
             "Evaluate expression numerically with variable substitutions")
        .def("clone", &Expression::clone, "Create a deep copy of this expression")
        // Pythonic string representation
        .def("__str__", &Expression::to_string)
        .def("__repr__", [](const Expression& e) {
            return "<Expression: " + e.to_string() + ">";
        })
        // Equality
        .def("__eq__", [](const Expression& a, const Expression& b) {
            return a.equals(b);
        })
        // Arithmetic operator overloads
        .def("__add__", [](Expression::Ptr a, Expression::Ptr b) {
            return add(std::move(a), std::move(b));
        })
        .def("__add__", [](Expression::Ptr a, double b) {
            return add(std::move(a), number(b));
        })
        .def("__radd__", [](Expression::Ptr a, double b) {
            return add(number(b), std::move(a));
        })
        .def("__sub__", [](Expression::Ptr a, Expression::Ptr b) {
            return add(std::move(a), neg(std::move(b)));
        })
        .def("__sub__", [](Expression::Ptr a, double b) {
            return add(std::move(a), number(-b));
        })
        .def("__rsub__", [](Expression::Ptr a, double b) {
            return add(number(b), neg(std::move(a)));
        })
        .def("__mul__", [](Expression::Ptr a, Expression::Ptr b) {
            return mul(std::move(a), std::move(b));
        })
        .def("__mul__", [](Expression::Ptr a, double b) {
            return mul(std::move(a), number(b));
        })
        .def("__rmul__", [](Expression::Ptr a, double b) {
            return mul(number(b), std::move(a));
        })
        .def("__truediv__", [](Expression::Ptr a, Expression::Ptr b) {
            return mul(std::move(a), pow(std::move(b), number(-1)));
        })
        .def("__truediv__", [](Expression::Ptr a, double b) {
            return mul(std::move(a), number(1.0 / b));
        })
        .def("__rtruediv", [](Expression::Ptr a, double b) {
            return mul(number(b), pow(std::move(a), number(-1)));
        })
        .def("__pow__", [](Expression::Ptr a, Expression::Ptr b) {
            return pow(std::move(a), std::move(b));
        })
        .def("__pow__", [](Expression::Ptr a, double b) {
            return pow(std::move(a), number(b));
        })
        .def("__neg__", [](Expression::Ptr a) {
            return neg(std::move(a));
        });

    py::class_<Number, Expression, std::shared_ptr<Number>>(sym, "Number")
        .def(py::init<double>())
        .def("value", &Number::value);

    py::class_<Symbol, Expression, std::shared_ptr<Symbol>>(sym, "Symbol")
        .def(py::init<std::string>())
        .def("name", &Symbol::name);

    py::class_<BinaryOp, Expression, std::shared_ptr<BinaryOp>>(sym, "BinaryOp");

    py::class_<Func, Expression, std::shared_ptr<Func>>(sym, "Func")
        .def("name", &Func::name);

    sym.def("number", [](double v) { return number(v); }, py::arg("value"));
    sym.def("symbol", [](const std::string& name) { return symbol(name); }, py::arg("name"));
    sym.def("add", [](Expression::Ptr a, Expression::Ptr b) { return add(std::move(a), std::move(b)); }, py::arg("a"), py::arg("b"));
    sym.def("mul", [](Expression::Ptr a, Expression::Ptr b) { return mul(std::move(a), std::move(b)); }, py::arg("a"), py::arg("b"));
    sym.def("pow", [](Expression::Ptr base, Expression::Ptr exp) { return pow(std::move(base), std::move(exp)); }, py::arg("base"), py::arg("exp"));
    sym.def("neg", [](Expression::Ptr a) { return neg(std::move(a)); }, py::arg("a"));
    sym.def("parse", [](const std::string& expr) {
        Parser p;
        return p.parse(expr);
    }, py::arg("expression"), "Parse a symbolic expression string");

    // ---- Tensor module ----
    auto tens = m.def_submodule("tensor", "张量计算");

    py::enum_<IndexType>(tens, "IndexType")
        .value("Upper", IndexType::Upper)
        .value("Lower", IndexType::Lower);

    py::class_<Index>(tens, "Index")
        .def(py::init<std::string, IndexType>(), py::arg("label"), py::arg("type"))
        .def_readwrite("label", &Index::label)
        .def_readwrite("index_type", &Index::type);

    py::class_<Tensor, std::shared_ptr<Tensor>>(tens, "Tensor")
        .def("rank", &Tensor::rank)
        .def("dimensions", &Tensor::dimensions)
        .def("indices", &Tensor::indices)
        .def("at", [](Tensor& t, const std::vector<int>& pos) { return t.at(pos); })
        .def("set", [](Tensor& t, const std::vector<int>& pos, Expression::Ptr val) {
            t.at(pos) = std::move(val);
        }, py::arg("position"), py::arg("value"))
        .def("raise_index", &Tensor::raise_index)
        .def("lower_index", &Tensor::lower_index)
        .def("contract", &Tensor::contract)
        .def("to_string", &Tensor::to_string)
        .def("to_latex", &Tensor::to_latex)
        // Pythonic access via tuple index
        .def("__getitem__", [](const Tensor& t, const std::vector<int>& pos) {
            return t.at(pos);
        })
        .def("__setitem__", [](Tensor& t, const std::vector<int>& pos, Expression::Ptr val) {
            t.at(pos) = std::move(val);
        })
        .def("__repr__", &Tensor::to_string);

    // ---- Geometry module ----
    auto geom = m.def_submodule("geometry", "微分几何");

    py::class_<Manifold, std::shared_ptr<Manifold>>(geom, "Manifold")
        .def(py::init<std::string, std::vector<std::string>>(),
             py::arg("name"), py::arg("coordinates"))
        .def("name", &Manifold::name)
        .def("dimension", &Manifold::dimension)
        .def("coordinates", &Manifold::coordinates)
        .def("coord", &Manifold::coord)
        .def("coord_index", &Manifold::coord_index)
        .def("__repr__", [](const Manifold& m) {
            return "Manifold('" + m.name() + "', dim=" + std::to_string(m.dimension()) + ")";
        });

    py::class_<Metric, std::shared_ptr<Metric>>(geom, "Metric")
        .def(py::init<Manifold::Ptr, std::vector<std::vector<Expression::Ptr>>>(),
             py::arg("manifold"), py::arg("components"))
        .def("dimension", &Metric::dimension)
        .def("g", &Metric::g)
        .def("g_inv", &Metric::g_inv)
        .def("christoffel_symbols", &Metric::christoffel_symbols)
        .def("riemann_tensor", &Metric::riemann_tensor)
        .def("ricci_tensor", &Metric::ricci_tensor)
        .def("scalar_curvature", &Metric::scalar_curvature)
        .def("einstein_tensor", &Metric::einstein_tensor,
             "Einstein tensor G_{mu nu} = R_{mu nu} - (1/2) g_{mu nu} R")
        .def("kretschmann_scalar", &Metric::kretschmann_scalar,
             "Kretschmann scalar K = R_{mu nu rho sigma} R^{mu nu rho sigma}")
        .def("covariant_tensor", &Metric::covariant_tensor)
        .def("inverse_metric_tensor", &Metric::inverse_metric_tensor)
        // Factory: diagonal metric from expression strings
        .def_static("from_diagonal", &metric_from_diagonal,
            py::arg("manifold"), py::arg("diagonal"),
            "Create a diagonal metric from a list of expression strings")
        .def("__repr__", [](const Metric& g) {
            return "Metric(dim=" + std::to_string(g.dimension()) + ")";
        });
}
