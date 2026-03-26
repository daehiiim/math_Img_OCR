import { useNavigate } from "react-router";

import { useAuth } from "../context/AuthContext";
import { OpenAiKeyForm } from "./OpenAiKeyForm";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Separator } from "./ui/separator";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "./ui/sheet";

interface AccountSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** 계정 시트의 프로필 카드 섹션을 렌더링한다. */
function AccountProfileCard({ name, email }: { name: string; email: string }) {
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">{name}</CardTitle></CardHeader>
      <CardContent><p className="text-sm text-muted-foreground">{email}</p></CardContent>
    </Card>
  );
}

/** 계정 시트에서 OpenAI 연결과 로그아웃을 함께 관리한다. */
export function AccountSheet({ open, onOpenChange }: AccountSheetProps) {
  const navigate = useNavigate();
  const { user, logout, connectOpenAi, disconnectOpenAi } = useAuth();

  if (!user) {
    return null;
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-md">
        <SheetHeader className="border-b">
          <SheetTitle>내 계정</SheetTitle>
          <SheetDescription>OpenAI 연결 상태와 계정 작업을 여기서 바로 관리합니다.</SheetDescription>
        </SheetHeader>
        <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-4 pb-6">
          <AccountProfileCard name={user.name} email={user.email} />
          <Card>
            <CardHeader><CardTitle className="text-base">{user.openAiConnected ? "OpenAI key 다시 저장" : "OpenAI key 저장"}</CardTitle></CardHeader>
            <CardContent><OpenAiKeyForm title={user.openAiConnected ? "OpenAI key 다시 저장" : "OpenAI key 저장"} description="잘못 저장한 key도 여기서 바로 덮어써 수정할 수 있습니다." submitLabel={user.openAiConnected ? "OpenAI key 다시 저장" : "OpenAI key 저장"} maskedKey={user.openAiMaskedKey} onSubmit={connectOpenAi} /></CardContent>
          </Card>
          <Separator />
          <div className="space-y-3">
            <Button type="button" variant="outline" className="w-full" onClick={() => { void logout(); onOpenChange(false); navigate("/"); }}>로그아웃</Button>
            <Button type="button" variant="destructive" className="w-full" disabled={!user.openAiConnected} onClick={() => void disconnectOpenAi()}>연결 해제</Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
