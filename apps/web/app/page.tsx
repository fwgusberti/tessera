"use client";

import { AuthGuard } from "@/lib/auth-guard";
import ChatInterface from "@/components/chat/ChatInterface";

export default function Home() {
  return (
    <AuthGuard>
      <div className="-mx-4 -my-8 min-h-[calc(100dvh-3.25rem)] flex flex-col">
        <ChatInterface />
      </div>
    </AuthGuard>
  );
}
