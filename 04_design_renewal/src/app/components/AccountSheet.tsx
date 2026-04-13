import { useState } from "react";
import { useNavigate } from "react-router";

import { useAuth } from "../context/AuthContext";
import { useAdmin } from "../context/AdminContext";
import { OpenAiKeyForm } from "./OpenAiKeyForm";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
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
  const { enterAdminMode } = useAdmin();
  const [adminPassword, setAdminPassword] = useState("");
  const [adminErrorMessage, setAdminErrorMessage] = useState<string | null>(null);
  const [isAdminSubmitting, setIsAdminSubmitting] = useState(false);

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

  // 관리자 비밀번호를 검증한 뒤 전용 관리자 보드로 이동한다.
  const handleEnterAdminMode = async () => {
    if (!adminPassword.trim()) {
      setAdminErrorMessage("관리자 비밀번호를 입력해 주세요.");
      return;
    }

    setIsAdminSubmitting(true);
    setAdminErrorMessage(null);

    try {
      await enterAdminMode(adminPassword);
      setAdminPassword("");
      onOpenChange(false);
      navigate("/workspace/admin");
    } catch (error) {
      const message = error instanceof Error ? error.message : "관리자 모드 진입에 실패했습니다.";
      setAdminErrorMessage(message);
    } finally {
      setIsAdminSubmitting(false);
    }
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

          <section className="space-y-3">
            <h3 className="text-[13px] font-semibold text-foreground">관리자 모드</h3>
            <div className="liquid-frost-panel liquid-frost-panel--soft space-y-4 rounded-[24px] px-4 py-4">
              <div>
                <p className="text-[13px] text-foreground">
                  계정 작업 아래에서 관리자 비밀번호를 검증한 뒤 전용 운영 보드로 이동합니다.
                </p>
                <p className="mt-1 text-[12px] text-muted-foreground">
                  인증 성공 시 현재 탭에만 30분 관리자 세션이 저장됩니다.
                </p>
              </div>

              <div className="space-y-2">
                <label htmlFor="admin-mode-password" className="text-[13px] font-medium text-foreground">
                  관리자 비밀번호
                </label>
                <Input
                  id="admin-mode-password"
                  type="password"
                  placeholder="관리자 비밀번호를 입력하세요"
                  value={adminPassword}
                  onChange={(event) => setAdminPassword(event.target.value)}
                  aria-invalid={adminErrorMessage ? "true" : "false"}
                />
              </div>

              {adminErrorMessage ? (
                <div className="rounded-[18px] border border-destructive/20 bg-destructive/5 px-3 py-2 text-[12px] text-destructive">
                  {adminErrorMessage}
                </div>
              ) : null}

              <Button
                type="button"
                className="w-full"
                onClick={() => void handleEnterAdminMode()}
                disabled={isAdminSubmitting}
              >
                관리자 보드 열기
              </Button>
            </div>
          </section>
        </div>
      </SheetContent>
    </Sheet>
  );
}
