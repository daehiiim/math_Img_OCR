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

export function AccountSheet({ open, onOpenChange }: AccountSheetProps) {
  const navigate = useNavigate();
  const { user, logout, connectOpenAi, disconnectOpenAi } = useAuth();

  if (!user) {
    return null;
  }

  const handleLogout = async () => {
    await logout();
    onOpenChange(false);
    navigate("/");
  };

  const handleDisconnect = async () => {
    await disconnectOpenAi();
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-md">
        <SheetHeader className="border-b border-border">
          <SheetTitle>내 계정</SheetTitle>
          <SheetDescription>OpenAI 연결 상태와 계정 작업을 여기서 바로 관리합니다.</SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-6 overflow-y-auto px-4 pb-6">
          <section className="rounded-xl border border-border bg-muted/20 px-4 py-4">
            <p className="text-[16px] font-semibold text-foreground">{user.name}</p>
            <p className="mt-1 text-[13px] text-muted-foreground">{user.email}</p>
          </section>

          <OpenAiKeyForm
            title={user.openAiConnected ? "OpenAI key 다시 저장" : "OpenAI key 저장"}
            description="잘못 저장한 key도 여기서 바로 덮어써 수정할 수 있습니다."
            submitLabel={user.openAiConnected ? "OpenAI key 다시 저장" : "OpenAI key 저장"}
            maskedKey={user.openAiMaskedKey}
            onSubmit={connectOpenAi}
          />

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
        </div>
      </SheetContent>
    </Sheet>
  );
}
