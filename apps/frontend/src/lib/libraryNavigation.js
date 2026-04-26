function normalizeReference(value) {
  return (value ?? "").trim().replace(/\\/g, "/");
}

function splitSegments(value) {
  return normalizeReference(value)
    .split("/")
    .filter(Boolean);
}

function joinRelativePath(basePath, relativePath) {
  const baseSegments = splitSegments(basePath);
  const relativeSegments = splitSegments(relativePath);
  const stack = baseSegments.slice(0, -1);

  for (const segment of relativeSegments) {
    if (segment === ".") {
      continue;
    }

    if (segment === "..") {
      stack.pop();
      continue;
    }

    stack.push(segment);
  }

  return stack.join("/");
}

export function resolveLibraryReference(reference, currentLibrary, currentDocument) {
  const normalized = normalizeReference(reference);

  if (!normalized) {
    return null;
  }

  if (/^https?:\/\//i.test(normalized)) {
    return { type: "external", href: normalized };
  }

  if (normalized.startsWith("#")) {
    return null;
  }

  const currentDocumentPath =
    currentLibrary && currentDocument ? `${currentLibrary.sourcePath}/${currentDocument.relativePath}` : null;

  let repoRelativePath = normalized;

  if (normalized.startsWith("./") || normalized.startsWith("../")) {
    if (!currentDocumentPath) {
      return null;
    }
    repoRelativePath = joinRelativePath(currentDocumentPath, normalized);
  } else if (normalized === "README.md" && currentLibrary) {
    repoRelativePath = `${currentLibrary.sourcePath}/README.md`;
  } else if (normalized.endsWith(".md") && currentLibrary && !normalized.startsWith("content/library/")) {
    if (normalized.includes("/")) {
      repoRelativePath = `content/library/${normalized}`;
    } else {
      repoRelativePath = `${currentLibrary.sourcePath}/${normalized}`;
    }
  }

  const normalizedRepoPath = normalizeReference(repoRelativePath);

  if (!normalizedRepoPath.endsWith(".md")) {
    return null;
  }

  return {
    type: "library-document",
    repoRelativePath: normalizedRepoPath,
  };
}
