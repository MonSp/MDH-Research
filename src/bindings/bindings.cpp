#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "symbol/expression.h"
#include "tensor/tensor.h"
#include "geometry/geometry.h"

namespace py = pybind11;
using namespace rc::symbol;
using namespace rc::tensor;
using namespace rc::geometry;

PYBIND11_MODULE(_research_core, m) {
    m.doc() = "大荒界-科研 符号计算核心";
    m.attr("version") = "0.1.0";

    // Symbol module
    auto sym = m.def_submodule("symbol", "符号表达式引擎");

    py::class_<Expression, std::shared_ptr<Expression>>(sym, "Expression")
        .def("to_string", &Expression::to_string)
        .def("simplify", &Expression::simplify)
        .def("diff", &Expression::diff, py::arg("var"))
        .def("is_zero", &Expression::is_zero)
        .def("is_one", &Expression::is_one)
        .def("__repr__", &Expression::to_string);

    py::class_<Number, Expression, std::shared_ptr<Number>>(sym, "Number")
        .def(py::init<double>())
        .def("value", &Number::value);

    py::class_<Symbol, Expression, std::shared_ptr<Symbol>>(sym, "Symbol")
        .def(py::init<std::string>())
        .def("name", &Symbol::name);

    py::class_<BinaryOp, Expression, std::shared_ptr<BinaryOp>>(sym, "BinaryOp");

    py::class_<Func, Expression, std::shared_ptr<Func>>(sym, "Func")
        .def("name", &Func::name);

    // Factory functions — wrap in lambdas to avoid overload/namespace ambiguity
    sym.def("number", [](double v) { return number(v); }, py::arg("value"));
    sym.def("symbol", [](const std::string& name) { return symbol(name); }, py::arg("name"));
    sym.def("add", [](Expression::Ptr a, Expression::Ptr b) { return add(std::move(a), std::move(b)); }, py::arg("a"), py::arg("b"));
    sym.def("mul", [](Expression::Ptr a, Expression::Ptr b) { return mul(std::move(a), std::move(b)); }, py::arg("a"), py::arg("b"));
    sym.def("pow", [](Expression::Ptr base, Expression::Ptr exp) { return pow(std::move(base), std::move(exp)); }, py::arg("base"), py::arg("exp"));
    sym.def("neg", [](Expression::Ptr a) { return neg(std::move(a)); }, py::arg("a"));

    // Tensor module
    auto tens = m.def_submodule("tensor", "张量计算");

    py::enum_<IndexType>(tens, "IndexType")
        .value("Upper", IndexType::Upper)
        .value("Lower", IndexType::Lower);

    py::class_<Index>(tens, "Index")
        .def_readwrite("label", &Index::label)
        .def_readwrite("index_type", &Index::type);

    py::class_<Tensor, std::shared_ptr<Tensor>>(tens, "Tensor")
        .def("rank", &Tensor::rank)
        .def("dimensions", &Tensor::dimensions)
        .def("indices", &Tensor::indices)
        .def("at", [](Tensor& t, const std::vector<int>& pos) { return t.at(pos); })
        .def("raise_index", &Tensor::raise_index)
        .def("lower_index", &Tensor::lower_index)
        .def("contract", &Tensor::contract)
        .def("to_string", &Tensor::to_string)
        .def("to_latex", &Tensor::to_latex);

    // Geometry module
    auto geom = m.def_submodule("geometry", "微分几何");

    py::class_<Manifold, std::shared_ptr<Manifold>>(geom, "Manifold")
        .def(py::init<std::string, std::vector<std::string>>(),
             py::arg("name"), py::arg("coordinates"))
        .def("name", &Manifold::name)
        .def("dimension", &Manifold::dimension)
        .def("coordinates", &Manifold::coordinates)
        .def("coord", &Manifold::coord)
        .def("coord_index", &Manifold::coord_index);

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
        .def("covariant_tensor", &Metric::covariant_tensor)
        .def("inverse_metric_tensor", &Metric::inverse_metric_tensor);
}
