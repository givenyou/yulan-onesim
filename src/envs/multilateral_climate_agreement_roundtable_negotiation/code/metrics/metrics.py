# -*- coding: utf-8 -*-
"""
Monitoring metrics for the roundtable negotiation scenario.

Each function receives a dict mapping variable names to the list of values
collected from all agents of the given type (None for agents that have not
written the value yet). Definitions live in scene_info.json -> metrics.
"""

from typing import Dict, Any, List, Optional, Callable
from onesim.monitor.utils import log_metric_error


def _values(data: Dict[str, Any], key: str) -> List[Any]:
    value = data.get(key) if isinstance(data, dict) else None
    if value is None:
        return []
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _numbers(values: List[Any]) -> List[float]:
    out = []
    for v in values:
        if isinstance(v, bool) or v is None:
            continue
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


def Negotiation_Outcome_Distribution(data: Dict[str, Any]) -> Any:
    try:
        counts = {"Not started": 0, "In progress": 0, "Consensus": 0, "Impasse": 0, "Failed": 0}
        for status in _values(data, "outcome_status"):
            label = str(status).strip() if status is not None else ""
            if label in counts:
                counts[label] += 1
            elif not label or label.lower() in ("none", "null", "pending"):
                counts["Not started"] += 1
            else:
                counts.setdefault(label, 0)
                counts[label] += 1
        return {k: v for k, v in counts.items() if v > 0} or {"Not started": 1}
    except Exception as e:
        log_metric_error("Negotiation Outcome Distribution", e, {"data": data})
        return {"Not started": 1}


def Negotiation_Progress(data: Dict[str, Any]) -> Any:
    try:
        open_counts = _numbers(_values(data, "open_divergence_count"))
        rounds = _numbers(_values(data, "current_round"))
        return {
            "Unsettled clauses (mean per table)": round(sum(open_counts) / len(open_counts), 2) if open_counts else 0,
            "Round reached (max)": max(rounds) if rounds else 0,
        }
    except Exception as e:
        log_metric_error("Negotiation Progress", e, {"data": data})
        return {"Unsettled clauses (mean per table)": 0, "Round reached (max)": 0}


def Clause_Alignment_vs_Divergence(data: Dict[str, Any]) -> Any:
    try:
        settled = sum(len(v) for v in _values(data, "aligned_clauses") if isinstance(v, (list, tuple)))
        unsettled = sum(len(v) for v in _values(data, "divergent_clauses") if isinstance(v, (list, tuple)))
        return {"Settled clauses": settled, "Unsettled clauses": unsettled}
    except Exception as e:
        log_metric_error("Clause Alignment vs Divergence", e, {"data": data})
        return {"Settled clauses": 0, "Unsettled clauses": 0}


def Delegate_Moves(data: Dict[str, Any]) -> Any:
    try:
        counts = {"amendment": 0, "endorsement": 0, "concession": 0, "failed": 0}
        for move in _values(data, "last_move"):
            if move in counts:
                counts[move] += 1
        return counts
    except Exception as e:
        log_metric_error("Delegate Moves", e, {"data": data})
        return {"amendment": 0, "endorsement": 0, "concession": 0, "failed": 0}


def Position_Shifts(data: Dict[str, Any]) -> Any:
    try:
        return {"Position changes since previous round": sum(_numbers(_values(data, "positions_changed_last_round")))}
    except Exception as e:
        log_metric_error("Position Shifts", e, {"data": data})
        return {"Position changes since previous round": 0}


def Delegate_Concession_Willingness(data: Dict[str, Any]) -> Any:
    try:
        values = _values(data, "willing_to_concede")
        willing = sum(1 for v in values if v is True)
        unwilling = sum(1 for v in values if v is False)
        not_yet = sum(1 for v in values if v is None)
        result = {"Willing": willing, "Not willing": unwilling, "Not spoken yet": not_yet}
        return {k: v for k, v in result.items() if v > 0} or {"Not spoken yet": 1}
    except Exception as e:
        log_metric_error("Delegate Concession Willingness", e, {"data": data})
        return {"Not spoken yet": 1}


METRIC_FUNCTIONS = {
    'Negotiation_Outcome_Distribution': Negotiation_Outcome_Distribution,
    'Negotiation_Progress': Negotiation_Progress,
    'Clause_Alignment_vs_Divergence': Clause_Alignment_vs_Divergence,
    'Delegate_Moves': Delegate_Moves,
    'Position_Shifts': Position_Shifts,
    'Delegate_Concession_Willingness': Delegate_Concession_Willingness,
}


def get_metric_function(function_name: str) -> Optional[Callable]:
    return METRIC_FUNCTIONS.get(function_name)
