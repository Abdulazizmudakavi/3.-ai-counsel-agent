"""Risk bands for contract points (lawyer-owned; starting values from the blueprint)."""

from __future__ import annotations

from counsel.contracts.common import RiskLevel

ORDER = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]


def band(points: int) -> RiskLevel:
    if points >= 30:
        return RiskLevel.CRITICAL
    if points >= 16:
        return RiskLevel.HIGH
    if points >= 6:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def max_level(*levels: RiskLevel) -> RiskLevel:
    return max(levels, key=ORDER.index)
