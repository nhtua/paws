"""
State Manager - Event Sourcing for Crash Recovery

Handles the append-only event log that enables resumability after crashes.
The Executor is stateless; this module manages persistent state.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict


@dataclass
class Event:
    """A single event in the log."""
    timestamp: str
    event_type: str
    step_id: Optional[str]
    payload: Dict[str, Any]


@dataclass 
class EventLog:
    """Append-only event log stored as JSON file."""
    log_path: Path
    events: List[Event] = field(default_factory=list)
    
    def append(self, event: Event):
        """Append event to in-memory list and persist to file."""
        self.events.append(event)
        self._persist()
    
    def _persist(self):
        """Write all events to file."""
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump([asdict(e) for e in self.events], f, indent=2)
    
    @classmethod
    def load(cls, log_path: Path) -> 'EventLog':
        """Load existing event log from file."""
        if not log_path.exists():
            return cls(log_path=log_path, events=[])
        
        with open(log_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        events = [Event(**e) for e in data]
        return cls(log_path=log_path, events=events)


def initialize_state(user_inputs: Dict[str, Any], log_path: str) -> EventLog:
    """
    Create a new append-only log and record State Zero.
    
    Args:
        user_inputs: The user_inputs section from the AOL file
        log_path: Path to store the event log JSON file
        
    Returns:
        New EventLog instance
    """
    path = Path(log_path)
    
    # Create parent directories if needed
    path.parent.mkdir(parents=True, exist_ok=True)
    
    log = EventLog(log_path=path, events=[])
    
    # Record State Zero
    state_zero = Event(
        timestamp=_now(),
        event_type="STATE_ZERO",
        step_id=None,
        payload={"user_inputs": user_inputs}
    )
    log.append(state_zero)
    
    return log


def append_event(
    log: EventLog, 
    event_type: str, 
    step_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None
) -> None:
    """
    Write an action or observation to the permanent log.
    
    Event types:
    - STATE_ZERO: Initial state
    - STEP_START: Step execution beginning
    - STEP_SUCCESS: Step completed successfully
    - STEP_FAILURE: Step failed
    - STEP_SKIPPED: Step skipped (condition false)
    - LOOP_ITERATION: Loop counter incremented
    - WORKFLOW_COMPLETE: All steps finished
    - WORKFLOW_ABORTED: Execution stopped due to error
    
    Args:
        log: The EventLog to append to
        event_type: Type of event
        step_id: ID of the step this event relates to (if applicable)
        payload: Additional data about the event
    """
    event = Event(
        timestamp=_now(),
        event_type=event_type,
        step_id=step_id,
        payload=payload or {}
    )
    log.append(event)


def get_last_successful_step(log: EventLog) -> Optional[str]:
    """
    Find the last step that emitted a SUCCESS event.
    
    Used for crash recovery - allows skipping already-completed steps.
    
    Args:
        log: The EventLog to search
        
    Returns:
        Step ID of the last successful step, or None if no steps completed
    """
    for event in reversed(log.events):
        if event.event_type == "STEP_SUCCESS" and event.step_id:
            return event.step_id
    return None


def get_loop_counter(log: EventLog, loop_id: str) -> int:
    """
    Get the current iteration count for a loop.
    
    Args:
        log: The EventLog to search
        loop_id: ID of the loop_begin step
        
    Returns:
        Current iteration count (0 if loop hasn't started)
    """
    count = 0
    for event in log.events:
        if event.event_type == "LOOP_ITERATION" and event.step_id == loop_id:
            count = event.payload.get("counter", count + 1)
    return count


def _now() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()
