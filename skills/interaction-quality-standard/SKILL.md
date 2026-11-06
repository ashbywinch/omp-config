---
name: interaction-quality-standard
description: Required fields and rules for an Interaction — one record of one
  call, email, letter or message. Says what each field holds and what must never
  go in it.
---

# Interaction Quality Standard

An Interaction is **one event**: a call that happened, a letter that arrived, a
message that was sent. It is the unit of the record, and it is the thing someone
reads in three weeks when they cannot remember who they were talking to, or when.

**A row is one event, and everything in it belongs to that event.** The other
events around it have their own rows. The only ways one row refers to another
are `followup_ref` and the document link.

## Required Fields

| Field | Holds | Never holds |
| --- | --- | --- |
| Title / summary (Notion) | what happened, in one line | the conclusion |
| Related to Epics | the matter this belongs to | a value stream, or a guess at a future epic |
| Task | the task carrying an action arising from this row | an unrelated task |
| Contact | the person or organisation, as the record names them | a phone label taken as a fact |
| Contact reference | `phone:<number>` where the number resolves on the phone but not in the address book | a number that is in the address book |
| From / To | the participants as the source shows them | a guess at who spoke first, or what they meant |
| Date and time | when it happened, local | when it was recorded |
| Duration | how long it lasted | a guess from the length of the text |
| Channel | email, phone, chat, note, letter | the device it was read on |
| Overview | what happened in **this** event: what was said, decided or promised, and what it requires — bullets, then `Action:` | any other message or conversation, what came of it later, where a file is, who someone is, background |
| Transcript | the text of a recording, once approved | a summary of it |
| Reference | `account:message_id` / `account:file_id` for this event | a path, a URL, a bare id |
| Follow-up | `chase` when they owe, `implement` when we owe | a restatement of the obligation — that is the `Action:` |
| Follow-up done / by | when it was closed, and by what | the date it was created |

## The overview

The overview is the only place the row says what happened, what was promised
and who owes what next. Every other column holds a value; without the overview
the row records that contact happened, not what came of it.

```
• Quote accepted at the agreed figure; delivery in four weeks from order.
• Two components back-ordered; the supplier confirms dates weekly.
Action: owner — chase the supplier once the revised dates arrive.
```

- **Describe the event, never the neighbours.** A chase that came in another
  message, a parcel that arrived afterwards, a decision taken later: each has
  its own row. Writing it here makes two rows that disagree.
- **If something elsewhere discharges this row's action**, that is
  `followup_ref` — not a sentence.
- **Say what the situation is**, so it can be understood without reopening the
  thread.
- **No pronoun should need resolving.** Not "it", not "the form" where two forms
  are in play, not "them" where the counterparty is the point.
- **Never repeat a column.** The sender, the date, the reference number and the
  file location are columns; the overview does not restate them.

## Follow-ups

- Every `Action:` creates a follow-up: `chase` when they owe what they promised,
  `implement` when we owe it.
- One interaction can carry any number of follow-ups; each obligation is its
  own.
- An action we owe is also a task with a deadline — a follow-up nothing surfaces
  never comes round again.
- A follow-up closes when the user says what arrived is right, and the record
  says what closed it.

## What does not earn a row

- A bare acknowledgement: "thanks", "got it", "oh fantastic". It earns a row
  only when it closes an action someone asked for.
- A view confirmation, or a template that promises feedback and nothing else.
- A notification with nothing decided in it. It is a fact about a system, not
  an event between people.

## Validation Checklist

- [ ] The row records one event; every sentence in the overview describes that event
- [ ] The epic is the one this event belongs to
- [ ] `From`/`To` come from the record, not from what the thread implies
- [ ] The `Action:` names who owes it, and the follow-up matches the direction
- [ ] An action we owe has a task with a deadline, and this row points at it
- [ ] `Follow-up done`/`by` are set once the obligation is closed, empty until then
- [ ] Nothing in the overview duplicates a column
