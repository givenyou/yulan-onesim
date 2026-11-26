"""Shared helpers for the roundtable negotiation agents.

These live in their own module because the platform's code view
(code/code_structure.json) only stores the async handlers of each agent.
Keeping helpers here means the agent files can be rebuilt from the code view
without losing them.
"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple

VALID_POSITIONS = ("Support", "Conditional Support", "Oppose")
UNSPECIFIED = "Unspecified"
VALID_MOVES = ("amendment", "endorsement", "concession")
DEFAULT_CLAUSE_IDS = ["Article 3", "Article 7", "Article 12", "Definitions"]


# ---------------------------------------------------------------- state

def get_state(agent) -> Dict[str, Any]:
    """Per-agent working state kept on the agent object, outside the profile.

    The profile is pasted into every prompt, so only small summary values are
    written there (for metrics); bulky per-round data stays here.
    """
    state = getattr(agent, "_negotiation_state", None)
    if state is None:
        state = {"round": 0, "rounds": {}}
        agent._negotiation_state = state
    return state


def round_state(state: Dict[str, Any], round_no: int) -> Dict[str, Any]:
    rounds = state.setdefault("rounds", {})
    if round_no not in rounds:
        rounds[round_no] = {}
    return rounds[round_no]


def event_name(event) -> str:
    return getattr(event, "event_kind", None) or event.__class__.__name__


# ---------------------------------------------------------------- coercion

def as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_bool(value: Any) -> bool:
    """Only an explicit yes counts; anything unclear is treated as no."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "y", "1")
    return False


def as_text(value: Any, limit: int = 4000) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        try:
            value = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            value = str(value)
    return value.strip()[:limit]


def as_id_list(value: Any) -> List[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(v) for v in value if v is not None and str(v).strip()]


def clause_list(value: Any) -> List[str]:
    ids = [str(v).strip() for v in value] if isinstance(value, (list, tuple)) else []
    ids = [v for v in ids if v]
    return ids or list(DEFAULT_CLAUSE_IDS)


# ---------------------------------------------------------------- clauses and positions

def _canon(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def match_clause_id(key: Any, clause_ids: List[str]) -> Optional[str]:
    """Map whatever the LLM wrote ("Article 3.1", "art. 7", an agenda line) to a clause id."""
    k = _canon(key)
    if not k:
        return None
    canon_ids = [(_canon(cid), cid) for cid in clause_ids]
    for c, cid in canon_ids:
        if k == c:
            return cid
    m = re.match(r"(?:art(?:icle)?\s*)?(\d+)\b", k)
    if m:
        for c, cid in canon_ids:
            cm = re.fullmatch(r"article (\d+)", c)
            if cm and cm.group(1) == m.group(1):
                return cid
    for c, cid in canon_ids:
        if not c or c.startswith("article "):
            continue
        singular = c.rstrip("s")
        if k.startswith(c + " ") or k == singular or k.startswith(singular + " "):
            return cid
    # Last resort: a longer phrase that names exactly one known clause
    # ("Review and amendment of Article 12 regarding compliance").
    mentioned = set()
    for num in re.findall(r"\barticle (\d+)\b", k):
        for c, cid in canon_ids:
            if c == f"article {num}":
                mentioned.add(cid)
    for c, cid in canon_ids:
        if c and not c.startswith("article ") and re.search(r"\b" + re.escape(c.rstrip("s")), k):
            mentioned.add(cid)
    if len(mentioned) == 1:
        return mentioned.pop()
    return None


def normalize_position(value: Any) -> Optional[str]:
    v = _canon(value).replace(" ", "")
    if not v:
        return None
    if "condition" in v:
        return "Conditional Support"
    if any(w in v for w in ("oppos", "reject", "object", "against", "notsupport", "nosupport")):
        return "Oppose"
    if "support" in v or v in ("accept", "agree", "approve", "endorse"):
        return "Support"
    return None


def normalize_positions(raw: Any, clause_ids: List[str],
                        fallback: Optional[Dict[str, str]] = None) -> Tuple[Dict[str, str], List[str], List[str]]:
    """Return (positions for every clause id, keys that could not be mapped, clause ids left unspecified).

    A clause the LLM did not cover is taken from `fallback` if given, otherwise
    marked "Unspecified". Nothing is invented.
    """
    pairs: List[Tuple[Any, Any]] = []
    if isinstance(raw, dict):
        pairs = list(raw.items())
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                key = item.get("clause_id") or item.get("clause") or item.get("id")
                pairs.append((key, item.get("position") or item.get("stance")))
    positions: Dict[str, str] = {}
    dropped: List[str] = []
    for key, value in pairs:
        cid = match_clause_id(key, clause_ids)
        pos = normalize_position(value)
        if cid is None or pos is None:
            dropped.append(f"{key}: {value}")
            continue
        positions.setdefault(cid, pos)
    missing: List[str] = []
    for cid in clause_ids:
        if cid in positions:
            continue
        if fallback and fallback.get(cid) in VALID_POSITIONS:
            positions[cid] = fallback[cid]
        else:
            positions[cid] = UNSPECIFIED
            missing.append(cid)
    return {cid: positions[cid] for cid in clause_ids}, dropped, missing


def normalize_conditions(raw: Any, clause_ids: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            cid = match_clause_id(key, clause_ids)
            text = as_text(value, 600)
            if cid and text:
                out[cid] = text
    return out


def map_clause_list(raw: Any, clause_ids: List[str]) -> List[str]:
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return []
    found = []
    for item in raw:
        cid = match_clause_id(item, clause_ids)
        if cid and cid not in found:
            found.append(cid)
    return [cid for cid in clause_ids if cid in found]


def map_clause_dict(raw: Any, clause_ids: List[str], limit: int = 1200) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            cid = match_clause_id(key, clause_ids)
            text = as_text(value, limit)
            if cid and text:
                out[cid] = text
    return out


def normalize_move(value: Any) -> str:
    v = _canon(value)
    if v.startswith("endors") or v.startswith("support"):
        return "endorsement"
    if v.startswith("conce") or v.startswith("compromis") or v.startswith("yield"):
        return "concession"
    return "amendment"


def count_position_changes(previous: Dict[str, str], current: Dict[str, str]) -> int:
    changed = 0
    for cid, pos in current.items():
        old = previous.get(cid)
        if old in VALID_POSITIONS and pos in VALID_POSITIONS and old != pos:
            changed += 1
    return changed


def tally_positions(all_positions: Dict[str, Dict[str, str]], clause_ids: List[str]) -> Dict[str, Dict[str, int]]:
    tally = {cid: {p: 0 for p in VALID_POSITIONS + (UNSPECIFIED,)} for cid in clause_ids}
    for positions in all_positions.values():
        for cid in clause_ids:
            pos = positions.get(cid, UNSPECIFIED)
            if pos not in tally[cid]:
                pos = UNSPECIFIED
            tally[cid][pos] += 1
    return tally


def unsettled_clauses(tally: Dict[str, Dict[str, int]], clause_ids: List[str]) -> List[str]:
    """A clause is unsettled if anyone opposes it or anyone has not stated a position."""
    return [cid for cid in clause_ids
            if tally.get(cid, {}).get("Oppose", 0) > 0 or tally.get(cid, {}).get(UNSPECIFIED, 0) > 0]


# ---------------------------------------------------------------- routing

def _natural_key(value: str):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", str(value))]


def find_table_delegates(agent) -> List[str]:
    """Delegates at this Chairperson's table, in speaking order.

    Uses the agent's own relationships (Relationship.csv), so it also works in
    distributed mode, and filters by group_id from the delegates' public profile.
    """
    my_group = agent.profile.get_data("group_id", None)
    found: Dict[str, Tuple[int, str]] = {}
    for rel in agent.get_all_relationships():
        target_id = str(rel.target_id)
        if target_id == "ENV":
            continue
        info = rel.target_info if isinstance(rel.target_info, dict) else {}
        agent_type = info.get("agent_type")
        if agent_type is not None and agent_type != "Delegate":
            continue
        if agent_type is None and "speaking_order" not in info:
            continue
        group = info.get("group_id")
        if my_group is not None and group is not None and str(group) != str(my_group):
            continue
        found[target_id] = (as_int(info.get("speaking_order"), 10 ** 6), target_id)
    ordered = sorted(found.values(), key=lambda x: (x[0], _natural_key(x[1])))
    return [tid for _, tid in ordered]


# ---------------------------------------------------------------- text for prompts

def positions_table_text(all_positions: Dict[str, Dict[str, str]], clause_ids: List[str],
                         names: Optional[Dict[str, str]] = None) -> str:
    names = names or {}
    lines = []
    for did, positions in all_positions.items():
        label = names.get(did, did)
        cells = ", ".join(f"{cid}: {positions.get(cid, UNSPECIFIED)}" for cid in clause_ids)
        lines.append(f"- Delegate {label} (ID {did}): {cells}")
    return "\n".join(lines) if lines else "(no positions)"


def amendment_text_block(amendments: List[Dict[str, Any]]) -> str:
    if not amendments:
        return "(none)"
    blocks = []
    for a in amendments:
        lines = [f"- Delegate ID {a.get('delegate_id')}"
                 + (f" ({a.get('country')})" if a.get('country') else "")
                 + f": move = {a.get('move')}"]
        if a.get("failed"):
            lines.append(f"  (no valid response this turn: {a.get('failure_reason', '')})")
        if a.get("target_clauses"):
            lines.append(f"  target clauses: {', '.join(a.get('target_clauses'))}")
        if a.get("endorsed_delegate_id"):
            lines.append(f"  endorses the proposal of delegate ID {a.get('endorsed_delegate_id')}")
        if a.get("amendment_text"):
            lines.append(f"  text: {a.get('amendment_text')}")
        if a.get("rationale"):
            lines.append(f"  rationale: {a.get('rationale')}")
        if a.get("conditions"):
            lines.append(f"  conditions: {json.dumps(a.get('conditions'), ensure_ascii=False)}")
        lines.append(f"  willing to make further concessions in a later round: "
                     f"{'yes' if a.get('willing_to_make_further_concessions') else 'no'}")
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


def tally_text(tally: Dict[str, Dict[str, int]]) -> str:
    return "\n".join(
        f"- {cid}: " + ", ".join(f"{p} {n}" for p, n in counts.items() if n)
        for cid, counts in tally.items()
    )


def default_round_summary(round_no: int, unsettled: List[str], settled: List[str],
                          failed_delegates: List[str]) -> str:
    parts = [f"Round {round_no}: settled clauses: {', '.join(settled) or 'none'}; "
             f"unsettled clauses: {', '.join(unsettled) or 'none'}."]
    if failed_delegates:
        parts.append(f"No valid response from delegate(s) {', '.join(failed_delegates)}.")
    return " ".join(parts)


def fallback_agreement_text(draft: str, accepted: List[Dict[str, Any]], positions: Dict[str, str]) -> str:
    lines = ["Agreed text (compiled automatically because the Chairperson's drafting step failed).",
             "", "Original draft:", draft, "", "Positions at adoption:"]
    lines += [f"- {cid}: {pos}" for cid, pos in positions.items()]
    texts = [a for a in accepted if a.get("amendment_text")]
    if texts:
        lines += ["", "Amendments on the table at adoption:"]
        lines += [f"- Delegate {a.get('delegate_id')}: {a.get('amendment_text')}" for a in texts]
    return "\n".join(lines)


def fallback_impasse_record(round_no: int, unsettled: List[str], tally: Dict[str, Dict[str, int]],
                            willingness: Dict[str, bool]) -> str:
    lines = [f"Impasse recorded after round {round_no} (compiled automatically because the "
             f"Chairperson's drafting step failed).",
             f"Unsettled clauses: {', '.join(unsettled) or 'none'}.", "Position counts:", tally_text(tally),
             "Willingness to consider further concessions:"]
    lines += [f"- Delegate {did}: {'yes' if ok else 'no'}" for did, ok in willingness.items()]
    return "\n".join(lines)
