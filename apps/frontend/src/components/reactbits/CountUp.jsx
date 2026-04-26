import React, { useEffect, useRef } from "react";
import { useInView, useMotionValue, useSpring } from "motion/react";

// Adapted from React Bits: src/ts-default/TextAnimations/CountUp/CountUp.tsx
export default function CountUp({
  to,
  from = 0,
  direction = "up",
  delay = 0,
  duration = 2,
  className = "",
  startWhen = true,
  separator = "",
}) {
  const ref = useRef(null);
  const motionValue = useMotionValue(direction === "down" ? to : from);
  const damping = 20 + 40 * (1 / duration);
  const stiffness = 100 * (1 / duration);
  const springValue = useSpring(motionValue, { damping, stiffness });
  const isInView = useInView(ref, { once: true, margin: "0px" });

  function getDecimalPlaces(numberValue) {
    const stringValue = numberValue.toString();
    if (!stringValue.includes(".")) {
      return 0;
    }

    const decimals = stringValue.split(".")[1];
    return Number.parseInt(decimals, 10) !== 0 ? decimals.length : 0;
  }

  const maxDecimals = Math.max(getDecimalPlaces(from), getDecimalPlaces(to));

  function formatValue(latest) {
    const hasDecimals = maxDecimals > 0;
    const options = {
      useGrouping: Boolean(separator),
      minimumFractionDigits: hasDecimals ? maxDecimals : 0,
      maximumFractionDigits: hasDecimals ? maxDecimals : 0,
    };

    const formattedNumber = Intl.NumberFormat("en-US", options).format(latest);
    return separator ? formattedNumber.replace(/,/g, separator) : formattedNumber;
  }

  useEffect(() => {
    if (ref.current) {
      ref.current.textContent = formatValue(direction === "down" ? to : from);
    }
  }, [direction, from, to]);

  useEffect(() => {
    if (!isInView || !startWhen) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      motionValue.set(direction === "down" ? from : to);
    }, delay * 1000);

    return () => window.clearTimeout(timeoutId);
  }, [delay, direction, from, isInView, motionValue, startWhen, to]);

  useEffect(() => {
    const unsubscribe = springValue.on("change", (latest) => {
      if (ref.current) {
        ref.current.textContent = formatValue(latest);
      }
    });

    return () => unsubscribe();
  }, [springValue]);

  return <span className={className} ref={ref} />;
}
