"""PawPal+ core domain models and schedule skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


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

	def mark_complete(self) -> None:
		# Idempotent by design: once complete, repeated calls keep it complete.
		self.completed = True

	def is_high_priority(self) -> bool:
		return self.priority.strip().lower() == "high"

	def is_time_constrained(self) -> bool:
		return bool(self.time_constraint.strip())


@dataclass
class Customer:
	customer_id: int
	name: str
	contact_info: str
	preferred_time_windows: str = ""
	care_preferences: str = ""
	pets: list[Pet] = field(default_factory=list)
	schedules: list[DailySchedule] = field(default_factory=list)
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
	) -> DailySchedule:
		if not self.owns_pet(planned_for):
			raise ValueError("Cannot create schedule for a pet not owned by this customer")

		schedule = DailySchedule(
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


@dataclass
class DailySchedule:
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

		self.tasks.append(task)
		self.total_minutes_used += task.duration_minutes
		self.total_cost += task.cost
		return True

	def sort_tasks_by_priority(self) -> None:
		priority_order = {"high": 0, "medium": 1, "low": 2}
		self.tasks.sort(
			key=lambda task: priority_order.get(task.priority.strip().lower(), 3)
		)

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
