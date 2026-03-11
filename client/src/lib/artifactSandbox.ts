import DOMPurify from "dompurify";

const EXTERNAL_URL_PATTERN = /^(https?:)?\/\//i;

export function sanitizeArtifactHtml(source: string): string {
  const cleaned = DOMPurify.sanitize(source, {
    USE_PROFILES: { html: true, svg: true, svgFilters: true },
    FORBID_TAGS: ["script", "iframe", "object", "embed", "link"],
    FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover", "onfocus"],
  });

  const parser = new DOMParser();
  const doc = parser.parseFromString(cleaned, "text/html");

  for (const node of doc.querySelectorAll<HTMLElement | SVGElement>("*")) {
    for (const attr of ["href", "src", "xlink:href"]) {
      const value = node.getAttribute(attr);
      if (!value) {
        continue;
      }
      if (EXTERNAL_URL_PATTERN.test(value) || value.startsWith("data:") || value.startsWith("//")) {
        node.removeAttribute(attr);
      }
    }
  }

  return doc.body.innerHTML.trim();
}

export function buildArtifactSrcDoc(content: string, title: string): string {
  return `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${title}</title>
    <style>
      body {
        margin: 0;
        padding: 16px;
        font-family: "IBM Plex Sans", sans-serif;
        color: #0f1f2e;
        background: #ffffff;
      }
      table {
        width: 100%;
        border-collapse: collapse;
      }
      th, td {
        border: 1px solid #d1dbe8;
        padding: 8px;
        text-align: left;
      }
      svg {
        max-width: 100%;
        height: auto;
      }
    </style>
  </head>
  <body>${content}</body>
</html>`;
}
