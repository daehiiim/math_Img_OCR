export interface StoredAdminSession {
  sessionToken: string;
  expiresAt: string;
}

const ADMIN_SESSION_KEY = "math-ocr:admin-session";

/** 브라우저 저장소 접근 가능 여부를 판단한다. */
function canUseStorage() {
  return typeof window !== "undefined";
}

/** 관리자 세션 만료 시각이 현재보다 지났는지 확인한다. */
export function isAdminSessionExpired(session: StoredAdminSession, now = new Date()) {
  return Number.isNaN(Date.parse(session.expiresAt)) || new Date(session.expiresAt) <= now;
}

/** 관리자 세션을 탭 단위 sessionStorage에 저장한다. */
export function saveAdminSession(session: StoredAdminSession) {
  if (!canUseStorage()) {
    return;
  }

  window.sessionStorage.setItem(ADMIN_SESSION_KEY, JSON.stringify(session));
}

/** 저장된 관리자 세션을 읽고, 손상되었거나 만료되면 자동으로 지운다. */
export function readAdminSession() {
  if (!canUseStorage()) {
    return null;
  }

  const raw = window.sessionStorage.getItem(ADMIN_SESSION_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as StoredAdminSession;
    if (!parsed.sessionToken || !parsed.expiresAt || isAdminSessionExpired(parsed)) {
      clearAdminSession();
      return null;
    }
    return parsed;
  } catch {
    clearAdminSession();
    return null;
  }
}

/** 저장된 관리자 세션을 제거한다. */
export function clearAdminSession() {
  if (!canUseStorage()) {
    return;
  }

  window.sessionStorage.removeItem(ADMIN_SESSION_KEY);
}
