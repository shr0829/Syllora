async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error ?? `Request failed: ${response.status}`);
  }

  return payload;
}

export function fetchProjects() {
  return request("/api/projects");
}

export function fetchLibraries() {
  return request("/api/library");
}

export function fetchLibrary(libraryId) {
  return request(`/api/library/${libraryId}`);
}

export function fetchProject(projectId) {
  return request(`/api/projects/${projectId}`);
}

export function subscribeProjectEvents(projectId, handlers = {}) {
  const source = new EventSource(`/api/projects/${projectId}/events`);

  source.onopen = () => {
    handlers.onOpen?.();
  };

  source.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      handlers.onProject?.(payload);
    } catch (error) {
      handlers.onError?.(error);
    }
  };

  source.onerror = (event) => {
    handlers.onError?.(event);
  };

  return () => {
    source.close();
  };
}

export function createProject(topic, message) {
  return request("/api/projects", {
    method: "POST",
    body: JSON.stringify({ topic, message }),
  });
}

export function sendProjectMessage(projectId, content) {
  return request(`/api/projects/${projectId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function generateResearch(projectId) {
  return request(`/api/projects/${projectId}/research`, {
    method: "POST",
  });
}

export function generatePlan(projectId) {
  return request(`/api/projects/${projectId}/plan`, {
    method: "POST",
  });
}

export function generateLesson(projectId, goalId) {
  return request(`/api/projects/${projectId}/goals/${goalId}/lesson`, {
    method: "POST",
  });
}

export function generateLessonBatch(projectId) {
  return request(`/api/projects/${projectId}/lessons/batch`, {
    method: "POST",
  });
}
