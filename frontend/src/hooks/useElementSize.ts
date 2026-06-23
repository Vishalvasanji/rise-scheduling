import { useCallback, useRef, useState } from "react";

interface Size {
  width: number;
  height: number;
}

// Measures an element's content box via ResizeObserver. Uses a *callback ref*
// (not a ref object) so the observer attaches the moment the node mounts —
// important because the measured element is rendered conditionally (after the
// schedule loads), so an on-mount effect would miss it and report height 0.
export function useElementSize<T extends HTMLElement>() {
  const [size, setSize] = useState<Size>({ width: 0, height: 0 });
  const observerRef = useRef<ResizeObserver | null>(null);

  const ref = useCallback((node: T | null) => {
    observerRef.current?.disconnect();
    if (!node) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const { width, height } = entry.contentRect;
        setSize({ width: Math.round(width), height: Math.round(height) });
      }
    });
    observer.observe(node);
    observerRef.current = observer;
  }, []);

  return { ref, ...size };
}
