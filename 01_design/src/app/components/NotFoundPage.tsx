import { useNavigate } from "react-router";
import { Button } from "./ui/button";
import { ArrowLeft, FileQuestion } from "lucide-react";

export function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <FileQuestion className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
        <h1 className="mb-2">페이지를 찾을 수 없습니다</h1>
        <p className="text-muted-foreground text-[14px] mb-6">
          요청하신 페이지가 존재하지 않습니다.
        </p>
        <Button onClick={() => navigate("/")} variant="outline" className="gap-2">
          <ArrowLeft className="w-4 h-4" />
          대시보드로 돌아가기
        </Button>
      </div>
    </div>
  );
}
