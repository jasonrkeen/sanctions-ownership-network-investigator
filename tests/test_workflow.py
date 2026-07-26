from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sowni.database import InvestigatorDatabase
from sowni.models import CaseWorkflowEvent


def workflow_event(
    *,
    status: str = "open",
    priority: str = "normal",
    actor: str = "JK",
    notes: str = "Opened the case for review.",
) -> CaseWorkflowEvent:
    return CaseWorkflowEvent(
        run_id="test-run",
        status=status,
        priority=priority,
        assignee="Analyst One",
        tags=[" sanctions ", "High Value", "SANCTIONS"],
        actor=actor,
        notes=notes,
        created_at="2026-07-26T12:00:00+00:00",
    )


class CaseWorkflowTests(unittest.TestCase):
    def test_events_are_append_only_and_latest_event_drives_state(self):
        with tempfile.TemporaryDirectory() as temp:
            database = InvestigatorDatabase(Path(temp) / "investigator.sqlite")
            try:
                default_state = database.get_case_workflow_state("test-run")
                first_id = database.save_case_workflow_event(workflow_event())
                second = workflow_event(
                    status="in_review",
                    priority="high",
                    notes="Prioritized after reviewing the ownership path.",
                )
                second.assignee = "Senior Analyst"
                second.created_at = "2026-07-26T13:00:00+00:00"
                second_id = database.save_case_workflow_event(second)
                events = database.list_case_workflow_events(run_id="test-run")
                current_state = database.get_case_workflow_state("test-run")
                event_count = database.count_case_workflow_events("test-run")
            finally:
                database.close()

        self.assertEqual(default_state["status"], "open")
        self.assertEqual(default_state["priority"], "normal")
        self.assertEqual((first_id, second_id), (1, 2))
        self.assertEqual([event.event_id for event in events], [2, 1])
        self.assertEqual(events[0].tags, ["sanctions", "High Value"])
        self.assertEqual(current_state["status"], "in_review")
        self.assertEqual(current_state["priority"], "high")
        self.assertEqual(current_state["assignee"], "Senior Analyst")
        self.assertEqual(event_count, 2)

    def test_workflow_event_requires_controlled_values_actor_and_notes(self):
        with tempfile.TemporaryDirectory() as temp:
            database = InvestigatorDatabase(Path(temp) / "investigator.sqlite")
            try:
                with self.assertRaisesRegex(ValueError, "Unsupported case status"):
                    database.save_case_workflow_event(
                        workflow_event(status="unsupported")
                    )
                with self.assertRaisesRegex(ValueError, "Unsupported case priority"):
                    database.save_case_workflow_event(
                        workflow_event(priority="urgent")
                    )
                with self.assertRaisesRegex(ValueError, "actor is required"):
                    database.save_case_workflow_event(
                        workflow_event(actor="")
                    )
                with self.assertRaisesRegex(ValueError, "notes are required"):
                    database.save_case_workflow_event(
                        workflow_event(notes="")
                    )
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()
