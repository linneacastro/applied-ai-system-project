import re
import streamlit as st
from pawpal_system import Priority, Task, Pet, Owner, Scheduler
from pawpal_rag_service import RagService


@st.cache_resource
def get_rag_service() -> RagService:
    return RagService()


_CONFLICT_RE = re.compile(
    r"Conflict: '(.+?)' \((.+?), (.+?)–(.+?)\) overlaps with '(.+?)' \((.+?), (.+?)–(.+?)\)"
)


def _render_conflicts(warnings: list, available_minutes: int) -> None:
    """Display conflict warnings prominently with structured, actionable detail."""
    st.error(
        f"⚠️ {len(warnings)} scheduling conflict(s) detected — "
        "review before starting your session."
    )
    for w in warnings:
        m = _CONFLICT_RE.match(w)
        if m:
            t1, p1, s1, e1, t2, p2, s2, e2 = m.groups()
            with st.container(border=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**{t1}**")
                    st.caption(f"{p1}  ·  {s1} – {e1}")
                with col2:
                    st.markdown(f"**{t2}**")
                    st.caption(f"{p2}  ·  {s2} – {e2}")
                st.caption("These two tasks overlap in time.")
        else:
            st.error(w)
    st.info(
        "💡 **To resolve conflicts:** shorten a task's duration, increase your "
        f"daily time budget (currently {available_minutes} min), or adjust your "
        "session start time so tasks no longer overlap."
    )


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

# --- Session state ---
if "owner" not in st.session_state:
    st.session_state.owner = None
if "plan" not in st.session_state:
    st.session_state.plan = None

st.divider()

# --- Owner Setup ---
st.subheader("Owner Setup")

if st.session_state.owner is not None:
    owner = st.session_state.owner
    st.success(
        f"Owner: **{owner.name}** — {owner.available_minutes} min/day · starts at {owner.session_start}"
    )
    st.caption(f"Preferences: {', '.join(owner.preferences) if owner.preferences else 'none'}")
    if st.button("Reset owner"):
        st.session_state.owner = None
        st.session_state.plan = None
        st.rerun()
else:
    with st.form("owner_form"):
        owner_name = st.text_input("Owner name", value="Jordan")
        available_minutes = st.number_input("Available minutes per day", min_value=1, value=120)
        preferences_input = st.text_input("Care preferences (comma-separated)", value="walk, grooming")
        session_start = st.text_input("Session start time (HH:MM)", value="08:00")
        owner_submitted = st.form_submit_button("Save Owner")

    if owner_submitted:
        preferences = [p.strip() for p in preferences_input.split(",") if p.strip()]
        try:
            st.session_state.owner = Owner(
                name=owner_name,
                available_minutes=available_minutes,
                preferences=preferences,
                session_start=session_start,
            )
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    st.info("Set up an owner above to get started.")
    st.stop()

owner = st.session_state.owner

st.divider()

# --- Add a Pet ---
st.subheader("Add a Pet")
with st.form("add_pet_form"):
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["dog", "cat", "other"])
    age = st.number_input("Age (years)", min_value=0, value=2)
    pet_submitted = st.form_submit_button("Add pet")

if pet_submitted:
    try:
        new_pet = Pet(name=pet_name, species=species, age=age)
        owner.add_pet(new_pet)
        st.session_state.plan = None  # invalidate stale plan
        st.success(f"Added pet '{pet_name}'!")
    except ValueError as e:
        st.error(str(e))

if owner.pets:
    st.caption("Registered: " + ", ".join(p.name for p in owner.pets))
else:
    st.info("No pets yet. Add one above.")

st.divider()

# --- Add a Task ---
st.subheader("Add a Task")
if not owner.pets:
    st.info("Add a pet first before scheduling tasks.")
else:
    with st.form("add_task_form"):
        selected_pet_name = st.selectbox("Assign to pet", [p.name for p in owner.pets])
        task_title = st.text_input("Task title", value="Morning walk")
        category = st.text_input("Category", value="walk")
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority = st.selectbox("Priority", ["LOW", "MEDIUM", "HIGH"], index=2)
        task_submitted = st.form_submit_button("Add task")

    if task_submitted:
        try:
            new_task = Task(
                title=task_title,
                category=category,
                duration=duration,
                priority=Priority[priority],
            )
            target_pet = next(p for p in owner.pets if p.name == selected_pet_name)
            target_pet.add_task(new_task)
            st.session_state.plan = None  # invalidate stale plan
            st.success(f"Task '{task_title}' added to {selected_pet_name}!")
        except ValueError as e:
            st.error(str(e))

st.divider()

# --- View & Filter Tasks ---
st.subheader("View & Filter Tasks")
if not owner.pets:
    st.info("No pets registered yet.")
else:
    col1, col2 = st.columns(2)
    with col1:
        pet_filter_options = ["All pets"] + [p.name for p in owner.pets]
        pet_filter = st.selectbox("Filter by pet", pet_filter_options)
    with col2:
        status_filter = st.radio("Filter by status", ["All", "Incomplete", "Completed"], horizontal=True)

    pet_name_arg = None if pet_filter == "All pets" else pet_filter
    completed_arg = None if status_filter == "All" else (status_filter == "Completed")

    task_to_pet = {task.id: pet.name for pet in owner.pets for task in pet.tasks}

    try:
        filtered_tasks = owner.get_tasks(completed=completed_arg, pet_name=pet_name_arg)
    except ValueError as e:
        st.error(str(e))
        filtered_tasks = []

    if filtered_tasks:
        filtered_tasks.sort(key=lambda t: (-t.priority, -t.duration))
        st.table([
            {
                "Pet": task_to_pet.get(t.id, "—"),
                "Task": t.title,
                "Category": t.category,
                "Duration (min)": t.duration,
                "Priority": t.priority.name,
                "Status": "✅ Done" if t.completed else "⏳ Pending",
            }
            for t in filtered_tasks
        ])
        st.caption(f"{len(filtered_tasks)} task(s) shown.")
    else:
        st.info("No tasks match the selected filters.")

    # --- Remove a Task ---
    all_tasks = owner.get_tasks()
    if all_tasks:
        st.markdown("#### Remove a Task")
        task_options = {
            f"{task_to_pet.get(t.id, '?')} — {t.title}": t for t in all_tasks
        }
        with st.form("remove_task_form"):
            selected_label = st.selectbox("Select task to remove", list(task_options.keys()))
            remove_submitted = st.form_submit_button("Remove task")

        if remove_submitted:
            task_to_remove = task_options[selected_label]
            pet_name = task_to_pet.get(task_to_remove.id)
            target_pet = next((p for p in owner.pets if p.name == pet_name), None)
            if target_pet:
                try:
                    target_pet.remove_task(task_to_remove)
                    st.session_state.plan = None
                    st.success(f"Removed '{task_to_remove.title}' from {pet_name}.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

st.divider()

# --- Build Schedule ---
st.subheader("Build Schedule")
if st.button("Generate schedule"):
    try:
        scheduler = Scheduler(owner)
        st.session_state.plan = scheduler.build_plan()
    except ValueError as e:
        st.error(str(e))

plan = st.session_state.plan
if plan is not None:
    st.success(
        f"Scheduled {len(plan['scheduled'])} tasks — "
        f"{plan['total_scheduled_minutes']} min used, "
        f"{plan['remaining_minutes']} min remaining."
    )

    if plan["warnings"]:
        _render_conflicts(plan["warnings"], owner.available_minutes)

    if plan["scheduled"]:
        st.markdown("#### Scheduled Tasks")
        st.table([
            {
                "Start": e["start_time"],
                "Pet": e["pet"],
                "Task": e["task"],
                "Category": e["category"],
                "Duration (min)": e["duration"],
                "Priority": e["priority"],
                "Preferred": "⭐" if e["preferred"] else "",
            }
            for e in plan["scheduled"]
        ])

    if plan["deferred"]:
        st.markdown("#### Deferred (fits in a longer session)")
        st.table([
            {"Task": e["task"], "Pet": e["pet"], "Duration (min)": e["duration"], "Priority": e["priority"]}
            for e in plan["deferred"]
        ])

    if plan["too_long"]:
        st.markdown("#### Too Long to Schedule")
        st.table([
            {"Task": e["task"], "Pet": e["pet"], "Duration (min)": e["duration"], "Priority": e["priority"]}
            for e in plan["too_long"]
        ])
        st.warning(f"These tasks each exceed your {owner.available_minutes}-min daily budget.")

    st.divider()

    st.subheader("🐾 Why this plan?")
    st.caption(
        "Ask PawPal+ for pet-care guidance grounded in our knowledge base. "
        "Answers cite the source files used."
    )

    pets_summary = " and ".join(
        f"{p.age}-year-old {p.species}" for p in owner.pets
    )
    default_query = (
        f"What feeding, walking, and grooming routines should I follow for {pets_summary}?"
    )

    with st.form("rag_explain_form"):
        query = st.text_input("Question", value=default_query)
        explain_submitted = st.form_submit_button("Get answer")

    if explain_submitted and query.strip():
        service = get_rag_service()
        try:
            with st.spinner("Searching knowledge base..."):
                result = service.explain(query)
        except Exception as e:
            st.error(f"Could not generate explanation: {e}")
        else:
            st.markdown(result["answer"])
            if result["sources"]:
                st.caption("**Sources:** " + ", ".join(result["sources"]))
            st.caption(
                f"Tokens used: {result['usage']['input_tokens']} in / "
                f"{result['usage']['output_tokens']} out"
            )
