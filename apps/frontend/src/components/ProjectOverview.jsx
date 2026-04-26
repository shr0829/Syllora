import React from "react";
import GenerationProgress from "./GenerationProgress";
import GenerationPreview from "./GenerationPreview";

function firstParagraph(document) {
  if (!document) {
    return "";
  }

  const firstSection = document.sections?.[0];
  return firstSection?.paragraphs?.[0] || document.intro?.[0] || "";
}

function shortenPath(filePath) {
  if (!filePath) {
    return "未生成";
  }
  const normalized = filePath.replace(/\\/g, "/");
  if (normalized.length <= 56) {
    return normalized;
  }
  return `...${normalized.slice(-56)}`;
}

function stageStatus(goal) {
  if (goal.lessonStatus === "running") {
    return goal.lesson?.document ? "正文流式生成中" : "准备生成中";
  }
  if (goal.lessonStatus === "ready" && goal.imageStatus === "running") {
    return "正文已完成，图示并发生成中";
  }
  if (goal.lessonStatus === "ready") {
    return "阶段详情已完成";
  }
  if (goal.lessonStatus === "error") {
    return "生成失败，可重试";
  }
  return "等待生成";
}

function imageStatus(goal) {
  if (goal.imageStatus === "ready" || goal.imageStatus === "fallback") {
    return "已完成";
  }
  if (goal.imageStatus === "running" || goal.imageStatus === "pending") {
    return "生成中";
  }
  if (goal.imageStatus === "error") {
    return "失败";
  }
  return "待生成";
}

function stageExcerpt(goal) {
  return firstParagraph(goal.lesson?.document) || goal.summary || "";
}

export default function ProjectOverview({
  project,
  pendingAction,
  onBackToChat,
  onRunResearch,
  onRunPlan,
  onGenerateAllLessons,
  onOpenGoal,
}) {
  const goals = project.goals ?? [];
  const researchSummary = firstParagraph(project.research.document);
  const sources = project.research.sources ?? [];
  const readyGoals = goals.filter((goal) => goal.lessonStatus === "ready").length;
  const runningGoals = goals.filter(
    (goal) => goal.lessonStatus === "running" || goal.imageStatus === "running",
  ).length;
  const hasActiveGeneration = Boolean(project.generation?.active);
  const batchEnabled = project.plan.status === "ready" && goals.length > 0 && !pendingAction && !hasActiveGeneration;

  return (
    <section className="project-page">
      <div className="thread-summary page-summary">
        <div>
          <p className="eyebrow">Learning Project</p>
          <h1 className="summary-title summary-title-page">{project.topic}</h1>
          <p className="hero-copy summary-copy">
            这里聚合研究文档、阶段计划和每个阶段的生成进度。批量生成时，正文和图示会并发推进，并且按阶段分段刷新。
          </p>
        </div>

        <div className="summary-actions">
          <button type="button" onClick={onBackToChat}>
            返回对话
          </button>
          <button type="button" onClick={onRunResearch} disabled={Boolean(pendingAction) || hasActiveGeneration}>
            {pendingAction === "research" ? "研究中..." : "刷新研究"}
          </button>
          <button
            type="button"
            onClick={onRunPlan}
            disabled={project.research.status !== "ready" || Boolean(pendingAction) || hasActiveGeneration}
          >
            {pendingAction === "plan" ? "生成中..." : "更新阶段"}
          </button>
          <button type="button" className="primary" onClick={onGenerateAllLessons} disabled={!batchEnabled}>
            {pendingAction === "lesson-batch" ? "并发生成中..." : "并发生成全部阶段"}
          </button>
        </div>
      </div>

      <GenerationProgress project={project} pendingAction={pendingAction} />
      <GenerationPreview project={project} pendingAction={pendingAction} />

      <div className="project-grid">
        <section className="main-surface">
          <div className="section-head">
            <div>
              <p className="eyebrow">Stages</p>
              <h2>按阶段推进学习</h2>
            </div>
            <span>
              已完成 {readyGoals}/{goals.length || 0}
              {runningGoals ? ` · 进行中 ${runningGoals}` : ""}
            </span>
          </div>

          <div className="stage-list">
            {goals.length ? (
              goals.map((goal) => {
                const excerpt = stageExcerpt(goal);
                return (
                  <article key={goal.id} className="stage-item">
                    <div className="stage-item-head">
                      <span>{goal.stageLabel || `阶段 ${goal.stageNumber}`}</span>
                      <strong>{stageStatus(goal)}</strong>
                    </div>

                    <div className="stage-item-main">
                      <div className="stage-copy">
                        <h3>{goal.title}</h3>
                        <p className="stage-summary">
                          {goal.summary || "系统会围绕这个阶段生成结构化讲解、知识点拆解、公式说明与多张图示。"}
                        </p>
                      </div>

                      <button type="button" className="stage-cta primary" onClick={() => onOpenGoal(goal.id)}>
                        {goal.lessonStatus === "ready" || goal.lessonStatus === "running"
                          ? "打开阶段"
                          : "生成并打开"}
                      </button>
                    </div>

                    {excerpt ? (
                      <div className="stage-live-preview">
                        <span className="stage-live-label">
                          {goal.lessonStatus === "running" ? "实时草稿" : "阶段摘录"}
                        </span>
                        <p>{excerpt}</p>
                      </div>
                    ) : null}

                    <div className="stage-inline-meta compact-meta">
                      <span>{goal.estimatedTime || "时长待定"}</span>
                      <span>{goal.tasks?.length || 0} 个学习动作</span>
                      <span>图示：{imageStatus(goal)}</span>
                    </div>
                  </article>
                );
              })
            ) : (
              <div className="empty-block">
                <strong>还没有阶段</strong>
                <span>先完成研究，再点击“更新阶段”生成学习路径。</span>
              </div>
            )}
          </div>
        </section>

        <aside className="context-column">
          <div className="context-card">
            <p className="eyebrow">Snapshot</p>
            <h3>项目快照</h3>
            <ul className="simple-list">
              <li>研究：{project.research.status}</li>
              <li>阶段计划：{project.plan.status}</li>
              <li>资料来源：{project.research.sourceCount || 0} 条</li>
              <li>阶段索引：{shortenPath(project.plan.stageIndexPath)}</li>
            </ul>
          </div>

          <div className="context-card">
            <p className="eyebrow">Research</p>
            <h3>研究摘要</h3>
            <p>
              {researchSummary ||
                "当前还没有研究摘要。配置真实 API 后，系统会自动联网检索并整理成可解析的研究文档。"}
            </p>

            {sources.length ? (
              <ul className="source-list compact compact-inline">
                {sources.slice(0, 3).map((source) => (
                  <li key={source.url}>
                    <a className="source-link" href={source.url} target="_blank" rel="noreferrer">
                      {source.title || source.url}
                    </a>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </aside>
      </div>
    </section>
  );
}
