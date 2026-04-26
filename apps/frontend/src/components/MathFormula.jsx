import React, { useEffect, useRef, useState } from "react";

let mathJaxLoader = null;

function loadMathJax() {
  if (typeof window === "undefined") {
    return Promise.resolve(null);
  }

  if (window.MathJax?.typesetPromise) {
    const startupPromise = window.MathJax?.startup?.promise;
    return startupPromise?.then ? startupPromise.then(() => window.MathJax) : Promise.resolve(window.MathJax);
  }

  if (mathJaxLoader) {
    return mathJaxLoader;
  }

  mathJaxLoader = new Promise((resolve, reject) => {
    window.MathJax = window.MathJax || {
      tex: {
        inlineMath: [["$", "$"], ["\\(", "\\)"]],
        displayMath: [["$$", "$$"], ["\\[", "\\]"]],
      },
      svg: { fontCache: "global" },
      startup: {
        typeset: false,
      },
    };

    const existingScript = document.querySelector('script[data-mathjax="learning-package"]');
    if (existingScript) {
      existingScript.addEventListener(
        "load",
        () => {
          const startupPromise = window.MathJax?.startup?.promise;
          if (startupPromise?.then) {
            startupPromise.then(() => resolve(window.MathJax)).catch(reject);
            return;
          }
          resolve(window.MathJax);
        },
        { once: true },
      );
      existingScript.addEventListener("error", reject, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js";
    script.async = true;
    script.dataset.mathjax = "learning-package";
    script.onload = () => {
      const startupPromise = window.MathJax?.startup?.promise;
      if (startupPromise?.then) {
        startupPromise.then(() => resolve(window.MathJax)).catch(reject);
        return;
      }
      resolve(window.MathJax);
    };
    script.onerror = reject;
    document.head.appendChild(script);
  });

  return mathJaxLoader;
}

export default function MathFormula({ formula, display = false }) {
  const containerRef = useRef(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function typeset() {
      const element = containerRef.current;
      if (!element) {
        return;
      }

      element.textContent = display ? `\\[${formula}\\]` : `\\(${formula}\\)`;
      try {
        const mathJax = await loadMathJax();
        if (cancelled || !mathJax?.typesetPromise || !element) {
          return;
        }
        await mathJax.typesetPromise([element]);
        if (!cancelled) {
          setReady(true);
        }
      } catch {
        if (!cancelled) {
          setReady(false);
        }
      }
    }

    setReady(false);
    typeset().catch(() => null);

    return () => {
      cancelled = true;
    };
  }, [display, formula]);

  if (display) {
    return (
      <div className={`math-block ${ready ? "is-rendered" : "is-fallback"}`}>
        <div ref={containerRef} className="math-block-surface" />
        {!ready ? <code className="math-fallback">{formula}</code> : null}
      </div>
    );
  }

  return (
    <span className={`math-inline ${ready ? "is-rendered" : "is-fallback"}`}>
      <span ref={containerRef} className="math-inline-surface" />
      {!ready ? <code className="math-fallback">{formula}</code> : null}
    </span>
  );
}
