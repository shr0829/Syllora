import React from "react";

export default function LearningSidebar({
  projects,
  libraries,
  activeProjectId,
  activeLibraryId,
  onSelectProject,
  onSelectLibrary,
  onStartNew,
  llm,
  contextLabel,
}) {
  const activeProject = projects.find((project) => project.id === activeProjectId) ?? null;
  const subtitle =
    contextLabel ||
    (llm.configured ? `${llm.model} · ${llm.imageModel}` : "本地模板模式 · 可直接预览流程");

  return (
    <header className="sidebar app-header">
      <button type="button" className="app-header-brand" onClick={onStartNew} title="返回首页">
        <span className="brand-mark">SY</span>
        <span className="app-header-copy">
          <strong>Syllora</strong>
          <span>{subtitle}</span>
        </span>
      </button>

      <div className="app-header-actions">
        {activeProject ? (
          <button type="button" className="header-pill is-active header-current-pill" onClick={() => onSelectProject(activeProject.id)}>
            <strong>{activeProject.topic}</strong>
            <span>{activeProject.goalsCount || 0} 阶段</span>
          </button>
        ) : null}

        {libraries[0] ? (
          <button
            type="button"
            className={libraries[0].id === activeLibraryId ? "header-action is-active" : "header-action"}
            onClick={() => onSelectLibrary(libraries[0].id)}
          >
            资料库
          </button>
        ) : null}

        <button type="button" className="header-action primary" onClick={onStartNew}>
          新主题
        </button>
      </div>
    </header>
  );
}
