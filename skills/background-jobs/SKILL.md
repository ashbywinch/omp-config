---
name: background-jobs
description: Launch a long-running job so the harness notifies you when it actually finishes — tracked background, no detach; a waiter for an already-detached process; how this differs from a supervised service
---

# Background jobs

The harness notifies you when the command **it launched** exits. It does not
notify you when a child you detached exits. That distinction is the whole
skill.

The shell tool's instructions say: “Background commands return immediately,
and you will be notified when they complete.” That promise is for the command
the harness launched; it does not extend to a child you detached. The rest of
this skill is how to keep that promise.

## Launch a job you want to report on

Run the real command as the background command:

```
shell(command="make evals-test …", background=true)
```

No `setsid`, no `nohup`, no trailing `&`. The tracked process is the job, and
its exit is the completion event. Tee the output to a log file so you can read
the result after the event.

If the completion event arrives immediately and contains only the launch
line, it is the launcher, not the job. The job is still running.

## A process that is already detached

Attach a tracked waiter; its exit is the real completion:

```
wait-for <pid> <log>          # background=true
```

or, without the tool:

```
tail --pid=<pid> -f /dev/null
```

Then read the tail of the log. Do not poll the log while the job runs.

Verify the pid is the real process, not the shell that launched it:

```
pgrep -af "<command fragment>"
ps -o pid,etime,cmd -p <pid>
```

`$!` is the process you backgrounded, which may itself be a launcher.

## A service that must outlive the session

This is the other case: a server, webhook receiver, or anything the user's
devices depend on. Start it through the hub as a supervised, detached
service (`skill://lan-server`), with a ready condition. Do not promise a
completion report for it; it is meant not to complete.

## The promise rule

Never say “I’ll tell you when it finishes” unless you can name the process
that will resume you: the tracked background command, or `wait-for`. If the
job is detached and unwatched, say you will check when next asked.
