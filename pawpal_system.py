from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional
from uuid import UUID, uuid4


class Priority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Task:
    title: str
    category: str
    duration: int
    priority: Priority
    completed: bool = False
    id: UUID = field(default_factory=uuid4)
    assigned: bool = field(default=False, repr=False, init=False)

    def __setattr__(self, name: str, value) -> None:
        """Validate duration and priority before setting any attribute."""
        title = getattr(self, "title", "(unknown)")
        if name == "duration" and value <= 0:
            raise ValueError(f"Task '{title}' duration must be greater than 0.")
        if name == "priority" and not isinstance(value, Priority):
            raise ValueError(f"Task '{title}' priority must be a Priority enum value.")
        object.__setattr__(self, name, value)

    def mark_complete(self) -> None:
        """Mark this task as completed, raising an error if already complete."""
        if self.completed:
            raise RuntimeError(f"Task '{self.title}' is already marked complete.")
        self.completed = True


@dataclass
class Pet:
    name: str
    species: str
    age: int
    tasks: List[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_owner", None)

    @property
    def owner(self) -> Optional[Owner]:
        """Return the owner this pet is registered to, or None."""
        return getattr(self, "_owner", None)

    def __setattr__(self, name: str, value) -> None:
        """Validate age before setting any attribute."""
        if name == "age" and value < 0:
            pet_name = getattr(self, "name", "(unknown)")
            raise ValueError(f"Pet '{pet_name}' age cannot be negative.")
        object.__setattr__(self, name, value)

    def add_task(self, task: Task) -> None:
        """Assign a task to this pet, raising an error if already assigned elsewhere."""
        if task.assigned:
            raise ValueError(f"Task '{task.title}' is already assigned to another pet.")
        task.assigned = True
        self.tasks.append(task)

    def edit_task(self, task: Task) -> None:
        """Replace an existing task (matched by id) with the updated version."""
        for i, t in enumerate(self.tasks):
            if t.id == task.id:
                if task.assigned and t is not task:
                    raise ValueError(f"Task '{task.title}' is already assigned to another pet.")
                t.assigned = False
                task.assigned = True
                self.tasks[i] = task
                return
        raise ValueError(f"Task '{task.title}' not found for {self.name}.")

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet by id, unassigning it."""
        for i, t in enumerate(self.tasks):
            if t.id == task.id:
                self.tasks.pop(i)
                t.assigned = False
                return
        raise ValueError(f"Task '{task.title}' not found for {self.name}.")

    def get_tasks(self) -> List[Task]:
        """Return a shallow copy of this pet's task list."""
        return list(self.tasks)


class Owner:
    def __init__(self, name: str, available_minutes: int, preferences: List[str], session_start: str = "08:00"):
        """Initialize an Owner with a name, daily time budget, care preferences, and session start time."""
        self.name = name
        self.available_minutes = available_minutes
        self.preferences = preferences
        self.session_start = session_start
        self.pets: List[Pet] = []

    @property
    def available_minutes(self) -> int:
        """Return the owner's daily available time budget in minutes."""
        return self._available_minutes

    @available_minutes.setter
    def available_minutes(self, value: int) -> None:
        """Set available_minutes, enforcing it must be greater than 0."""
        if value <= 0:
            raise ValueError("available_minutes must be greater than 0.")
        self._available_minutes = value

    @property
    def session_start(self) -> str:
        """Return the session start time as an HH:MM string."""
        return self._session_start

    @session_start.setter
    def session_start(self, value: str) -> None:
        """Set session_start, validating format and updating session_start_minutes."""
        parts = value.split(":")
        try:
            if len(parts) != 2 or not (0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError(f"session_start '{value}' must be a valid time in HH:MM format.")
        self._session_start = value
        self._session_start_minutes = int(parts[0]) * 60 + int(parts[1])

    @property
    def session_start_minutes(self) -> int:
        """Return the session start time as total minutes since midnight."""
        return self._session_start_minutes

    def add_pet(self, pet: Pet) -> None:
        """Register a pet to this owner, raising an error if already owned or duplicate name."""
        if pet.owner is not None:
            raise ValueError(f"'{pet.name}' already belongs to '{pet.owner.name}'. Remove it first.")
        if any(p.name.lower() == pet.name.lower() for p in self.pets):
            raise ValueError(f"A pet named '{pet.name}' is already registered to {self.name}.")
        object.__setattr__(pet, "_owner", self)
        self.pets.append(pet)

    def get_tasks(self, completed: Optional[bool] = None, pet_name: Optional[str] = None) -> List[Task]:
        """Return tasks across all pets, optionally filtered by completion status and/or pet name."""
        results = []
        found_pet = False
        for pet in self.pets:
            if pet_name is not None and pet.name.lower() != pet_name.lower():
                continue
            found_pet = True
            for task in pet.tasks:
                if completed is None or task.completed == completed:
                    results.append(task)
        if pet_name is not None and not found_pet:
            raise ValueError(f"No pet named '{pet_name}' found for {self.name}.")
        return results

    def remove_pet(self, pet: Pet) -> None:
        """Unregister a pet from this owner, clearing its owner reference."""
        for i, p in enumerate(self.pets):
            if p is pet:
                self.pets.pop(i)
                for task in pet.tasks:
                    task.assigned = False
                object.__setattr__(pet, "_owner", None)
                return
        raise ValueError(f"No pet named '{pet.name}' found for {self.name}.")


class Scheduler:
    def __init__(self, owner: Owner):
        """Initialize the Scheduler with the owner whose pets and tasks will be planned."""
        self.owner = owner

    def build_plan(self) -> dict:
        """Build a prioritized schedule of pet tasks within the owner's available time budget."""
        if not self.owner.pets:
            raise ValueError(f"'{self.owner.name}' has no registered pets to schedule.")
        preferences = {p.lower() for p in self.owner.preferences}

        candidate_tasks = [
            (pet, task)
            for pet in self.owner.pets
            for task in list(pet.tasks)
            if not task.completed
        ]

        if not candidate_tasks:
            raise ValueError(f"'{self.owner.name}' has no incomplete tasks to schedule.")

        candidate_tasks.sort(key=lambda pt: (
            -pt[1].priority,
            0 if pt[1].category.lower() in preferences else 1,
            -pt[1].duration,
        ))

        scheduled = []
        first_pass_skipped = []
        remaining_minutes = self.owner.available_minutes

        session_start_minutes = self.owner.session_start_minutes
        current_minute = 0

        for pet, task in candidate_tasks:
            entry = {
                "id": task.id,
                "pet": pet.name,
                "task": task.title,
                "category": task.category,
                "duration": task.duration,
                "priority": task.priority.name,
                "preferred": task.category.lower() in preferences,
            }
            if task.duration <= remaining_minutes:
                total = session_start_minutes + current_minute
                scheduled.append({**entry, "start_time": f"{(total // 60) % 24:02}:{total % 60:02}"})
                remaining_minutes -= task.duration
                current_minute += task.duration
            else:
                first_pass_skipped.append(entry)

        remaining_to_fit = sorted(first_pass_skipped, key=lambda e: e["duration"])
        while True:
            fitted_any = False
            still_unfit = []
            for entry in remaining_to_fit:
                if entry["duration"] <= remaining_minutes:
                    total = session_start_minutes + current_minute
                    scheduled.append({**entry, "start_time": f"{(total // 60) % 24:02}:{total % 60:02}"})
                    remaining_minutes -= entry["duration"]
                    current_minute += entry["duration"]
                    fitted_any = True
                else:
                    still_unfit.append(entry)
            remaining_to_fit = still_unfit
            if not fitted_any:
                break
        second_pass_skipped = remaining_to_fit

        too_long = [e for e in second_pass_skipped if e["duration"] > self.owner.available_minutes]
        deferred = [e for e in second_pass_skipped if e["duration"] <= self.owner.available_minutes]

        return {
            "owner": self.owner.name,
            "scheduled": scheduled,
            "deferred": deferred,
            "too_long": too_long,
            "total_scheduled_minutes": self.owner.available_minutes - remaining_minutes,
            "remaining_minutes": remaining_minutes,
        }
