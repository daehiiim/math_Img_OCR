export interface StoredProfile {
  name: string;
  email: string;
  avatarInitials: string;
  credits: number;
  openAiConnected: boolean;
  openAiMaskedKey: string | null;
  usedCredits: number;
  chargedJobIds: string[];
}

const PENDING_PATH_KEY = "math-ocr:pending-path";
const PROFILE_STORE_KEY = "math-ocr:profiles";

function canUseStorage() {
  return typeof window !== "undefined";
}

function readProfiles() {
  if (!canUseStorage()) {
    return {} as Record<string, StoredProfile>;
  }

  const raw = window.localStorage.getItem(PROFILE_STORE_KEY);
  if (!raw) {
    return {} as Record<string, StoredProfile>;
  }

  try {
    return JSON.parse(raw) as Record<string, StoredProfile>;
  } catch {
    return {} as Record<string, StoredProfile>;
  }
}

function writeProfiles(profiles: Record<string, StoredProfile>) {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(PROFILE_STORE_KEY, JSON.stringify(profiles));
}

function createAvatarInitials(name: string, email: string) {
  const trimmed = name.trim();
  if (trimmed) {
    return trimmed.slice(0, 1).toUpperCase();
  }

  return email.slice(0, 1).toUpperCase();
}

export function createDefaultProfile(name: string, email: string): StoredProfile {
  return {
    name,
    email,
    avatarInitials: createAvatarInitials(name, email),
    credits: 0,
    openAiConnected: false,
    openAiMaskedKey: null,
    usedCredits: 0,
    chargedJobIds: [],
  };
}

export function readStoredProfile(email: string) {
  const profiles = readProfiles();
  return profiles[email] ?? null;
}

export function saveStoredProfile(profile: StoredProfile) {
  const profiles = readProfiles();
  profiles[profile.email] = profile;
  writeProfiles(profiles);
}

export function clearStoredProfile(email: string) {
  const profiles = readProfiles();
  delete profiles[email];
  writeProfiles(profiles);
}

export function savePendingPath(path: string) {
  if (!canUseStorage()) {
    return;
  }

  window.sessionStorage.setItem(PENDING_PATH_KEY, path);
}

export function readPendingPath() {
  if (!canUseStorage()) {
    return "/workspace";
  }

  return window.sessionStorage.getItem(PENDING_PATH_KEY) ?? "/workspace";
}

export function clearPendingPath() {
  if (!canUseStorage()) {
    return;
  }

  window.sessionStorage.removeItem(PENDING_PATH_KEY);
}
