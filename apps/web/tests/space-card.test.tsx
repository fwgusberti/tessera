import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import type { Space } from "@/lib/types";
import { SpaceCard } from "@/components/spaces/SpaceCard";

const mockSpace: Space = {
  id: "s1",
  slug: "engineering",
  name: "Engineering",
  sector: "Technology",
  default_language: "en",
  confidence_threshold: 0.7,
  retention_policy: {},
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("SpaceCard — action links", () => {
  it("renders a Members link pointing to /spaces/{id}/members", () => {
    render(<SpaceCard space={mockSpace} role="editor" />);
    const link = screen.getByRole("link", { name: /members/i });
    expect(link).toHaveAttribute("href", `/spaces/${mockSpace.id}/members`);
  });

  it("renders a Documents link pointing to /documents?space={id}", () => {
    render(<SpaceCard space={mockSpace} role="editor" />);
    const link = screen.getByRole("link", { name: /documents/i });
    expect(link).toHaveAttribute("href", `/documents?space=${mockSpace.id}`);
  });

  it("both action links are present when role is admin", () => {
    render(<SpaceCard space={mockSpace} role="admin" />);
    expect(screen.getByRole("link", { name: /members/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /documents/i })).toBeInTheDocument();
  });

  it("both action links are present when role is viewer", () => {
    render(<SpaceCard space={mockSpace} role="viewer" />);
    expect(screen.getByRole("link", { name: /members/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /documents/i })).toBeInTheDocument();
  });

  it("both action links are present when role is null", () => {
    render(<SpaceCard space={mockSpace} role={null} />);
    expect(screen.getByRole("link", { name: /members/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /documents/i })).toBeInTheDocument();
  });
});

describe("SpaceCard — display", () => {
  it("displays the space name", () => {
    render(<SpaceCard space={mockSpace} role={null} />);
    expect(screen.getByText("Engineering")).toBeInTheDocument();
  });

  it("displays the space sector", () => {
    render(<SpaceCard space={mockSpace} role={null} />);
    expect(screen.getByText("Technology")).toBeInTheDocument();
  });

  it("renders a RoleBadge with the correct role when role is provided", () => {
    render(<SpaceCard space={mockSpace} role="editor" />);
    expect(screen.getByText("editor")).toBeInTheDocument();
  });

  it("renders no role badge when role is null", () => {
    render(<SpaceCard space={mockSpace} role={null} />);
    expect(screen.queryByText(/admin|editor|viewer/i)).not.toBeInTheDocument();
  });

  it("long space name does not overflow layout", () => {
    const longName = "A".repeat(200);
    render(<SpaceCard space={{ ...mockSpace, name: longName }} role={null} />);
    const nameEl = screen.getByText(longName);
    expect(nameEl.className).toMatch(/truncate|overflow-hidden/);
  });
});
