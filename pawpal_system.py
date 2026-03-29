"""PawPal+ core domain models and schedule skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class PetProfile:
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
	pets: list[PetProfile] = field(default_factory=list)
	requested_pickup_time: datetime | None = None
	requested_dropoff_time: datetime | None = None

	def add_pet(self, pet: PetProfile) -> None:
		self.pets.append(pet)

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
	planned_for: PetProfile
	pickup_time: datetime | None = None
	dropoff_time: datetime | None = None
	tasks: list[Task] = field(default_factory=list)
	total_minutes_used: int = 0
	total_cost: float = 0.0

	def add_task(self, task: Task) -> bool:
		if task.duration_minutes <= 0:
			return False

		self.tasks.append(task)
		self.total_minutes_used = self.calculate_total_minutes()
		self.total_cost = self.calculate_total_cost()
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

	def validate_time_constraints(self) -> bool:
		# Placeholder for time-window parsing and constraint validation logic.
		return True
