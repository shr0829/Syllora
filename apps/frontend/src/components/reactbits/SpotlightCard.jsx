import React, { useRef } from "react";
import "./SpotlightCard.css";

// Adapted from React Bits: src/ts-default/Components/SpotlightCard/SpotlightCard.tsx
export default function SpotlightCard({
  children,
  className = "",
  spotlightColor = "rgba(37, 99, 235, 0.16)",
}) {
  const cardRef = useRef(null);

  function handleMouseMove(event) {
    if (!cardRef.current) {
      return;
    }

    const rect = cardRef.current.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    cardRef.current.style.setProperty("--mouse-x", `${x}px`);
    cardRef.current.style.setProperty("--mouse-y", `${y}px`);
    cardRef.current.style.setProperty("--spotlight-color", spotlightColor);
  }

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      className={`card-spotlight ${className}`.trim()}
    >
      {children}
    </div>
  );
}
