# Who uses HomeStretch, why, and how

## The user and the problem

Maria's mother Rosa, 78, has just come home from the hospital after heart failure. Maria is now the one keeping
her safe, and she was handed a discharge packet, three medicines (one new, one at a new dose, one stopped), and a
list of warning signs. The first 30 days are when readmissions happen, and the common causes are the ones Maria
can actually prevent: the old bottle still in the cabinet, the old dose still being taken, an over-the-counter
painkiller the plan says to avoid, and a warning sign nobody recognized in time.

**Why she would open it every day:** it is the one place that knows Rosa's plan. It tells her what to give today, what
is still wrong with the bottles at home, and whether what she is seeing right now needs a call to the clinic, urgent
care, or 911. Every answer cites the plan or the drug label it came from.

## First use (about 5 minutes)

1. **Opens HomeStretch** → *Today* shows "Caring for Rosa · Day 5 of 30 at home" and the capsule strip.
2. **Bottles → photographs each bottle** (or picks samples) → *Check these bottles*.
   Behind it: Prompt A reads each label, RxNorm checks each name, Prompt B compares the bottles with the plan.
   She sees stickers: *Stopped at discharge* (old metoprolol), *Dose changed* (old furosemide), *Not on her list*
   (Advil, which the plan says to avoid), and *Not picked up yet* (the new metoprolol); the reply notes the lisinopril
   matches her plan. Each claim carries a small grey source tag (*her plan*, *drug label*, *bottle check*).
3. **Back on Today,** those open items now sit under *Still to sort out*, so they stay visible until they are fixed.

## Every day (under a minute)

1. *Today* → ticks off the morning medicines (the changed and new ones are marked) → logs Rosa's morning weight.
   A gain of 3 lb or more since the last entry shows "call the clinic today" with the number (the plan's warn-1).
2. Glances at *Still to sort out* and *Coming up* (Dr. Patel, Thursday 10:30).

## When something comes up

- **A question** → *Ask*: "Does the water pill make her lose potassium?" The model chooses a label search and
  answers "The label says furosemide can lower potassium [ref-2]… ask her clinic". "What should I ask the pharmacy?"
  needs no lookup: it answers from this session's bottle check.
- **Something feels wrong** → the box at the top of *Today*: "Her chest feels tight and she's gasping" → a red
  **Call 911 now** with the sign from her plan. "She's dizzy when she stands up" → *call the clinic today* with the
  number. No lookups run on a possible emergency, so the answer comes first.

## Limits of this build (class project)

The app shows one synthetic patient (Rosa) and a fixed demo date; the evals also cover 20 other synthetic patients; medicine check-offs and weights last for the session only; no
reminders or notifications (that needs an installable phone app, planned after A4); no login. Not medical advice.
