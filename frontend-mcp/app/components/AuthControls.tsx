"use client";

import {
  Show,
  SignInButton,
  SignUpButton,
  useAuth,
  useClerk,
} from "@clerk/nextjs";
import { useEffect, useState } from "react";
import {
  get_api_base,
  read_stored_session_id,
  store_session_id,
} from "../lib/chat_session";

function ClearStoredSessionOnSignedOut() {
  /** Clear stale browser session ids whenever Clerk renders signed-out state. */
  useEffect(() => {
    store_session_id(null);
  }, []);

  return null;
}

export default function AuthControls() {
  /** Header auth controls that clear chat memory before signing out. */
  const { getToken } = useAuth();
  const { signOut } = useClerk();
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function reset_chat_session(): Promise<void> {
    /** Ask the API to clear this user's current chat session. */
    const token = await getToken();
    if (!token) return;

    async function post_reset(session_id: string | null): Promise<Response> {
      return fetch(`${get_api_base()}/session/reset`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ session_id }),
      });
    }

    const stored_session_id = read_stored_session_id();
    let res = await post_reset(stored_session_id);
    if (!res.ok && stored_session_id) {
      res = await post_reset(null);
    }

    if (!res.ok) {
      const detail = await res.json().catch(() => null);
      throw new Error(detail?.detail || "Could not clear chat session");
    }
  }

  async function on_sign_out(): Promise<void> {
    /** Clear chat memory and then complete Clerk sign-out. */
    setError(null);
    setSigningOut(true);

    try {
      await reset_chat_session();
      store_session_id(null);
      await signOut({ redirectUrl: "/" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign out failed");
      setSigningOut(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <Show when="signed-out">
        <ClearStoredSessionOnSignedOut />
        <SignInButton mode="modal">
          <button
            type="button"
            className="text-sm font-medium text-zinc-700 transition hover:text-zinc-950 dark:text-zinc-200 dark:hover:text-white"
          >
            Sign in
          </button>
        </SignInButton>
        <SignUpButton mode="modal">
          <button
            type="button"
            className="rounded-lg bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            Sign up
          </button>
        </SignUpButton>
      </Show>
      <Show when="signed-in">
        <div className="flex items-center gap-2">
          {error && (
            <span className="max-w-44 truncate text-xs text-red-600 dark:text-red-300">
              {error}
            </span>
          )}
          <button
            type="button"
            onClick={on_sign_out}
            disabled={signingOut}
            className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-700 transition enabled:hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-200 dark:enabled:hover:bg-zinc-900"
          >
            {signingOut ? "Signing out..." : "Sign out"}
          </button>
        </div>
      </Show>
    </div>
  );
}
