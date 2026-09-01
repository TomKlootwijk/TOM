from __future__ import annotations

import math
from typing import Iterable
import numpy as np


def trim_ascending(coeff: Iterable[float], scale: float = 1.0) -> list[float]:
    c = [float(x) for x in coeff]
    threshold = 64.0 * np.finfo(float).eps * max(scale, max((abs(x) for x in c), default=1.0), 1.0)
    while len(c) > 1 and abs(c[-1]) <= threshold:
        c.pop()
    return c


def real_roots_unit_interval(coeff_ascending: Iterable[float], root_tol: float = 1e-10) -> tuple[list[float], float, bool]:
    """Return clustered real roots, a coefficient condition indicator, and degeneracy flag."""
    coeff = [float(x) for x in coeff_ascending]
    norm = max((abs(x) for x in coeff), default=0.0)
    if not math.isfinite(norm):
        return [], math.inf, True
    coeff = trim_ascending(coeff, norm)
    if len(coeff) == 1:
        return [], 0.0 if abs(coeff[0]) == 0.0 else math.inf, abs(coeff[0]) <= 1e-15

    nonzero = [abs(x) for x in coeff if abs(x) > 0.0]
    condition = math.inf if not nonzero else max(nonzero) / min(nonzero)
    roots = np.roots(list(reversed(coeff)))
    out: list[float] = []
    imag_tol = max(root_tol, 256.0 * np.finfo(float).eps)
    for r in roots:
        rr = float(np.real(r))
        ii = float(abs(np.imag(r)))
        if ii <= imag_tol * max(1.0, abs(rr)) and -root_tol <= rr <= 1.0 + root_tol:
            rr = min(1.0, max(0.0, rr))
            out.append(rr)
    out.sort()
    clustered: list[float] = []
    for r in out:
        if not clustered or abs(r - clustered[-1]) > 8.0 * root_tol:
            clustered.append(r)
        else:
            clustered[-1] = 0.5 * (clustered[-1] + r)
    return clustered, condition, False


def eval_ascending(coeff: Iterable[float], t: float) -> float:
    result = 0.0
    for c in reversed(list(coeff)):
        result = result * t + c
    return result
