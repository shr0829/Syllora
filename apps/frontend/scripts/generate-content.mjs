import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..", "..");
const outputDir = path.join(frontendRoot, "src", "generated");
const outputFile = path.join(outputDir, "learningContent.json");

const trackConfig = [
  {
    id: "foundations",
    directory: path.join(repoRoot, "content", "library", "learning_tracks", "pytorch_to_transformer"),
    readme: "README.md",
  },
  {
    id: "llm-apps",
    directory: path.join(repoRoot, "content", "library", "llm_agent_learning"),
    readme: "README.md",
  },
];

function normalizeParagraphs(lines) {
  const paragraphs = [];
  let buffer = [];

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      if (buffer.length) {
        paragraphs.push(buffer.join(" "));
        buffer = [];
      }
      continue;
    }

    if (line.startsWith("- ") || /^\d+\.\s/.test(line)) {
      if (buffer.length) {
        paragraphs.push(buffer.join(" "));
        buffer = [];
      }
      continue;
    }

    buffer.push(line);
  }

  if (buffer.length) {
    paragraphs.push(buffer.join(" "));
  }

  return paragraphs;
}

function parseSubsections(lines) {
  const subsections = [];
  let current = null;

  for (const line of lines) {
    const heading = line.match(/^###\s+(.+)$/);

    if (heading) {
      current = { title: heading[1].trim(), lines: [] };
      subsections.push(current);
      continue;
    }

    if (current) {
      current.lines.push(line);
    }
  }

  return subsections.map((section) => {
    const bullets = section.lines
      .map((line) => line.trim())
      .filter((line) => line.startsWith("- "))
      .map((line) => line.slice(2).trim());

    return {
      title: section.title,
      paragraphs: normalizeParagraphs(section.lines),
      bullets,
    };
  });
}

function parseMarkdownDocument(raw, filePath) {
  const lines = raw.replace(/\r\n/g, "\n").split("\n");
  const titleLine = lines.find((line) => line.startsWith("# "));
  const title = titleLine ? titleLine.replace(/^#\s+/, "").trim() : path.basename(filePath, ".md");

  const sections = [];
  const introLines = [];
  let currentSection = null;

  for (const line of lines) {
    const heading = line.match(/^##\s+(.+)$/);

    if (heading) {
      currentSection = { title: heading[1].trim(), lines: [] };
      sections.push(currentSection);
      continue;
    }

    if (line.startsWith("# ")) {
      continue;
    }

    if (currentSection) {
      currentSection.lines.push(line);
    } else {
      introLines.push(line);
    }
  }

  return {
    title,
    intro: normalizeParagraphs(introLines),
    sections: sections.map((section) => {
      const bullets = section.lines
        .map((line) => line.trim())
        .filter((line) => line.startsWith("- "))
        .map((line) => line.slice(2).trim());

      return {
        title: section.title,
        paragraphs: normalizeParagraphs(section.lines),
        bullets,
        subsections: parseSubsections(section.lines),
      };
    }),
  };
}

function buildStageEntries(trackId, readmeDocument) {
  return readmeDocument.sections
    .filter((section) => /^阶段\s*\d+/.test(section.title))
    .map((section, index) => {
      const goalSection = section.subsections.find((item) => item.title.includes("目标"));
      const deliverableSection =
        section.subsections.find((item) => item.title.includes("项目任务")) ??
        section.subsections.find((item) => item.title.includes("最小产出")) ??
        section.subsections.find((item) => item.title.includes("目标产出"));
      const questionSection =
        section.subsections.find((item) => item.title.includes("查验问题")) ??
        section.subsections.find((item) => item.title.includes("必须理解")) ??
        section.subsections.find((item) => item.title.includes("本周问题"));

      return {
        id: `${trackId}-stage-${index + 1}`,
        title: section.title,
        summary: goalSection?.paragraphs[0] ?? section.paragraphs[0] ?? "阅读原文档查看该阶段的学习目标。",
        deliverables: deliverableSection?.bullets ?? [],
        keyQuestions: questionSection?.bullets ?? [],
        sections: section.subsections,
      };
    });
}

async function buildTrack(track) {
  const files = (await readdir(track.directory)).filter((entry) => entry.endsWith(".md"));
  const documents = [];

  for (const file of files) {
    const absolutePath = path.join(track.directory, file);
    const raw = await readFile(absolutePath, "utf8");
    const parsed = parseMarkdownDocument(raw, absolutePath);

    documents.push({
      slug: file.replace(/\.md$/i, "").toLowerCase(),
      fileName: file,
      relativePath: path.relative(repoRoot, absolutePath).replace(/\\/g, "/"),
      ...parsed,
    });
  }

  documents.sort((left, right) => {
    if (left.fileName === track.readme) return -1;
    if (right.fileName === track.readme) return 1;
    return left.fileName.localeCompare(right.fileName, "zh-CN");
  });

  const readmeDocument = documents.find((document) => document.fileName === track.readme) ?? documents[0];

  return {
    documents,
    stages: readmeDocument ? buildStageEntries(track.id, readmeDocument) : [],
  };
}

const result = {};

for (const track of trackConfig) {
  result[track.id] = await buildTrack(track);
}

await mkdir(outputDir, { recursive: true });
await writeFile(outputFile, JSON.stringify(result, null, 2), "utf8");

console.log(`Generated ${path.relative(frontendRoot, outputFile)}`);
