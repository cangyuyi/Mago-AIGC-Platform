import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ChatInterface } from "@/components/chat/chat-interface";

/**
 * The workflow pauses at human-in-the-loop gates and the UI must surface the
 * pending gate, then resume the paused checkpoint. These tests drive the chat
 * component against a scripted SSE stream so the gate contract (banner text,
 * resume payload, chunk rendering) cannot silently regress.
 */

/** Build a fetch Response whose body streams the given SSE frames. */
function sseResponse(frames: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const frame of frames) controller.enqueue(encoder.encode(frame));
      controller.close();
    },
  });
  return { ok: true, status: 200, body, text: async () => "" } as unknown as Response;
}

function rec(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ChatInterface HITL gate", () => {
  it("renders the pending gate banner from the done event", async () => {
    fetchMock.mockResolvedValueOnce(
      sseResponse([
        rec("meta", { run_id: "r1", mode: "detailed" }),
        rec("ideas", { ideas: [{ id: "idea001", title: "口红测评", description: "五支显白色号" }] }),
        rec("done", {
          run_id: "r1",
          state: {
            hitl_required: true,
            hitl_node: "brief_review",
            hitl_prompt: "请确认创意简报后继续",
          },
        }),
        "data: [DONE]\n\n",
      ]),
    );

    render(<ChatInterface mode="detailed" />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "口红测评" } });
    fireEvent.click(screen.getByRole("button", { name: "发送消息" }));

    await waitFor(() => {
      expect(screen.getByText("请确认创意简报")).toBeInTheDocument();
    });
    expect(screen.getByText("请确认创意简报后继续")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /确认并继续/ })).toBeInTheDocument();
  });

  it("resumes the paused run with an approval payload", async () => {
    fetchMock.mockResolvedValueOnce(
      sseResponse([
        rec("meta", { run_id: "r1", mode: "detailed" }),
        rec("done", {
          run_id: "r1",
          state: { hitl_required: true, hitl_node: "script_review", hitl_prompt: "请确认脚本" },
        }),
        "data: [DONE]\n\n",
      ]),
    );
    // Second call is the resume turn.
    fetchMock.mockResolvedValueOnce(
      sseResponse([rec("meta", { run_id: "r2", mode: "detailed" }), "data: [DONE]\n\n"]),
    );

    render(<ChatInterface mode="detailed" />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "口红测评" } });
    fireEvent.click(screen.getByRole("button", { name: "发送消息" }));

    const approve = await screen.findByRole("button", { name: /确认并继续/ });
    fireEvent.click(approve);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });
    const secondBody = JSON.parse(fetchMock.mock.calls[1][1].body as string);
    expect(secondBody.resume).toEqual({ approved: true });
    expect(secondBody.mode).toBe("detailed");
  });

  it("streams token chunks into the assistant bubble", async () => {
    fetchMock.mockResolvedValueOnce(
      sseResponse([
        rec("meta", { run_id: "r1", mode: "quick" }),
        rec("chunk", { node: "storyteller", text: "第一段" }),
        rec("chunk", { node: "storyteller", text: "第二段" }),
        "data: [DONE]\n\n",
      ]),
    );

    render(<ChatInterface mode="quick" />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "口红测评" } });
    fireEvent.click(screen.getByRole("button", { name: "发送消息" }));

    await waitFor(() => {
      expect(screen.getByText(/第一段第二段/)).toBeInTheDocument();
    });
  });

  it("hides the gate banner once the run resumes", async () => {
    fetchMock.mockResolvedValueOnce(
      sseResponse([
        rec("meta", { run_id: "r1", mode: "detailed" }),
        rec("done", {
          run_id: "r1",
          state: { hitl_required: true, hitl_node: "brief_review", hitl_prompt: "请确认创意简报" },
        }),
        "data: [DONE]\n\n",
      ]),
    );
    fetchMock.mockResolvedValueOnce(
      sseResponse([
        rec("meta", { run_id: "r2", mode: "detailed" }),
        rec("done", { run_id: "r2", state: { hitl_required: false } }),
        "data: [DONE]\n\n",
      ]),
    );

    render(<ChatInterface mode="detailed" />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "口红测评" } });
    fireEvent.click(screen.getByRole("button", { name: "发送消息" }));

    const approve = await screen.findByRole("button", { name: /确认并继续/ });
    fireEvent.click(approve);

    await waitFor(() => {
      expect(screen.queryByText("请确认创意简报")).not.toBeInTheDocument();
    });
  });
});
