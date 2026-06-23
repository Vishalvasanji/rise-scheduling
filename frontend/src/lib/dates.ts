// Shared date helpers for the schedule UI.

// Parse a YYYY-MM-DD string as a LOCAL calendar date. `new Date("2026-06-22")`
// parses as UTC midnight, which renders as the previous day in negative-UTC
// timezones — an off-by-one on the Gantt. Building from parts avoids that.
export function parseLocalDate(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

// Format a date (or YYYY-MM-DD string) as MM/DD/YY.
export function mmddyy(value: string | Date): string {
  const d = typeof value === "string" ? parseLocalDate(value) : value;
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const yy = String(d.getFullYear()).slice(-2);
  return `${mm}/${dd}/${yy}`;
}
