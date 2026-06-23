import { useEffect, useRef, useState } from "react";

interface Size {
  width: number;
  height: number;
}

// Measures an element's content box and keeps it updated via ResizeObserver.
// Used to give the Gantt a concrete pixel height so it scrolls internally
// instead of growing the page.
export function useElementSize<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [size, setSize] = useState<Size>({ width: 0, height: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const { width, height } = entry.contentRect;
        setSize({ width: Math.round(width), height: Math.round(height) });
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, ...size };
}
