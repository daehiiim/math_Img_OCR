import { describe, expect, it } from "vitest";

import { resolvePostLoginPath, resolveUploadGate } from "./authFlow";

describe("resolveUploadGate", () => {
  it("로그인하지 않은 사용자는 로그인으로 보낸다", () => {
    expect(
      resolveUploadGate({
        isAuthenticated: false,
        openAiConnected: false,
        credits: 0,
      })
    ).toBe("login");
  });

  it("로그인했고 OpenAI API key가 연결되어 있으면 바로 업로드 가능하다", () => {
    expect(
      resolveUploadGate({
        isAuthenticated: true,
        openAiConnected: true,
        credits: 0,
      })
    ).toBe("ready");
  });

  it("로그인했고 크레딧이 남아 있으면 바로 업로드 가능하다", () => {
    expect(
      resolveUploadGate({
        isAuthenticated: true,
        openAiConnected: false,
        credits: 3,
      })
    ).toBe("ready");
  });

  it("로그인했지만 OpenAI API key와 크레딧이 모두 없으면 연결 페이지로 보낸다", () => {
    expect(
      resolveUploadGate({
        isAuthenticated: true,
        openAiConnected: false,
        credits: 0,
      })
    ).toBe("connect-openai");
  });
});

describe("resolvePostLoginPath", () => {
  it("로그인 후 사용 가능 상태면 원래 경로로 복귀한다", () => {
    expect(
      resolvePostLoginPath({
        openAiConnected: true,
        credits: 0,
      })
    ).toBe("/new");
  });

  it("로그인 후 사용 가능 상태가 아니면 OpenAI 연결 페이지로 이동한다", () => {
    expect(
      resolvePostLoginPath({
        openAiConnected: false,
        credits: 0,
      })
    ).toBe("/connect-openai");
  });

  it("draft 복원 경로는 사용 가능 상태가 아니어도 그대로 유지한다", () => {
    expect(
      resolvePostLoginPath(
        {
          openAiConnected: false,
          credits: 0,
        },
        "/new?resumeDraft=1"
      )
    ).toBe("/new?resumeDraft=1");
  });
});
