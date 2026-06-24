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

// Inclusive working-day count (Mon–Fri) between two dates, matching the backend
// calendar (Mon–Fri, no holidays in the pilot). Used for summary-row durations.
export function businessDays(start: string | Date, finish: string | Date): number {
  const a = typeof start === "string" ? parseLocalDate(start) : new Date(start);
  const b = typeof finish === "string" ? parseLocalDate(finish) : new Date(finish);
  if (b < a) return 0;
  let count = 0;
  const cur = new Date(a.getFullYear(), a.getMonth(), a.getDate());
  const end = new Date(b.getFullYear(), b.getMonth(), b.getDate());
  while (cur <= end) {
    const dow = cur.getDay();
    if (dow !== 0 && dow !== 6) count++;
    cur.setDate(cur.getDate() + 1);
  }
  return count;
}
