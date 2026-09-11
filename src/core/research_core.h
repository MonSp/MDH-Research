#pragma once

// research_core: 符号计算引擎与基础微分几何
// 大荒界-科研 (MDH-Research)

#include <string>
#include <vector>
#include <memory>
#include <unordered_map>
#include <optional>
#include <stdexcept>

namespace rc {

// Forward declarations
class Expression;
class Tensor;
class Manifold;
class Metric;
class Connection;
using ExprPtr = std::shared_ptr<Expression>;
using TensorPtr = std::shared_ptr<Tensor>;

} // namespace rc
