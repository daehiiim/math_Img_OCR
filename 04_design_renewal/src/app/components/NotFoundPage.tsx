import { StatusPanel } from "./shared/StatusPanel";

/** 존재하지 않는 경로를 공통 상태 패널로 안내한다. */
export function NotFoundPage() {
  return (
    <div className="flex min-h-full items-center justify-center px-4 py-12">
      <StatusPanel
        title="페이지를 찾을 수 없습니다"
        description="요청하신 페이지가 존재하지 않습니다."
        tone="warning"
        badge="404"
        primaryAction={{ label: "홈으로 돌아가기", href: "/" }}
      />
    </div>
  );
}
