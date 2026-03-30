import json
from pathlib import Path

import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

from pawpal_system import Customer, Pet, Scheduler, Task

DATA_FILE = "data.json"

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { margin: 0; font-size: 2.5rem; }
    .main-header p  { margin: 0.25rem 0 0; opacity: 0.85; font-size: 1rem; }

    .metric-box {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.1rem 1rem 0.9rem;
        text-align: center;
    }
    .metric-box .icon  { font-size: 1.4rem; display: block; margin-bottom: 4px; }
    .metric-box .value { font-size: 1.9rem; font-weight: 700; color: #667eea; display: block; }
    .metric-box .label { font-size: 0.75rem; color: #718096; text-transform: uppercase;
                         letter-spacing: 0.5px; display: block; margin-top: 2px; }

    .conflict-box {
        background: #fff8f0;
        border: 1px solid #dd6b20;
        border-left: 4px solid #dd6b20;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.4rem;
        font-size: 0.9rem;
    }
    .ok-box {
        background: #f0fff4;
        border: 1px solid #38a169;
        border-left: 4px solid #38a169;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.4rem;
        font-size: 0.9rem;
        color: #276749;
    }

    div[data-testid="stSidebar"] { background: #f7f8fc; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── formatting helpers ────────────────────────────────────────────────────────

_TASK_KEYWORDS: list[tuple[list[str], str]] = [
    (["walk", "stroll", "run", "jog", "exercise"],          "🦮"),
    (["feed", "food", "meal", "breakfast", "dinner", "lunch", "treat"], "🍽️"),
    (["medication", "medicine", "pill", "drug", "dose", "injection"],   "💊"),
    (["bath", "groom", "wash", "brush", "nail", "clip"],    "🛁"),
    (["play", "fetch", "toy", "game"],                      "🎾"),
    (["vet", "checkup", "appointment", "doctor"],           "🏥"),
    (["litter", "scoop", "clean", "poop"],                  "🧹"),
    (["water", "drink", "refill", "hydrat"],                "💧"),
    (["train", "sit", "stay", "command"],                   "🎓"),
    (["sleep", "rest", "nap", "bed"],                       "😴"),
]

def _task_emoji(title: str) -> str:
    lower = title.lower()
    for keywords, emoji in _TASK_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return emoji
    return "📋"


def _species_emoji(species: str) -> str:
    return {"dog": "🐕", "cat": "🐈"}.get(species.lower(), "🐾")


def _priority_label(priority: str) -> str:
    return {"high": "🔴 High", "medium": "🟠 Medium", "low": "🟢 Low"}.get(
        priority.strip().lower(), priority.capitalize()
    )


def _status_label(completed: bool) -> str:
    return "✅ Done" if completed else "⏳ Pending"


# Row background colors keyed by raw priority
_PRIORITY_BG = {"high": "#fff5f5", "medium": "#fffaf0", "low": "#f0fff4"}
_DONE_BG = "#f7fafc"


def _style_rows(df: pd.DataFrame):  # returns pandas Styler
    """Apply priority-based row background colors; grey out completed rows."""
    def row_style(row: pd.Series) -> list[str]:
        raw_p = str(row.get("_priority_raw", "")).lower()
        is_done = bool(row.get("_done", False))
        bg = _DONE_BG if is_done else _PRIORITY_BG.get(raw_p, "#ffffff")
        text = "#718096" if is_done else "#1a202c"
        return [f"background-color: {bg}; color: {text}"] * len(row)

    return df.style.apply(row_style, axis=1)


def _schedule_dataframe(
    tasks: list[Task],
    owner_label: str,
    pet_label: str,
    total: int,
) -> pd.DataFrame:
    rows = []
    for rank, task in enumerate(tasks):
        rows.append(
            {
                "Owner":           owner_label,
                "Pet":             f"{_species_emoji(pet_label)} {pet_label}" if pet_label else pet_label,
                "Task":            f"{_task_emoji(task.title)} {task.title}",
                "Start":           task.time_constraint if task.time_constraint else "Flexible",
                "End":             _end_time(task),
                "Duration (min)":  task.duration_minutes,
                "Priority":        _priority_label(task.priority),
                "Status":          _status_label(task.completed),
                "Reasoning":       _reasoning(task, rank + 1, total),
                # Hidden helper columns used only for styling
                "_priority_raw":   task.priority.strip().lower(),
                "_done":           task.completed,
            }
        )
    return pd.DataFrame(rows)


def _render_schedule_table(df: pd.DataFrame) -> None:
    """Display df as a styled, color-coded dataframe, hiding internal columns."""
    internal_cols = pd.Index([c for c in df.columns if c.startswith("_")])
    styled = _style_rows(df).hide(subset=internal_cols, axis="columns")
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ── session state init ────────────────────────────────────────────────────────

def _save_vault() -> None:
    """Persist all customers in the vault to a single DATA_FILE JSON array."""
    customers = list(st.session_state.vault["customers_by_key"].values())
    all_data = [_customer_to_dict(c) for c in customers]
    Path(DATA_FILE).write_text(json.dumps(all_data, indent=2), encoding="utf-8")


def _customer_to_dict(customer: Customer) -> dict:
    """Return the same JSON shape that Customer.save_to_json writes."""

    def _date_str(d) -> str | None:
        return d.isoformat() if d is not None else None

    def _dt_str(dt) -> str | None:
        return dt.isoformat() if dt is not None else None

    pets_data = [
        {
            "pet_id": p.pet_id,
            "name": p.name,
            "species": p.species,
            "age": p.age,
            "medications": p.medications,
            "special_care_notes": p.special_care_notes,
        }
        for p in customer.pets
    ]

    schedules_data = [
        {
            "schedule_date": s.schedule_date.isoformat(),
            "available_windows": s.available_windows,
            "planned_for_pet_id": s.planned_for.pet_id,
            "pickup_time": _dt_str(s.pickup_time),
            "dropoff_time": _dt_str(s.dropoff_time),
            "tasks": [
                {
                    "task_id": t.task_id,
                    "title": t.title,
                    "duration_minutes": t.duration_minutes,
                    "priority": t.priority,
                    "time_constraint": t.time_constraint,
                    "cost": t.cost,
                    "completed": t.completed,
                    "recurrence": t.recurrence,
                    "scheduled_for": _date_str(t.scheduled_for),
                    "recurrence_generated": t.recurrence_generated,
                }
                for t in s.tasks
            ],
        }
        for s in customer.schedules
    ]

    return {
        "customer_id": customer.customer_id,
        "name": customer.name,
        "contact_info": customer.contact_info,
        "preferred_time_windows": customer.preferred_time_windows,
        "care_preferences": customer.care_preferences,
        "pets": pets_data,
        "schedules": schedules_data,
    }


def _customer_from_dict(data: dict) -> Customer:
    """Reconstruct a Customer (with pets and schedules) from a plain dict."""

    def _parse_date(value: str | None) -> date | None:
        return date.fromisoformat(value) if value else None

    def _parse_datetime(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value) if value else None

    pets = [
        Pet(
            pet_id=p["pet_id"],
            name=p["name"],
            species=p["species"],
            age=p["age"],
            medications=p.get("medications", ""),
            special_care_notes=p.get("special_care_notes", ""),
        )
        for p in data.get("pets", [])
    ]
    pets_by_id: dict[int, Pet] = {pet.pet_id: pet for pet in pets}

    customer = Customer(
        customer_id=data["customer_id"],
        name=data["name"],
        contact_info=data.get("contact_info", ""),
        preferred_time_windows=data.get("preferred_time_windows", ""),
        care_preferences=data.get("care_preferences", ""),
        pets=pets,
    )

    for schedule_data in data.get("schedules", []):
        planned_for = pets_by_id.get(schedule_data["planned_for_pet_id"])
        if planned_for is None:
            continue

        schedule = Scheduler(
            schedule_date=date.fromisoformat(schedule_data["schedule_date"]),
            available_windows=schedule_data.get("available_windows", ""),
            planned_for=planned_for,
            customer_id=customer.customer_id,
            pickup_time=_parse_datetime(schedule_data.get("pickup_time")),
            dropoff_time=_parse_datetime(schedule_data.get("dropoff_time")),
        )

        for task_data in schedule_data.get("tasks", []):
            task = Task(
                task_id=task_data["task_id"],
                title=task_data["title"],
                duration_minutes=task_data["duration_minutes"],
                priority=task_data["priority"],
                time_constraint=task_data.get("time_constraint", ""),
                cost=task_data.get("cost", 0.0),
                completed=task_data.get("completed", False),
                recurrence=task_data.get("recurrence", ""),
                scheduled_for=_parse_date(task_data.get("scheduled_for")),
                recurrence_generated=task_data.get("recurrence_generated", False),
            )
            schedule.tasks.append(task)

        schedule.refresh_totals()
        customer.schedules.append(schedule)

    return customer


def _init_session_vault() -> None:
    if "vault" not in st.session_state:
        vault: dict = {
            "customers_by_key": {},
            "pets_by_key": {},
            "schedules_by_key": {},
            "next_customer_id": 1,
            "next_pet_id": 1,
            "next_task_id": 1,
        }

        data_path = Path(DATA_FILE)
        if data_path.exists():
            try:
                raw = data_path.read_text(encoding="utf-8").strip()
                if raw:
                    all_customers_data = json.loads(raw)
                    max_customer_id = 0
                    max_pet_id = 0
                    max_task_id = 0

                    for cdata in all_customers_data:
                        customer = _customer_from_dict(cdata)

                        key = customer.name.strip().lower()
                        vault["customers_by_key"][key] = customer

                        max_customer_id = max(max_customer_id, customer.customer_id)

                        for pet in customer.pets:
                            pet_key = f"{customer.customer_id}:{pet.name.strip().lower()}"
                            vault["pets_by_key"][pet_key] = pet
                            max_pet_id = max(max_pet_id, pet.pet_id)

                        for schedule in customer.schedules:
                            sched_key = (
                                f"{customer.customer_id}:"
                                f"{schedule.planned_for.pet_id}:"
                                f"{schedule.schedule_date.isoformat()}"
                            )
                            vault["schedules_by_key"][sched_key] = schedule
                            for task in schedule.tasks:
                                max_task_id = max(max_task_id, task.task_id)

                    vault["next_customer_id"] = max_customer_id + 1
                    vault["next_pet_id"] = max_pet_id + 1
                    vault["next_task_id"] = max_task_id + 1

            except (json.JSONDecodeError, KeyError, ValueError):
                # Corrupted or unreadable file — start with a fresh vault.
                pass

        st.session_state.vault = vault

    if "task_queues" not in st.session_state:
        st.session_state.task_queues = {}


_init_session_vault()


# ── domain helpers ────────────────────────────────────────────────────────────

def _owner_key(name: str) -> str:
    return name.strip().lower()


def _queue_key(owner_name: str, pet_name: str) -> str:
    return f"{owner_name.strip().lower()}:{pet_name.strip().lower()}"


def _current_tasks(owner_name: str, pet_name: str) -> list[dict]:
    key = _queue_key(owner_name, pet_name)
    if key not in st.session_state.task_queues:
        st.session_state.task_queues[key] = []
    return st.session_state.task_queues[key]


def get_or_create_owner(owner_name: str) -> tuple[Customer, bool]:
    key = _owner_key(owner_name)
    existing = st.session_state.vault["customers_by_key"].get(key)
    if existing is not None:
        return existing, False
    cid = st.session_state.vault["next_customer_id"]
    owner = Customer(customer_id=cid, name=owner_name.strip() or "Owner", contact_info="")
    st.session_state.vault["customers_by_key"][key] = owner
    st.session_state.vault["next_customer_id"] += 1
    return owner, True


def get_or_create_pet(owner: Customer, pet_name: str, species: str) -> tuple[Pet, bool]:
    key = f"{owner.customer_id}:{pet_name.strip().lower()}"
    existing = st.session_state.vault["pets_by_key"].get(key)
    if existing is not None:
        return existing, False
    pid = st.session_state.vault["next_pet_id"]
    pet = Pet(pet_id=pid, name=pet_name.strip() or "Pet", species=species, age=1)
    owner.add_pet(pet)
    st.session_state.vault["pets_by_key"][key] = pet
    st.session_state.vault["next_pet_id"] += 1
    return pet, True


def get_or_create_schedule(owner: Customer, pet: Pet) -> tuple[Scheduler, bool]:
    today = date.today()
    key = f"{owner.customer_id}:{pet.pet_id}:{today.isoformat()}"
    existing = st.session_state.vault["schedules_by_key"].get(key)
    if existing is not None:
        return existing, False
    schedule = owner.create_schedule(
        schedule_date=today, available_windows="Flexible", planned_for=pet
    )
    st.session_state.vault["schedules_by_key"][key] = schedule
    return schedule, True


def _task_signature(task: Task) -> tuple[str, int, str, str]:
    return (
        task.title.strip().lower(),
        int(task.duration_minutes),
        task.priority.strip().lower(),
        task.time_constraint.strip(),
    )


def sync_ui_tasks_to_schedule(schedule: Scheduler, ui_tasks: list[dict]) -> int:
    existing = {_task_signature(t) for t in schedule.tasks}
    added = 0
    for ui_task in ui_tasks:
        sig = (
            ui_task["title"].strip().lower(),
            int(ui_task["duration_minutes"]),
            ui_task["priority"].strip().lower(),
            ui_task.get("time_constraint", "").strip(),
        )
        if sig in existing:
            continue
        task = Task(
            task_id=st.session_state.vault["next_task_id"],
            title=ui_task["title"],
            duration_minutes=int(ui_task["duration_minutes"]),
            priority=ui_task["priority"],
            time_constraint=ui_task.get("time_constraint", ""),
        )
        if schedule.add_task(task):
            st.session_state.vault["next_task_id"] += 1
            existing.add(sig)
            added += 1
    return added


def _all_schedules() -> list[Scheduler]:
    return list(st.session_state.vault["schedules_by_key"].values())


def _owner_name_for(customer_id: int) -> str:
    for customer in st.session_state.vault["customers_by_key"].values():
        if customer.customer_id == customer_id:
            return customer.name
    return "Unknown"


def _validate_time(value: str) -> bool:
    try:
        datetime.strptime(value.strip(), "%H:%M")
        return True
    except ValueError:
        return False


def _end_time(task: Task) -> str:
    tc = task.time_constraint.strip()
    if not tc:
        return "—"
    try:
        start = datetime.strptime(tc, "%H:%M")
        return (start + timedelta(minutes=task.duration_minutes)).strftime("%H:%M")
    except ValueError:
        return "—"


def _reasoning(task: Task, rank: int, total: int) -> str:
    parts = []
    if task.time_constraint.strip():
        parts.append(f"📌 Pinned to {task.time_constraint}")
    p = task.priority.lower()
    if p == "high":
        parts.append(f"🔴 High priority — #{rank} of {total}, scheduled first")
    elif p == "medium":
        parts.append(f"🟠 Medium priority — #{rank} of {total}, after urgent tasks")
    else:
        parts.append(f"🟢 Low priority — #{rank} of {total}, scheduled last")
    if task.completed:
        parts.append("✅ already completed")
    return "; ".join(parts)


def _detect_overlap_conflicts(schedules: list[Scheduler]) -> list[str]:
    timed: list[tuple[str, str, datetime, datetime]] = []
    today = date.today()
    for sched in schedules:
        for task in sched.tasks:
            tc = task.time_constraint.strip()
            if not tc:
                continue
            try:
                start_dt = datetime.strptime(f"{today.isoformat()} {tc}", "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            end_dt = start_dt + timedelta(minutes=task.duration_minutes)
            timed.append((sched.planned_for.name, task.title, start_dt, end_dt))

    warnings: list[str] = []
    for i in range(len(timed)):
        for j in range(i + 1, len(timed)):
            pet_a, title_a, start_a, end_a = timed[i]
            pet_b, title_b, start_b, end_b = timed[j]
            if start_a < end_b and start_b < end_a:
                warnings.append(
                    f'"{title_a}" ({pet_a}, {start_a.strftime("%H:%M")}–{end_a.strftime("%H:%M")}) '
                    f'overlaps "{title_b}" ({pet_b}, {start_b.strftime("%H:%M")}–{end_b.strftime("%H:%M")})'
                )
    return warnings


# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 👤 Owner & Pet")
    owner_name = st.text_input("Owner name", value="Jordan")
    pet_name   = st.text_input("Pet name",   value="Mochi")
    species    = st.selectbox(
        "Species",
        ["dog", "cat", "other"],
        format_func=lambda s: f"{_species_emoji(s)} {s.capitalize()}",
    )

    st.divider()
    st.caption(f"📅 Today: {date.today().strftime('%B %d, %Y')}")

    current_tasks = _current_tasks(owner_name, pet_name)
    if current_tasks:
        total_min = sum(t["duration_minutes"] for t in current_tasks)
        hours, mins = divmod(total_min, 60)
        duration_label = f"{hours}h {mins}m" if hours else f"{mins}m"
        timed_count = sum(1 for t in current_tasks if t.get("time_constraint"))
        st.markdown(
            f"""
            <div class="metric-box">
                <span class="icon">📋</span>
                <span class="value">{len(current_tasks)}</span>
                <span class="label">Tasks queued</span>
            </div><br>
            <div class="metric-box">
                <span class="icon">⏱️</span>
                <span class="value">{duration_label}</span>
                <span class="label">Total time</span>
            </div><br>
            <div class="metric-box">
                <span class="icon">📌</span>
                <span class="value">{timed_count}</span>
                <span class="label">With time slot</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    all_scheds_sidebar = _all_schedules()
    if all_scheds_sidebar:
        st.divider()
        st.markdown("**🗓️ All Scheduled Pets**")
        for sched in all_scheds_sidebar:
            owner_label = _owner_name_for(sched.customer_id)
            sp_emoji = _species_emoji(sched.planned_for.species)
            done = sum(1 for t in sched.tasks if t.completed)
            st.caption(
                f"{sp_emoji} **{sched.planned_for.name}** ({owner_label}) "
                f"— {len(sched.tasks)} tasks, {done} done"
            )


# ── main header ───────────────────────────────────────────────────────────────

current_tasks = _current_tasks(owner_name, pet_name)
sp_emoji = _species_emoji(species)

st.markdown(
    f"""
    <div class="main-header">
        <h1>🐾 PawPal+</h1>
        <p>Smart daily care scheduling — {sp_emoji} <strong>{pet_name}</strong>
           owned by <strong>{owner_name}</strong></p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── task builder ──────────────────────────────────────────────────────────────

st.subheader("➕ Add a Care Task")
st.caption("Pin a time slot (HH:MM) to enable conflict detection across owners.")

col1, col2, col3, col4, col5 = st.columns([3, 1.2, 1.5, 1.5, 1])
with col1:
    task_title = st.text_input(
        "Task title", value="Morning walk",
        label_visibility="collapsed", placeholder="Task title",
    )
with col2:
    pin_time = st.checkbox("📌 Pin time", value=False)
with col3:
    time_input = st.text_input(
        "Time (HH:MM)", value="09:00",
        label_visibility="collapsed", placeholder="HH:MM",
        disabled=not pin_time,
    )
with col4:
    duration = st.number_input(
        "Duration (min)", min_value=1, max_value=240, value=20,
        label_visibility="collapsed",
    )
with col5:
    priority = st.selectbox(
        "Priority", ["high", "medium", "low"],
        label_visibility="collapsed",
        format_func=_priority_label,
    )

col_btn, _ = st.columns([1, 6])
with col_btn:
    add_clicked = st.button("＋ Add Task", use_container_width=True)

if add_clicked:
    if not task_title.strip():
        st.warning("⚠️ Please enter a task title before adding.")
    elif pin_time and not _validate_time(time_input):
        st.warning(f'⚠️ "{time_input}" is not valid. Use HH:MM format (e.g. 09:00).')
    else:
        time_constraint = time_input.strip() if pin_time else ""
        current_tasks.append(
            {
                "title": task_title.strip(),
                "duration_minutes": int(duration),
                "priority": priority,
                "time_constraint": time_constraint,
            }
        )
        st.toast(
            f'{_task_emoji(task_title)} Added "{task_title}" for {owner_name} / {pet_name}',
            icon="✅",
        )


# ── queued tasks — editable table ─────────────────────────────────────────────

st.markdown(f"**📋 Queued Tasks for {owner_name} / {sp_emoji} {pet_name}**")
st.caption("Click any cell to edit. Use the row checkbox to delete a task.")

if current_tasks:
    df_queue = pd.DataFrame(current_tasks)

    # Add a display-only emoji column for visual scanning
    df_queue.insert(0, "Type", df_queue["title"].apply(_task_emoji))

    edited_df = st.data_editor(
        df_queue,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        disabled=["Type"],
        column_config={
            "Type": st.column_config.TextColumn("", width="small"),
            "title": st.column_config.TextColumn("Task Title", width="large"),
            "duration_minutes": st.column_config.NumberColumn(
                "Duration (min)", min_value=1, max_value=240, step=1
            ),
            "priority": st.column_config.SelectboxColumn(
                "Priority", options=["high", "medium", "low"]
            ),
            "time_constraint": st.column_config.TextColumn(
                "Time Slot (HH:MM)", help="Leave blank for flexible scheduling"
            ),
        },
    )

    # Sync edits back to session state (drop the display-only Type column)
    updated = edited_df.drop(columns=["Type"], errors="ignore").to_dict("records")
    for row in updated:
        if pd.isna(row.get("time_constraint")) or row.get("time_constraint") is None:
            row["time_constraint"] = ""
        row["duration_minutes"] = int(row["duration_minutes"]) if row.get("duration_minutes") else 1
    st.session_state.task_queues[_queue_key(owner_name, pet_name)] = updated
    current_tasks = updated
else:
    st.info(f"No tasks queued for {owner_name} / {sp_emoji} {pet_name} — add one above.")

st.divider()


# ── schedule generation ───────────────────────────────────────────────────────

st.subheader("📅 Generate Schedule")

col_gen, col_filter = st.columns([2, 3])
with col_gen:
    generate_clicked = st.button(
        "▶ Generate Schedule", type="primary",
        disabled=not bool(current_tasks),
    )
with col_filter:
    priority_filter = st.multiselect(
        "Filter by priority",
        options=["high", "medium", "low"],
        default=["high", "medium", "low"],
        label_visibility="collapsed",
        placeholder="🎯 Filter by priority…",
        format_func=_priority_label,
    )

if generate_clicked:
    owner,    _ = get_or_create_owner(owner_name)
    pet,      _ = get_or_create_pet(owner, pet_name, species)
    schedule, _ = get_or_create_schedule(owner, pet)

    added = sync_ui_tasks_to_schedule(schedule, current_tasks)
    schedule.sort_tasks_by_priority()
    _save_vault()

    st.success(
        f"✅ Schedule ready for **{sp_emoji} {pet.name}** ({species}) on "
        f"{schedule.schedule_date.strftime('%B %d, %Y')} — "
        f"**{len(schedule.tasks)}** task(s) total, **{added}** newly added."
    )

    # ── conflict detection ────────────────────────────────────────────────────
    all_scheds = _all_schedules()
    overlaps = _detect_overlap_conflicts(all_scheds)

    if overlaps:
        for msg in overlaps:
            st.markdown(
                f'<div class="conflict-box">⚠️ <strong>Scheduling conflict</strong> — {msg}</div>',
                unsafe_allow_html=True,
            )
    else:
        timed_tasks = [t for t in schedule.tasks if t.time_constraint.strip()]
        if timed_tasks:
            st.markdown(
                '<div class="ok-box">✅ <strong>No time conflicts</strong> detected across all scheduled owners.</div>',
                unsafe_allow_html=True,
            )

    # ── metrics ───────────────────────────────────────────────────────────────
    total_min  = sum(t.duration_minutes for t in schedule.tasks)
    high_count = sum(1 for t in schedule.tasks if t.priority.lower() == "high")
    done_count = sum(1 for t in schedule.tasks if t.completed)
    h, m = divmod(total_min, 60)

    for col, icon, value, label in zip(
        st.columns(4),
        ["📋", "⏱️", "🔴", "✅"],
        [len(schedule.tasks), f"{h}h {m}m" if h else f"{m}m", high_count, done_count],
        ["Total Tasks", "Total Time", "High Priority", "Completed"],
    ):
        col.markdown(
            f'<div class="metric-box">'
            f'<span class="icon">{icon}</span>'
            f'<span class="value">{value}</span>'
            f'<span class="label">{label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── sorted + filtered table with reasoning ────────────────────────────────
    active_priorities = priority_filter or ["high", "medium", "low"]
    filtered = [t for t in schedule.tasks if t.priority.lower() in active_priorities]
    total = len(schedule.tasks)

    filter_note = f" — filtered: {', '.join(_priority_label(p) for p in priority_filter)}" \
        if len(priority_filter) < 3 else ""
    st.markdown(f"**{sp_emoji} {owner_name} / {pet_name} — Sorted by Priority{filter_note}**")

    if filtered:
        df = _schedule_dataframe(filtered, owner_name, species, total)
        _render_schedule_table(df)
    else:
        st.warning("⚠️ No tasks match the selected priority filter.")

st.divider()

# ── all schedules across all owners/pets ─────────────────────────────────────

all_scheds = _all_schedules()
if all_scheds:
    st.subheader("🗓️ All Scheduled Owners & Pets")
    active_priorities = priority_filter if "priority_filter" in dir() else ["high", "medium", "low"]

    all_rows_data: list[tuple[Task, str, str, str, int]] = []
    for sched in all_scheds:
        owner_label = _owner_name_for(sched.customer_id)
        pet_sp = sched.planned_for.species
        for rank, task in enumerate(sched.tasks):
            if task.priority.lower() not in (active_priorities or ["high", "medium", "low"]):
                continue
            all_rows_data.append((task, owner_label, sched.planned_for.name, pet_sp, len(sched.tasks)))

    if all_rows_data:
        rows = []
        for task, owner_label, pname, pspecies, total_count in all_rows_data:
            rank = next(
                i for i, (t, *_) in enumerate(all_rows_data)
                if t is task and owner_label == _
            ) if False else 0  # rank not critical for all-view
            rows.append(
                {
                    "Owner":           owner_label,
                    "Pet":             f"{_species_emoji(pspecies)} {pname}",
                    "Task":            f"{_task_emoji(task.title)} {task.title}",
                    "Start":           task.time_constraint if task.time_constraint else "Flexible",
                    "End":             _end_time(task),
                    "Duration (min)":  task.duration_minutes,
                    "Priority":        _priority_label(task.priority),
                    "Status":          _status_label(task.completed),
                    "_priority_raw":   task.priority.strip().lower(),
                    "_done":           task.completed,
                }
            )
        df_all = pd.DataFrame(rows)
        _render_schedule_table(df_all)
    else:
        st.info("No scheduled tasks yet across any owner.")
