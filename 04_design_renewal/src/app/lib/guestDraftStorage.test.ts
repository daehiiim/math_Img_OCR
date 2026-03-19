import { beforeEach, describe, expect, it, vi } from "vitest";

import { clearGuestDraft, readGuestDraft, saveGuestDraft } from "./guestDraftStorage";

class FakeObjectStore {
  constructor(private store: Map<string, Blob>) {}

  put(value: Blob, key: string) {
    this.store.set(key, value);
    return {};
  }

  get(key: string) {
    return {
      result: this.store.get(key),
    };
  }

  delete(key: string) {
    this.store.delete(key);
    return {};
  }
}

class FakeTransaction {
  error: Error | null = null;
  oncomplete: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(private store: Map<string, Blob>) {}

  objectStore() {
    queueMicrotask(() => {
      this.oncomplete?.();
    });
    return new FakeObjectStore(this.store);
  }
}

class FakeDatabase {
  private stores = new Map<string, Map<string, Blob>>();
  objectStoreNames = {
    contains: (name: string) => this.stores.has(name),
  };

  createObjectStore(name: string) {
    this.stores.set(name, new Map());
    return {};
  }

  transaction(name: string) {
    return new FakeTransaction(this.stores.get(name) ?? new Map());
  }

  close() {}
}

class FakeOpenRequest {
  error: Error | null = null;
  onerror: (() => void) | null = null;
  onsuccess: (() => void) | null = null;
  onupgradeneeded: (() => void) | null = null;

  constructor(public result: FakeDatabase, private isFirstOpen: boolean) {
    queueMicrotask(() => {
      if (this.isFirstOpen) {
        this.onupgradeneeded?.();
      }
      this.onsuccess?.();
    });
  }
}

class FakeIndexedDbFactory {
  private database: FakeDatabase | null = null;

  open() {
    const isFirstOpen = this.database === null;
    if (!this.database) {
      this.database = new FakeDatabase();
    }
    return new FakeOpenRequest(this.database, isFirstOpen);
  }
}

describe("guestDraftStorage", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.stubGlobal("indexedDB", new FakeIndexedDbFactory());
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:guest-draft");
  });

  it("메타데이터는 sessionStorage에, 파일은 IndexedDB에 저장하고 복원한다", async () => {
    await saveGuestDraft({
      image: {
        file: new File(["draft"], "draft.png", { type: "image/png" }),
        name: "draft.png",
        mimeType: "image/png",
        width: 320,
        height: 240,
      },
      executionOptions: {
        doOcr: true,
        doImageStylize: false,
        doExplanation: true,
      },
      regions: [
        {
          id: "q1",
          polygon: [
            [0, 0],
            [10, 0],
            [10, 10],
            [0, 10],
          ],
          type: "mixed",
          order: 1,
        },
      ],
    });

    const restoredDraft = await readGuestDraft();

    expect(restoredDraft?.image.url).toBe("blob:guest-draft");
    expect(restoredDraft?.image.file.name).toBe("draft.png");
    expect(restoredDraft?.regions).toHaveLength(1);

    await clearGuestDraft();

    expect(await readGuestDraft()).toBeNull();
  });
});
