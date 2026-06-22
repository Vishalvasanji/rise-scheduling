"""Data-access layer. All DB access goes through this package and the
repositories — no raw connection handling anywhere else in the app, so the
SQLite -> Turso/Postgres swap is a connection-URL change only (SCOPE §5.1)."""
