import type { JobExecutionOptions, Region } from "../store/jobStore";

export interface GuestDraftExecutionOptions extends JobExecutionOptions {}

export interface GuestDraftImage {
  url: string;
  file: File;
  name: string;
  mimeType: string;
  width: number;
  height: number;
}

export interface GuestDraft {
  image: GuestDraftImage;
  executionOptions: GuestDraftExecutionOptions;
  regions: Region[];
}

export interface GuestDraftSaveInput {
  image: Omit<GuestDraftImage, "url">;
  executionOptions: GuestDraftExecutionOptions;
  regions: Region[];
}

interface StoredGuestDraft {
  image: {
    blobKey: string;
    name: string;
    mimeType: string;
    width: number;
    height: number;
  };
  executionOptions: GuestDraftExecutionOptions;
  regions: Region[];
}

const GUEST_DRAFT_STORAGE_KEY = "math-ocr:guest-draft";
const GUEST_DRAFT_DATABASE_NAME = "math-ocr-guest-drafts";
const GUEST_DRAFT_STORE_NAME = "draft-files";
const GUEST_DRAFT_BLOB_KEY = "active";
const GUEST_DRAFT_SAVE_ERROR = "공개 draft 저장에 실패했습니다. 이미지 크기를 줄이거나 다시 시도해주세요.";

function canUseBrowserStorage(): boolean {
  return typeof window !== "undefined" && typeof window.sessionStorage !== "undefined";
}

function canUseIndexedDb(): boolean {
  return typeof window !== "undefined" && typeof window.indexedDB !== "undefined";
}

/** guest draft용 IndexedDB를 연다. */
function openGuestDraftDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (!canUseIndexedDb()) {
      reject(new Error(GUEST_DRAFT_SAVE_ERROR));
      return;
    }

    const request = window.indexedDB.open(GUEST_DRAFT_DATABASE_NAME, 1);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(GUEST_DRAFT_STORE_NAME)) {
        database.createObjectStore(GUEST_DRAFT_STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error(GUEST_DRAFT_SAVE_ERROR));
  });
}

/** IndexedDB에 공개 draft 파일을 저장한다. */
async function writeGuestDraftFile(file: File): Promise<void> {
  const database = await openGuestDraftDatabase();

  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(GUEST_DRAFT_STORE_NAME, "readwrite");
    transaction.oncomplete = () => {
      database.close();
      resolve();
    };
    transaction.onerror = () => {
      database.close();
      reject(transaction.error ?? new Error(GUEST_DRAFT_SAVE_ERROR));
    };
    transaction.objectStore(GUEST_DRAFT_STORE_NAME).put(file, GUEST_DRAFT_BLOB_KEY);
  });
}

/** IndexedDB에서 공개 draft 파일을 읽는다. */
async function readGuestDraftFile(): Promise<Blob | null> {
  if (!canUseIndexedDb()) {
    return null;
  }

  const database = await openGuestDraftDatabase();

  return new Promise<Blob | null>((resolve, reject) => {
    const transaction = database.transaction(GUEST_DRAFT_STORE_NAME, "readonly");
    const request = transaction.objectStore(GUEST_DRAFT_STORE_NAME).get(GUEST_DRAFT_BLOB_KEY);
    transaction.oncomplete = () => {
      database.close();
      resolve((request.result as Blob | undefined) ?? null);
    };
    transaction.onerror = () => {
      database.close();
      reject(transaction.error ?? new Error(GUEST_DRAFT_SAVE_ERROR));
    };
  });
}

/** IndexedDB에 저장된 공개 draft 파일을 제거한다. */
async function deleteGuestDraftFile(): Promise<void> {
  if (!canUseIndexedDb()) {
    return;
  }

  const database = await openGuestDraftDatabase();

  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(GUEST_DRAFT_STORE_NAME, "readwrite");
    transaction.oncomplete = () => {
      database.close();
      resolve();
    };
    transaction.onerror = () => {
      database.close();
      reject(transaction.error ?? new Error(GUEST_DRAFT_SAVE_ERROR));
    };
    transaction.objectStore(GUEST_DRAFT_STORE_NAME).delete(GUEST_DRAFT_BLOB_KEY);
  });
}

/** 공개 draft를 브라우저 저장소에 기록한다. */
export async function saveGuestDraft(draft: GuestDraftSaveInput): Promise<void> {
  if (!canUseBrowserStorage()) {
    throw new Error(GUEST_DRAFT_SAVE_ERROR);
  }

  const storedDraft: StoredGuestDraft = {
    image: {
      blobKey: GUEST_DRAFT_BLOB_KEY,
      name: draft.image.name,
      mimeType: draft.image.mimeType,
      width: draft.image.width,
      height: draft.image.height,
    },
    executionOptions: draft.executionOptions,
    regions: draft.regions,
  };

  try {
    await writeGuestDraftFile(draft.image.file);
    window.sessionStorage.setItem(GUEST_DRAFT_STORAGE_KEY, JSON.stringify(storedDraft));
  } catch {
    window.sessionStorage.removeItem(GUEST_DRAFT_STORAGE_KEY);
    await deleteGuestDraftFile().catch(() => undefined);
    throw new Error(GUEST_DRAFT_SAVE_ERROR);
  }
}

/** 공개 draft를 브라우저 저장소에서 읽는다. */
export async function readGuestDraft(): Promise<GuestDraft | null> {
  if (!canUseBrowserStorage()) {
    return null;
  }

  const rawDraft = window.sessionStorage.getItem(GUEST_DRAFT_STORAGE_KEY);
  if (!rawDraft) {
    return null;
  }

  let storedDraft: StoredGuestDraft;
  try {
    storedDraft = JSON.parse(rawDraft) as StoredGuestDraft;
  } catch {
    window.sessionStorage.removeItem(GUEST_DRAFT_STORAGE_KEY);
    return null;
  }

  const fileBlob = await readGuestDraftFile().catch(() => null);
  if (!fileBlob) {
    window.sessionStorage.removeItem(GUEST_DRAFT_STORAGE_KEY);
    return null;
  }

  const file = new File([fileBlob], storedDraft.image.name, {
    type: storedDraft.image.mimeType || fileBlob.type || "application/octet-stream",
  });

  return {
    image: {
      url: URL.createObjectURL(file),
      file,
      name: storedDraft.image.name,
      mimeType: storedDraft.image.mimeType,
      width: storedDraft.image.width,
      height: storedDraft.image.height,
    },
    executionOptions: storedDraft.executionOptions,
    regions: storedDraft.regions,
  };
}

/** 공개 draft를 브라우저 저장소에서 삭제한다. */
export async function clearGuestDraft(): Promise<void> {
  if (!canUseBrowserStorage()) {
    return;
  }

  window.sessionStorage.removeItem(GUEST_DRAFT_STORAGE_KEY);
  await deleteGuestDraftFile().catch(() => undefined);
}
