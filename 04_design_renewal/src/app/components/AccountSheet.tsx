import { useNavigate } from "react-router";

import { useAuth } from "../context/AuthContext";
import { OpenAiKeyForm } from "./OpenAiKeyForm";
import { Button } from "./ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "./ui/sheet";

interface AccountSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** 계정 요약, OpenAI 연결 상태, 계정 액션을 시트에서 관리한다. */
export function AccountSheet({ open, onOpenChange }: AccountSheetProps) {
  const navigate = useNavigate();
  const { user, logout, connectOpenAi, disconnectOpenAi } = useAuth();

  if (!user) {
    return null;
  }

  // 로그아웃 이후 시트를 닫고 홈으로 이동한다.
  const handleLogout = async () => {
    await logout();
    onOpenChange(false);
    navigate("/");
  };

  // 연결 해제는 현재 시트 문맥을 유지한 채 수행한다.
  const handleDisconnect = async () => {
    await disconnectOpenAi();
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-md border-l-0 p-0">
        <SheetHeader className="border-b border-white/55 px-5 pb-4 pt-5">
          <SheetTitle>내 계정</SheetTitle>
          <SheetDescription>OpenAI 연결 상태와 계정 작업을 여기서 바로 관리합니다.</SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-6 overflow-y-auto px-5 pb-6 pt-5">
          <section className="space-y-3">
            <h3 className="text-[13px] font-semibold text-foreground">계정 요약</h3>
            <div className="liquid-frost-panel liquid-frost-panel--soft rounded-[24px] px-4 py-4">
              <p className="text-[16px] font-semibold text-foreground">{user.name}</p>
              <p className="mt-1 text-[13px] text-muted-foreground">{user.email}</p>
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-[13px] font-semibold text-foreground">연결 상태</h3>
            <div className="liquid-chip liquid-chip--accent rounded-[24px] px-4 py-3 text-[12px] text-muted-foreground">
              {user.openAiConnected
                ? "OpenAI 키가 연결되어 있어 바로 재저장하거나 해제할 수 있습니다."
                : "아직 OpenAI 키가 연결되지 않았습니다. 아래 폼에서 바로 저장하세요."}
            </div>
            <OpenAiKeyForm
              title={user.openAiConnected ? "OpenAI key 다시 저장" : "OpenAI key 저장"}
              description="잘못 저장한 key도 여기서 바로 덮어써 수정할 수 있습니다."
              submitLabel={user.openAiConnected ? "OpenAI key 다시 저장" : "OpenAI key 저장"}
              maskedKey={user.openAiMaskedKey}
              onSubmit={connectOpenAi}
            />
          </section>

          <section className="space-y-3">
            <h3 className="text-[13px] font-semibold text-foreground">계정 작업</h3>
            <div className="space-y-3">
              <Button type="button" variant="outline" className="w-full" onClick={() => void handleLogout()}>
                로그아웃
              </Button>
              <Button
                type="button"
                variant="destructive"
                className="w-full"
                onClick={() => void handleDisconnect()}
                disabled={!user.openAiConnected}
              >
                연결 해제
              </Button>
            </div>
          </section>
        </div>
      </SheetContent>
    </Sheet>
  );
}
