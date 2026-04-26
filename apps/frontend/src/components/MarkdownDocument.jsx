import React, { useState } from "react";
import InlineRichText from "./InlineRichText";
import MarkdownSections, { MarkdownBlocks } from "./MarkdownSections";

function buildFallbackBlocks(lines = []) {
  return lines
    .flatMap((line) => String(line || "").split(/(?=##\s|###\s)/g))
    .map((line) => line.trim())
    .filter((line) => Boolean(line) && line !== "#")
    .flatMap((line, index) => {
      function splitHeadingText(text) {
        const rawText = text.trim();
        const separatorIndex = rawText.lastIndexOf(" ");
        if (separatorIndex <= 0) {
          return { heading: rawText, body: null };
        }

        const heading = rawText.slice(0, separatorIndex).trim();
        const body = rawText.slice(separatorIndex + 1).trim();
        const shouldSplit = body.length >= 8 || /[。；，：、]/.test(body);
        return shouldSplit ? { heading, body } : { heading: rawText, body: null };
      }

      if (line.startsWith("### ")) {
        const { heading, body } = splitHeadingText(line.replace(/^###\s+/, ""));
        return [
          { key: `h4-${index}`, type: "h4", text: heading },
          ...(body ? [{ key: `h4-body-${index}`, type: "p", text: body }] : []),
        ];
      }
      if (line.startsWith("## ")) {
        const { heading, body } = splitHeadingText(line.replace(/^##\s+/, ""));
        return [
          { key: `h3-${index}`, type: "h3", text: heading },
          ...(body ? [{ key: `h3-body-${index}`, type: "p", text: body }] : []),
        ];
      }
      return { key: `p-${index}`, type: "p", text: line };
    });
}

function FallbackIntro({ lines, onResolveReference }) {
  const blocks = buildFallbackBlocks(lines);

  if (!blocks.length) {
    return null;
  }

  return (
    <div className="markdown-fallback">
      {blocks.map((block) => {
        if (block.type === "h3") {
          return <h3 key={block.key}>{block.text}</h3>;
        }
        if (block.type === "h4") {
          return <h4 key={block.key}>{block.text}</h4>;
        }
        return (
          <p key={block.key}>
            <InlineRichText text={block.text} onResolveReference={onResolveReference} />
          </p>
        );
      })}
    </div>
  );
}

function DocumentFigure({ figure, onOpen }) {
  if (!figure) {
    return null;
  }

  const isReady = Boolean(figure.url);
  const isRunning = figure.status === "running" || figure.status === "pending";
  const isFallback = figure.status === "fallback";

  return (
    <figure className="document-figure">
      <div className="document-figure-head">
        <div>
          <p className="eyebrow">Diagram</p>
          <strong>{figure.title || "阶段图示"}</strong>
        </div>
        {isReady ? <span className="figure-hint">点击图片放大</span> : null}
      </div>

      {isReady ? (
        <button type="button" className="document-figure-button" onClick={onOpen}>
          <img className="document-figure-image" src={figure.url} alt={figure.alt || figure.title || "图示"} />
        </button>
      ) : (
        <div className="image-placeholder document-figure-placeholder">
          <strong>
            {isRunning
              ? "图示生成中..."
              : figure.status === "error"
                ? "图示生成失败"
                : isFallback
                  ? "已切换为占位图示"
                  : "图示尚未生成"}
          </strong>
          <span>
            {isRunning
              ? "正文可以先阅读，图示完成后会自动刷新到这里。"
              : isFallback
                ? "当前使用稳定的占位图示，后续可以再次触发真实生图。"
                : "图示会直接插入到正文流中，便于边看边学。"}
          </span>
        </div>
      )}

      {figure.caption ? <figcaption>{figure.caption}</figcaption> : null}
    </figure>
  );
}

function Lightbox({ figure, onClose }) {
  if (!figure?.url) {
    return null;
  }

  return (
    <div className="media-lightbox" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="media-lightbox-dialog" onClick={(event) => event.stopPropagation()}>
        <button type="button" className="media-lightbox-close" onClick={onClose}>
          关闭
        </button>
        <img className="media-lightbox-image" src={figure.url} alt={figure.alt || figure.title || "图示"} />
      </div>
    </div>
  );
}

export default function MarkdownDocument({
  document,
  onResolveReference,
  inlineFigure = null,
  inlineFigures = null,
}) {
  const [activeFigureIndex, setActiveFigureIndex] = useState(null);

  if (!document) {
    return null;
  }

  const hasSections = Boolean(document.sections?.length);
  const figures = (Array.isArray(inlineFigures) && inlineFigures.length ? inlineFigures : [inlineFigure]).filter(Boolean);
  const activeFigure = activeFigureIndex === null ? null : figures[activeFigureIndex] ?? null;

  return (
    <>
      <div className="document-view">
        <header className="document-head">
          <h2>{document.title}</h2>
          {document.introBlocks?.length ? (
            <div className="document-intro">
              <MarkdownBlocks
                entry={{ blocks: document.introBlocks, paragraphs: document.intro ?? [] }}
                onResolveReference={onResolveReference}
              />
            </div>
          ) : document.intro?.length && !hasSections ? (
            <FallbackIntro lines={document.intro} onResolveReference={onResolveReference} />
          ) : document.intro?.length ? (
            <div className="document-intro">
              {document.intro.map((paragraph) => (
                <p key={paragraph}>
                  <InlineRichText text={paragraph} onResolveReference={onResolveReference} />
                </p>
              ))}
            </div>
          ) : null}
        </header>

        {figures.length ? (
          <div className={`document-figure-stack ${figures.length > 1 ? "is-gallery" : ""}`}>
            {figures.map((figure, index) => (
              <DocumentFigure
                key={`${figure.url || figure.title || "figure"}-${index}`}
                figure={figure}
                onOpen={() => setActiveFigureIndex(index)}
              />
            ))}
          </div>
        ) : null}

        <MarkdownSections sections={document.sections ?? []} onResolveReference={onResolveReference} />
      </div>

      {activeFigure ? <Lightbox figure={activeFigure} onClose={() => setActiveFigureIndex(null)} /> : null}
    </>
  );
}
