from pawpal_system import Owner, Pet, Task, Priority, Scheduler


def print_schedule(plan: dict) -> None:
    width = 60
    print("\n" + "=" * width)
    print(f"  TODAY'S SCHEDULE FOR {plan['owner'].upper()}")
    print("=" * width)

    if plan["scheduled"]:
        print(f"\n  SCHEDULED  ({plan['total_scheduled_minutes']} min / {plan['remaining_minutes']} min remaining)\n")
        for entry in plan["scheduled"]:
            preferred_tag = " *" if entry["preferred"] else ""
            print(f"  [{entry['priority']:<6}]  {entry['start_time']}  {entry['task']:<28}  {entry['duration']:>3} min  ({entry['pet']}){preferred_tag}")
    else:
        print("\n  No tasks could be scheduled.")

    if plan["deferred"]:
        print(f"\n  DEFERRED  (fit in a longer session)\n")
        for entry in plan["deferred"]:
            print(f"  [{entry['priority']:<6}]  {entry['task']:<28}  {entry['duration']:>3} min  ({entry['pet']})")

    if plan["too_long"]:
        print(f"\n  TOO LONG  (exceeds total available time)\n")
        for entry in plan["too_long"]:
            print(f"  [{entry['priority']:<6}]  {entry['task']:<28}  {entry['duration']:>3} min  ({entry['pet']})")

    print("\n" + "=" * width + "\n")
    if plan["scheduled"] and any(e["preferred"] for e in plan["scheduled"]):
        print("  * preferred category\n")


def print_task_list(label: str, tasks: list) -> None:
    width = 60
    print("\n" + "-" * width)
    print(f"  {label}")
    print("-" * width)
    if tasks:
        for t in tasks:
            status = "done" if t.completed else "pending"
            print(f"  [{t.priority.name:<6}]  {t.title:<28}  {t.duration:>3} min  [{status}]")
    else:
        print("  (none)")
    print()


# --- Setup ---

owner = Owner(
    name="Alex",
    available_minutes=60,
    preferences=["feeding", "exercise"],
    session_start="08:00",
)

dog = Pet(name="Biscuit", species="Dog", age=4)
cat = Pet(name="Mochi",   species="Cat", age=2)

owner.add_pet(dog)
owner.add_pet(cat)

# Tasks added deliberately out of order:
# LOW before HIGH, short before long, grooming before feeding, etc.
dog.add_task(Task(title="Flea treatment",     category="Grooming",  duration=15, priority=Priority.LOW))
cat.add_task(Task(title="Laser pointer play", category="Exercise",  duration=20, priority=Priority.LOW))
cat.add_task(Task(title="Vet appointment",    category="Health",    duration=90, priority=Priority.HIGH))
dog.add_task(Task(title="Breakfast",          category="Feeding",   duration=10, priority=Priority.HIGH))
cat.add_task(Task(title="Litter box clean",   category="Hygiene",   duration=10, priority=Priority.HIGH))
dog.add_task(Task(title="Morning walk",       category="Exercise",  duration=30, priority=Priority.HIGH))
cat.add_task(Task(title="Dinner",             category="Feeding",   duration=5,  priority=Priority.MEDIUM))

# --- Filter demos ---

print_task_list(
    "ALL TASKS (added out of order)",
    owner.get_tasks(),
)

print_task_list(
    "BISCUIT'S TASKS ONLY",
    owner.get_tasks(pet_name="Biscuit"),
)

print_task_list(
    "MOCHI'S TASKS ONLY",
    owner.get_tasks(pet_name="Mochi"),
)

# Mark one task complete to show the completed/incomplete filter
dog.tasks[0].mark_complete()   # Flea treatment -> done

print_task_list(
    "INCOMPLETE TASKS ONLY",
    owner.get_tasks(completed=False),
)

print_task_list(
    "COMPLETED TASKS ONLY",
    owner.get_tasks(completed=True),
)

# --- Schedule (sorting demo) ---

scheduler = Scheduler(owner=owner)
plan = scheduler.build_plan()
print_schedule(plan)
