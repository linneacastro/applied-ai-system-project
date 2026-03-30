# PawPal+ Project Reflection

## 1. System Design

PawPal+ is a Streamlit app designed to help pet owners stay on top of their pet care routines. It lets users enter basic info about themselves and their pet, add and manage care tasks like walks, feeding, medications, grooming, and enrichment, and then generates a daily schedule based on their available time, task priorities, and preferences. It also explains the reasoning behind the plan it creates, so the owner understands why things were scheduled the way they were.

The three core actions, summarized: 
1. Enter a pet
2. Create tasks like walks, grooming, etc.
3. Generate a daiy schedule and view it

**a. Initial design**

- Briefly describe your initial UML design.
The system is built around four classes. The Owner holds the user's name, how many minutes they have available in a day, and care preferences. They can have one or more Pets, and each Pet stores basic info like name, species, and age, along with a list of Tasks that can be added, edited, or removed. Each Task captures the details of a single care activity: its title, category (like feeding or grooming), how long it takes, its priority level, and whether it's been completed. Finally, the Scheduler takes the Owner's time constraints and the Pet's task list and uses them together to produce a daily care plan.

- What classes did you include, and what responsibilities did you assign to each?

There are four classes, each with a focused responsibility:

Owner — represents the person using the app; holds their name, available time, and preferences, and keeps track of which pets they have.
Pet — represents the pet being cared for; stores basic info like name, species, and age, and manages the list of tasks associated with that pet.
Task — represents a single care activity; holds the details like title, category, duration, priority, and whether it's been completed.
Scheduler — the brain of the app; it reads the owner's time constraints and the pet's task list and uses that information to build a daily care plan.

**b. Design changes**

- Did your design change during implementation?
Yes! When I asked about bottlenecks in logic or missing relationships, it returned to me quite a few items. This was a really eye opening prompt.

- If yes, describe at least one change and why you made it.
Here is one change made to the Priority. Priority is now  IntEnum (new)
This replaces the free int field. Callers can now only pass Priority.LOW, Priority.MEDIUM, or Priority.HIGH. Before there could be ambiguous values passed in like 99 or -1 that made their way to build_plan().

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?

The scheduler considers three main constraints:

Time is the primary hard constraint — the owner's available_minutes budget acts as a cap. Tasks are greedily packed into the session starting from session_start_minutes, and any task whose duration exceeds the remaining time is skipped (deferred or marked as too-long).

Priority is the primary soft constraint — tasks are sorted by their Priority enum value (descending), so high-priority tasks are scheduled first and are least likely to get bumped when time runs short.

Preferences act as a tiebreaker — the owner's preferred task categories (e.g., "grooming", "exercise") are boosted in sort order so that preferred-category tasks slot in before non-preferred ones of equal priority and duration.

- How did you decide which constraints mattered most?

Priority was ranked first because a missed high-priority task (like medication) has real consequences for a pet's wellbeing, so it should always be scheduled before lower-priority ones regardless of preferences. Time comes next as a hard physical constraint. Preferences were treated last as a quality-of-life tiebreaker, since they improve the owner's experience but don't affect correctness or pet health the way priority and time do.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.

The scheduler uses a greedy first-fit approach — it picks tasks in priority order and immediately locks each one in if it fits. This is fast and simple, but it can leave time on the table. For example, one large low-priority task might get scheduled early and block several smaller high-priority tasks that could have fit in the same slot.

Another thing that is a tradeoff is the way my current scheduler is stacking tasks one right after the other with no break inbetween. I think that in a future iteration, it would be more schedule sensitive and allow the user to pick a time to make things happen. This is something I'm planning on adressing once I have had time to test the full program in the web UI.

- Why is that tradeoff reasonable for this scenario?
I could do something dynamic like knapsack optimization to maximize total value within the time budget, but I chose the greedy method was chosen for simplicity and predictability. I kind of want to be able to choose a simple option first and see how it plays out before making larger changes. 
---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?

I used AI tools in all parts of this project - to help me brainstorm the initial UML diagram, to flesh out the skeleton of classes, to then fill out the classes, build tests, and iterate. I feel like I just kept riffing on what I got, and using the AI (Claude) to ask questions and keep going. 

- What kinds of prompts or questions were most helpful?

The most helpful prompts were the ones where I described what I was trying to accomplish and asked for weaknesses in my current approach. Those gave me concrete, actionable feedback rather than vague suggestions. I also used AI to help me think through tradeoffs, like whether to use a greedy approach versus something like knapsack optimization for scheduling. The prompt that I used the most was something like "Please do a runthrough of this file for logic flaws and bottlenecks." I did this until I got to just a few edge cases. 

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.

When the assignment asked me to add conflict detection, AI suggested implementing a full overlap-checking function — and I did write it. But when I thought about it more, I realized the suggestion didn't fully fit my design: my scheduler stacks tasks back-to-back sequentially, so overlaps are structurally impossible. I kept the detect_conflicts method because it was required, but I pushed back on the idea that it was meaningful for this system. Rather than accepting the AI's framing that "conflict detection = good, add it," I recognized it was a feature that made sense in a different kind of scheduler (one where tasks have fixed or user-assigned times), and noted that for my design it would always return an empty list. That distinction — understanding why a pattern exists before applying it — came from my own evaluation, not the AI's suggestion.

- How did you evaluate or verify what the AI suggested?

I ran the code and checked whether the output matched what the AI described. For logic changes, I traced through the behavior manually and used the test suite as a sanity check. For structural suggestions, I reasoned through the design myself and asked if the scenario the AI was guarding against couldn't happen in my system, I treated the suggestion as a mismatch, even if the code itself was technically correct.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?

I tested five main behavior areas:

Task validation — bad inputs like zero/negative duration, invalid frequency, and negative pet age all raise errors correctly.
Recurring tasks — completing a daily or weekly task generates the correct next occurrence with the right due date, a new ID, and the same attributes. One-off tasks return None. Completing an already-completed task raises an error.
Task assignment rules — a task can't be added to two pets at once; removing a task properly unassigns it.
Scheduler time budget — scheduled tasks stay within the owner's time limit; oversized tasks go to too_long; tasks that fit the budget but got bumped go to deferred; high-priority tasks schedule before low-priority ones; preferred categories are ordered first among equal priorities; start times are chronological.
Owner registration rules — a pet can't be added to two owners; duplicate pet names (case-insensitive) are rejected; removing a pet clears its owner reference; task filtering by completion status and pet name works correctly.

- Why were these tests important?

The tests mattered because the scheduler's correctness depends on the classes beneath it working exactly right. A task with a bad priority value or a pet with a duplicate name could silently corrupt the schedule. Testing each layer ensured that bugs would surface at their source rather than as mysterious wrong output at the end.

**b. Confidence**

- How confident are you that your scheduler works correctly?

I'm fairly confident the core logic works correctly. The test suite covers the main scenarios: priority ordering, time budget enforcement, deferred vs. too-long distinctions, and preference-based tiebreaking. That said, the greedy approach has known gaps, and I haven't tested the scheduler against a wide range of real-world inputs through the UI. My confidence is high for the cases I explicitly tested and lower for edge cases I haven't encountered yet.

- What edge cases would you test next if you had more time?

I'd want to test the scheduler through the UI with realistic inputs, like a pet with many tasks of mixed priorities and a tight time budget, to see how the plan looks in practice. I'd also test what happens when all tasks are the same priority and duration, when the owner's available time exactly matches the total task time, and when a recurring task is completed multiple times in a row to make sure the due dates chain correctly.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

I'm most satisfied with the process part of the project... so not one particular aspect of it. I love that I got to be hands on with it from the get go because it gives me a template to use with future projects. I really like starting with a UML class diagram because you can start to form an understanding of how things will fit together before even starting to code. 

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

I would improve on the actual UI design. I would also improve on how my program was fitting in tasks. It currently was just stacking them in, sort of like a puzzle, but it didn't give any flexibility for going back to edit or reorganize tasks.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

You need an organized, clear process before you start writing code. When I went into AI conversations with a specific question or a concrete piece of code to review, I got much more useful feedback than when I asked something vague. The same was true for the design itself: thinking through the class responsibilities upfront made it easier to catch problems early, like the priority field issue, rather than discovering them after the logic was already built around bad assumptions.
