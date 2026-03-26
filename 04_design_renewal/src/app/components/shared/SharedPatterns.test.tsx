import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { ExecutionOptionsPanel } from "./ExecutionOptionsPanel";
import { PageIntro } from "./PageIntro";
import { StatusPanel } from "./StatusPanel";
import { UserCreditPill } from "./UserCreditPill";

describe("shared presentation patterns", () => {
  it("PageIntro는 뒤로가기, 제목, 설명, 상태 배지, 액션을 함께 노출한다", () => {
    render(
      <MemoryRouter>
        <PageIntro
          title="결제 완료하기"
          description="Polar checkout으로 안전하게 결제됩니다."
          badge="결제 준비"
          backHref="/pricing"
          backLabel="가격 페이지로 돌아가기"
          actions={<button type="button">보조 액션</button>}
        />
      </MemoryRouter>
    );

    expect(screen.getByRole("link", { name: "가격 페이지로 돌아가기" })).toHaveAttribute(
      "href",
      "/pricing"
    );
    expect(screen.getByText("결제 완료하기")).toBeInTheDocument();
    expect(screen.getByText("Polar checkout으로 안전하게 결제됩니다.")).toBeInTheDocument();
    expect(screen.getByText("결제 준비")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "보조 액션" })).toBeInTheDocument();
  });

  it("StatusPanel은 경고 메시지와 CTA를 카드 안에 함께 보여준다", () => {
    render(
      <MemoryRouter>
        <StatusPanel
          title="페이지를 찾을 수 없습니다"
          description="요청하신 페이지가 존재하지 않습니다."
          tone="warning"
          badge="404"
          primaryAction={{ label: "홈으로 돌아가기", href: "/" }}
          secondaryAction={{ label: "워크스페이스", href: "/workspace" }}
        />
      </MemoryRouter>
    );

    expect(screen.getByRole("alert")).toHaveTextContent("요청하신 페이지가 존재하지 않습니다.");
    expect(screen.getByText("404")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "홈으로 돌아가기" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "워크스페이스" })).toHaveAttribute(
      "href",
      "/workspace"
    );
  });

  it("UserCreditPill은 남은 이미지, 사용량, OpenAI 연결 상태와 CTA를 함께 보여준다", async () => {
    const user = userEvent.setup();
    const handleAction = vi.fn();

    render(
      <UserCreditPill
        credits={7}
        usedCredits={11}
        openAiConnected={true}
        actionLabel="이미지 충전"
        onAction={handleAction}
      />
    );

    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("11")).toBeInTheDocument();
    expect(screen.getByText("OpenAI 연결됨")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "이미지 충전" }));

    expect(handleAction).toHaveBeenCalledTimes(1);
  });

  it("ExecutionOptionsPanel은 옵션 목록, 예상 차감, 경고 문구와 실행 버튼을 함께 렌더링한다", async () => {
    const user = userEvent.setup();
    const handleToggle = vi.fn();
    const handleRun = vi.fn();

    render(
      <ExecutionOptionsPanel
        title="파이프라인 실행"
        description="원하는 작업만 선택해서 실행할 수 있습니다."
        options={[
          {
            id: "do-ocr",
            key: "doOcr",
            label: "문제 타이핑",
            description: "OCR과 수식 추출을 실행합니다.",
          },
          {
            id: "do-image",
            key: "doImageStylize",
            label: "이미지 생성",
            description: "이미지 생성 결과를 만듭니다.",
          },
        ]}
        values={{
          doOcr: true,
          doImageStylize: false,
          doExplanation: false,
        }}
        requiredCredits={3}
        summary="선택한 문제 수 기준으로 잔액을 먼저 확인합니다."
        warning="검증 경고 2개가 있어 결과를 다시 확인하세요."
        actionLabel="파이프라인 실행"
        onToggle={handleToggle}
        onAction={handleRun}
      />
    );

    expect(screen.getByRole("heading", { name: "파이프라인 실행" })).toBeInTheDocument();
    expect(screen.getByText("3 크레딧")).toBeInTheDocument();
    expect(screen.getByText("검증 경고 2개가 있어 결과를 다시 확인하세요.")).toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: "문제 타이핑" }));
    await user.click(screen.getByRole("button", { name: "파이프라인 실행" }));

    expect(handleToggle).toHaveBeenCalledWith("doOcr", false);
    expect(handleRun).toHaveBeenCalledTimes(1);
  });
});
