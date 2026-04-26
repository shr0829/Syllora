import React from "react";

function getStatusLabel(status) {
  if (status === "complete" || status === "fallback") return "已完成";
  if (status === "running") return "进行中";
  if (status === "error") return "失败";
  return "等待中";
}

function getStatusClass(status) {
  if (status === "complete" || status === "fallback") return "is-complete";
  if (status === "running") return "is-running";
  if (status === "error") return "is-error";
  return "is-pending";
}

function fallbackTitle(action) {
  if (action === "pipeline") return "正在生成学习路径";
  if (action === "research") return "正在研究主题资料";
  if (action === "plan") return "正在拆分阶段计划";
  if (action === "lesson") return "正在生成阶段详情";
  if (action === "lesson-batch") return "正在并发生成多个阶段";
  if (action === "chat") return "正在更新项目上下文";
  return "正在处理中";
}

function buildFallbackSteps(project, pendingAction) {
  if (!project) {
    return [];
  }

  if (pendingAction === "pipeline") {
    return [
      {
        id: "research",
        label: "研究主题",
        detail: project.research.status === "ready" ? "研究文档已生成。" : "正在整理主题资料。",
        status: project.research.status === "ready" ? "complete" : "running",
      },
      {
        id: "plan",
        label: "拆分阶段",
        detail: project.plan.status === "ready" ? "阶段计划已生成。" : "等待研究完成后生成。",
        status:
          project.plan.status === "ready"
            ? "complete"
            : project.research.status === "ready"
              ? "running"
              : "pending",
      },
    ];
  }

  return [];
}

export default function GenerationProgress({ project, pendingAction }) {
  if (!project) {
    return null;
  }

  const generation = project.generation ?? {};
  const active = Boolean(generation.active) || Boolean(pendingAction);
  const steps = (generation.steps?.length ? generation.steps : buildFallbackSteps(project, pendingAction)).filter(Boolean);

  if (!active) {
    return null;
  }

  const completedCount = steps.filter((step) => step.status === "complete" || step.status === "fallback").length;
  const runningStep = steps.find((step) => step.status === "running") ?? null;
  const percent = steps.length ? Math.max(8, Math.round((completedCount / steps.length) * 100)) : 12;
  const title = generation.title || fallbackTitle(generation.action || pendingAction);
  const message =
    generation.message ||
    (pendingAction === "pipeline"
      ? "研究和阶段计划会分段落盘，页面会持续刷新最新状态。"
      : "内容生成过程中会自动同步最新状态。");

  return (
    <section className={`generation-panel ${active ? "is-active" : ""}`}>
      <div className="generation-head">
        <div className="generation-head-copy">
          <p className="eyebrow">Live Progress</p>
          <h2>{title}</h2>
          <p>{message}</p>
        </div>
        <div className="generation-metric">
          <strong className="generation-percent">{percent}%</strong>
          <span>{runningStep?.label || (active ? "Streaming" : "Ready")}</span>
        </div>
      </div>

      <div className="generation-progress-shell">
        <div className="generation-progress-track" aria-hidden="true">
          <span
            className={`generation-progress-fill ${active ? "is-active" : ""}`}
            style={{ width: `${percent}%` }}
          />
        </div>

        <div className="generation-progress-meta">
          <span>
            {completedCount}/{steps.length || 0} complete
          </span>
          <span>{runningStep?.label || (active ? "Preparing next segment" : "All synced")}</span>
        </div>
      </div>

      {steps.length ? (
        <div className="generation-step-list">
          {steps.map((step) => (
            <article key={step.id} className={`generation-step ${getStatusClass(step.status)}`}>
              <div className="generation-step-head">
                <strong>
                  <span className={`generation-step-dot ${getStatusClass(step.status)}`} aria-hidden="true" />
                  {step.label}
                </strong>
                <span>{getStatusLabel(step.status)}</span>
              </div>
              <p>{step.detail}</p>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
