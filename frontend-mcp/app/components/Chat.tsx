"use client";

import { useAuth } from "@clerk/nextjs";
import {
  type FormEvent,
  type ReactNode,
  useCallback,
  useRef,
  useState,
} from "react";
import {
  get_api_base,
  read_stored_session_id,
  store_session_id,
} from "../lib/chat_session";

type Role = "user" | "assistant";

type ChatLine = {
  role: Role;
  content: string;
};

const SUGGESTED_PROMPTS: string[] = [
  "What monitors do you sell?",
  "Show me wireless keyboards under $100",
  "Log me in - my email is alex@example.com",
  "Show my recent orders",
];

function render_inline_markdown(text: string, key_prefix: string): ReactNode[] {
  /** Render a single line of inline markdown (links, code, bold, italic). */
  const nodes: ReactNode[] = [];
  const pattern =
    /(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*)/g;
  let last_index = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last_index) {
      nodes.push(text.slice(last_index, match.index));
    }

    const key = `${key_prefix}-${match.index}`;
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

    last_index = pattern.lastIndex;
  }

  if (last_index < text.length) {
    nodes.push(text.slice(last_index));
  }

  return nodes;
}

function split_markdown_table_row(line: string): string[] {
  /** Split a "| a | b |" row into ["a", "b"]. */
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function is_markdown_table_separator(line: string): boolean {
  /** Detect "|---|---|" style table separator rows. */
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function MarkdownMessage({ content }: { content: string }) {
  /** Lightweight markdown renderer used for assistant replies. */
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
      const code_lines: string[] = [];
      index += 1;

      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        code_lines.push(lines[index]);
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
          <code>{code_lines.join("\n")}</code>
        </pre>,
      );
      continue;
    }

    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      blocks.push(
        <div key={`heading-${index}`} className="mb-1 mt-2 text-sm font-semibold">
          {render_inline_markdown(heading[2], `heading-${index}`)}
        </div>,
      );
      index += 1;
      continue;
    }

    if (
      index + 1 < lines.length &&
      line.includes("|") &&
      is_markdown_table_separator(lines[index + 1])
    ) {
      const headers = split_markdown_table_row(line);
      const rows: string[][] = [];
      index += 2;

      while (index < lines.length && lines[index].includes("|")) {
        rows.push(split_markdown_table_row(lines[index]));
        index += 1;
      }

      blocks.push(
        <div key={`table-${index}`} className="my-2 max-w-full overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr>
                {headers.map((header, header_index) => (
                  <th
                    key={`table-header-${header_index}`}
                    className="border border-current/20 px-2 py-1 font-semibold"
                  >
                    {render_inline_markdown(header, `table-${index}-h-${header_index}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, row_index) => (
                <tr key={`table-row-${row_index}`}>
                  {headers.map((_, cell_index) => (
                    <td
                      key={`table-cell-${row_index}-${cell_index}`}
                      className="border border-current/20 px-2 py-1 align-top"
                    >
                      {render_inline_markdown(
                        row[cell_index] ?? "",
                        `table-${index}-${row_index}-${cell_index}`,
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
      const quote_lines: string[] = [];
      while (index < lines.length && /^>\s?/.test(lines[index])) {
        quote_lines.push(lines[index].replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push(
        <blockquote
          key={`quote-${index}`}
          className="my-2 border-l-2 border-current/30 pl-3 opacity-90"
        >
          {quote_lines.map((quote_line, quote_index) => (
            <p key={`quote-line-${quote_index}`} className="my-1">
              {render_inline_markdown(quote_line, `quote-${index}-${quote_index}`)}
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
          {items.map((item, item_index) => (
            <li key={`ul-item-${item_index}`}>
              {render_inline_markdown(item, `ul-${index}-${item_index}`)}
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
          {items.map((item, item_index) => (
            <li key={`ol-item-${item_index}`}>
              {render_inline_markdown(item, `ol-${index}-${item_index}`)}
            </li>
          ))}
        </ol>,
      );
      continue;
    }

    const paragraph_lines: string[] = [];
    while (
      index < lines.length &&
      lines[index].trim() &&
      !lines[index].trim().startsWith("```") &&
      !/^(#{1,6})\s+/.test(lines[index]) &&
      !/^>\s?/.test(lines[index]) &&
      !/^\s*[-*+]\s+/.test(lines[index]) &&
      !/^\s*\d+\.\s+/.test(lines[index])
    ) {
      paragraph_lines.push(lines[index]);
      index += 1;
    }

    blocks.push(
      <p key={`p-${index}`} className="my-1">
        {render_inline_markdown(paragraph_lines.join(" "), `p-${index}`)}
      </p>,
    );
  }

  return <div className="space-y-1">{blocks}</div>;
}

export default function Chat() {
  /** Meridian Electronics customer support chat panel. */
  const { getToken, isSignedIn } = useAuth();
  const [messages, setMessages] = useState<ChatLine[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(() =>
    read_stored_session_id(),
  );
  const list_ref = useRef<HTMLDivElement>(null);

  const scroll_to_bottom = useCallback(() => {
    /** Scroll the message list to the latest item on the next animation frame. */
    requestAnimationFrame(() => {
      list_ref.current?.scrollTo({
        top: list_ref.current.scrollHeight,
        behavior: "smooth",
      });
    });
  }, []);

  async function send_message(text: string): Promise<void> {
    /** POST a single user message to /chat and append the assistant reply. */
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const prior = messages;
    const user_line: ChatLine = { role: "user", content: trimmed };
    const next_history = [...prior, user_line];

    setError(null);
    setMessages(next_history);
    setInput("");
    setLoading(true);
    scroll_to_bottom();

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (isSignedIn) {
        const token = await getToken();
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
      }

      const res = await fetch(`${get_api_base()}/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          session_id: sessionId,
          messages: next_history.map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail || res.statusText);
      }

      const data = (await res.json()) as {
        message?: string;
        session_id?: string;
      };
      if (typeof data.message !== "string") {
        throw new Error("Response did not include a message");
      }
      if (typeof data.session_id === "string" && data.session_id) {
        setSessionId(data.session_id);
        store_session_id(data.session_id);
      }

      setMessages([
        ...next_history,
        { role: "assistant", content: data.message },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      setMessages(prior);
    } finally {
      setLoading(false);
      scroll_to_bottom();
    }
  }

  async function on_submit(e: FormEvent) {
    /** Form handler that delegates to send_message. */
    e.preventDefault();
    await send_message(input);
  }

  return (
    <div className="flex h-[min(720px,calc(100vh-8rem))] w-full max-w-2xl flex-col rounded-lg border border-zinc-200 bg-zinc-50 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <header className="border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
        <h1 className="text-lg font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          Meridian Electronics Support
        </h1>
        <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
          Browse products, log in with email + PIN, view orders, and place new
          orders - all through the chat.
        </p>
      </header>

      <div
        ref={list_ref}
        className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4"
      >
        {messages.length === 0 && (
          <div className="space-y-3 text-sm text-zinc-500 dark:text-zinc-400">
            <p>Try one of these to get started:</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => send_message(prompt)}
                  disabled={loading}
                  className="rounded-full border border-zinc-300 bg-white px-3 py-1 text-xs text-zinc-700 transition enabled:hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200 dark:enabled:hover:bg-zinc-800"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
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
            <MarkdownMessage content={m.content} />
          </div>
        ))}

        {loading && (
          <div className="mr-auto max-w-[85%] rounded-2xl border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400">
            Thinking...
          </div>
        )}
      </div>

      {error && (
        <p className="border-t border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
          {error}
        </p>
      )}

      <form
        onSubmit={on_submit}
        className="flex gap-2 border-t border-zinc-200 p-3 dark:border-zinc-800"
      >
        <input
          className="min-w-0 flex-1 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 outline-none ring-zinc-400 focus:ring-2 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:ring-zinc-600"
          placeholder="Ask about products, orders, or place an order..."
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
