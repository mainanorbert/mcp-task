import { auth } from "@clerk/nextjs/server";
import Chat from "./components/Chat";

export default async function Home() {
  const { userId } = await auth();

  return (
    <div className="flex min-h-full flex-col items-center justify-center px-4 py-10">
      {userId ? (
        <Chat />
      ) : (
        <main className="flex w-full max-w-2xl flex-col items-center rounded-lg border border-zinc-200 bg-zinc-50 px-6 py-10 text-center shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
          <h1 className="text-lg font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            mcp challenge
          </h1>
          <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
            Sign in or sign up to start chatting.
          </p>
        </main>
      )}
    </div>
  );
}
