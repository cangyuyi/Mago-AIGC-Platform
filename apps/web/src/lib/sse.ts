/**
 * Small SSE parser for fetch() response bodies.
 *
 * Browsers expose a streamed response as arbitrary chunks, so one chunk is not
 * guaranteed to contain a complete event. This parser buffers both partial
 * lines and multi-line data fields and dispatches an event only at the blank
 * line that terminates an SSE record.
 */
export class SSEParser {
  private buffer = "";
  private eventName = "message";
  private dataLines: string[] = [];

  feed(chunk: string, onEvent: (eventName: string, data: string) => void): void {
    this.buffer += chunk;
    const lines = this.buffer.split(/\r?\n/);
    this.buffer = lines.pop() ?? "";

    for (const line of lines) {
      this.consumeLine(line, onEvent);
    }
  }

  end(onEvent: (eventName: string, data: string) => void): void {
    if (this.buffer) {
      this.consumeLine(this.buffer, onEvent);
      this.buffer = "";
    }
    // A stream may end immediately after the last data line without the final
    // blank separator. Flush that record so the final event is not lost.
    if (this.dataLines.length > 0) {
      this.dispatch(onEvent);
    }
  }

  private consumeLine(line: string, onEvent: (eventName: string, data: string) => void): void {
    if (line === "") {
      this.dispatch(onEvent);
      return;
    }
    if (line.startsWith(":")) return; // SSE comment/heartbeat.

    const separator = line.indexOf(":");
    const field = separator === -1 ? line : line.slice(0, separator);
    let value = separator === -1 ? "" : line.slice(separator + 1);
    if (value.startsWith(" ")) value = value.slice(1);

    if (field === "event") {
      this.eventName = value || "message";
    } else if (field === "data") {
      this.dataLines.push(value);
    }
  }

  private dispatch(onEvent: (eventName: string, data: string) => void): void {
    if (this.dataLines.length > 0) {
      onEvent(this.eventName, this.dataLines.join("\n"));
    }
    this.eventName = "message";
    this.dataLines = [];
  }
}
