import { useNavigate } from "react-router";
import { Button } from "./ui/button";
import { ArrowLeft, FileQuestion } from "lucide-react";

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="liquid-page-shell liquid-page-shell--auth flex h-full w-full max-w-[460px] items-center justify-center">
      <section
        aria-label="회복 표면"
        className="liquid-frost-panel liquid-frost-panel--soft w-full rounded-[32px] p-10 text-center"
      >
        <div className="mb-5 flex flex-wrap justify-center gap-2">
          <span className="liquid-chip liquid-chip--accent rounded-full px-4 py-2 text-[12px] font-medium text-foreground">
            Lost in Transit
          </span>
          <span className="liquid-chip rounded-full px-4 py-2 text-[12px] text-foreground/72">
            Return safely
          </span>
        </div>
        <div className="liquid-inline-note mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-[22px]">
          <FileQuestion className="h-8 w-8 text-muted-foreground" />
        </div>
        <h1 className="mb-2 text-[24px] tracking-[-0.02em] text-foreground">페이지를 찾을 수 없습니다</h1>
        <p className="mb-6 text-[14px] text-muted-foreground">
          요청하신 페이지가 존재하지 않습니다.
        </p>
        <Button onClick={() => navigate("/")} variant="glass" size="pill" className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          홈으로 돌아가기
        </Button>
      </section>
    </div>
  );
}
