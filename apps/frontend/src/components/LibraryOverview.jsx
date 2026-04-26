import React from "react";
import DocumentLibrary from "./DocumentLibrary";
import MarkdownDocument from "./MarkdownDocument";

export default function LibraryOverview({
  library,
  activeDocument,
  onBackToChat,
  onSelectDocument,
  onResolveReference,
}) {
  return (
    <section className="project-page">
      <div className="thread-summary page-summary">
        <div>
          <p className="eyebrow">Knowledge Library</p>
          <h1>{library.title}</h1>
          <p className="hero-copy">{library.description}</p>
        </div>

        <div className="summary-actions">
          <button type="button" onClick={onBackToChat}>
            返回对话
          </button>
        </div>
      </div>

      <div className="library-layout">
        <aside className="context-column">
          <div className="context-card">
            <p className="eyebrow">Documents</p>
            <h3>仓库文档</h3>
            <DocumentLibrary
              documents={library.documents}
              activeDocumentSlug={activeDocument?.slug ?? null}
              onSelectDocument={onSelectDocument}
            />
          </div>
        </aside>

        <section className="main-surface">
          <div className="section-head">
            <div>
              <p className="eyebrow">Parsed Markdown</p>
              <h2>{activeDocument?.title ?? "暂无文档"}</h2>
            </div>
            <span>{activeDocument?.relativePath ?? "未选择"}</span>
          </div>

          {activeDocument ? (
            <>
              <p className="document-path-label">{activeDocument.relativePath}</p>
              <MarkdownDocument document={activeDocument.document} onResolveReference={onResolveReference} />
            </>
          ) : (
            <div className="empty-block">
              <strong>当前资料库没有可展示的 Markdown 文档。</strong>
              <span>你可以先检查对应目录下是否存在 README.md 或其他 Markdown 文件。</span>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
