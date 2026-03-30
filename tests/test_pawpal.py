"""Tests for PawPal+ domain models."""

import os
import sys

# Allow imports from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date

from pawpal_system import Customer, Pet, Scheduler, Task


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


def test_scheduler_sort_by_time_orders_hhmm_and_puts_blank_last():
    tasks = [
        Task(task_id=1, title="Meal", duration_minutes=20, priority="medium", time_constraint="09:45"),
        Task(task_id=2, title="Medication", duration_minutes=10, priority="high", time_constraint="08:30"),
        Task(task_id=3, title="Play", duration_minutes=15, priority="low", time_constraint=""),
        Task(task_id=4, title="Walk", duration_minutes=30, priority="high", time_constraint="10:00"),
    ]

    Scheduler.sort_by_time(tasks)

    assert [task.time_constraint for task in tasks] == ["08:30", "09:45", "10:00", ""]


def test_customer_filter_tasks_by_completion_or_pet_name():
    owner = Customer(customer_id=1, name="Jordan", contact_info="jordan@email.com")
    mochi = Pet(pet_id=101, name="Mochi", species="dog", age=4)
    nova = Pet(pet_id=102, name="Nova", species="cat", age=9)
    owner.add_pet(mochi)
    owner.add_pet(nova)

    dog_schedule = owner.create_schedule(
        schedule_date=date.today(),
        available_windows="08:00-12:00",
        planned_for=mochi,
    )
    cat_schedule = owner.create_schedule(
        schedule_date=date.today(),
        available_windows="13:00-18:00",
        planned_for=nova,
    )

    walk = Task(task_id=1, title="Walk", duration_minutes=30, priority="high", completed=True)
    feed = Task(task_id=2, title="Feed", duration_minutes=15, priority="medium", completed=False)
    meds = Task(task_id=3, title="Medication", duration_minutes=10, priority="high", completed=False)

    dog_schedule.add_task(walk)
    dog_schedule.add_task(feed)
    cat_schedule.add_task(meds)

    completed_tasks = owner.filter_tasks(completed=True)
    assert [task.title for task in completed_tasks] == ["Walk"]

    mochi_tasks = owner.filter_tasks(pet_name="Mochi")
    assert [task.title for task in mochi_tasks] == ["Walk", "Feed"]
