from typing import Any, List, Optional
import json
import asyncio
from loguru import logger
from onesim.models import JsonBlockParser
from onesim.agent import GeneralAgent
from onesim.profile import AgentProfile
from onesim.memory import MemoryStrategy
from onesim.planning import PlanningBase
from onesim.events import *
from onesim.relationship import RelationshipManager
from .events import *
from .negotiation_utils import *


class Delegate(GeneralAgent):
    def __init__(self,
                 sys_prompt: str | None = None,
                 model_config_name: str = None,
                 event_bus_queue: asyncio.Queue = None,
                 profile: AgentProfile = None,
                 memory: MemoryStrategy = None,
                 planning: PlanningBase = None,
                 relationship_manager: RelationshipManager = None) -> None:
        super().__init__(sys_prompt, model_config_name, event_bus_queue, profile, memory, planning, relationship_manager)
        self.register_event("DraftDistributedEvent", "review_draft_and_form_position")
        self.register_event("PositionFormedEvent", "propose_amendment_or_concession")
        self.register_event("PriorAmendmentsEvent", "propose_amendment_or_concession")

    async def review_draft_and_form_position(self, event: Event) -> List[Event]:
        # Every path below ends with a PositionFormedEvent, so the next step always runs.
        round_no = as_int(getattr(event, "round_number", 1), 1)
        state = get_state(self)
        rs = round_state(state, round_no)
        if rs.get("review_started"):
            logger.warning(f"Delegate {self.profile_id}: duplicate draft for round {round_no} ignored.")
            return []
        rs["review_started"] = True

        clause_ids = clause_list(getattr(event, "clause_ids", None))
        rs["clause_ids"] = clause_ids
        rs["chair_id"] = str(event.from_agent_id)
        rs["speaking_order"] = as_id_list(getattr(event, "speaking_order", None)) or [str(self.profile_id)]
        rs["max_rounds"] = as_int(getattr(event, "max_rounds", round_no), round_no)
        rs["previous_round_summary"] = as_text(getattr(event, "previous_round_summary", ""))
        rs["open_divergences"] = list(getattr(event, "open_divergences", None) or [])
        rs["chair_proposals"] = dict(getattr(event, "chair_proposals", None) or {})
        state["round"] = max(state.get("round", 0), round_no)
        previous_positions = dict(state.get("last_positions", {}))

        positions = {cid: UNSPECIFIED for cid in clause_ids}
        conditions = {}
        notes = ""
        failed = False
        failure_reason = ""
        try:
            observation = "\n".join([
                f"Negotiation round: {round_no} of {rs['max_rounds']}",
                "Draft agreement:",
                as_text(getattr(event, "draft_content", "")),
                "Agenda:",
                "\n".join(f"- {item}" for item in (getattr(event, "agenda_items", None) or [])),
                "Your positions at the end of the previous round: "
                + (json.dumps(previous_positions, ensure_ascii=False) if previous_positions else "none (first round)"),
                "Chair's summary of the previous round: " + (rs["previous_round_summary"] or "none"),
                "Clauses still unsettled: " + (", ".join(rs["open_divergences"]) or "none"),
                "Chair's compromise proposals: "
                + (json.dumps(rs["chair_proposals"], ensure_ascii=False) if rs["chair_proposals"] else "none"),
            ])
            instruction = """You are a national delegate at a roundtable negotiation on a draft multilateral climate cooperation agreement.
Review the draft (and, after the first round, the chair's summary and compromise proposals) and state your country's position on every clause, based on the national interests in your profile on emission reduction intensity and climate finance.

Use exactly these clause IDs as keys: <<CLAUSE_IDS>>
Allowed positions: "Support", "Conditional Support", "Oppose".
Only use "Conditional Support" if you can name the condition that would make the clause acceptable.

Return a JSON object:
{
    "clause_positions": {"<clause ID>": "Support | Conditional Support | Oppose"},
    "conditions": {"<clause ID with Conditional Support>": "<what would make it acceptable>"},
    "reasoning_summary": "<2-3 sentences on how your national interests shape these positions>"
}""".replace("<<CLAUSE_IDS>>", json.dumps(clause_ids))
            result = await self.generate_reaction(instruction, observation)
            if not isinstance(result, dict):
                raise ValueError("reply is not a JSON object")
            positions, dropped, missing = normalize_positions(result.get("clause_positions"), clause_ids)
            conditions = normalize_conditions(result.get("conditions"), clause_ids)
            notes = as_text(result.get("reasoning_summary"), 1200)
            if dropped:
                logger.warning(f"Delegate {self.profile_id}: ignored unrecognised positions {dropped}")
            if missing:
                logger.warning(f"Delegate {self.profile_id}: no position given for {missing}; recorded as {UNSPECIFIED}")
            if len(missing) == len(clause_ids):
                failed = True
                failure_reason = "no usable clause positions in the reply"
        except Exception as e:
            failed = True
            failure_reason = f"{type(e).__name__}: {e}"
            logger.error(f"Delegate {self.profile_id}: reviewing the draft failed in round {round_no}: {failure_reason}")

        rs["review_positions"] = positions
        rs["review_conditions"] = conditions
        rs["review_notes"] = notes
        rs["review_failed"] = failed
        self.profile.update_data("current_round", round_no)
        return [PositionFormedEvent(
            self.profile_id,
            self.profile_id,
            round_number=round_no,
            delegate_id=str(self.profile_id),
            clause_positions=positions,
            conditions=conditions,
            position_notes=notes,
            failed=failed,
            failure_reason=failure_reason,
        )]

    async def propose_amendment_or_concession(self, event: Event) -> List[Event]:
        # Runs once per round, after this delegate has its own positions and has
        # heard every delegate who speaks before it. Always reports to the chair.
        round_no = as_int(getattr(event, "round_number", 1), 1)
        state = get_state(self)
        rs = round_state(state, round_no)
        kind = event_name(event)
        if kind == "PositionFormedEvent":
            if str(event.from_agent_id) != str(self.profile_id):
                return []
            rs["own_positions_ready"] = True
        elif kind == "PriorAmendmentsEvent":
            rs["prior_amendments"] = list(getattr(event, "prior_amendments", None) or [])
        else:
            return []

        if rs.get("proposal_started") or not rs.get("own_positions_ready"):
            return []
        order = rs.get("speaking_order") or [str(self.profile_id)]
        my_index = order.index(str(self.profile_id)) if str(self.profile_id) in order else 0
        if my_index > 0 and rs.get("prior_amendments") is None:
            return []
        rs["proposal_started"] = True

        clause_ids = rs.get("clause_ids") or clause_list(None)
        prior = rs.get("prior_amendments") or []
        review_positions = rs.get("review_positions") or {cid: UNSPECIFIED for cid in clause_ids}
        previous_final = dict(state.get("last_positions", {}))
        country = as_text(self.profile.get_data("country", ""), 200)

        proposal = {
            "delegate_id": str(self.profile_id),
            "country": country,
            "move": "failed",
            "target_clauses": [],
            "amendment_text": "",
            "rationale": "",
            "endorsed_delegate_id": "",
            "willing_to_make_further_concessions": False,
            "clause_positions": dict(review_positions),
            "conditions": dict(rs.get("review_conditions") or {}),
            "failed": True,
            "failure_reason": "",
        }
        try:
            observation = "\n".join([
                f"Negotiation round: {round_no} of {rs.get('max_rounds', round_no)}",
                f"You speak in position {my_index + 1} of {len(order)}.",
                "Your positions after reviewing the draft this round: " + json.dumps(review_positions, ensure_ascii=False),
                "Your conditions: " + json.dumps(rs.get("review_conditions") or {}, ensure_ascii=False),
                "Your reasoning: " + (rs.get("review_notes") or "none"),
                "Clauses still unsettled from earlier rounds: " + (", ".join(rs.get("open_divergences") or []) or "none"),
                "Chair's compromise proposals: "
                + (json.dumps(rs.get("chair_proposals") or {}, ensure_ascii=False) if rs.get("chair_proposals") else "none"),
                "Proposals made earlier in this round by other delegates:",
                amendment_text_block(prior),
            ])
            instruction = """You are a national delegate at a roundtable negotiation on a draft multilateral climate cooperation agreement. It is your turn to speak.
Choose one move:
- "amendment": propose specific new wording for one or more clauses;
- "endorsement": back a proposal already made in this round by another delegate (give that delegate's ID);
- "concession": soften your own position on a clause to help the table reach agreement.
After hearing the earlier speakers you may revise your positions. Report your positions as they stand at the end of your turn.

Use exactly these clause IDs: <<CLAUSE_IDS>>
Allowed positions: "Support", "Conditional Support", "Oppose".
IDs of delegates who spoke before you in this round: <<PRIOR_IDS>>

Return a JSON object:
{
    "move": "amendment | endorsement | concession",
    "target_clauses": ["<clause ID>"],
    "amendment_text": "<the wording you propose, or the concession you make>",
    "rationale": "<diplomatic or legal justification>",
    "endorsed_delegate_id": "<ID of the delegate whose proposal you endorse, otherwise empty string>",
    "final_positions": {"<clause ID>": "Support | Conditional Support | Oppose"},
    "conditions": {"<clause ID with Conditional Support>": "<what would make it acceptable>"},
    "willing_to_make_further_concessions": true or false
}
Set willing_to_make_further_concessions to true only if you would genuinely consider additional concessions in a later round.""".replace(
                "<<CLAUSE_IDS>>", json.dumps(clause_ids)).replace(
                "<<PRIOR_IDS>>", json.dumps([str(a.get("delegate_id")) for a in prior]))
            result = await self.generate_reaction(instruction, observation)
            if not isinstance(result, dict):
                raise ValueError("reply is not a JSON object")

            move = normalize_move(result.get("move"))
            prior_ids = [str(a.get("delegate_id")) for a in prior if a.get("delegate_id")]
            endorsed = as_text(result.get("endorsed_delegate_id"), 50)
            if endorsed not in prior_ids:
                if endorsed:
                    logger.warning(f"Delegate {self.profile_id}: endorsed unknown delegate '{endorsed}', ignored")
                endorsed = ""
            if move == "endorsement" and not endorsed:
                move = "amendment"
            final_positions, dropped, _ = normalize_positions(result.get("final_positions"), clause_ids, fallback=review_positions)
            if dropped:
                logger.warning(f"Delegate {self.profile_id}: ignored unrecognised positions {dropped}")
            conditions = dict(rs.get("review_conditions") or {})
            conditions.update(normalize_conditions(result.get("conditions"), clause_ids))
            conditions = {cid: text for cid, text in conditions.items() if final_positions.get(cid) == "Conditional Support"}
            proposal.update({
                "move": move,
                "target_clauses": map_clause_list(result.get("target_clauses"), clause_ids),
                "amendment_text": as_text(result.get("amendment_text"), 2000),
                "rationale": as_text(result.get("rationale"), 1500),
                "endorsed_delegate_id": endorsed,
                "willing_to_make_further_concessions": as_bool(result.get("willing_to_make_further_concessions")),
                "clause_positions": final_positions,
                "conditions": conditions,
                "failed": False,
            })
        except Exception as e:
            proposal["failure_reason"] = f"{type(e).__name__}: {e}"
            logger.error(f"Delegate {self.profile_id}: proposing failed in round {round_no}: {proposal['failure_reason']}")

        if rs.get("review_failed") and not proposal["failure_reason"]:
            proposal["failure_reason"] = "positions could not be formed when reviewing the draft"
        positions_changed = count_position_changes(previous_final, proposal["clause_positions"])
        proposal["positions_changed"] = positions_changed

        merged = dict(previous_final)
        merged.update({cid: pos for cid, pos in proposal["clause_positions"].items() if pos != UNSPECIFIED})
        state["last_positions"] = merged
        rs["proposal"] = proposal
        self.profile.update_data("current_round", round_no)
        self.profile.update_data("clause_positions", proposal["clause_positions"])
        self.profile.update_data("last_move", proposal["move"])
        self.profile.update_data("willing_to_concede", proposal["willing_to_make_further_concessions"])
        self.profile.update_data("positions_changed_last_round", positions_changed)

        events = []
        chair_id = rs.get("chair_id")
        if chair_id:
            events.append(AmendmentProposedEvent(self.profile_id, chair_id, round_number=round_no, **proposal))
        else:
            logger.error(f"Delegate {self.profile_id}: no chairperson known for round {round_no}; proposal not delivered.")
        if my_index + 1 < len(order):
            events.append(PriorAmendmentsEvent(
                self.profile_id,
                order[my_index + 1],
                round_number=round_no,
                prior_amendments=prior + [proposal],
            ))
        return events
