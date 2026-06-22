import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";

vi.mock("@/lib/chat", () => ({
  askAssistant: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ status: "authenticated", user: { id: "u1", email: "t@t.com", isAdmin: false }, accessToken: "tok" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth-guard", () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { askAssistant } from "@/lib/chat";
import ChatInterface from "@/components/chat/ChatInterface";

const mockAskAssistant = askAssistant as unknown as ReturnType<typeof vi.fn>;

const fakeAnswer = {
  answer: "The answer to your question.",
  confidence: 0.9,
  dont_know: false,
  citations: [],
};

describe("ChatInterface — US1: Ask a Question", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a textarea input for the question", () => {
    render(<ChatInterface />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("renders a submit button", () => {
    render(<ChatInterface />);
    expect(screen.getByRole("button", { name: /ask/i })).toBeInTheDocument();
  });

  it("shows welcome heading when no turns exist", () => {
    render(<ChatInterface />);
    expect(screen.getByRole("heading", { name: /tessera/i })).toBeInTheDocument();
  });

  it("shows tagline when no turns exist", () => {
    render(<ChatInterface />);
    expect(screen.getByText(/your knowledge, always answered/i)).toBeInTheDocument();
  });

  it("calls askAssistant with the typed question on form submit", async () => {
    mockAskAssistant.mockResolvedValueOnce(fakeAnswer);
    render(<ChatInterface />);

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "What is the policy?" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      expect(mockAskAssistant).toHaveBeenCalledWith("What is the policy?", []);
    });
  });

  it("shows a loading indicator while the answer is pending", async () => {
    mockAskAssistant.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(fakeAnswer), 200)),
    );
    render(<ChatInterface />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "A question" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    expect(await screen.findByRole("status")).toBeInTheDocument();
  });

  it("renders the answer after the response arrives", async () => {
    mockAskAssistant.mockResolvedValueOnce(fakeAnswer);
    render(<ChatInterface />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "What is the policy?" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      expect(screen.getByText("The answer to your question.")).toBeInTheDocument();
    });
  });

  it("clears the textarea after a successful submission", async () => {
    mockAskAssistant.mockResolvedValueOnce(fakeAnswer);
    render(<ChatInterface />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "My question" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      expect((screen.getByRole("textbox") as HTMLTextAreaElement).value).toBe("");
    });
  });
});

// ─── US2: Conversational Follow-Up ───────────────────────────────────────────

describe("ChatInterface — US2: Conversational Follow-Up", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("passes history of completed turns to askAssistant on the second submission", async () => {
    mockAskAssistant.mockResolvedValue(fakeAnswer);
    render(<ChatInterface />);

    // First turn
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "First question" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    await waitFor(() => expect(screen.getByText("The answer to your question.")).toBeInTheDocument());

    // Second turn
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Follow-up question" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      expect(mockAskAssistant).toHaveBeenLastCalledWith("Follow-up question", [
        { role: "user", content: "First question" },
        { role: "assistant", content: "The answer to your question." },
      ]);
    });
  });

  it("renders multiple turns in chronological order", async () => {
    mockAskAssistant.mockResolvedValue(fakeAnswer);
    render(<ChatInterface />);

    for (const q of ["First question", "Second question"]) {
      fireEvent.change(screen.getByRole("textbox"), { target: { value: q } });
      fireEvent.click(screen.getByRole("button", { name: /ask/i }));
      await waitFor(() => expect(mockAskAssistant).toHaveBeenCalled());
    }

    await waitFor(() => {
      const questions = screen.getAllByText(/question/i);
      expect(questions.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("shows 'New conversation' button only when turns exist", async () => {
    mockAskAssistant.mockResolvedValueOnce(fakeAnswer);
    render(<ChatInterface />);

    expect(screen.queryByRole("button", { name: /new conversation/i })).toBeNull();

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "A question" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /new conversation/i })).toBeInTheDocument();
    });
  });

  it("clears all turns when 'New conversation' is clicked", async () => {
    mockAskAssistant.mockResolvedValueOnce(fakeAnswer);
    render(<ChatInterface />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "A question" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    await waitFor(() => screen.getByText("The answer to your question."));

    fireEvent.click(screen.getByRole("button", { name: /new conversation/i }));

    expect(screen.queryByText("The answer to your question.")).toBeNull();
    expect(screen.getByRole("heading", { name: /tessera/i })).toBeInTheDocument();
  });
});

// ─── US3: Empty and Error States ─────────────────────────────────────────────

describe("ChatInterface — US3: Empty and Error States", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("disables the submit button when input is empty", () => {
    render(<ChatInterface />);
    expect(screen.getByRole("button", { name: /ask/i })).toBeDisabled();
  });

  it("disables the submit button when input is whitespace only", () => {
    render(<ChatInterface />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "   " } });
    expect(screen.getByRole("button", { name: /ask/i })).toBeDisabled();
  });

  it("does not call askAssistant when form submitted with empty input", () => {
    render(<ChatInterface />);
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    expect(mockAskAssistant).not.toHaveBeenCalled();
  });

  it("shows error message in the conversation when askAssistant rejects", async () => {
    mockAskAssistant.mockRejectedValueOnce(new Error("Service unavailable"));
    render(<ChatInterface />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "My question" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      expect(screen.getByText(/service unavailable/i)).toBeInTheDocument();
    });
  });

  it("re-populates the textarea with the failed question on error", async () => {
    mockAskAssistant.mockRejectedValueOnce(new Error("Service unavailable"));
    render(<ChatInterface />);

    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "My failed question" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      expect((input as HTMLTextAreaElement).value).toBe("My failed question");
    });
  });
});

// ─── T005: Conversation View (US2 new layout tests) ──────────────────────────

describe("conversation view", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a MessageBubble element for a completed turn", async () => {
    mockAskAssistant.mockResolvedValueOnce(fakeAnswer);
    render(<ChatInterface />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "A question" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      expect(screen.getByText("The answer to your question.")).toBeInTheDocument();
    });
  });

  it("shows New conversation button when turns exist", async () => {
    mockAskAssistant.mockResolvedValueOnce(fakeAnswer);
    render(<ChatInterface />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "A question" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /new conversation/i })).toBeInTheDocument();
    });
  });

  it("Ask button is still present in conversation view", async () => {
    mockAskAssistant.mockResolvedValueOnce(fakeAnswer);
    render(<ChatInterface />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "A question" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /ask/i })).toBeInTheDocument();
    });
  });
});

// ─── US3 (feature 027): Citation document links in MessageBubble ─────────────

import MessageBubble from "@/components/chat/MessageBubble";
import type { ChatTurn } from "@/lib/types";

const completeTurnWithCitations: ChatTurn = {
  id: "t1",
  question: "What is the policy?",
  status: "complete",
  answer: {
    answer: "Here is the answer.",
    confidence: 0.9,
    dont_know: false,
    citations: [
      {
        chunk_id: "c1",
        document_id: "doc-001",
        document_version_id: "v1",
        quote: "This is the first citation quote text that is more than 80 chars long for testing purposes here.",
        score: 0.85,
      },
      {
        chunk_id: "c2",
        document_id: "doc-002",
        document_version_id: "v2",
        quote: "Second citation quote.",
        score: 0.75,
      },
    ],
  },
};

describe("MessageBubble — US3: citation document links", () => {
  it("renders Sources heading when answer is complete with citations", () => {
    render(<MessageBubble turn={completeTurnWithCitations} />);
    expect(screen.getByText("Sources")).toBeInTheDocument();
  });

  it("renders one link per citation", () => {
    render(<MessageBubble turn={completeTurnWithCitations} />);
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(2);
  });

  it("each citation link has correct href to /documents/{document_id}", () => {
    render(<MessageBubble turn={completeTurnWithCitations} />);
    const links = screen.getAllByRole("link");
    expect(links[0]).toHaveAttribute("href", "/documents/doc-001");
    expect(links[1]).toHaveAttribute("href", "/documents/doc-002");
  });

  it("each citation link opens in a new tab", () => {
    render(<MessageBubble turn={completeTurnWithCitations} />);
    const links = screen.getAllByRole("link");
    expect(links[0]).toHaveAttribute("target", "_blank");
    expect(links[1]).toHaveAttribute("target", "_blank");
  });

  it("does not render Sources section when dont_know is true", () => {
    const dontKnowTurn: ChatTurn = {
      ...completeTurnWithCitations,
      answer: { ...completeTurnWithCitations.answer!, dont_know: true },
    };
    render(<MessageBubble turn={dontKnowTurn} />);
    expect(screen.queryByText("Sources")).not.toBeInTheDocument();
  });

  it("does not render Sources section when citations array is empty", () => {
    const noSourcesTurn: ChatTurn = {
      ...completeTurnWithCitations,
      answer: { ...completeTurnWithCitations.answer!, citations: [] },
    };
    render(<MessageBubble turn={noSourcesTurn} />);
    expect(screen.queryByText("Sources")).not.toBeInTheDocument();
  });

  it("does not render Sources section when citations is absent", () => {
    const noSourcesTurn: ChatTurn = {
      ...completeTurnWithCitations,
      answer: { answer: "No citations here.", confidence: 0.9, dont_know: false },
    };
    render(<MessageBubble turn={noSourcesTurn} />);
    expect(screen.queryByText("Sources")).not.toBeInTheDocument();
  });

  it("does not render Sources section when status is pending", () => {
    const pendingTurn: ChatTurn = {
      ...completeTurnWithCitations,
      status: "pending",
      answer: null,
    };
    render(<MessageBubble turn={pendingTurn} />);
    expect(screen.queryByText("Sources")).not.toBeInTheDocument();
  });
});

// ─── T007: Starter Prompts (US3) ─────────────────────────────────────────────

describe("starter prompts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders 4 starter prompt chips on the welcome screen", () => {
    render(<ChatInterface />);
    expect(screen.getByText("What's in our product roadmap?")).toBeInTheDocument();
    const chips = screen.getAllByRole("button").filter(
      (btn) => btn.textContent !== "Ask" && btn.textContent !== "New conversation"
    );
    expect(chips).toHaveLength(4);
  });

  it("clicking a chip populates the textarea with that chip text", () => {
    render(<ChatInterface />);
    fireEvent.click(screen.getByText("What's in our product roadmap?"));
    expect((screen.getByRole("textbox") as HTMLTextAreaElement).value).toBe(
      "What's in our product roadmap?"
    );
  });

  it("does not render chips when turns exist", async () => {
    mockAskAssistant.mockResolvedValueOnce(fakeAnswer);
    render(<ChatInterface />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "A question" } });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));

    await waitFor(() => {
      expect(screen.queryByText("What's in our product roadmap?")).toBeNull();
    });
  });
});
