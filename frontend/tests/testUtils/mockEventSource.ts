/** A minimal, controllable stand-in for the browser's native `EventSource` — jsdom doesn't
 * implement it. Tests install this via `vi.stubGlobal("EventSource", MockEventSource)` and drive
 * it with `.emit(data)` / `.triggerError()` to simulate real server-sent events without a real
 * network connection. */
export class MockEventSource {
  static instances: MockEventSource[] = [];

  url: string;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  emit(data: unknown): void {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  triggerError(): void {
    this.onerror?.();
  }

  close(): void {
    this.closed = true;
  }

  static reset(): void {
    MockEventSource.instances = [];
  }
}
