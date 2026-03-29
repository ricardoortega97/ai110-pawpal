"""Tests for PawPal+ domain models."""

import os
import sys

# Allow imports from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date

from pawpal_system import Customer, Pet, Task


# ---------------------------------------------------------------------------
# Test 1 — Task Completion
# ---------------------------------------------------------------------------
# Verification checklist:
# ## [ ] Normal case: mark_complete() changes status to True
# ## [ ] Edge case: task starts as incomplete (completed defaults to False)
# ---------------------------------------------------------------------------
def test_mark_complete_changes_status():
    task = Task(task_id=1, title="Morning Walk", duration_minutes=30, priority="high")

    # Edge case: task must start as incomplete before anything is called
    assert task.completed is False

    task.mark_complete()

    assert task.completed is True


# ---------------------------------------------------------------------------
# Test 2 — Task Addition
# ---------------------------------------------------------------------------
# Verification checklist:
# ## [ ] Normal case: adding a valid task increases the pet's task count by 1
# ## [ ] Edge case: task with zero duration is rejected (count unchanged)
# ---------------------------------------------------------------------------
def test_add_task_increases_pet_task_count():
    pet = Pet(pet_id=1, name="Mochi", species="dog", age=3)
    owner = Customer(customer_id=1, name="Jordan", contact_info="jordan@email.com")
    owner.add_pet(pet)

    schedule = owner.create_schedule(
        schedule_date=date.today(),
        available_windows="08:00-12:00",
        planned_for=pet,
    )

    assert len(schedule.tasks) == 0

    valid_task = Task(task_id=1, title="Morning Walk", duration_minutes=30, priority="high", cost=10.0)
    schedule.add_task(valid_task)

    assert len(schedule.tasks) == 1

    # Edge case: zero duration is invalid — task must be rejected, count stays at 1
    bad_task = Task(task_id=2, title="Ghost Task", duration_minutes=0, priority="low", cost=0.0)
    result = schedule.add_task(bad_task)
    assert result is False
    assert len(schedule.tasks) == 1
