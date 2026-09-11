"""SymPy bidirectional conversion bridge (T16).

Converts between the C++ expression engine and SymPy expressions,
enabling symbolic verification and manipulation.
"""

from __future__ import annotations

import sys
import os
from typing import Any

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

try:
    import _research_core as rc
except ImportError:
    rc = None

import sympy as sp


def expr_to_sympy(expr) -> sp.Expr:
    """Convert a C++ Expression to a SymPy expression.

    Uses SymPy's parser on the string representation.
    """
    if rc is None:
        raise RuntimeError("C++ bindings not available")

    from sympy.parsing.sympy_parser import parse_expr

    s = str(expr)

    # Convert our format to SymPy-parseable format
    # Replace ^ with **
    s = s.replace('^', '**')
    # Remove outer parentheses if they wrap the entire expression
    if s.startswith('(') and s.endswith(')'):
        # Check if they're matching
        depth = 0
        for i, c in enumerate(s):
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            if depth == 0 and i < len(s) - 1:
                break
        else:
            # The outer parens match the whole expression
            s = s[1:-1]

    return parse_expr(s)


def _parse_to_sympy(s: str) -> sp.Expr:
    """Parse our expression string format into SymPy.

    Our format: "(a + b)", "(a * b)", "a^2", "(-a)", "sin(x)"
    """
    s = s.strip()

    # Try to parse as number
    try:
        val = float(s)
        if val == int(val) and '.' not in s and 'e' not in s.lower():
            return sp.Integer(int(val))
        return sp.Float(val)
    except (ValueError, TypeError):
        pass

    # Handle negation: "(-expr)"
    if s.startswith("(-") and s.endswith(")"):
        return -_parse_to_sympy(s[2:-1])

    # Handle binary operations (find the top-level operator)
    # Look for + or - not inside parentheses (leftmost for right-associativity fix)
    # For + and -, search LEFT-to-RIGHT to get the correct split
    depth = 0
    for i in range(len(s)):
        c = s[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        elif depth == 0 and c in ('+', '-') and i > 0:
            # Check it's not a unary minus (after an operator or at start)
            prev_char = s[i-1]
            if prev_char in ('+', '-', '*', '/', '^', '('):
                continue
            left = _parse_to_sympy(s[:i])
            right = _parse_to_sympy(s[i+1:])
            if c == '+':
                return left + right
            else:
                return left - right

    # Look for * or / at top level
    depth = 0
    for i in range(len(s) - 1, 0, -1):
        c = s[i]
        if c == ')':
            depth += 1
        elif c == '(':
            depth -= 1
        elif depth == 0 and c in ('*', '/'):
            left = _parse_to_sympy(s[:i])
            right = _parse_to_sympy(s[i+1:])
            if c == '*':
                return left * right
            else:
                return left / right

    # Look for ^ (power)
    depth = 0
    for i in range(len(s) - 1, 0, -1):
        c = s[i]
        if c == ')':
            depth += 1
        elif c == '(':
            depth -= 1
        elif depth == 0 and c == '^':
            base = _parse_to_sympy(s[:i])
            exp = _parse_to_sympy(s[i+1:])
            return base ** exp

    # Function call: "name(args)"
    if '(' in s and s.endswith(')'):
        paren_idx = s.index('(')
        name = s[:paren_idx]
        args_str = s[paren_idx+1:-1]
        args = _split_args(args_str)
        sympy_args = [_parse_to_sympy(a) for a in args]

        func_map = {
            'sin': sp.sin, 'cos': sp.cos, 'tan': sp.tan,
            'sinh': sp.sinh, 'cosh': sp.cosh, 'tanh': sp.tanh,
            'exp': sp.exp, 'log': sp.log,
            'asin': sp.asin, 'acos': sp.acos, 'atan': sp.atan,
            'pi': lambda: sp.pi,
        }
        if name in func_map:
            fn = func_map[name]
            if callable(fn):
                return fn(*sympy_args)
            return fn
        # Unknown function: create a SymPy Function
        f = sp.Function(name)
        return f(*sympy_args)

    # Parenthesized expression
    if s.startswith('(') and s.endswith(')'):
        return _parse_to_sympy(s[1:-1])

    # Symbol
    return sp.Symbol(s)


def _split_args(s: str) -> list[str]:
    """Split comma-separated arguments respecting parentheses."""
    args = []
    depth = 0
    current = []
    for c in s:
        if c == '(':
            depth += 1
            current.append(c)
        elif c == ')':
            depth -= 1
            current.append(c)
        elif c == ',' and depth == 0:
            args.append(''.join(current).strip())
            current = []
        else:
            current.append(c)
    if current:
        args.append(''.join(current).strip())
    return args


def sympy_to_expr(sp_expr: sp.Expr):
    """Convert a SymPy expression to a C++ Expression.

    Uses the C++ parser with a reconstructed string.
    """
    if rc is None:
        raise RuntimeError("C++ bindings not available")

    s = _sympy_to_str(sp_expr)
    return rc.parse(s)


def _sympy_to_str(expr: sp.Expr) -> str:
    """Convert a SymPy expression to a string parseable by our C++ parser."""
    if expr.is_Number:
        if expr.is_Integer:
            return str(int(expr))
        return str(float(expr))

    if expr.is_Symbol:
        return str(expr)

    if isinstance(expr, sp.Add):
        terms = sp.Add.make_args(expr)
        parts = [_sympy_to_str(t) for t in terms]
        return "(" + " + ".join(parts) + ")"

    if isinstance(expr, sp.Mul):
        factors = sp.Mul.make_args(expr)
        parts = []
        for f in factors:
            s = _sympy_to_str(f)
            if isinstance(f, sp.Add):
                parts.append("(" + s + ")")
            else:
                parts.append(s)
        return " * ".join(parts)

    if isinstance(expr, sp.Pow):
        base, exp = expr.as_base_exp()
        return _sympy_to_str(base) + "^" + _sympy_to_str(exp)

    if isinstance(expr, sp.Function):
        name = str(expr.func)
        args = ", ".join(_sympy_to_str(a) for a in expr.args)
        return f"{name}({args})"

    # Fallback: use str() and hope the parser can handle it
    return str(expr)


def tensor_to_sympy(tensor, n: int | None = None) -> sp.MutableDenseNDimArray:
    """Convert a C++ Tensor to a SymPy N-dimensional array."""
    rank = tensor.rank()
    dims = tensor.dimensions()
    if n is None:
        n = dims[0] if dims else 0

    if rank == 0:
        return expr_to_sympy(tensor.at([]))
    elif rank == 2:
        return sp.Matrix([[expr_to_sympy(tensor.at([i, j])) for j in range(n)] for i in range(n)])
    elif rank == 3:
        arr = sp.MutableDenseNDimArray.zeros(n, n, n)
        for i in range(n):
            for j in range(n):
                for k in range(n):
                    arr[i, j, k] = expr_to_sympy(tensor.at([i, j, k]))
        return arr
    elif rank == 4:
        arr = sp.MutableDenseNDimArray.zeros(n, n, n, n)
        for i in range(n):
            for j in range(n):
                for k in range(n):
                    for l in range(n):
                        arr[i, j, k, l] = expr_to_sympy(tensor.at([i, j, k, l]))
        return arr
    else:
        raise ValueError(f"Unsupported tensor rank: {rank}")
