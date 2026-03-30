"""Formatting utilities for PawPal+ CLI output with colors, emojis, and tables."""

from colorama import Fore, Back, Style, init
from tabulate import tabulate
from datetime import date

from pawpal_system import Customer, Pet, Task, Scheduler

# Initialize colorama for cross-platform color support
init(autoreset=True)


# ── Color & Style Constants ───────────────────────────────────────────────────

class Colors:
	"""ANSI color codes and styles."""
	HEADER = Fore.MAGENTA + Style.BRIGHT
	SUCCESS = Fore.GREEN + Style.BRIGHT
	WARNING = Fore.YELLOW + Style.BRIGHT
	ERROR = Fore.RED + Style.BRIGHT
	INFO = Fore.CYAN
	MUTED = Fore.BLACK + Style.DIM
	PRIORITY_HIGH = Fore.RED + Style.BRIGHT
	PRIORITY_MEDIUM = Fore.YELLOW
	PRIORITY_LOW = Fore.GREEN
	RESET = Style.RESET_ALL


class Emojis:
	"""Task and status emojis."""
	SCHEDULE = "📅"
	TASK = "✓"
	WALK = "🚶"
	FEEDING = "🍽️"
	MEDICATION = "💊"
	GROOMING = "✂️"
	PLAY = "🎾"
	ENRICHMENT = "🧩"
	CONFLICT = "⚠️"
	SUCCESS = "✅"
	PENDING = "⏳"
	COMPLETE = "🎉"
	PET = "🐾"
	PERSON = "👤"
	CLOCK = "🕐"
	MONEY = "💰"
	ATTENTION = "🚨"


def get_task_emoji(task_title: str) -> str:
	"""Return emoji based on task title."""
	title_lower = task_title.lower()
	
	if "walk" in title_lower:
		return Emojis.WALK
	elif "feed" in title_lower or "food" in title_lower or "meal" in title_lower:
		return Emojis.FEEDING
	elif "med" in title_lower or "medication" in title_lower:
		return Emojis.MEDICATION
	elif "groom" in title_lower or "bath" in title_lower or "wash" in title_lower:
		return Emojis.GROOMING
	elif "play" in title_lower or "toy" in title_lower:
		return Emojis.PLAY
	elif "enrich" in title_lower:
		return Emojis.ENRICHMENT
	else:
		return Emojis.TASK


def get_priority_color(priority: str) -> str:
	"""Return color code based on priority."""
	priority_lower = priority.strip().lower()
	if priority_lower == "high":
		return Colors.PRIORITY_HIGH
	elif priority_lower == "medium":
		return Colors.PRIORITY_MEDIUM
	else:
		return Colors.PRIORITY_LOW


def get_status_indicator(completed: bool) -> str:
	"""Return status indicator with emoji."""
	if completed:
		return f"{Emojis.COMPLETE} {Colors.SUCCESS}Done{Colors.RESET}"
	else:
		return f"{Emojis.PENDING} {Colors.WARNING}Pending{Colors.RESET}"


def format_header(title: str, emoji: str = "") -> str:
	"""Format a section header."""
	prefix = f"{emoji} " if emoji else ""
	separator = "=" * (len(title) + len(prefix) + 2)
	return f"\n{Colors.HEADER}{prefix}{title}{Colors.RESET}\n{Colors.MUTED}{separator}{Colors.RESET}"


def format_subheader(title: str) -> str:
	"""Format a sub-header."""
	separator = "-" * (len(title) + 2)
	return f"\n{Colors.INFO}{title}{Colors.RESET}\n{Colors.MUTED}{separator}{Colors.RESET}"


def format_task_row(task: Task) -> list:
	"""Format a task as a table row."""
	emoji = get_task_emoji(task.title)
	priority_color = get_priority_color(task.priority)
	status = get_status_indicator(task.completed)
	
	return [
		f"{emoji} {task.title}",
		f"{priority_color}{task.priority.upper()}{Colors.RESET}",
		f"{task.duration_minutes} min",
		task.time_constraint or "—",
		f"${task.cost:.2f}",
		status,
	]


def print_schedule(owner: Customer, target_date: date) -> None:
	"""Print daily schedule with formatted table output."""
	print(format_header(f"PawPal+ Daily Schedule for {owner.name}", Emojis.SCHEDULE))
	print(f"{Colors.MUTED}Date: {target_date.isoformat()}{Colors.RESET}")
	
	matching_schedules = [
		schedule for schedule in owner.schedules if schedule.schedule_date == target_date
	]
	
	if not matching_schedules:
		print(f"\n{Colors.INFO}No schedules found for this date.{Colors.RESET}")
		return
	
	for schedule in matching_schedules:
		pet = schedule.planned_for
		pet_emoji = Emojis.PET
		
		# Add senior indicator
		senior_indicator = f" {Colors.WARNING}[SENIOR]{Colors.RESET}" if pet.is_senior() else ""
		med_indicator = f" {Colors.ERROR}[MEDS]{Colors.RESET}" if pet.requires_medication() else ""
		
		print(f"\n{pet_emoji} {Colors.SUCCESS}{pet.name}{Colors.RESET} | {pet.species.capitalize()}, age {pet.age}{senior_indicator}{med_indicator}")
		print(f"{Emojis.CLOCK} Available: {schedule.available_windows}")
		
		if schedule.pickup_time and schedule.dropoff_time:
			pickup_str = schedule.pickup_time.strftime("%H:%M")
			dropoff_str = schedule.dropoff_time.strftime("%H:%M")
			print(f"{Emojis.CLOCK} Pickup: {pickup_str} | Dropoff: {dropoff_str}")
		
		if not schedule.tasks:
			print(f"{Colors.MUTED}No tasks scheduled.{Colors.RESET}")
			continue
		
		# Sort and display tasks in table
		schedule.sort_tasks_by_time()
		headers = ["Task", "Priority", "Duration", "Time", "Cost", "Status"]
		rows = [format_task_row(task) for task in schedule.tasks]
		
		print("\n" + tabulate(rows, headers=headers, tablefmt="grid"))
		
		# Summary stats
		print(f"\n{Colors.INFO}Summary:{Colors.RESET}")
		total_time_hours = schedule.total_minutes_used / 60
		print(f"  {Emojis.CLOCK} Total Time: {schedule.total_minutes_used} min ({total_time_hours:.1f}h)")
		print(f"  {Emojis.MONEY} Total Cost: {Colors.SUCCESS}${schedule.total_cost:.2f}{Colors.RESET}")


def print_filtered_tasks(owner: Customer) -> None:
	"""Print filtered task views with formatted output."""
	print(format_header("Task Views", Emojis.TASK))
	
	# Incomplete tasks
	incomplete_tasks = owner.filter_tasks(completed=False)
	print(format_subheader(f"Incomplete Tasks ({len(incomplete_tasks)})"))
	
	if incomplete_tasks:
		headers = ["Task", "Pet", "Priority", "Time", "Duration", "Cost"]
		rows = []
		for task in incomplete_tasks:
			# Find which pet this task belongs to
			pet_name = next(
				(s.planned_for.name for s in owner.schedules for t in s.tasks if t.task_id == task.task_id),
				"Unknown"
			)
			emoji = get_task_emoji(task.title)
			priority_color = get_priority_color(task.priority)
			rows.append([
				f"{emoji} {task.title}",
				pet_name,
				f"{priority_color}{task.priority.upper()}{Colors.RESET}",
				task.time_constraint or "—",
				f"{task.duration_minutes} min",
				f"${task.cost:.2f}",
			])
		print(tabulate(rows, headers=headers, tablefmt="grid"))
	else:
		print(f"{Colors.SUCCESS}✨ All tasks complete!{Colors.RESET}")
	
	# Tasks by pet
	if owner.pets:
		print(format_subheader("Tasks by Pet"))
		for pet in owner.pets:
			pet_tasks = owner.filter_tasks(pet_name=pet.name)
			print(f"\n{Emojis.PET} {Colors.SUCCESS}{pet.name}{Colors.RESET} ({len(pet_tasks)} tasks)")
			
			if pet_tasks:
				headers = ["Task", "Priority", "Time", "Duration", "Status"]
				rows = []
				for task in pet_tasks:
					emoji = get_task_emoji(task.title)
					priority_color = get_priority_color(task.priority)
					status = "✅ Done" if task.completed else "⏳ Pending"
					rows.append([
						f"{emoji} {task.title}",
						f"{priority_color}{task.priority.upper()}{Colors.RESET}",
						task.time_constraint or "—",
						f"{task.duration_minutes} min",
						status,
					])
				print(tabulate(rows, headers=headers, tablefmt="simple"))
			else:
				print(f"{Colors.MUTED}No tasks scheduled{Colors.RESET}")


def print_conflict_warnings(owner: Customer) -> None:
	"""Print conflict detection results with formatted warnings."""
	print(format_header("Scheduling Analysis", Emojis.ATTENTION))
	
	if not owner.schedules:
		print(f"{Colors.INFO}No schedules to analyze.{Colors.RESET}")
		return
	
	warnings = owner.schedules[0].detect_time_conflicts_with(owner.schedules[1:])
	
	if not warnings:
		print(f"{Colors.SUCCESS}{Emojis.SUCCESS} No scheduling conflicts detected!{Colors.RESET}")
		return
	
	print(f"{Colors.WARNING}{Emojis.CONFLICT} Found {len(warnings)} warning(s):{Colors.RESET}\n")
	for i, warning in enumerate(warnings, 1):
		icon = f"{Colors.ERROR}✗{Colors.RESET}"
		print(f"  {icon} {warning}")


def print_pet_summary(owner: Customer) -> None:
	"""Print summary of pets under care."""
	print(format_header("Pet Care Summary", Emojis.PET))
	
	if not owner.pets:
		print(f"{Colors.MUTED}No pets registered.{Colors.RESET}")
		return
	
	headers = ["Pet", "Species", "Age", "Status", "Notes"]
	rows = []
	
	for pet in owner.pets:
		age_display = f"{pet.age} (Senior)" if pet.is_senior() else str(pet.age)
		status_parts = []
		
		if pet.is_senior():
			status_parts.append(f"{Colors.WARNING}Senior Care{Colors.RESET}")
		if pet.requires_medication():
			status_parts.append(f"{Colors.ERROR}Requires Meds{Colors.RESET}")
		
		status = " | ".join(status_parts) if status_parts else f"{Colors.SUCCESS}Healthy{Colors.RESET}"
		notes = pet.special_care_notes if pet.special_care_notes else "—"
		
		rows.append([
			f"{Emojis.PET} {pet.name}",
			pet.species.capitalize(),
			age_display,
			status,
			notes,
		])
	
	print(tabulate(rows, headers=headers, tablefmt="grid"))
