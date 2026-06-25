# CLAUDE.md

Guidance for Claude Code working in the `rise-scheduling` repo. This is a LIHTC
schedule hub: a React + Vite + TypeScript frontend (`frontend/`) deployed on Vercel,
and a FastAPI + SQLAlchemy backend (`backend/`) with a CPM scheduling engine.

## Pull requests

When you open a PR for work the user requested, take it all the way to merged so the
user doesn't have to merge manually:

1. Push the branch and open the PR.
2. Wait for the Vercel/CI check to pass (don't poll with `sleep` — rely on PR activity
   events; if you're not subscribed, check status before merging).
3. If it's a draft, mark it ready, then **merge it**.

If CI fails, fix it and proceed to merge. Only pause to ask the user first when a
change is risky or ambiguous, or when CI can't be made green.
