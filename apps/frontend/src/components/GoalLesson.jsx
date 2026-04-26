import React from "react";
import GenerationProgress from "./GenerationProgress";
import GenerationPreview from "./GenerationPreview";
import MarkdownDocument from "./MarkdownDocument";

function statusText(status, readyText, pendingText, errorText = "生成失败") {
  if (status === "ready" || status === "complete" || status === "fallback") return readyText;
  if (status === "running" || status === "pending") return pendingText;
  if (status === "error") return errorText;
  return "尚未生成";
}

export default function GoalLesson({
  project,
  goal,
  pendingAction,
  onBackToProject,
  onGenerateLesson,
}) {
  const document = goal.lesson?.document ?? null;
  const images = goal.lesson?.images ?? (goal.lesson?.image ? [goal.lesson.image] : []);
  const isGenerating =
    pendingAction === "lesson" || goal.lessonStatus === "running" || goal.imageStatus === "running";
  const inlineFigures = images
    .filter(Boolean)
    .map((figure, index) => ({
      ...figure,
      status: figure?.status || goal.imageStatus || "idle",
      title:
        figure?.title ||
        `${goal.stageLabel || `阶段 ${goal.stageNumber}`} 图示${images.length > 1 ? ` ${index + 1}` : ""}`,
      caption:
        figure?.caption ||
        (figure?.status === "running" || goal.imageStatus === "running"
          ? "图示与正文并发生成，完成后会自动刷新到当前页面。"
          : "图示与正文保持同一阅读流，支持点击放大查看。"),
    }));

  return (
    <section className="lesson-page">
      <div className="thread-summary page-summary lesson-summary">
        <div>
          <p className="eyebrow">Stage Detail</p>
          <h1 className="summary-title summary-title-lesson">{goal.title}</h1>
          <p className="hero-copy summary-copy">
            {goal.summary || "这里展示单个阶段的详细讲解、知识点拆解、公式说明与多张图示。"}
          </p>

          <div className="status-chip-row">
            <span className="status-chip">
              正文：{statusText(goal.lessonStatus, "已生成", "生成中")}
            </span>
            <span className="status-chip">
              图示：{statusText(goal.imageStatus, "已生成", "生成中")}
            </span>
            <span className="status-chip">预计时长：{goal.estimatedTime || "待补充"}</span>
          </div>
        </div>

        <div className="summary-actions">
          <button type="button" onClick={onBackToProject}>
            返回项目页
          </button>
          <button type="button" className="primary" onClick={onGenerateLesson} disabled={Boolean(pendingAction)}>
            {pendingAction === "lesson" ? "生成中..." : document ? "重新生成" : "生成阶段详情"}
          </button>
        </div>
      </div>

      <GenerationProgress project={project} pendingAction={pendingAction} />
      {project.generation?.action !== "lesson-batch" ? (
        <GenerationPreview project={project} pendingAction={pendingAction} goalId={goal.id} />
      ) : null}

      <div className="lesson-stack">
        <section className="main-surface lesson-surface">
          {document ? (
            <MarkdownDocument document={document} inlineFigures={inlineFigures} />
          ) : (
            <div className="empty-block lesson-empty">
              <strong>{isGenerating ? "系统正在生成阶段讲解..." : "当前还没有阶段正文"}</strong>
              <span>
                进入阶段后，系统会先流式写入正文，再并发生成多张讲解图示；如果包含公式，页面也会直接渲染。
              </span>
            </div>
          )}
        </section>

        <section className="lesson-meta-grid">
          <div className="context-card">
            <p className="eyebrow">Metadata</p>
            <h3>阶段信息</h3>
            <ul className="simple-list">
              <li>所属项目：{project.topic}</li>
              <li>阶段标签：{goal.stageLabel || `阶段 ${goal.stageNumber}`}</li>
              <li>预计时长：{goal.estimatedTime || "未设置"}</li>
              <li>完成标志：{goal.outcome || "查看正文"}</li>
            </ul>
          </div>

          <div className="context-card">
            <p className="eyebrow">Delivery</p>
            <h3>当前状态</h3>
            <ul className="simple-list">
              <li>正文：{statusText(goal.lessonStatus, "可直接阅读", "正在生成中")}</li>
              <li>图示：{statusText(goal.imageStatus, "已插入正文流", "正在并发生成")}</li>
              <li>学习动作：{goal.tasks?.length || 0} 项</li>
              <li>阶段产出：{goal.deliverables?.length || 0} 项</li>
            </ul>
          </div>
        </section>
      </div>
    </section>
  );
}
