import streamlit as st
from datetime import date

from pawpal_system import Customer, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")


def _init_session_vault() -> None:
    if "vault" not in st.session_state:
        st.session_state.vault = {
            "customers_by_key": {},
            "pets_by_key": {},
            "schedules_by_key": {},
            "next_customer_id": 1,
            "next_pet_id": 1,
            "next_task_id": 1,
        }


def _owner_key(name: str) -> str:
    return name.strip().lower()


def get_or_create_owner(owner_name: str) -> tuple[Customer, bool]:
    _init_session_vault()
    key = _owner_key(owner_name)

    existing_owner = st.session_state.vault["customers_by_key"].get(key)
    if existing_owner is not None:
        return existing_owner, False

    customer_id = st.session_state.vault["next_customer_id"]
    owner = Customer(
        customer_id=customer_id,
        name=owner_name.strip() or "Owner",
        contact_info="",
    )
    st.session_state.vault["customers_by_key"][key] = owner
    st.session_state.vault["next_customer_id"] += 1
    return owner, True


def get_or_create_pet(owner: Customer, pet_name: str, species: str) -> tuple[Pet, bool]:
    _init_session_vault()
    key = f"{owner.customer_id}:{pet_name.strip().lower()}"

    existing_pet = st.session_state.vault["pets_by_key"].get(key)
    if existing_pet is not None:
        return existing_pet, False

    pet_id = st.session_state.vault["next_pet_id"]
    pet = Pet(
        pet_id=pet_id,
        name=pet_name.strip() or "Pet",
        species=species,
        age=1,
    )
    owner.add_pet(pet)
    st.session_state.vault["pets_by_key"][key] = pet
    st.session_state.vault["next_pet_id"] += 1
    return pet, True


def get_or_create_schedule(owner: Customer, pet: Pet) -> tuple[Scheduler, bool]:
    _init_session_vault()
    schedule_day = date.today()
    key = f"{owner.customer_id}:{pet.pet_id}:{schedule_day.isoformat()}"

    existing_schedule = st.session_state.vault["schedules_by_key"].get(key)
    if existing_schedule is not None:
        return existing_schedule, False

    schedule = owner.create_schedule(
        schedule_date=schedule_day,
        available_windows="Flexible",
        planned_for=pet,
    )
    st.session_state.vault["schedules_by_key"][key] = schedule
    return schedule, True


def _task_signature(task: Task) -> tuple[str, int, str]:
    return (task.title.strip().lower(), int(task.duration_minutes), task.priority.strip().lower())


def sync_ui_tasks_to_schedule(schedule: Scheduler, ui_tasks: list[dict]) -> int:
    _init_session_vault()
    existing = {_task_signature(task) for task in schedule.tasks}
    added = 0

    for ui_task in ui_tasks:
        signature = (
            ui_task["title"].strip().lower(),
            int(ui_task["duration_minutes"]),
            ui_task["priority"].strip().lower(),
        )
        if signature in existing:
            continue

        task = Task(
            task_id=st.session_state.vault["next_task_id"],
            title=ui_task["title"],
            duration_minutes=int(ui_task["duration_minutes"]),
            priority=ui_task["priority"],
        )
        if schedule.add_task(task):
            st.session_state.vault["next_task_id"] += 1
            existing.add(signature)
            added += 1

    return added

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

st.markdown("### Tasks")
st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

if st.button("Add task"):
    st.session_state.tasks.append(
        {"title": task_title, "duration_minutes": int(duration), "priority": priority}
    )

if st.session_state.tasks:
    st.write("Current tasks:")
    st.table(st.session_state.tasks)
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("This button should call your scheduling logic once you implement it.")

if st.button("Generate schedule"):
    owner, created = get_or_create_owner(owner_name)
    if created:
        st.success(f"Created owner in session vault: {owner.name} (id={owner.customer_id})")
    else:
        st.info(f"Using existing owner from session vault: {owner.name} (id={owner.customer_id})")

    pet, pet_created = get_or_create_pet(owner, pet_name, species)
    if pet_created:
        st.success(f"Created pet in session vault: {pet.name} (id={pet.pet_id})")
    else:
        st.info(f"Using existing pet from session vault: {pet.name} (id={pet.pet_id})")

    schedule, schedule_created = get_or_create_schedule(owner, pet)
    if schedule_created:
        st.success(
            f"Created schedule in session vault for {pet.name} on {schedule.schedule_date.isoformat()}"
        )
    else:
        st.info(
            f"Using existing schedule from session vault for {pet.name} on {schedule.schedule_date.isoformat()}"
        )

    added_count = sync_ui_tasks_to_schedule(schedule, st.session_state.tasks)
    st.write(f"Schedule now has {len(schedule.tasks)} task(s). Added {added_count} new task(s).")

    schedule.sort_tasks_by_priority()
    st.markdown("### Scheduled Tasks")
    st.table(
        [
            {
                "title": task.title,
                "duration_minutes": task.duration_minutes,
                "priority": task.priority,
                "completed": task.completed,
            }
            for task in schedule.tasks
        ]
    )

    st.markdown(
        """
Suggested approach:
1. Design your UML (draft).
2. Create class stubs (no logic).
3. Implement scheduling behavior.
4. Connect your scheduler here and display results.
"""
    )
