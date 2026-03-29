import streamlit as st
from pawpal_system import Priority, Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

# --- Session state: initialize Owner once ---
if "owner" not in st.session_state:
    st.session_state.owner = None

st.divider()

# --- Owner Setup ---
st.subheader("Owner Setup")
with st.form("owner_form"):
    owner_name = st.text_input("Owner name", value="Jordan")
    available_minutes = st.number_input("Available minutes per day", min_value=1, value=120)
    preferences_input = st.text_input("Care preferences (comma-separated)", value="walk, grooming")
    session_start = st.text_input("Session start time (HH:MM)", value="08:00")
    owner_submitted = st.form_submit_button("Save Owner")

if owner_submitted:
    if st.session_state.owner is not None:
        st.warning("Owner already set. Remove all pets first to reset.")
    else:
        preferences = [p.strip() for p in preferences_input.split(",") if p.strip()]
        try:
            st.session_state.owner = Owner(
                name=owner_name,
                available_minutes=int(available_minutes),
                preferences=preferences,
                session_start=session_start,
            )
            st.success(f"Owner '{owner_name}' saved!")
        except ValueError as e:
            st.error(str(e))

if st.session_state.owner is None:
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
        new_pet = Pet(name=pet_name, species=species, age=int(age))
        owner.add_pet(new_pet)
        st.success(f"Added pet '{pet_name}'!")
    except ValueError as e:
        st.error(str(e))

if owner.pets:
    st.write("Registered pets:", [p.name for p in owner.pets])
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
                duration=int(duration),
                priority=Priority[priority],
            )
            target_pet = next(p for p in owner.pets if p.name == selected_pet_name)
            target_pet.add_task(new_task)
            st.success(f"Task '{task_title}' added to {selected_pet_name}!")
        except ValueError as e:
            st.error(str(e))

    for pet in owner.pets:
        tasks = pet.get_tasks()
        if tasks:
            st.write(f"**{pet.name}'s tasks:**")
            st.table([
                {
                    "title": t.title,
                    "category": t.category,
                    "duration (min)": t.duration,
                    "priority": t.priority.name,
                    "completed": t.completed,
                }
                for t in tasks
            ])

st.divider()

# --- Build Schedule ---
st.subheader("Build Schedule")
if st.button("Generate schedule"):
    scheduler = Scheduler(owner)
    plan = scheduler.build_plan()

    st.success(
        f"Scheduled {len(plan['scheduled'])} tasks "
        f"({plan['total_scheduled_minutes']} min used, "
        f"{plan['remaining_minutes']} min remaining)"
    )

    if plan["scheduled"]:
        st.markdown("#### Scheduled")
        st.table(plan["scheduled"])

    if plan["deferred"]:
        st.markdown("#### Deferred (fit another day)")
        st.table(plan["deferred"])

    if plan["too_long"]:
        st.markdown("#### Too long to schedule")
        st.table(plan["too_long"])
