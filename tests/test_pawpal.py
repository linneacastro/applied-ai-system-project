import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import date, timedelta
from pawpal_system import Task, Pet, Owner, Scheduler, Priority


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_task(title="Walk", category="Exercise", duration=30, priority=Priority.MEDIUM,
              frequency=None, due_date=None):
    return Task(title=title, category=category, duration=duration,
                priority=priority, frequency=frequency, due_date=due_date)


def make_owner(name="Alex", minutes=120, preferences=None, session_start="08:00"):
    return Owner(name=name, available_minutes=minutes,
                 preferences=preferences or ["Exercise"], session_start=session_start)


# ===========================================================================
# BEHAVIOR 1 — Task validation rejects bad inputs
# ===========================================================================

def test_mark_complete_changes_status():
    task = make_task()
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Biscuit", species="Dog", age=4)
    task = Task(title="Breakfast", category="Feeding", duration=10, priority=Priority.HIGH)
    assert len(pet.get_tasks()) == 0
    pet.add_task(task)
    assert len(pet.get_tasks()) == 1


def test_task_zero_duration_raises():
    with pytest.raises(ValueError, match="duration"):
        make_task(duration=0)


def test_task_negative_duration_raises():
    with pytest.raises(ValueError, match="duration"):
        make_task(duration=-5)


def test_task_invalid_frequency_raises():
    with pytest.raises(ValueError, match="frequency"):
        make_task(frequency="monthly")


def test_task_valid_frequencies_accepted():
    t1 = make_task(frequency="daily")
    t2 = make_task(frequency="weekly")
    t3 = make_task(frequency=None)
    assert t1.frequency == "daily"
    assert t2.frequency == "weekly"
    assert t3.frequency is None


def test_pet_negative_age_raises():
    with pytest.raises(ValueError, match="age"):
        Pet(name="Rex", species="Dog", age=-1)


# ===========================================================================
# BEHAVIOR 2 — Recurring tasks generate correct next occurrence on completion
# ===========================================================================

def test_one_off_task_complete_returns_none():
    task = make_task(frequency=None)
    result = task.mark_complete()
    assert result is None


def test_daily_task_advances_due_date_by_one_day():
    # Use a future due_date so max(due_date, today) == due_date
    due = date.today() + timedelta(days=5)
    task = make_task(frequency="daily", due_date=due)
    next_task = task.mark_complete()
    assert next_task is not None
    assert next_task.due_date == due + timedelta(days=1)
    assert next_task.completed is False
    assert next_task.id != task.id


def test_weekly_task_advances_due_date_by_seven_days():
    # Use a future due_date so max(due_date, today) == due_date
    due = date.today() + timedelta(days=5)
    task = make_task(frequency="weekly", due_date=due)
    next_task = task.mark_complete()
    assert next_task is not None
    assert next_task.due_date == due + timedelta(weeks=1)


def test_recurring_task_no_due_date_uses_today_as_base():
    task = make_task(frequency="daily", due_date=None)
    next_task = task.mark_complete()
    assert next_task.due_date == date.today() + timedelta(days=1)


def test_recurring_task_past_due_date_uses_today_as_base():
    # due_date in the past → max(due_date, today) == today
    past_due = date(2020, 1, 1)
    task = make_task(frequency="daily", due_date=past_due)
    next_task = task.mark_complete()
    assert next_task.due_date == date.today() + timedelta(days=1)


def test_completing_already_completed_task_raises():
    task = make_task()
    task.mark_complete()
    with pytest.raises(RuntimeError, match="already marked complete"):
        task.mark_complete()


def test_recurring_task_inherits_same_attributes():
    task = make_task(title="Feed", category="Feeding", duration=15,
                     priority=Priority.HIGH, frequency="weekly",
                     due_date=date(2026, 4, 1))
    next_task = task.mark_complete()
    assert next_task.title == task.title
    assert next_task.category == task.category
    assert next_task.duration == task.duration
    assert next_task.priority == task.priority
    assert next_task.frequency == task.frequency


# ===========================================================================
# BEHAVIOR 3 — A task cannot be assigned to more than one pet
# ===========================================================================

def test_task_cannot_be_added_to_two_pets():
    pet1 = Pet(name="Rex", species="Dog", age=3)
    pet2 = Pet(name="Luna", species="Cat", age=2)
    task = make_task()
    pet1.add_task(task)
    with pytest.raises(ValueError, match="already assigned"):
        pet2.add_task(task)


def test_pet_complete_task_adds_next_occurrence():
    pet = Pet(name="Rex", species="Dog", age=3)
    task = make_task(frequency="daily", due_date=date.today())
    pet.add_task(task)
    assert len(pet.get_tasks()) == 1
    next_task = pet.complete_task(task)
    assert next_task is not None
    assert len(pet.get_tasks()) == 2
    assert next_task.assigned is True


def test_pet_complete_daily_task_next_occurrence_due_date():
    due = date.today() + timedelta(days=3)
    pet = Pet(name="Rex", species="Dog", age=3)
    task = make_task(title="Morning walk", frequency="daily", due_date=due)
    pet.add_task(task)
    next_task = pet.complete_task(task)
    assert next_task in pet.get_tasks()
    assert next_task.due_date == due + timedelta(days=1)


def test_remove_task_unassigns_it():
    pet = Pet(name="Rex", species="Dog", age=3)
    task = make_task()
    pet.add_task(task)
    pet.remove_task(task)
    assert len(pet.get_tasks()) == 0
    assert task.assigned is False


# ===========================================================================
# BEHAVIOR 4 — Scheduler respects the owner's time budget
# ===========================================================================

def test_scheduler_schedules_tasks_within_budget():
    owner = make_owner(minutes=60)
    pet = Pet(name="Buddy", species="Dog", age=2)
    pet.add_task(make_task(title="Walk", duration=30))
    pet.add_task(make_task(title="Play", duration=20))
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan()
    total = sum(e["duration"] for e in plan["scheduled"])
    assert total <= 60
    assert plan["total_scheduled_minutes"] + plan["remaining_minutes"] == 60


def test_scheduler_puts_oversized_task_in_too_long():
    owner = make_owner(minutes=20)
    pet = Pet(name="Buddy", species="Dog", age=2)
    pet.add_task(make_task(title="LongWalk", duration=90))
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan()
    assert any(e["task"] == "LongWalk" for e in plan["too_long"])
    assert not any(e["task"] == "LongWalk" for e in plan["scheduled"])


def test_scheduler_second_pass_fills_gap():
    # First task (50 min) skips a 30-min task, leaving 70 min.
    # The 30-min task should be picked up in the second pass.
    owner = make_owner(minutes=100)
    pet = Pet(name="Buddy", species="Dog", age=2)
    # HIGH priority, long — schedules first
    pet.add_task(make_task(title="LongTask", duration=50, priority=Priority.HIGH))
    # LOW priority, fits after LongTask
    pet.add_task(make_task(title="ShortTask", duration=30, priority=Priority.LOW))
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan()
    scheduled_titles = [e["task"] for e in plan["scheduled"]]
    assert "LongTask" in scheduled_titles
    assert "ShortTask" in scheduled_titles
    assert not plan["deferred"]


def test_scheduler_deferred_vs_too_long_distinction():
    owner = make_owner(minutes=30)
    pet = Pet(name="Buddy", species="Dog", age=2)
    pet.add_task(make_task(title="Fits", duration=30))
    pet.add_task(make_task(title="Skipped", duration=25))   # fits budget but can't all go in
    pet.add_task(make_task(title="TooLong", duration=50))   # exceeds total budget
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan()
    too_long_titles = [e["task"] for e in plan["too_long"]]
    assert "TooLong" in too_long_titles
    deferred_titles = [e["task"] for e in plan["deferred"]]
    assert "Skipped" in deferred_titles


def test_scheduler_high_priority_before_low():
    owner = make_owner(minutes=200)
    pet = Pet(name="Buddy", species="Dog", age=2)
    pet.add_task(make_task(title="LowTask", duration=30, priority=Priority.LOW))
    pet.add_task(make_task(title="HighTask", duration=30, priority=Priority.HIGH))
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan()
    titles = [e["task"] for e in plan["scheduled"]]
    assert titles.index("HighTask") < titles.index("LowTask")


def test_scheduler_preferred_category_before_nonpreferred_same_priority():
    owner = make_owner(minutes=200, preferences=["Exercise"])
    pet = Pet(name="Buddy", species="Dog", age=2)
    pet.add_task(make_task(title="Groom", category="Grooming", duration=20, priority=Priority.MEDIUM))
    pet.add_task(make_task(title="Walk", category="Exercise", duration=20, priority=Priority.MEDIUM))
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan()
    titles = [e["task"] for e in plan["scheduled"]]
    assert titles.index("Walk") < titles.index("Groom")


def test_scheduler_start_times_are_chronological():
    owner = make_owner(minutes=200, session_start="08:00")
    pet = Pet(name="Buddy", species="Dog", age=2)
    pet.add_task(make_task(title="Task1", duration=30, priority=Priority.HIGH))
    pet.add_task(make_task(title="Task2", duration=20, priority=Priority.MEDIUM))
    pet.add_task(make_task(title="Task3", duration=15, priority=Priority.LOW))
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan()
    times = [e["start_time"] for e in plan["scheduled"]]
    assert times == sorted(times), f"Start times not in order: {times}"


def test_scheduler_raises_with_no_pets():
    owner = make_owner()
    with pytest.raises(ValueError, match="no registered pets"):
        Scheduler(owner).build_plan()


def test_scheduler_raises_with_no_incomplete_tasks():
    owner = make_owner()
    pet = Pet(name="Buddy", species="Dog", age=2)
    task = make_task()
    pet.add_task(task)
    task.mark_complete()
    owner.add_pet(pet)
    with pytest.raises(ValueError, match="no incomplete tasks"):
        Scheduler(owner).build_plan()


def test_detect_conflicts_flags_overlapping_tasks():
    owner = make_owner()
    scheduler = Scheduler(owner)
    overlapping = [
        {"task": "Walk", "pet": "Rex", "start_time": "08:00", "duration": 30},
        {"task": "Feed", "pet": "Rex", "start_time": "08:15", "duration": 20},
    ]
    warnings = scheduler.detect_conflicts(overlapping)
    assert len(warnings) == 1
    assert "Walk" in warnings[0]
    assert "Feed" in warnings[0]


def test_detect_conflicts_no_warning_for_sequential_tasks():
    owner = make_owner()
    scheduler = Scheduler(owner)
    sequential = [
        {"task": "Walk", "pet": "Rex", "start_time": "08:00", "duration": 30},
        {"task": "Feed", "pet": "Rex", "start_time": "08:30", "duration": 20},
    ]
    warnings = scheduler.detect_conflicts(sequential)
    assert warnings == []


def test_scheduler_build_plan_warnings_empty_for_sequential_schedule():
    owner = make_owner(minutes=120)
    pet = Pet(name="Buddy", species="Dog", age=2)
    pet.add_task(make_task(title="Walk", duration=30))
    pet.add_task(make_task(title="Feed", duration=20))
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan()
    assert plan["warnings"] == []


def test_scheduler_start_time_appears_in_entries():
    owner = make_owner(minutes=60, session_start="09:00")
    pet = Pet(name="Buddy", species="Dog", age=2)
    pet.add_task(make_task(title="Walk", duration=30))
    owner.add_pet(pet)
    plan = Scheduler(owner).build_plan()
    assert plan["scheduled"][0]["start_time"] == "09:00"


# ===========================================================================
# BEHAVIOR 5 — Owner enforces pet registration rules
# ===========================================================================

def test_owner_rejects_pet_already_owned():
    owner1 = make_owner(name="Alice")
    owner2 = make_owner(name="Bob")
    pet = Pet(name="Rex", species="Dog", age=3)
    owner1.add_pet(pet)
    with pytest.raises(ValueError, match="already belongs"):
        owner2.add_pet(pet)


def test_owner_rejects_duplicate_pet_name_case_insensitive():
    owner = make_owner()
    owner.add_pet(Pet(name="Rex", species="Dog", age=3))
    with pytest.raises(ValueError, match="already registered"):
        owner.add_pet(Pet(name="rex", species="Cat", age=2))


def test_remove_pet_clears_owner_reference():
    owner = make_owner()
    pet = Pet(name="Rex", species="Dog", age=3)
    owner.add_pet(pet)
    owner.remove_pet(pet)
    assert pet.owner is None
    assert pet not in owner.pets


def test_owner_get_tasks_filtered_by_completion():
    owner = make_owner()
    pet = Pet(name="Rex", species="Dog", age=3)
    t1 = make_task(title="Done")
    t2 = make_task(title="Pending")
    pet.add_task(t1)
    pet.add_task(t2)
    t1.mark_complete()
    owner.add_pet(pet)
    done = owner.get_tasks(completed=True)
    pending = owner.get_tasks(completed=False)
    assert len(done) == 1 and done[0].title == "Done"
    assert len(pending) == 1 and pending[0].title == "Pending"


def test_owner_get_tasks_by_pet_name_not_found_raises():
    owner = make_owner()
    owner.add_pet(Pet(name="Rex", species="Dog", age=3))
    with pytest.raises(ValueError, match="No pet named"):
        owner.get_tasks(pet_name="Luna")


def test_owner_session_start_invalid_format_raises():
    with pytest.raises(ValueError, match="HH:MM"):
        make_owner(session_start="9am")


def test_owner_available_minutes_zero_raises():
    with pytest.raises(ValueError, match="available_minutes"):
        make_owner(minutes=0)
