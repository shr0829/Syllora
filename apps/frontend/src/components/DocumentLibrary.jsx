import React from "react";

export default function DocumentLibrary({
  documents,
  activeDocumentSlug,
  onSelectDocument,
}) {
  return (
    <div className="document-library">
      {documents.map((document) => (
        <button
          key={document.slug}
          type="button"
          className={document.slug === activeDocumentSlug ? "document-button is-active" : "document-button"}
          onClick={() => onSelectDocument(document.slug)}
        >
          <span className="document-name">{document.title}</span>
          <span className="document-path">{document.relativePath}</span>
        </button>
      ))}
    </div>
  );
}
