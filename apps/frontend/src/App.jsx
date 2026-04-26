import React, { useEffect, useMemo, useState } from "react";
import ChatWorkspace from "./components/ChatWorkspace";
import GoalLesson from "./components/GoalLesson";
import LearningSidebar from "./components/LearningSidebar";
import LibraryOverview from "./components/LibraryOverview";
import ProjectOverview from "./components/ProjectOverview";
import {
  createProject,
  fetchLibraries,
  fetchLibrary,
  fetchProject,
  fetchProjects,
  generateLesson,
  generateLessonBatch,
  generatePlan,
  generateResearch,
  sendProjectMessage,
  subscribeProjectEvents,
} from "./lib/api";
import { resolveLibraryReference } from "./lib/libraryNavigation";

function deriveTopicFromMessage(message) {
  const normalized = message.trim().replace(/\s+/g, " ");
  return normalized.slice(0, 24) || "新学习项目";
}

function summarizeProject(project) {
  const conversation = project?.conversation ?? [];
  const lastAssistantMessage =
    [...conversation].reverse().find((message) => message.role === "assistant")?.content ?? "";

  return {
    id: project.id,
    folderName: project.folderName,
    topic: project.topic,
    createdAt: project.createdAt,
    updatedAt: project.updatedAt,
    researchStatus: project.research?.status ?? "idle",
    planStatus: project.plan?.status ?? "idle",
    generationActive: Boolean(project.generation?.active),
    generationAction: project.generation?.action ?? null,
    goalsCount: project.goals?.length ?? 0,
    lessonReadyCount: (project.goals ?? []).filter((goal) => goal.lessonStatus === "ready").length,
    sourceCount: project.research?.sourceCount ?? 0,
    lastAssistantMessage,
  };
}

export default function App() {
  const [projects, setProjects] = useState([]);
  const [libraries, setLibraries] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [activeGoalId, setActiveGoalId] = useState(null);
  const [activeLibrary, setActiveLibrary] = useState(null);
  const [activeLibraryDocumentSlug, setActiveLibraryDocumentSlug] = useState(null);
  const [currentView, setCurrentView] = useState("chat");
  const [composerValue, setComposerValue] = useState("");
  const [pendingAction, setPendingAction] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [llm, setLlm] = useState({ configured: false, model: "未配置", imageModel: "未配置" });
  const [liveConnectionState, setLiveConnectionState] = useState("idle");

  async function refreshWorkspace(preferredProjectId = null) {
    const [projectsPayload, librariesPayload] = await Promise.all([fetchProjects(), fetchLibraries()]);
    setProjects(projectsPayload.projects);
    setLibraries(librariesPayload.libraries);
    setLlm(projectsPayload.llm);

    const nextProjectId = preferredProjectId ?? activeProject?.id ?? null;
    if (!nextProjectId) {
      setActiveProject(null);
      return;
    }

    const projectPayload = await fetchProject(nextProjectId);
    setActiveProject(projectPayload.project);
    setLlm(projectPayload.llm);
  }

  async function refreshLiveProject(projectId) {
    return Promise.all([fetchProjects(), fetchProject(projectId)]);
  }

  useEffect(() => {
    async function loadInitialState() {
      const params = new URLSearchParams(window.location.search);
      const projectId = params.get("project");
      const goalId = params.get("goal");
      const libraryId = params.get("library");
      const view = params.get("view");

      const [projectsPayload, librariesPayload] = await Promise.all([fetchProjects(), fetchLibraries()]);
      setProjects(projectsPayload.projects);
      setLibraries(librariesPayload.libraries);
      setLlm(projectsPayload.llm);

      if (libraryId && view === "library") {
        const payload = await fetchLibrary(libraryId);
        setActiveLibrary(payload.library);
        setActiveLibraryDocumentSlug(payload.library.activeDocumentSlug);
        setCurrentView("library");
        return;
      }

      if (projectId && (view === "project" || view === "goal")) {
        const payload = await fetchProject(projectId);
        setActiveProject(payload.project);
        setLlm(payload.llm);
        if (view === "goal" && goalId) {
          setActiveGoalId(goalId);
          setCurrentView("goal");
        } else {
          setCurrentView("project");
        }
      }
    }

    loadInitialState().catch((error) => {
      setErrorMessage(error.message);
    });
  }, []);

  useEffect(() => {
    if (!activeProject?.id) {
      setLiveConnectionState("idle");
      return undefined;
    }

    let isClosed = false;
    setLiveConnectionState("connecting");

    const unsubscribe = subscribeProjectEvents(activeProject.id, {
      onOpen: () => {
        if (!isClosed) {
          setLiveConnectionState("open");
        }
      },
      onProject: (payload) => {
        if (isClosed || !payload?.project) {
          return;
        }
        setActiveProject(payload.project);
        if (payload.llm) {
          setLlm(payload.llm);
        }
        setProjects((current) => {
          const nextSummary = summarizeProject(payload.project);
          const existingIndex = current.findIndex((project) => project.id === payload.project.id);
          if (existingIndex === -1) {
            return [nextSummary, ...current];
          }
          const nextProjects = [...current];
          nextProjects[existingIndex] = {
            ...nextProjects[existingIndex],
            ...nextSummary,
          };
          return nextProjects;
        });
      },
      onError: () => {
        if (!isClosed) {
          setLiveConnectionState("error");
        }
      },
    });

    return () => {
      isClosed = true;
      setLiveConnectionState("idle");
      unsubscribe();
    };
  }, [activeProject?.id]);

  useEffect(() => {
    if (
      !activeProject?.id ||
      liveConnectionState === "open" ||
      (!pendingAction && !activeProject?.generation?.active)
    ) {
      return undefined;
    }

    let cancelled = false;

    async function pollProject() {
      try {
        const [projectsPayload, projectPayload] = await refreshLiveProject(activeProject.id);
        if (cancelled) {
          return;
        }
        setProjects(projectsPayload.projects);
        setLlm(projectPayload.llm);
        setActiveProject(projectPayload.project);
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(error.message);
        }
      }
    }

    pollProject().catch(() => null);
    const intervalId = window.setInterval(() => {
      pollProject().catch(() => null);
    }, 1200);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [activeProject?.generation?.active, activeProject?.id, liveConnectionState, pendingAction]);

  const activeGoal = useMemo(() => {
    if (!activeProject || !activeGoalId) {
      return null;
    }
    return activeProject.goals.find((goal) => goal.id === activeGoalId) ?? null;
  }, [activeGoalId, activeProject]);

  const activeLibraryDocument = useMemo(() => {
    if (!activeLibrary) {
      return null;
    }
    return (
      activeLibrary.documents.find((document) => document.slug === activeLibraryDocumentSlug) ??
      activeLibrary.documents[0] ??
      null
    );
  }, [activeLibrary, activeLibraryDocumentSlug]);

  const contextLabel = useMemo(() => {
    if (activeGoal?.title) {
      return activeGoal.title;
    }
    if (activeProject?.topic) {
      return activeProject.topic;
    }
    if (activeLibrary?.title) {
      return activeLibrary.title;
    }
    return "";
  }, [activeGoal?.title, activeLibrary?.title, activeProject?.topic]);

  async function openLibraryDocumentByPath(repoRelativePath) {
    const normalizedPath = repoRelativePath.replace(/\\/g, "/");
    const librarySummary = libraries.find(
      (item) => normalizedPath === item.sourcePath || normalizedPath.startsWith(`${item.sourcePath}/`),
    );

    if (!librarySummary) {
      return false;
    }

    const payload =
      activeLibrary?.id === librarySummary.id ? { library: activeLibrary } : await fetchLibrary(librarySummary.id);
    const nextLibrary = payload.library;
    const nextRelativePath = normalizedPath.slice(`${librarySummary.sourcePath}/`.length);
    const nextDocument =
      nextLibrary.documents.find((document) => document.relativePath === nextRelativePath) ??
      nextLibrary.documents.find(
        (document) => `${librarySummary.sourcePath}/${document.relativePath}` === normalizedPath,
      ) ??
      null;

    setActiveLibrary(nextLibrary);
    setActiveLibraryDocumentSlug(nextDocument?.slug ?? nextLibrary.activeDocumentSlug);
    setActiveGoalId(null);
    setActiveProject(null);
    setCurrentView("library");
    return true;
  }

  function handleResolveLibraryReference(reference, options = {}) {
    const resolved = resolveLibraryReference(reference, activeLibrary, activeLibraryDocument);

    if (options.navigate && resolved?.type === "library-document") {
      setPendingAction("library");
      setErrorMessage("");

      openLibraryDocumentByPath(resolved.repoRelativePath)
        .then((success) => {
          if (!success) {
            setErrorMessage(`未找到可跳转的文档：${reference}`);
          }
        })
        .catch((error) => {
          setErrorMessage(error.message);
        })
        .finally(() => {
          setPendingAction("");
        });
    }

    return resolved;
  }

  async function runProjectAction(actionName, runner, options = {}) {
    if (!activeProject) {
      return null;
    }

    setPendingAction(actionName);
    setErrorMessage("");

    try {
      const payload = await runner(activeProject.id);
      setActiveProject(payload.project);
      setLlm(payload.llm);
      await refreshWorkspace(payload.project.id);
      if (options.view) {
        setCurrentView(options.view);
      }
      return payload.project;
    } catch (error) {
      setErrorMessage(error.message);
      return null;
    } finally {
      setPendingAction("");
    }
  }

  async function runBootstrapPipeline(projectId) {
    setPendingAction("pipeline");
    setErrorMessage("");

    try {
      const researchPayload = await generateResearch(projectId);
      setActiveProject(researchPayload.project);
      setLlm(researchPayload.llm);
      setCurrentView("project");

      const planPayload = await generatePlan(projectId);
      setActiveProject(planPayload.project);
      setLlm(planPayload.llm);
      setCurrentView("project");
      await refreshWorkspace(projectId);
    } catch (error) {
      setErrorMessage(error.message);
      setCurrentView("project");
      await refreshWorkspace(projectId).catch(() => null);
    } finally {
      setPendingAction("");
    }
  }

  async function handleCreateOrChat(event) {
    event.preventDefault();
    const message = composerValue.trim();
    if (!message) {
      return;
    }

    if (activeProject) {
      setPendingAction("chat");
      setErrorMessage("");

      try {
        const payload = await sendProjectMessage(activeProject.id, message);
        setActiveProject(payload.project);
        setLlm(payload.llm);
        await refreshWorkspace(payload.project.id);
        setComposerValue("");
      } catch (error) {
        setErrorMessage(error.message);
      } finally {
        setPendingAction("");
      }
      return;
    }

    setPendingAction("pipeline");
    setErrorMessage("");

    try {
      const topic = deriveTopicFromMessage(message);
      const payload = await createProject(topic, message);
      setActiveProject(payload.project);
      setActiveLibrary(null);
      setActiveLibraryDocumentSlug(null);
      setLlm(payload.llm);
      setCurrentView("project");
      setComposerValue("");
      await refreshWorkspace(payload.project.id);
      await runBootstrapPipeline(payload.project.id);
    } catch (error) {
      setErrorMessage(error.message);
      setPendingAction("");
    }
  }

  async function openProject(projectId, view = "project") {
    setPendingAction("loading");
    setErrorMessage("");

    try {
      const payload = await fetchProject(projectId);
      setActiveProject(payload.project);
      setActiveGoalId(null);
      setActiveLibrary(null);
      setActiveLibraryDocumentSlug(null);
      setCurrentView(view);
      setLlm(payload.llm);
      await refreshWorkspace(projectId);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setPendingAction("");
    }
  }

  async function openLibrary(libraryId) {
    setPendingAction("library");
    setErrorMessage("");

    try {
      const payload = await fetchLibrary(libraryId);
      setActiveLibrary(payload.library);
      setActiveLibraryDocumentSlug(payload.library.activeDocumentSlug);
      setActiveGoalId(null);
      setActiveProject(null);
      setCurrentView("library");
      const librariesPayload = await fetchLibraries();
      setLibraries(librariesPayload.libraries);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setPendingAction("");
    }
  }

  async function openGoal(goalId) {
    if (!activeProject) {
      return;
    }

    const goal = activeProject.goals.find((item) => item.id === goalId);
    setActiveGoalId(goalId);
    setCurrentView("goal");

    if (
      !goal ||
      goal.lessonStatus === "ready" ||
      goal.lessonStatus === "running" ||
      goal.imageStatus === "running" ||
      pendingAction
    ) {
      return;
    }

    setPendingAction("lesson");
    setErrorMessage("");

    try {
      const payload = await generateLesson(activeProject.id, goalId);
      setActiveProject(payload.project);
      setLlm(payload.llm);
      await refreshWorkspace(payload.project.id);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setPendingAction("");
    }
  }

  function handleStartNew() {
    setActiveProject(null);
    setActiveGoalId(null);
    setActiveLibrary(null);
    setActiveLibraryDocumentSlug(null);
    setCurrentView("chat");
    setComposerValue("");
    setErrorMessage("");
  }

  return (
    <div className="app-shell app-shell-learning">
      <LearningSidebar
        projects={projects}
        libraries={libraries}
        activeProjectId={activeProject?.id ?? null}
        activeLibraryId={activeLibrary?.id ?? null}
        onSelectProject={(projectId) => openProject(projectId, "project")}
        onSelectLibrary={openLibrary}
        onStartNew={handleStartNew}
        llm={llm}
        contextLabel={contextLabel}
      />

      <main className="app-main app-main-chat">
        {errorMessage ? <div className="error-banner">{errorMessage}</div> : null}

        {currentView === "chat" ? (
          <ChatWorkspace
            composerValue={composerValue}
            onComposerChange={setComposerValue}
            onSubmit={handleCreateOrChat}
            activeProject={activeProject}
            pendingAction={pendingAction}
            onRunResearch={() => runProjectAction("research", generateResearch, { view: "project" })}
            onRunPlan={() => runProjectAction("plan", generatePlan, { view: "project" })}
            onOpenProject={() => setCurrentView("project")}
            projects={projects}
            llm={llm}
            onSelectProject={(projectId) => openProject(projectId, "project")}
          />
        ) : null}

        {currentView === "project" && activeProject ? (
          <ProjectOverview
            project={activeProject}
            pendingAction={pendingAction}
            onBackToChat={() => setCurrentView("chat")}
            onRunResearch={() => runProjectAction("research", generateResearch, { view: "project" })}
            onRunPlan={() => runProjectAction("plan", generatePlan, { view: "project" })}
            onGenerateAllLessons={() => runProjectAction("lesson-batch", generateLessonBatch, { view: "project" })}
            onOpenGoal={openGoal}
          />
        ) : null}

        {currentView === "goal" && activeProject && activeGoal ? (
          <GoalLesson
            project={activeProject}
            goal={activeGoal}
            pendingAction={pendingAction}
            onBackToProject={() => setCurrentView("project")}
            onGenerateLesson={async () => {
              setPendingAction("lesson");
              setErrorMessage("");
              try {
                const payload = await generateLesson(activeProject.id, activeGoal.id);
                setActiveProject(payload.project);
                setLlm(payload.llm);
                await refreshWorkspace(payload.project.id);
              } catch (error) {
                setErrorMessage(error.message);
              } finally {
                setPendingAction("");
              }
            }}
          />
        ) : null}

        {currentView === "library" && activeLibrary ? (
          <LibraryOverview
            library={activeLibrary}
            activeDocument={activeLibraryDocument}
            onBackToChat={() => setCurrentView("chat")}
            onSelectDocument={setActiveLibraryDocumentSlug}
            onResolveReference={handleResolveLibraryReference}
          />
        ) : null}
      </main>
    </div>
  );
}
