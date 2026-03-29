from datetime import date, datetime

from pawpal_system import Customer, Pet, Task


def print_schedule(owner: Customer, target_date: date) -> None:
	print(f"\nPawPal Daily Schedule for {owner.name} ({target_date.isoformat()})")
	print("=" * 60)

	matching_schedules = [
		schedule for schedule in owner.schedules if schedule.schedule_date == target_date
	]

	if not matching_schedules:
		print("No schedules found for today.")
		return

	for schedule in matching_schedules:
		pet = schedule.planned_for
		print(f"\nPet: {pet.name} ({pet.species}, age {pet.age})")
		print(f"Available Window: {schedule.available_windows}")
		print(f"Tasks ({len(schedule.tasks)}):")

		schedule.sort_tasks_by_priority()
		for task in schedule.tasks:
			print(
				f"  - [{task.priority.upper()}] {task.title} | "
				f"{task.duration_minutes} min | time: {task.time_constraint} | ${task.cost:.2f}"
			)

		print(f"Total Minutes: {schedule.total_minutes_used}")
		print(f"Total Cost: ${schedule.total_cost:.2f}")


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

	# Add at least three tasks with different times across pets.
	dog_schedule.add_task(
		Task(
			task_id=1,
			title="Morning Walk",
			duration_minutes=30,
			priority="high",
			time_constraint="09:00",
			cost=12.0,
		)
	)
	dog_schedule.add_task(
		Task(
			task_id=2,
			title="Breakfast Feeding",
			duration_minutes=15,
			priority="medium",
			time_constraint="09:45",
			cost=4.0,
		)
	)
	cat_schedule.add_task(
		Task(
			task_id=3,
			title="Medication",
			duration_minutes=10,
			priority="high",
			time_constraint="14:00",
			cost=6.5,
		)
	)

	print_schedule(owner, today)


if __name__ == "__main__":
	main()
