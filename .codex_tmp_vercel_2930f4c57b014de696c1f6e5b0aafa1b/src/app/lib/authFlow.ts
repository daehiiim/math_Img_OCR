export interface UploadGateState {
  isAuthenticated: boolean;
  openAiConnected: boolean;
  credits: number;
}

export type UploadGateDecision =
  | "login"
  | "connect-openai"
  | "ready";

export function resolveUploadGate(state: UploadGateState): UploadGateDecision {
  if (!state.isAuthenticated) {
    return "login";
  }

  if (state.openAiConnected || state.credits > 0) {
    return "ready";
  }

  return "connect-openai";
}

export function resolvePostLoginPath(
  state: Pick<UploadGateState, "openAiConnected" | "credits">,
  nextPath = "/new"
): string {
  if (state.openAiConnected || state.credits > 0) {
    return nextPath;
  }

  return "/connect-openai";
}
