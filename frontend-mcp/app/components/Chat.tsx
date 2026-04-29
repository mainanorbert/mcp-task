"use client";

import {
  type FormEvent,
  type ReactNode,
  useCallback,
  useRef,
  useState,
} from "react";

type Role = "user" | "assistant";

type ChatLine = {
  role: Role;
  content: string;
};

type StreamEvent = {
  event: string;
  data: Record<string, string>;
};

const default_api_base = "http://localhost:8000";

function get_api_base(): string {
  const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";
  return base || default_api_base;
}

function parseStreamEvent(block: string): StreamEvent | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0) return null;

  try {
    return { event, data: JSON.parse(dataLines.join("\n")) };
  } catch {
    return { event, data: {} };
  }
}

function renderInlineMarkdown(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern =
    /(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }

    const key = `${keyPrefix}-${match.index}`;
    if (match[2] && match[3]) {
      nodes.push(
        <a
          key={key}
          href={match[3]}
          target="_blank"
          rel="noreferrer"
          className="underline underline-offset-2"
        >
          {match[2]}
        </a>,
      );
    } else if (match[4]) {
      nodes.push(
        <code
          key={key}
          className="rounded bg-black/10 px-1 py-0.5 font-mono text-[0.92em] dark:bg-white/10"
        >
          {match[4]}
        </code>,
      );
    } else if (match[5]) {
      nodes.push(<strong key={key}>{match[5]}</strong>);
    } else if (match[6]) {
      nodes.push(<em key={key}>{match[6]}</em>);
    }

    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

function splitMarkdownTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isMarkdownTableSeparator(line: string): boolean {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function MarkdownMessage({ content }: { content: string }) {
  const lines = content.split(/\r?\n/);
  const blocks: ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    if (trimmed.startsWith("```")) {
      const codeLines: string[] = [];
      index += 1;

      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        codeLines.push(lines[index]);
        index += 1;
      }

      if (index < lines.length) {
        index += 1;
      }

      blocks.push(
        <pre
          key={`code-${index}`}
          className="my-2 max-w-full overflow-x-auto rounded-lg bg-zinc-950 p-3 text-xs text-zinc-50 dark:bg-black"
        >
          <code>{codeLines.join("\n")}</code>
        </pre>,
      );
      continue;
    }

    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      const level = Math.min(heading[1].length, 3);
      const className =
        level === 1
          ? "mb-2 mt-1 text-base font-semibold"
          : "mb-1 mt-2 text-sm font-semibold";
      blocks.push(
        <div key={`heading-${index}`} className={className}>
          {renderInlineMarkdown(heading[2], `heading-${index}`)}
        </div>,
      );
      index += 1;
      continue;
    }

    if (
      index + 1 < lines.length &&
      line.includes("|") &&
      isMarkdownTableSeparator(lines[index + 1])
    ) {
      const headers = splitMarkdownTableRow(line);
      const rows: string[][] = [];
      index += 2;

      while (index < lines.length && lines[index].includes("|")) {
        rows.push(splitMarkdownTableRow(lines[index]));
        index += 1;
      }

      blocks.push(
        <div key={`table-${index}`} className="my-2 max-w-full overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr>
                {headers.map((header, headerIndex) => (
                  <th
                    key={`table-header-${headerIndex}`}
                    className="border border-current/20 px-2 py-1 font-semibold"
                  >
                    {renderInlineMarkdown(header, `table-${index}-h-${headerIndex}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={`table-row-${rowIndex}`}>
                  {headers.map((_, cellIndex) => (
                    <td
                      key={`table-cell-${rowIndex}-${cellIndex}`}
                      className="border border-current/20 px-2 py-1 align-top"
                    >
                      {renderInlineMarkdown(
                        row[cellIndex] ?? "",
                        `table-${index}-${rowIndex}-${cellIndex}`,
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    if (/^>\s?/.test(line)) {
      const quoteLines: string[] = [];
      while (index < lines.length && /^>\s?/.test(lines[index])) {
        quoteLines.push(lines[index].replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push(
        <blockquote
          key={`quote-${index}`}
          className="my-2 border-l-2 border-current/30 pl-3 opacity-90"
        >
          {quoteLines.map((quoteLine, quoteIndex) => (
            <p key={`quote-line-${quoteIndex}`} className="my-1">
              {renderInlineMarkdown(quoteLine, `quote-${index}-${quoteIndex}`)}
            </p>
          ))}
        </blockquote>,
      );
      continue;
    }

    if (/^\s*[-*+]\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*[-*+]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*[-*+]\s+/, ""));
        index += 1;
      }
      blocks.push(
        <ul key={`ul-${index}`} className="my-2 list-disc space-y-1 pl-5">
          {items.map((item, itemIndex) => (
            <li key={`ul-item-${itemIndex}`}>
              {renderInlineMarkdown(item, `ul-${index}-${itemIndex}`)}
            </li>
          ))}
        </ul>,
      );
      continue;
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*\d+\.\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*\d+\.\s+/, ""));
        index += 1;
      }
      blocks.push(
        <ol key={`ol-${index}`} className="my-2 list-decimal space-y-1 pl-5">
          {items.map((item, itemIndex) => (
            <li key={`ol-item-${itemIndex}`}>
              {renderInlineMarkdown(item, `ol-${index}-${itemIndex}`)}
            </li>
          ))}
        </ol>,
      );
      continue;
    }

    const paragraphLines: string[] = [];
    while (
      index < lines.length &&
      lines[index].trim() &&
      !lines[index].trim().startsWith("```") &&
      !/^(#{1,6})\s+/.test(lines[index]) &&
      !/^>\s?/.test(lines[index]) &&
      !/^\s*[-*+]\s+/.test(lines[index]) &&
      !/^\s*\d+\.\s+/.test(lines[index])
    ) {
      paragraphLines.push(lines[index]);
      index += 1;
    }

    blocks.push(
      <p key={`p-${index}`} className="my-1">
        {renderInlineMarkdown(paragraphLines.join(" "), `p-${index}`)}
      </p>,
    );
  }

  return <div className="space-y-1">{blocks}</div>;
}

export default function Chat() {
  const [messages, setMessages] = useState<ChatLine[]>([]);
  const [input, setInput] = useState("");
  const [useWebSearch, setUseWebSearch] = useState(false);
  const [loading, setLoading] = useState(false);
  const [streamStatus, setStreamStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      listRef.current?.scrollTo({
        top: listRef.current.scrollHeight,
        behavior: "smooth",
      });
    });
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const prior = messages;
    setError(null);
    setStreamStatus(useWebSearch ? "Searching the web..." : "Thinking...");
    const userLine: ChatLine = { role: "user", content: trimmed };
    const nextHistory = [...prior, userLine];
    const assistantLine: ChatLine = { role: "assistant", content: "" };
    setMessages([...nextHistory, assistantLine]);
    setInput("");
    setLoading(true);
    scrollToBottom();

    try {
      const res = await fetch(`${get_api_base()}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: nextHistory.map((m) => ({
            role: m.role,
            content: m.content,
          })),
          use_web_search: useWebSearch,
        }),
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || res.statusText);
      }

      if (!res.body) {
        throw new Error("Streaming response was empty");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder
          .decode(value, { stream: !done })
          .replace(/\r\n/g, "\n");

        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const block = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);

          const parsed = parseStreamEvent(block);
          if (parsed?.event === "delta") {
            const content = parsed.data.content ?? "";
            setMessages((prev) =>
              prev.map((m, index) =>
                index === prev.length - 1 && m.role === "assistant"
                  ? { ...m, content: m.content + content }
                  : m,
              ),
            );
            setStreamStatus(null);
            scrollToBottom();
          } else if (parsed?.event === "status") {
            setStreamStatus(parsed.data.message ?? null);
          } else if (parsed?.event === "error") {
            throw new Error(parsed.data.message || "Request failed");
          } else if (parsed?.event === "done") {
            setStreamStatus(null);
          }

          boundary = buffer.indexOf("\n\n");
        }

        if (done) break;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      setMessages(prior);
    } finally {
      setLoading(false);
      setStreamStatus(null);
      scrollToBottom();
    }
  }

  return (
    <div className="flex h-[min(720px,calc(100vh-8rem))] w-full max-w-2xl flex-col rounded-2xl border border-zinc-200 bg-zinc-50 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <header className="border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
        <h1 className="text-lg font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          Chat
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Polite assistant — abusive or harmful requests are declined gently.
        </p>
        <label className="mt-2 flex cursor-pointer items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
          <input
            type="checkbox"
            checked={useWebSearch}
            onChange={(e) => setUseWebSearch(e.target.checked)}
            disabled={loading}
            className="size-4 rounded border-zinc-300"
          />
          Search the web (Playwright MCP — slower; needs Node on the server)
        </label>
      </header>

      <div
        ref={listRef}
        className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4"
      >
        {messages.length === 0 && (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Send a message to start. The model is{" "}
            <span className="font-mono text-zinc-700 dark:text-zinc-300">
              gpt-4.1-mini
            </span>{" "}
            via your backend API.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={`${i}-${m.role}`}
            className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
              m.role === "user"
                ? "ml-auto bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "mr-auto border border-zinc-200 bg-white text-zinc-800 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
            }`}
          >
            {m.content ? (
              <MarkdownMessage content={m.content} />
            ) : loading && i === messages.length - 1 ? (
              streamStatus
            ) : (
              ""
            )}
          </div>
        ))}
      </div>

      {error && (
        <p className="border-t border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
          {error}
        </p>
      )}

      <form
        onSubmit={onSubmit}
        className="flex gap-2 border-t border-zinc-200 p-3 dark:border-zinc-800"
      >
        <input
          className="min-w-0 flex-1 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 outline-none ring-zinc-400 focus:ring-2 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:ring-zinc-600"
          placeholder="Type a message…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          aria-label="Message"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="shrink-0 rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition enabled:hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:enabled:hover:bg-zinc-200"
        >
          Send
        </button>
      </form>
    </div>
  );
}
