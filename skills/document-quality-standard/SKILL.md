---
name: document-quality-standard
description: Required fields and rules for a document record in Notion — one row
  indexing one file, whether the file lives in Drive or arrived with a message.
---

# Document Quality Standard

This is the standard for the **record** of a document, not for the document
itself: one Notion row that indexes one file. The file lives in Drive, or in the
store standing in for it.

A file that arrives with an email is still its own thing — the message stays in
mail, and the record points at the file, not at the message. The standard for the
message is `skill://interaction-quality-standard`.

## Required Fields

| Field | Holds | Never holds |
| --- | --- | --- |
| Name | the file's stored name, as it is | a renamed copy, the sender, the folder |
| Kind | what kind of file it is, in two or three words | a description of the epic |
| Date | the date on the document itself | the date it arrived |
| Link | to the file in Drive (`account:file_id` where the store is a stand-in) | a path, a URL, a bare id |
| Readable copy | a link to a markdown copy of its text, when one is warranted | a note saying there is none |
| Related to Epics | the deepest epic it belongs to — a Notion epic, never a value stream | a value stream |
| Interaction | the message it arrived with, or that it answers (`skill://interaction-quality-standard`) | an unrelated message |
| Note | what it is and what it says that matters, in two or three lines; anything it requires of the reader goes first | anything another column already holds |

## The name

Record the name the file has.

## The readable copy

A copy exists for one reason: the original cannot be read or searched cheaply.
A scan with no text layer, a photograph of a letter, a long report. Store the
text beside the original and point the readable-copy field at it.

A clean document — a `.docx`, a text-layer PDF — does not earn one. A copy of
something already readable is a second copy, and worse than none.

## One file, one row

Two rows for one file splits the record. Two copies of one file in one folder is
the same fault in the storage. Before creating anything, look for what is
already there — by reference, amount and date, not by the subject line.

## Validation Checklist

- [ ] One row, pointing at one file
- [ ] The row points at the file, not at the message that carried it
- [ ] The name is the file's own
- [ ] The date is the document's own
- [ ] The note says what it is and what it requires, and repeats no column
- [ ] The interaction link is set, and the interaction points back
- [ ] The readable copy exists exactly when the original cannot be read
