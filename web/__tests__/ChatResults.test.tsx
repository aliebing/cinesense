import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ChatResults from "@/components/chat/ChatResults";
import type { RankedMovie } from "@/lib/types";

const pick = {
  movie: { id: "m1", title: "Heat", year: 1995, youtube_key: "abc123" },
  reasons: ["tense"],
} as unknown as RankedMovie;

describe("ChatResults", () => {
  it("shows the picks without a hover trailer", () => {
    render(<ChatResults results={[pick]} onOpen={vi.fn()} />);
    expect(screen.getByTestId("chat-pick")).toBeInTheDocument();
    expect(screen.queryByTestId("hover-trailer")).toBeNull();
  });
});
