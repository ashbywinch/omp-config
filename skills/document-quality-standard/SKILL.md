---
name: document-quality-standard
description: Required fields and rules for a Document — one file of record, whether
  in Drive or attached to an Interaction. Says what each field holds and what must
  never go in it.
---

# Document Quality Standard

A Document is **one file that answers a question later** — who offered what, what
was charged, what the council decided, what the engineer concluded. The point of
the record is that the file can be found, and that whoever finds it can read it.

It is not an Interaction. The email that carried a file stays in mail, and the
Interaction carries its reference; only what was *attached* is a Document.

## Required Fields

| Field | Holds | Never holds |
| --- | --- | --- |
| Name | the filename as stored: `<date> <what it is> <what distinguishes it>` | the sender, the folder, "final" |
| Kind | what kind of document it is, in two or three words | a description of the matter |
| Date | the document's own date | the date it arrived |
| Link | to the file in Drive (`account:file_id` where the store is a stand-in) | a path, a URL, a bare id |
| Readable copy | a link to the text copy, when one is warranted | a note saying there is none |
| Related to Epics | the matter it belongs to | a value stream |
| Interaction | the interaction it arrived with, or that it answers | an unrelated interaction |
| Note | what the document is, and what it says that matters — anything it requires first, in two or three lines | where it is, who sent it, the channel, whether a copy was made |

## The name

`<date> <what it is> <the thing that distinguishes it>`. The date is the
document's own. The distinguisher tells it from its siblings — an amount, a
version, a property — not the sender and not the folder.

The pattern to follow is the one **in the folder the file is going into**: read
its siblings there. A similarly-named document in another matter is not a
precedent, and borrowing its shape suggests a connection that does not exist.

## The note

Two or three lines: what it is, and what it says that matters. Anything it
requires of the reader goes first — a form to sign, an account to change, an
appointment to attend.

The note is not the path (the folder holds that), not the sender (the
interaction holds that), and not a remark on whether a copy was made: an empty
readable-copy field says that by itself.

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

- [ ] The file answers a question later; if not, there is no row
- [ ] It is one file, and the row points at it, not at the email that carried it
- [ ] The name follows the folder's own pattern and carries no sender
- [ ] The date is the document's own
- [ ] The note says what it is and what it requires, and repeats no field
- [ ] The interaction link is set, and the interaction points back
- [ ] The readable copy exists exactly when the original cannot be read
