"""Tests for the State Manager module."""

import pytest
import json
from pathlib import Path

from paws.state_manager import (
    EventLog,
    Event,
    initialize_state,
    append_event,
    get_last_successful_step,
    get_loop_counter
)


class TestEventLog:
    def test_create_empty_log(self, tmp_path):
        log_path = tmp_path / "test.json"
        log = EventLog(log_path=log_path)
        
        assert log.events == []
        assert log.log_path == log_path
    
    def test_append_event(self, tmp_path):
        log_path = tmp_path / "test.json"
        log = EventLog(log_path=log_path)
        
        event = Event(
            timestamp="2026-01-17T00:00:00Z",
            event_type="TEST",
            step_id="step_1",
            payload={"key": "value"}
        )
        log.append(event)
        
        assert len(log.events) == 1
        assert log.events[0].event_type == "TEST"
        
        # Check file was written
        assert log_path.exists()
        with open(log_path) as f:
            data = json.load(f)
        assert len(data) == 1
    
    def test_load_existing_log(self, tmp_path):
        log_path = tmp_path / "existing.json"
        
        # Create a log file
        existing_data = [
            {"timestamp": "2026-01-17T00:00:00Z", "event_type": "STATE_ZERO", "step_id": None, "payload": {}},
            {"timestamp": "2026-01-17T00:01:00Z", "event_type": "STEP_SUCCESS", "step_id": "s1", "payload": {}}
        ]
        with open(log_path, 'w') as f:
            json.dump(existing_data, f)
        
        # Load it
        log = EventLog.load(log_path)
        
        assert len(log.events) == 2
        assert log.events[0].event_type == "STATE_ZERO"
        assert log.events[1].step_id == "s1"


class TestInitializeState:
    def test_creates_log_with_state_zero(self, tmp_path):
        log_path = tmp_path / "logs" / "test.json"
        user_inputs = {"prompt": "Hello", "resources": []}
        
        log = initialize_state(user_inputs, str(log_path))
        
        assert len(log.events) == 1
        assert log.events[0].event_type == "STATE_ZERO"
        assert log.events[0].payload["user_inputs"] == user_inputs
        assert log_path.exists()
    
    def test_creates_parent_directories(self, tmp_path):
        log_path = tmp_path / "deep" / "nested" / "logs" / "test.json"
        
        log = initialize_state({"prompt": "test"}, str(log_path))
        
        assert log_path.exists()


class TestAppendEvent:
    def test_append_step_start(self, tmp_path):
        log = initialize_state({"prompt": "test"}, str(tmp_path / "log.json"))
        
        append_event(log, "STEP_START", "step_1", {"description": "First step"})
        
        assert len(log.events) == 2
        assert log.events[1].event_type == "STEP_START"
        assert log.events[1].step_id == "step_1"
    
    def test_append_without_payload(self, tmp_path):
        log = initialize_state({"prompt": "test"}, str(tmp_path / "log.json"))
        
        append_event(log, "WORKFLOW_COMPLETE")
        
        assert log.events[-1].event_type == "WORKFLOW_COMPLETE"
        assert log.events[-1].payload == {}


class TestGetLastSuccessfulStep:
    def test_no_successful_steps(self, tmp_path):
        log = initialize_state({"prompt": "test"}, str(tmp_path / "log.json"))
        
        result = get_last_successful_step(log)
        
        assert result is None
    
    def test_finds_last_success(self, tmp_path):
        log = initialize_state({"prompt": "test"}, str(tmp_path / "log.json"))
        append_event(log, "STEP_SUCCESS", "step_1")
        append_event(log, "STEP_SUCCESS", "step_2")
        append_event(log, "STEP_START", "step_3")
        
        result = get_last_successful_step(log)
        
        assert result == "step_2"
    
    def test_ignores_failures(self, tmp_path):
        log = initialize_state({"prompt": "test"}, str(tmp_path / "log.json"))
        append_event(log, "STEP_SUCCESS", "step_1")
        append_event(log, "STEP_FAILURE", "step_2")
        
        result = get_last_successful_step(log)
        
        assert result == "step_1"


class TestGetLoopCounter:
    def test_no_iterations(self, tmp_path):
        log = initialize_state({"prompt": "test"}, str(tmp_path / "log.json"))
        
        result = get_loop_counter(log, "my_loop")
        
        assert result == 0
    
    def test_counts_iterations(self, tmp_path):
        log = initialize_state({"prompt": "test"}, str(tmp_path / "log.json"))
        append_event(log, "LOOP_ITERATION", "my_loop", {"counter": 1})
        append_event(log, "LOOP_ITERATION", "my_loop", {"counter": 2})
        append_event(log, "LOOP_ITERATION", "my_loop", {"counter": 3})
        
        result = get_loop_counter(log, "my_loop")
        
        assert result == 3
