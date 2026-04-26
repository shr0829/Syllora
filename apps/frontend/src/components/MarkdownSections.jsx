import React from "react";
import InlineRichText from "./InlineRichText";
import MathFormula from "./MathFormula";

function RichParagraph({ text, onResolveReference }) {
  return (
    <p>
      <InlineRichText text={text} onResolveReference={onResolveReference} />
    </p>
  );
}

function RichList({ items, ordered, onResolveReference }) {
  const ListTag = ordered ? "ol" : "ul";
  return (
    <ListTag>
      {items.map((item) => (
        <li key={item}>
          <InlineRichText text={item} onResolveReference={onResolveReference} />
        </li>
      ))}
    </ListTag>
  );
}

function RichTable({ headers = [], rows = [], onResolveReference }) {
  if (!headers.length) {
    return null;
  }

  return (
    <div className="markdown-table-wrap">
      <table className="markdown-table">
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>
                <InlineRichText text={header} onResolveReference={onResolveReference} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${headers.join("-")}-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${rowIndex}-${cellIndex}`}>
                  <InlineRichText text={cell} onResolveReference={onResolveReference} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function normalizeBlocks(entry) {
  if (entry?.blocks?.length) {
    return entry.blocks;
  }

  return [
    ...(entry?.paragraphs ?? []).map((paragraph) => ({ type: "paragraph", text: paragraph })),
    ...(entry?.tables ?? []).map((table) => ({ type: "table", ...table })),
    ...((entry?.bullets ?? []).length ? [{ type: "list", ordered: false, items: entry.bullets }] : []),
  ];
}

export function MarkdownBlocks({ entry, onResolveReference }) {
  return normalizeBlocks(entry).map((block, index) => {
    if (block.type === "paragraph") {
      return <RichParagraph key={`p-${index}-${block.text}`} text={block.text} onResolveReference={onResolveReference} />;
    }

    if (block.type === "list") {
      return (
        <RichList
          key={`l-${index}`}
          items={block.items ?? []}
          ordered={Boolean(block.ordered)}
          onResolveReference={onResolveReference}
        />
      );
    }

    if (block.type === "table") {
      return (
        <RichTable
          key={`t-${index}`}
          headers={block.headers ?? []}
          rows={block.rows ?? []}
          onResolveReference={onResolveReference}
        />
      );
    }

    if (block.type === "math") {
      return <MathFormula key={`m-${index}`} formula={block.text ?? ""} display />;
    }

    return null;
  });
}

export default function MarkdownSections({ sections, onResolveReference }) {
  return (
    <div className="markdown-sections">
      {sections.map((section) => (
        <section key={section.title} className="markdown-section">
          <h3>{section.title}</h3>
          <MarkdownBlocks entry={section} onResolveReference={onResolveReference} />

          {(section.subsections ?? []).map((subsection) => (
            <div key={subsection.title} className="markdown-subsection">
              <h4>{subsection.title}</h4>
              <MarkdownBlocks entry={subsection} onResolveReference={onResolveReference} />
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}
