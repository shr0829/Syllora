import React from "react";
import MathFormula from "./MathFormula";

const INLINE_TOKEN_PATTERN = /(\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`|\$([^$\n]+?)\$)/g;

function renderTextSegment(text, keyBase) {
  if (!text) {
    return null;
  }
  return <React.Fragment key={keyBase}>{text}</React.Fragment>;
}

export default function InlineRichText({ text, onResolveReference }) {
  if (!text) {
    return null;
  }

  const nodes = [];
  let lastIndex = 0;
  let matchIndex = 0;
  let match;

  while ((match = INLINE_TOKEN_PATTERN.exec(text)) !== null) {
    const [raw, , markdownLabel, markdownHref, codeValue, mathValue] = match;
    const startIndex = match.index;

    if (startIndex > lastIndex) {
      nodes.push(renderTextSegment(text.slice(lastIndex, startIndex), `text-${matchIndex}`));
    }

    if (markdownLabel && markdownHref) {
      const resolved =
        onResolveReference?.(markdownHref) ??
        (/^https?:\/\//i.test(markdownHref) ? { type: "external", href: markdownHref } : null);
      if (resolved?.type === "external") {
        nodes.push(
          <a
            key={`link-${matchIndex}`}
            className="inline-doc-link"
            href={resolved.href}
            target="_blank"
            rel="noreferrer"
          >
            {markdownLabel}
          </a>,
        );
      } else if (resolved?.type === "library-document") {
        nodes.push(
          <button
            key={`link-${matchIndex}`}
            type="button"
            className="inline-doc-link inline-doc-link-button"
            onClick={() => onResolveReference?.(markdownHref, { navigate: true })}
          >
            {markdownLabel}
          </button>,
        );
      } else {
        nodes.push(<span key={`link-${matchIndex}`}>{raw}</span>);
      }
    } else if (codeValue) {
      const resolved = onResolveReference?.(codeValue);
      if (resolved?.type === "library-document") {
        nodes.push(
          <button
            key={`code-${matchIndex}`}
            type="button"
            className="inline-doc-link inline-doc-link-code"
            onClick={() => onResolveReference?.(codeValue, { navigate: true })}
          >
            <code>{codeValue}</code>
          </button>,
        );
      } else {
        nodes.push(
          <code key={`code-${matchIndex}`} className="inline-code">
            {codeValue}
          </code>,
        );
      }
    } else if (mathValue) {
      nodes.push(<MathFormula key={`math-${matchIndex}`} formula={mathValue.trim()} />);
    }

    lastIndex = startIndex + raw.length;
    matchIndex += 1;
  }

  if (lastIndex < text.length) {
    nodes.push(renderTextSegment(text.slice(lastIndex), "text-tail"));
  }

  return nodes;
}
