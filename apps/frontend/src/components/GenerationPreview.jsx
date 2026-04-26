import React from "react";
import MarkdownDocument from "./MarkdownDocument";

function previewLabel(kind) {
  if (kind === "research") return "Research Draft";
  if (kind === "plan") return "Plan Draft";
  if (kind === "lesson") return "Lesson Draft";
  return "Live Draft";
}

function buildPreviewDocument(preview, generationTitle) {
  if (preview?.document) {
    return preview.document;
  }

  const markdown = String(preview?.markdown ?? "").trim();
  if (!markdown) {
    return null;
  }

  const paragraphs = markdown
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter(Boolean);

  return {
    title: preview?.title || generationTitle || "Live Draft",
    intro: paragraphs,
    introBlocks: [],
    sections: [],
  };
}

function PreviewSkeleton({ message }) {
  return (
    <div className="live-preview-skeleton">
      <div className="live-preview-skeleton-line short" />
      <div className="live-preview-skeleton-line" />
      <div className="live-preview-skeleton-line" />
      <div className="live-preview-skeleton-line long" />
      {message ? <p className="live-preview-note">{message}</p> : null}
    </div>
  );
}

export default function GenerationPreview({ project, pendingAction, goalId = null }) {
  if (!project) {
    return null;
  }

  const generation = project.generation ?? {};
  const preview = generation.preview ?? {};
  const isTargetedLesson =
    preview.kind === "lesson" && goalId && generation.targetGoalId && generation.targetGoalId !== goalId;
  const isBatchLessonPreviewOnGoal = preview.kind === "lesson-batch" && goalId;

  if (isTargetedLesson || isBatchLessonPreviewOnGoal) {
    return null;
  }

  const isActive = Boolean(generation.active) || Boolean(pendingAction);
  const hasPreview = Boolean(String(preview.markdown ?? "").trim());

  if (!isActive) {
    return null;
  }

  const document = buildPreviewDocument(preview, generation.title);

  return (
    <section className={`live-preview-panel ${isActive ? "is-active" : ""}`}>
      <div className="live-preview-head">
        <div className="live-preview-title-group">
          <p className="eyebrow">Live Draft</p>
          <h2>{preview.title || generation.title || previewLabel(preview.kind)}</h2>
          <p className="live-preview-note">
            {generation.message || "The system will stream partial content here before the final document settles."}
          </p>
        </div>

        <div className="live-preview-status">
          <span className={`live-status-dot ${isActive ? "is-active" : "is-idle"}`} />
          <strong>{isActive ? "Streaming" : "Synced"}</strong>
        </div>
      </div>

      <div className="live-preview-surface">
        {document ? <MarkdownDocument document={document} /> : <PreviewSkeleton message={generation.message} />}
      </div>

      {isActive ? (
        <div className="live-preview-footer">
          <span className="live-caret" aria-hidden="true" />
          <span>Streaming in segments…</span>
        </div>
      ) : null}
    </section>
  );
}
