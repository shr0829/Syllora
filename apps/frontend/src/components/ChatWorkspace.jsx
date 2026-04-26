import React from "react";
import GenerationProgress from "./GenerationProgress";
import GenerationPreview from "./GenerationPreview";

const QUICK_PROMPTS = [
  "我想系统学习 RAG，最后做一个可运行的检索问答 Demo。",
  "我想学 AI Agent，希望从工具调用到评测都拆成阶段。",
  "我想补齐 Transformer 基础，再过渡到 LLM 应用。",
];

function formatRole(role) {
  return role === "assistant" ? "LearningPackage" : "你";
}

function StartPanel({
  composerValue,
  onComposerChange,
  onSubmit,
  pendingAction,
  projects,
  onSelectProject,
}) {
  return (
    <section className="workspace workspace-home">
      <div className="hero-shell">
        <p className="eyebrow">AI Learning Workspace</p>
        <h1 className="hero-title">
          说出你想学什么，
          <br />
          我来帮你拆成阶段路径。
        </h1>
        <p className="hero-copy hero-copy-center">
          系统会先研究主题，再生成阶段计划；当你点开某个阶段时，再补全这一阶段的详细讲解和图示。
        </p>

        <form className="hero-composer" onSubmit={onSubmit}>
          <textarea
            value={composerValue}
            onChange={(event) => onComposerChange(event.target.value)}
            placeholder="例如：我想从零系统学习 RAG，最后做一个可运行的检索问答 Demo。"
            rows={4}
          />
          <div className="hero-actions">
            <button type="submit" disabled={!composerValue.trim() || Boolean(pendingAction)}>
              {pendingAction === "pipeline" ? "正在生成学习路径..." : "开始生成"}
            </button>
          </div>
        </form>

        <div className="quick-prompt-row">
          {QUICK_PROMPTS.map((prompt) => (
            <button key={prompt} type="button" className="quick-prompt" onClick={() => onComposerChange(prompt)}>
              {prompt}
            </button>
          ))}
        </div>
      </div>

      <section className="recent-strip">
        <div className="section-head section-head-start">
          <div>
            <p className="eyebrow">Recent Projects</p>
            <h2>继续最近的学习主题</h2>
          </div>
        </div>

        <div className="recent-row">
          {projects.length ? (
            projects.slice(0, 4).map((project) => (
              <button
                key={project.id}
                type="button"
                className="recent-card"
                onClick={() => onSelectProject(project.id)}
              >
                <strong>{project.topic}</strong>
                <span>{project.goalsCount || 0} 阶段</span>
              </button>
            ))
          ) : (
            <div className="empty-block">
              <strong>还没有学习主题</strong>
              <span>从上方输入框开始，先建立第一个学习仓库。</span>
            </div>
          )}
        </div>
      </section>
    </section>
  );
}

export default function ChatWorkspace({
  composerValue,
  onComposerChange,
  onSubmit,
  activeProject,
  pendingAction,
  onRunResearch,
  onRunPlan,
  onOpenProject,
  projects,
  onSelectProject,
}) {
  const messages = activeProject?.conversation ?? [];

  if (!activeProject) {
    return (
      <StartPanel
        composerValue={composerValue}
        onComposerChange={onComposerChange}
        onSubmit={onSubmit}
        pendingAction={pendingAction}
        projects={projects}
        onSelectProject={onSelectProject}
      />
    );
  }

  return (
    <section className="workspace workspace-thread">
      <div className="thread-summary compact-summary">
        <div>
          <p className="eyebrow">Current Project</p>
          <h1 className="summary-title summary-title-thread">{activeProject.topic}</h1>
          <p className="hero-copy summary-copy">
            {activeProject.research.status === "ready" ? "研究已完成" : "等待研究"} ·{" "}
            {activeProject.plan.status === "ready" ? "阶段已生成" : "等待阶段计划"} ·{" "}
            {activeProject.goals.length || 0} 个阶段
          </p>
        </div>

        <div className="summary-actions">
          <button type="button" onClick={onRunResearch} disabled={Boolean(pendingAction)}>
            {pendingAction === "research" ? "研究中..." : "刷新研究"}
          </button>
          <button
            type="button"
            onClick={onRunPlan}
            disabled={activeProject.research.status !== "ready" || Boolean(pendingAction)}
          >
            {pendingAction === "plan" ? "生成中..." : "更新阶段"}
          </button>
          <button type="button" className="primary" onClick={onOpenProject} disabled={Boolean(pendingAction)}>
            打开项目页
          </button>
        </div>
      </div>

      <GenerationProgress project={activeProject} pendingAction={pendingAction} />
      <GenerationPreview project={activeProject} pendingAction={pendingAction} />

      <section className="thread-card">
        <div className="chat-thread">
          {messages.map((message) => (
            <article
              key={message.id}
              className={message.role === "assistant" ? "chat-message is-assistant" : "chat-message is-user"}
            >
              <div className="chat-meta">
                <strong>{formatRole(message.role)}</strong>
                <span>{new Date(message.createdAt).toLocaleString("zh-CN")}</span>
              </div>
              <p>{message.content}</p>
            </article>
          ))}
        </div>

        <form className="thread-composer" onSubmit={onSubmit}>
          <textarea
            value={composerValue}
            onChange={(event) => onComposerChange(event.target.value)}
            placeholder="继续补充目标、限制条件或你想要的最终产出。"
            rows={4}
          />
          <div className="thread-composer-actions">
            <span>补充对话会更新学习上下文，但不会覆盖已落盘的文件。</span>
            <button type="submit" disabled={!composerValue.trim() || Boolean(pendingAction)}>
              {pendingAction === "chat" ? "发送中..." : "发送"}
            </button>
          </div>
        </form>
      </section>
    </section>
  );
}
