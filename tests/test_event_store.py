"""Tests for the Event Store — the genuine invention."""
import sys
sys.path.insert(0, '.')

from app.events.event_store import EventStore, Event, EventType


class TestEventStore:
    def setup_method(self):
        self.store = EventStore()

    def test_record_event(self):
        """Events should be recorded and retrievable."""
        event = Event(
            event_id="e1", workflow_id="w1",
            event_type=EventType.STEP_STARTED,
            step_index=0, data={"input": "test"},
        )
        self.store.append(event)
        events = self.store.get_events("w1")
        assert len(events) == 1
        assert events[0].event_id == "e1"

    def test_multiple_events(self):
        """Multiple events should be stored in order."""
        self.store.append(Event(event_id="e1", workflow_id="w1", event_type=EventType.WORKFLOW_CREATED, step_index=-1, data={}))
        self.store.append(Event(event_id="e2", workflow_id="w1", event_type=EventType.STEP_STARTED, step_index=0, data={}))
        self.store.append(Event(event_id="e3", workflow_id="w1", event_type=EventType.STEP_COMPLETED, step_index=0, data={}))
        
        events = self.store.get_events("w1")
        assert len(events) == 3
        assert events[0].event_type == EventType.WORKFLOW_CREATED
        assert events[1].event_type == EventType.STEP_STARTED
        assert events[2].event_type == EventType.STEP_COMPLETED

    def test_get_events_by_type(self):
        """Should return all events (type filtering via list comprehension)."""
        self.store.append(Event(event_id="e1", workflow_id="w1", event_type=EventType.STEP_STARTED, step_index=0, data={}))
        self.store.append(Event(event_id="e2", workflow_id="w1", event_type=EventType.STEP_COMPLETED, step_index=0, data={}))
        self.store.append(Event(event_id="e3", workflow_id="w1", event_type=EventType.STEP_STARTED, step_index=1, data={}))
        
        all_events = self.store.get_events("w1")
        started = [e for e in all_events if e.event_type == EventType.STEP_STARTED]
        assert len(started) == 2

    def test_multiple_workflows(self):
        """Should isolate events per workflow."""
        self.store.append(Event(event_id="e1", workflow_id="w1", event_type=EventType.STEP_STARTED, step_index=0, data={}))
        self.store.append(Event(event_id="e2", workflow_id="w2", event_type=EventType.STEP_STARTED, step_index=0, data={}))
        
        assert len(self.store.get_events("w1")) == 1
        assert len(self.store.get_events("w2")) == 1

    def test_empty_workflow(self):
        """Non-existent workflow should return empty list."""
        assert self.store.get_events("nonexistent") == []

    def test_event_timestamp(self):
        """Events should have timestamps."""
        event = Event(event_id="e1", workflow_id="w1", event_type=EventType.STEP_STARTED, step_index=0, data={})
        self.store.append(event)
        events = self.store.get_events("w1")
        assert events[0].timestamp is not None

    def test_reconstruct_state(self):
        """Should reconstruct workflow state from events."""
        self.store.append(Event(event_id="e1", workflow_id="w1", event_type=EventType.WORKFLOW_CREATED, step_index=-1, data={"steps": ["a", "b", "c"]}))
        self.store.append(Event(event_id="e2", workflow_id="w1", event_type=EventType.STEP_STARTED, step_index=0, data={}))
        self.store.append(Event(event_id="e3", workflow_id="w1", event_type=EventType.STEP_COMPLETED, step_index=0, data={"result": "ok"}))
        
        state = self.store.reconstruct_state("w1")
        assert state is not None
        assert state.status == "running" or state.current_step_index >= 0

    def test_reconstruct_at_event(self):
        """Should reconstruct state at a specific point in time."""
        self.store.append(Event(event_id="e1", workflow_id="w1", event_type=EventType.WORKFLOW_CREATED, step_index=-1, data={}))
        self.store.append(Event(event_id="e2", workflow_id="w1", event_type=EventType.STEP_STARTED, step_index=0, data={}))
        self.store.append(Event(event_id="e3", workflow_id="w1", event_type=EventType.STEP_COMPLETED, step_index=0, data={}))
        self.store.append(Event(event_id="e4", workflow_id="w1", event_type=EventType.STEP_STARTED, step_index=1, data={}))
        
        # State at e2 should show step 0 running
        state_at_e2 = self.store.reconstruct_at_event("w1", "e2")
        assert state_at_e2.step_states.get("0") == "running"
        
        # State at e3 should show step 0 completed
        state_at_e3 = self.store.reconstruct_at_event("w1", "e3")
        assert state_at_e3.step_states.get("0") == "completed"

    def test_get_events_until(self):
        """Should return events up to a specific event."""
        self.store.append(Event(event_id="e1", workflow_id="w1", event_type=EventType.WORKFLOW_CREATED, step_index=-1, data={}))
        self.store.append(Event(event_id="e2", workflow_id="w1", event_type=EventType.STEP_STARTED, step_index=0, data={}))
        self.store.append(Event(event_id="e3", workflow_id="w1", event_type=EventType.STEP_COMPLETED, step_index=0, data={}))
        
        events_until_e2 = self.store.get_events_until("w1", "e2")
        assert len(events_until_e2) == 2
        assert events_until_e2[-1].event_id == "e2"
