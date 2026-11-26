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


class Chairperson(GeneralAgent):
    def __init__(self,
                 sys_prompt: str | None = None,
                 model_config_name: str = None,
                 event_bus_queue: asyncio.Queue = None,
                 profile: AgentProfile = None,
                 memory: MemoryStrategy = None,
                 planning: PlanningBase = None,
                 relationship_manager: RelationshipManager = None) -> None:
        super().__init__(sys_prompt, model_config_name, event_bus_queue, profile, memory, planning, relationship_manager)
        self.register_event("StartEvent", "set_agenda_and_distribute_draft")
        self.register_event("AmendmentProposedEvent", "collect_positions_and_divergences")
        self.register_event("PositionsCollectedEvent", "determine_outcome")
        self.register_event("ConsensusReachedEvent", "issue_agreed_text")
        self.register_event("ImpasseDeclaredEvent", "declare_impasse")

    async def set_agenda_and_distribute_draft(self, event: Event) -> List[Event]:
        # One StartEvent = one environment step. Each step opens a new negotiation
        # round until the table has concluded; after that the step is closed at once.
        state = get_state(self)
        if state.get("concluded"):
            return [NegotiationClosedEvent(
                self.profile_id, "ENV",
                round_number=state.get("round", 0),
                closure_reason="already_concluded",
                final_outcome=state.get("outcome", ""),
            )]
        if state.get("round_open"):
            # The environment moved on (e.g. idle timeout) while this round is still running.
            # The running round will close the step when it finishes.
            logger.warning(f"Chairperson {self.profile_id}: StartEvent received while round "
                           f"{state.get('round')} is still open; consider a larger bus_idle_timeout.")
            return []
        state["round_open"] = True
        round_no = state.get("round", 0) + 1

        delegates = find_table_delegates(self)
        draft_content = as_text(await self.get_env_data("draft_content", ""), 20000)
        clause_ids = clause_list(await self.get_env_data("clause_ids", None))
        agenda_items = await self.get_env_data("agenda_items", [])
        max_rounds = max(1, as_int(await self.get_env_data("max_rounds", 3), 3))

        problem = ""
        if not delegates:
            problem = "no_delegates_at_table"
        elif not draft_content:
            problem = "missing_draft_content"
        if problem:
            logger.error(f"Chairperson {self.profile_id}: cannot open the negotiation ({problem}).")
            state.update({"concluded": True, "round_open": False, "outcome": "Failed", "round": round_no})
            self.profile.update_data("outcome_status", "Failed")
            self.profile.update_data("current_round", round_no)
            return [NegotiationClosedEvent(self.profile_id, "ENV", round_number=round_no,
                                           closure_reason=problem, final_outcome="Failed")]

        state.update({
            "round": round_no,
            "max_rounds": max_rounds,
            "clause_ids": clause_ids,
            "draft_content": draft_content,
        })
        round_state(state, round_no).update({
            "expected": list(delegates),
            "received": {},
            "collected": False,
            "deciding": False,
        })
        self.profile.update_data("current_round", round_no)
        self.profile.update_data("outcome_status", "In progress")

        return [
            DraftDistributedEvent(
                self.profile_id,
                delegate_id,
                round_number=round_no,
                max_rounds=max_rounds,
                draft_content=draft_content,
                clause_ids=clause_ids,
                agenda_items=list(agenda_items) if isinstance(agenda_items, list) else [],
                speaking_order=list(delegates),
                previous_round_summary=state.get("last_summary", ""),
                open_divergences=list(state.get("open_divergences", [])),
                chair_proposals=dict(state.get("chair_proposals", {})),
            )
            for delegate_id in delegates
        ]

    async def collect_positions_and_divergences(self, event: Event) -> List[Event]:
        # Waits until every delegate at the table has spoken in this round.
        # No LLM call: positions arrive structured and are tallied in code.
        state = get_state(self)
        round_no = as_int(getattr(event, "round_number", 0), 0)
        rs = state.get("rounds", {}).get(round_no)
        sender = str(event.from_agent_id)
        if rs is None or rs.get("collected"):
            logger.warning(f"Chairperson {self.profile_id}: late proposal from {sender} for round {round_no} ignored.")
            return []
        if sender not in rs.get("expected", []):
            logger.warning(f"Chairperson {self.profile_id}: proposal from {sender}, who is not at this table, ignored.")
            return []
        if sender in rs["received"]:
            return []

        clause_ids = state.get("clause_ids") or clause_list(None)
        positions, _, _ = normalize_positions(getattr(event, "clause_positions", None), clause_ids)
        rs["received"][sender] = {
            "delegate_id": sender,
            "country": as_text(getattr(event, "country", ""), 200),
            "move": as_text(getattr(event, "move", "")) or "amendment",
            "target_clauses": map_clause_list(getattr(event, "target_clauses", None), clause_ids),
            "amendment_text": as_text(getattr(event, "amendment_text", ""), 2000),
            "rationale": as_text(getattr(event, "rationale", ""), 1500),
            "endorsed_delegate_id": as_text(getattr(event, "endorsed_delegate_id", ""), 50),
            "willing_to_make_further_concessions": as_bool(getattr(event, "willing_to_make_further_concessions", False)),
            "clause_positions": positions,
            "conditions": normalize_conditions(getattr(event, "conditions", None), clause_ids),
            "positions_changed": as_int(getattr(event, "positions_changed", 0), 0),
            "failed": as_bool(getattr(event, "failed", False)),
            "failure_reason": as_text(getattr(event, "failure_reason", ""), 500),
        }
        if len(rs["received"]) < len(rs["expected"]):
            return []
        rs["collected"] = True

        amendments = [rs["received"][did] for did in rs["expected"]]
        all_positions = {a["delegate_id"]: a["clause_positions"] for a in amendments}
        tally = tally_positions(all_positions, clause_ids)
        unsettled = unsettled_clauses(tally, clause_ids)
        self.profile.update_data("open_divergence_count", len(unsettled))
        return [PositionsCollectedEvent(
            self.profile_id,
            self.profile_id,
            round_number=round_no,
            all_positions=all_positions,
            all_amendments=amendments,
            clause_tally=tally,
            unsettled_clauses=unsettled,
        )]

    async def determine_outcome(self, event: Event) -> List[Event]:
        # The outcome rule is applied in code so it cannot contradict the positions:
        #   every clause settled                -> Consensus
        #   clauses unsettled after last round  -> Impasse
        #   otherwise                           -> adjourn to the next round
        # The LLM only flags incompatible conditions, proposes compromises and summarises.
        state = get_state(self)
        round_no = as_int(getattr(event, "round_number", 0), 0)
        rs = state.get("rounds", {}).get(round_no)
        if rs is None or rs.get("deciding"):
            return []
        rs["deciding"] = True

        clause_ids = state.get("clause_ids") or clause_list(None)
        max_rounds = state.get("max_rounds", 1)
        all_positions = getattr(event, "all_positions", None) or {}
        amendments = getattr(event, "all_amendments", None) or []
        tally = getattr(event, "clause_tally", None) or tally_positions(all_positions, clause_ids)
        unsettled = map_clause_list(getattr(event, "unsettled_clauses", None), clause_ids)
        willingness = {str(a.get("delegate_id")): as_bool(a.get("willing_to_make_further_concessions")) for a in amendments}
        failed_delegates = [str(a.get("delegate_id")) for a in amendments if a.get("failed")]
        names = {str(a.get("delegate_id")): a.get("country") or str(a.get("delegate_id")) for a in amendments}

        conflicts, proposals, summary = [], {}, ""
        try:
            observation = "\n".join([
                f"Round {round_no} of {max_rounds}.",
                "Positions at the end of this round:",
                positions_table_text(all_positions, clause_ids, names),
                "Counts per clause:",
                tally_text(tally),
                "Clauses unsettled because someone opposes them or gave no position: " + (", ".join(unsettled) or "none"),
                "Proposals made this round:",
                amendment_text_block(amendments),
                "Your summary of the previous round: " + (state.get("last_summary") or "none"),
            ])
            instruction = """You chair a roundtable negotiation on a draft multilateral climate cooperation agreement.
The outcome is decided by a fixed rule, not by you: a clause is settled only if nobody opposes it and every delegate has stated a position; the negotiation ends in consensus when every clause is settled, ends in impasse when clauses are still unsettled after the final round, and otherwise continues with another round.

Your tasks:
1. "conflicting_conditions": clause IDs that look settled (everyone supports or conditionally supports) but where the conditions attached are incompatible with each other, so the clause is not really agreed. Use [] if there are none.
2. "compromise_proposals": for each unsettled clause, including any you list in 1, one concrete compromise wording the delegates can consider in the next round.
3. "chair_summary": a neutral summary of where the negotiation stands, 3 to 5 sentences.

Use exactly these clause IDs: <<CLAUSE_IDS>>
Return a JSON object:
{
    "conflicting_conditions": ["<clause ID>"],
    "compromise_proposals": {"<clause ID>": "<compromise wording>"},
    "chair_summary": "<summary>"
}""".replace("<<CLAUSE_IDS>>", json.dumps(clause_ids))
            result = await self.generate_reaction(instruction, observation)
            if not isinstance(result, dict):
                raise ValueError("reply is not a JSON object")
            conflicts = [cid for cid in map_clause_list(result.get("conflicting_conditions"), clause_ids)
                         if cid not in unsettled]
            proposals = map_clause_dict(result.get("compromise_proposals"), clause_ids)
            summary = as_text(result.get("chair_summary"), 2000)
        except Exception as e:
            logger.error(f"Chairperson {self.profile_id}: chair analysis failed in round {round_no}: "
                         f"{type(e).__name__}: {e}. Falling back to the rule-based summary.")

        open_clauses = [cid for cid in clause_ids if cid in unsettled or cid in conflicts]
        settled = [cid for cid in clause_ids if cid not in open_clauses]
        if not summary:
            summary = default_round_summary(round_no, open_clauses, settled, failed_delegates)
        proposals = {cid: text for cid, text in proposals.items() if cid in open_clauses}

        if not open_clauses:
            outcome = "Consensus"
        elif round_no >= max_rounds:
            outcome = "Impasse"
        else:
            outcome = "Continue"

        state.setdefault("history", []).append({
            "round": round_no,
            "unsettled": open_clauses,
            "conflicting_conditions": conflicts,
            "failed_delegates": failed_delegates,
            "outcome": outcome,
        })
        state["open_divergences"] = open_clauses
        state["chair_proposals"] = proposals
        state["last_summary"] = summary
        state["last_tally"] = tally
        self.profile.update_data("open_divergence_count", len(open_clauses))
        self.profile.update_data("aligned_clauses", settled)
        self.profile.update_data("divergent_clauses", open_clauses)
        self.profile.update_data("round_summary", summary)

        if outcome == "Consensus":
            final_positions = {}
            for cid in clause_ids:
                counts = tally.get(cid, {})
                final_positions[cid] = "Conditional Support" if counts.get("Conditional Support", 0) else "Support"
            return [ConsensusReachedEvent(
                self.profile_id, self.profile_id,
                round_number=round_no,
                aligned_clauses=settled,
                final_accepted_positions=final_positions,
                accepted_amendments=amendments,
                chair_summary=summary,
            )]
        if outcome == "Impasse":
            return [ImpasseDeclaredEvent(
                self.profile_id, self.profile_id,
                round_number=round_no,
                divergent_clauses=open_clauses,
                concession_willingness_status=willingness,
                clause_tally=tally,
                chair_summary=summary,
            )]
        state["round_open"] = False
        self.profile.update_data("outcome_status", "In progress")
        return [RoundAdjournedEvent(
            self.profile_id, "ENV",
            round_number=round_no,
            open_divergences=open_clauses,
            chair_summary=summary,
        )]

    async def issue_agreed_text(self, event: Event) -> List[Event]:
        state = get_state(self)
        if state.get("concluded"):
            return []
        state["concluded"] = True
        round_no = as_int(getattr(event, "round_number", state.get("round", 0)), state.get("round", 0))
        clause_ids = state.get("clause_ids") or clause_list(None)
        draft = state.get("draft_content", "")
        final_positions = getattr(event, "final_accepted_positions", None) or {}
        accepted = getattr(event, "accepted_amendments", None) or []

        final_text = ""
        try:
            observation = "\n".join([
                "Original draft:", draft,
                "Final positions per clause: " + json.dumps(final_positions, ensure_ascii=False),
                "Proposals and conditions on the table in the final round:",
                amendment_text_block(accepted),
                "Chair's summary: " + as_text(getattr(event, "chair_summary", "")),
            ])
            instruction = """You chair a roundtable negotiation on a multilateral climate cooperation agreement, and every clause has now been settled.
Write the final agreed text. Start from the original draft and work in the amendments and the conditions that the delegates' final positions depend on. Keep the clause structure of the draft: <<CLAUSE_IDS>>. Do not add clauses that were not negotiated.

Return a JSON object:
{
    "final_agreed_text": "<complete text of the agreed agreement>"
}""".replace("<<CLAUSE_IDS>>", json.dumps(clause_ids))
            result = await self.generate_reaction(instruction, observation)
            if isinstance(result, dict):
                final_text = as_text(result.get("final_agreed_text"), 20000)
        except Exception as e:
            logger.error(f"Chairperson {self.profile_id}: drafting the agreed text failed: {type(e).__name__}: {e}")
        if not final_text:
            final_text = fallback_agreement_text(draft, accepted, final_positions)

        state.update({"round_open": False, "outcome": "Consensus"})
        self.profile.update_data("outcome_status", "Consensus")
        self.profile.update_data("final_agreed_text", final_text)
        return [AgreementFinalizedEvent(self.profile_id, "ENV", round_number=round_no,
                                        final_agreed_text=final_text, simulation_status="Consensus")]

    async def declare_impasse(self, event: Event) -> List[Event]:
        state = get_state(self)
        if state.get("concluded"):
            return []
        state["concluded"] = True
        round_no = as_int(getattr(event, "round_number", state.get("round", 0)), state.get("round", 0))
        clause_ids = state.get("clause_ids") or clause_list(None)
        divergent = map_clause_list(getattr(event, "divergent_clauses", None), clause_ids)
        willingness = getattr(event, "concession_willingness_status", None) or {}
        tally = getattr(event, "clause_tally", None) or state.get("last_tally", {})

        record = ""
        try:
            observation = "\n".join([
                f"Rounds held: {round_no}",
                "Unsettled clauses: " + (", ".join(divergent) or "none"),
                "Position counts per clause:",
                tally_text(tally),
                "Willingness to consider further concessions: " + json.dumps(willingness, ensure_ascii=False),
                "Chair's summary: " + as_text(getattr(event, "chair_summary", "")),
            ])
            instruction = """You chair a roundtable negotiation on a multilateral climate cooperation agreement. The final round has ended with clauses still unsettled, so the negotiation ends in impasse.
Write a formal impasse record covering: the position distribution on each unsettled clause, the main reasons agreement was not reached, and each delegate's stated willingness to make further concessions.
Willingness to consider concessions later does not mean a compromise was reached. Describe a delegate as unwilling only if their status is false.

Return a JSON object:
{
    "impasse_record": "<formal impasse record>"
}"""
            result = await self.generate_reaction(instruction, observation)
            if isinstance(result, dict):
                record = as_text(result.get("impasse_record"), 20000)
        except Exception as e:
            logger.error(f"Chairperson {self.profile_id}: drafting the impasse record failed: {type(e).__name__}: {e}")
        if not record:
            record = fallback_impasse_record(round_no, divergent, tally,
                                             {str(k): as_bool(v) for k, v in willingness.items()})

        state.update({"round_open": False, "outcome": "Impasse"})
        self.profile.update_data("outcome_status", "Impasse")
        self.profile.update_data("impasse_record", record)
        return [ImpasseRecordedEvent(self.profile_id, "ENV", round_number=round_no,
                                     impasse_record=record, simulation_status="Impasse")]
