from onesim.events import Event
from typing import Dict, List, Any
from datetime import datetime


class StartEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)


class DraftDistributedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        round_number: int = 1,
        max_rounds: int = 1,
        draft_content: str = "",
        clause_ids: List[str] = None,
        agenda_items: List[str] = None,
        speaking_order: List[str] = None,
        previous_round_summary: str = "",
        open_divergences: List[str] = None,
        chair_proposals: Dict[str, str] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.round_number = round_number
        self.max_rounds = max_rounds
        self.draft_content = draft_content
        self.clause_ids = clause_ids if clause_ids is not None else []
        self.agenda_items = agenda_items if agenda_items is not None else []
        self.speaking_order = speaking_order if speaking_order is not None else []
        self.previous_round_summary = previous_round_summary
        self.open_divergences = open_divergences if open_divergences is not None else []
        self.chair_proposals = chair_proposals if chair_proposals is not None else {}


class NegotiationClosedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        round_number: int = 0,
        closure_reason: str = "",
        final_outcome: str = "",
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.round_number = round_number
        self.closure_reason = closure_reason
        self.final_outcome = final_outcome


class PositionFormedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        round_number: int = 1,
        delegate_id: str = "",
        clause_positions: Dict[str, str] = None,
        conditions: Dict[str, str] = None,
        position_notes: str = "",
        failed: bool = False,
        failure_reason: str = "",
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.round_number = round_number
        self.delegate_id = delegate_id
        self.clause_positions = clause_positions if clause_positions is not None else {}
        self.conditions = conditions if conditions is not None else {}
        self.position_notes = position_notes
        self.failed = failed
        self.failure_reason = failure_reason


class PriorAmendmentsEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        round_number: int = 1,
        prior_amendments: List[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.round_number = round_number
        self.prior_amendments = prior_amendments if prior_amendments is not None else []


class AmendmentProposedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        round_number: int = 1,
        delegate_id: str = "",
        country: str = "",
        move: str = "amendment",
        target_clauses: List[str] = None,
        amendment_text: str = "",
        rationale: str = "",
        endorsed_delegate_id: str = "",
        willing_to_make_further_concessions: bool = False,
        clause_positions: Dict[str, str] = None,
        conditions: Dict[str, str] = None,
        positions_changed: int = 0,
        failed: bool = False,
        failure_reason: str = "",
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.round_number = round_number
        self.delegate_id = delegate_id
        self.country = country
        self.move = move
        self.target_clauses = target_clauses if target_clauses is not None else []
        self.amendment_text = amendment_text
        self.rationale = rationale
        self.endorsed_delegate_id = endorsed_delegate_id
        self.willing_to_make_further_concessions = willing_to_make_further_concessions
        self.clause_positions = clause_positions if clause_positions is not None else {}
        self.conditions = conditions if conditions is not None else {}
        self.positions_changed = positions_changed
        self.failed = failed
        self.failure_reason = failure_reason


class PositionsCollectedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        round_number: int = 1,
        all_positions: Dict[str, Dict[str, str]] = None,
        all_amendments: List[Dict[str, Any]] = None,
        clause_tally: Dict[str, Dict[str, int]] = None,
        unsettled_clauses: List[str] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.round_number = round_number
        self.all_positions = all_positions if all_positions is not None else {}
        self.all_amendments = all_amendments if all_amendments is not None else []
        self.clause_tally = clause_tally if clause_tally is not None else {}
        self.unsettled_clauses = unsettled_clauses if unsettled_clauses is not None else []


class ConsensusReachedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        round_number: int = 1,
        aligned_clauses: List[str] = None,
        final_accepted_positions: Dict[str, str] = None,
        accepted_amendments: List[Dict[str, Any]] = None,
        chair_summary: str = "",
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.round_number = round_number
        self.aligned_clauses = aligned_clauses if aligned_clauses is not None else []
        self.final_accepted_positions = final_accepted_positions if final_accepted_positions is not None else {}
        self.accepted_amendments = accepted_amendments if accepted_amendments is not None else []
        self.chair_summary = chair_summary


class ImpasseDeclaredEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        round_number: int = 1,
        divergent_clauses: List[str] = None,
        concession_willingness_status: Dict[str, bool] = None,
        clause_tally: Dict[str, Dict[str, int]] = None,
        chair_summary: str = "",
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.round_number = round_number
        self.divergent_clauses = divergent_clauses if divergent_clauses is not None else []
        self.concession_willingness_status = concession_willingness_status if concession_willingness_status is not None else {}
        self.clause_tally = clause_tally if clause_tally is not None else {}
        self.chair_summary = chair_summary


class RoundAdjournedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        round_number: int = 1,
        open_divergences: List[str] = None,
        chair_summary: str = "",
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.round_number = round_number
        self.open_divergences = open_divergences if open_divergences is not None else []
        self.chair_summary = chair_summary


class AgreementFinalizedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        round_number: int = 1,
        final_agreed_text: str = "",
        simulation_status: str = "Consensus",
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.round_number = round_number
        self.final_agreed_text = final_agreed_text
        self.simulation_status = simulation_status


class ImpasseRecordedEvent(Event):
    def __init__(self,
        from_agent_id: str,
        to_agent_id: str,
        round_number: int = 1,
        impasse_record: str = "",
        simulation_status: str = "Impasse",
        **kwargs: Any
    ) -> None:
        super().__init__(from_agent_id=from_agent_id, to_agent_id=to_agent_id, **kwargs)
        self.round_number = round_number
        self.impasse_record = impasse_record
        self.simulation_status = simulation_status
