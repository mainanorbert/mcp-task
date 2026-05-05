export const CHAT_SESSION_STORAGE_KEY = "meridian.chat.session_id";

const DEFAULT_API_BASE = "http://localhost:8000";

export function get_api_base(): string {
  /** Return the configured backend base URL, falling back to localhost. */
  const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";
  return base || DEFAULT_API_BASE;
}

export function read_stored_session_id(): string | null {
  /** Read the signed chat session token stored by the browser. */
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(CHAT_SESSION_STORAGE_KEY);
}

export function store_session_id(session_id: string | null): void {
  /** Store or clear the signed chat session token. */
  if (typeof window === "undefined") return;

  if (session_id) {
    window.sessionStorage.setItem(CHAT_SESSION_STORAGE_KEY, session_id);
  } else {
    window.sessionStorage.removeItem(CHAT_SESSION_STORAGE_KEY);
  }
}
