import { auth } from "@clerk/nextjs/server";
import Chat from "./components/Chat";

export default async function Home() {
  /** Landing page: shows the chat for signed-in users, sign-in prompt otherwise. */
  const { userId } = await auth();

  return (
    <div className="flex min-h-full flex-col items-center justify-center px-4 py-10">
      {userId ? (
        <Chat />
      ) : (
        <main className="flex w-full max-w-2xl flex-col items-center rounded-lg border border-zinc-200 bg-zinc-50 px-6 py-10 text-center shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            Meridian Electronics Support
          </h1>
          <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
            AI-powered customer support for products and orders.
            <br />
            Sign in or sign up to start chatting.
          </p>
          <ul className="mt-4 space-y-1 text-left text-xs text-zinc-500 dark:text-zinc-400">
            <li>- Browse monitors, keyboards, printers, networking gear</li>
            <li>- Authenticate with email + 4-digit PIN</li>
            <li>- View past orders or place a new one</li>
          </ul>
        </main>
      )}
    </div>
  );
}
