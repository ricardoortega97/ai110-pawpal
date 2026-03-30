"""PawPal+ core domain models and schedule skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Sequence


@dataclass
class Pet:
	pet_id: int
	name: str
	species: str
	age: int
	medications: str = ""
	special_care_notes: str = ""

	def is_senior(self) -> bool:
		return self.age >= 7

	def requires_medication(self) -> bool:
		return bool(self.medications.strip())


@dataclass
class Task:
	task_id: int
	title: str
	duration_minutes: int
	priority: str
	time_constraint: str = ""
	cost: float = 0.0
	completed: bool = False
	recurrence: str = ""
	scheduled_for: date | None = None
	recurrence_generated: bool = False

	def mark_complete(self) -> None:
		# Idempotent by design: once complete, repeated calls keep it complete.
		self.completed = True

	def is_high_priority(self) -> bool:
		return self.priority.strip().lower() == "high"

	def is_time_constrained(self) -> bool:
		return bool(self.time_constraint.strip())

	def recurrence_interval_days(self) -> int:
		recurrence_type = self.recurrence.strip().lower()
		if recurrence_type == "daily":
			return 1
		if recurrence_type == "weekly":
			return 7
		return 0

	def create_next_occurrence(self, next_task_id: int, base_date: date) -> Task | None:
		interval_days = self.recurrence_interval_days()
		if interval_days <= 0 or self.recurrence_generated:
			return None

		source_date = self.scheduled_for or base_date
		next_date = source_date + timedelta(days=interval_days)
		self.recurrence_generated = True

		return Task(
			task_id=next_task_id,
			title=self.title,
			duration_minutes=self.duration_minutes,
			priority=self.priority,
			time_constraint=self.time_constraint,
			cost=self.cost,
			completed=False,
			recurrence=self.recurrence,
			scheduled_for=next_date,
		)


@dataclass
class Customer:
	customer_id: int
	name: str
	contact_info: str
	preferred_time_windows: str = ""
	care_preferences: str = ""
	pets: list[Pet] = field(default_factory=list)
	schedules: list[Scheduler] = field(default_factory=list)
	requested_pickup_time: datetime | None = None
	requested_dropoff_time: datetime | None = None

	def add_pet(self, pet: Pet) -> None:
		if any(existing.pet_id == pet.pet_id for existing in self.pets):
			raise ValueError(f"Pet with id {pet.pet_id} already exists for this customer")
		self.pets.append(pet)

	def owns_pet(self, pet: Pet) -> bool:
		return any(existing.pet_id == pet.pet_id for existing in self.pets)

	def create_schedule(
		self,
		schedule_date: date,
		available_windows: str,
		planned_for: Pet,
		pickup_time: datetime | None = None,
		dropoff_time: datetime | None = None,
	) -> Scheduler:
		if not self.owns_pet(planned_for):
			raise ValueError("Cannot create schedule for a pet not owned by this customer")

		schedule = Scheduler(
			schedule_date=schedule_date,
			available_windows=available_windows,
			planned_for=planned_for,
			customer_id=self.customer_id,
			pickup_time=pickup_time,
			dropoff_time=dropoff_time,
		)
		self.schedules.append(schedule)
		return schedule

	def update_preferences(self, time_windows: str, care_notes: str) -> None:
		self.preferred_time_windows = time_windows
		self.care_preferences = care_notes

	def request_pickup(self, preferred_time: datetime) -> None:
		self.requested_pickup_time = preferred_time

	def request_dropoff(self, preferred_time: datetime) -> None:
		self.requested_dropoff_time = preferred_time

	def filter_tasks(
		self,
		completed: bool | None = None,
		pet_name: str | None = None,
	) -> list[Task]:
		filtered_tasks: list[Task] = []
		normalized_pet_name = pet_name.strip().lower() if pet_name else None

		for schedule in self.schedules:
			if normalized_pet_name and schedule.planned_for.name.strip().lower() != normalized_pet_name:
				continue

			for task in schedule.tasks:
				if completed is not None and task.completed != completed:
					continue
				filtered_tasks.append(task)

		return filtered_tasks


@dataclass
class Scheduler:
	schedule_date: date
	available_windows: str
	planned_for: Pet
	customer_id: int
	pickup_time: datetime | None = None
	dropoff_time: datetime | None = None
	tasks: list[Task] = field(default_factory=list)
	total_minutes_used: int = 0
	total_cost: float = 0.0

	def __post_init__(self) -> None:
		self.refresh_totals()
		if self.pickup_time and self.dropoff_time and self.pickup_time > self.dropoff_time:
			raise ValueError("pickup_time cannot be later than dropoff_time")

	def add_task(self, task: Task) -> bool:
		if task.duration_minutes <= 0 or task.cost < 0:
			return False

		if task.scheduled_for is None:
			task.scheduled_for = self.schedule_date

		self.tasks.append(task)
		self.total_minutes_used += task.duration_minutes
		self.total_cost += task.cost
		return True

	def _next_task_id(self) -> int:
		if not self.tasks:
			return 1
		return max(task.task_id for task in self.tasks) + 1

	def mark_task_complete(self, task_id: int) -> Task | None:
		for task in self.tasks:
			if task.task_id != task_id:
				continue

			task.mark_complete()
			next_task = task.create_next_occurrence(
				next_task_id=self._next_task_id(),
				base_date=self.schedule_date,
			)
			if next_task is not None:
				self.add_task(next_task)
			return next_task

		return None

	def detect_time_conflicts_with(self, other_schedules: Sequence[Scheduler] | None = None) -> list[str]:
		schedules_to_check: list[Scheduler] = [self]
		if other_schedules:
			schedules_to_check.extend(other_schedules)
		return Scheduler.detect_time_conflicts(schedules_to_check)

	@staticmethod
	def detect_time_conflicts(schedules: Sequence[Scheduler]) -> list[str]:
		warnings: list[str] = []
		tasks_by_slot: dict[tuple[date, str], list[tuple[str, str]]] = {}

		for schedule in schedules:
			for task in schedule.tasks:
				time_text = task.time_constraint.strip()
				if not time_text:
					continue

				try:
					datetime.strptime(time_text, "%H:%M")
				except ValueError:
					warnings.append(
						f"Warning: Invalid time '{task.time_constraint}' for task '{task.title}' on pet '{schedule.planned_for.name}'."
					)
					continue

				slot_date = task.scheduled_for or schedule.schedule_date
				slot_key = (slot_date, time_text)
				tasks_by_slot.setdefault(slot_key, []).append(
					(schedule.planned_for.name, task.title)
				)

		for (slot_date, time_text), entries in sorted(tasks_by_slot.items()):
			if len(entries) < 2:
				continue

			entry_text = ", ".join(
				f"{pet_name}:{task_title}" for pet_name, task_title in entries
			)
			warnings.append(
				f"Warning: Time conflict at {slot_date.isoformat()} {time_text} -> {entry_text}"
			)

		return warnings

	def sort_tasks_by_priority(self) -> None:
		priority_order = {"high": 0, "medium": 1, "low": 2}
		self.tasks.sort(
			key=lambda task: priority_order.get(task.priority.strip().lower(), 3)
		)

	@staticmethod
	def sort_by_time(tasks: list[Task]) -> list[Task]:
		# Keep tasks without a time constraint at the end of the list.
		tasks.sort(
			key=lambda task: (
				task.time_constraint.strip() == "",
				task.time_constraint.strip() if task.time_constraint.strip() else "99:99",
			)
		)
		return tasks

	def sort_tasks_by_time(self) -> None:
		Scheduler.sort_by_time(self.tasks)

	def calculate_total_minutes(self) -> int:
		return sum(task.duration_minutes for task in self.tasks)

	def calculate_total_cost(self) -> float:
		return sum(task.cost for task in self.tasks)

	def refresh_totals(self) -> None:
		self.total_minutes_used = self.calculate_total_minutes()
		self.total_cost = self.calculate_total_cost()

	def validate_time_constraints(self) -> bool:
		if self.pickup_time and self.dropoff_time and self.pickup_time > self.dropoff_time:
			return False

		if any(task.duration_minutes <= 0 for task in self.tasks):
			return False

		if any(task.cost < 0 for task in self.tasks):
			return False

		return True
