from datetime import date, datetime

from pawpal_system import Customer, Pet, Task
from formatting import (
	print_schedule,
	print_filtered_tasks,
	print_conflict_warnings,
	print_pet_summary,
	Colors,
	Emojis,
)


def main() -> None:
	today = date.today()

	# Create owner and two pets.
	owner = Customer(customer_id=1, name="Jordan", contact_info="jordan@email.com")
	machi = Pet(pet_id=101, name="Mochi", species="dog", age=4)
	nova = Pet(pet_id=102, name="Nova", species="cat", age=9, medications="thyroid")
	owner.add_pet(machi)
	owner.add_pet(nova)

	# Create one schedule per pet for today.
	dog_schedule = owner.create_schedule(
		schedule_date=today,
		available_windows="08:00-12:00",
		planned_for=machi,
		pickup_time=datetime.combine(today, datetime.strptime("08:15", "%H:%M").time()),
		dropoff_time=datetime.combine(today, datetime.strptime("11:30", "%H:%M").time()),
	)

	cat_schedule = owner.create_schedule(
		schedule_date=today,
		available_windows="13:00-18:00",
		planned_for=nova,
		pickup_time=datetime.combine(today, datetime.strptime("13:30", "%H:%M").time()),
		dropoff_time=datetime.combine(today, datetime.strptime("17:00", "%H:%M").time()),
	)

	# Add tasks out of chronological order to verify time-based sorting.
	dog_schedule.add_task(
		Task(
			task_id=1,
			title="Breakfast Feeding",
			duration_minutes=15,
			priority="medium",
			time_constraint="09:45",
			cost=4.0,
		)
	)
	dog_schedule.add_task(
		Task(
			task_id=2,
			title="Morning Walk",
			duration_minutes=30,
			priority="high",
			time_constraint="09:00",
			cost=12.0,
		)
	)
	dog_schedule.add_task(
		Task(
			task_id=3,
			title="Water Refill",
			duration_minutes=5,
			priority="low",
			time_constraint="08:30",
			cost=1.0,
		)
	)
	cat_schedule.add_task(
		Task(
			task_id=4,
			title="Litter Scoop",
			duration_minutes=10,
			priority="medium",
			time_constraint="16:00",
			cost=3.0,
		)
	)
	cat_schedule.add_task(
		Task(
			task_id=5,
			title="Medication",
			duration_minutes=10,
			priority="high",
			time_constraint="09:00",
			cost=6.5,
		)
	)

	# Mark one task complete so completion filtering has visible results.
	dog_schedule.tasks[1].mark_complete()

	# Display formatted output
	print_pet_summary(owner)
	print_schedule(owner, today)
	print_filtered_tasks(owner)
	print_conflict_warnings(owner)
	
	print(f"\n{Colors.SUCCESS}✨ Schedule generation complete!{Colors.RESET}\n")


if __name__ == "__main__":
	main()
