import { ImageIcon, KeyRound, LogOut } from "lucide-react";
import { Link, Outlet, useNavigate } from "react-router";

import { useAuth } from "../context/AuthContext";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";

/** 작업실 상단 상태 배지를 공통 조합으로 렌더링한다. */
function StudioHeaderStatus() {
  const { user } = useAuth();

  if (!user) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <Badge variant="outline"><ImageIcon />{`${user.credits}개 이미지 남음`}</Badge>
      {user.openAiConnected ? <Badge variant="secondary"><KeyRound />OpenAI 연결됨</Badge> : null}
    </div>
  );
}

/** 공개 작업 시작 화면과 인증 전 새 작업 진입점을 위한 공통 헤더 레이아웃을 렌더링한다. */
export function StudioLayout() {
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuth();

  return (
    <div className="min-h-screen bg-muted/20">
      <header className="border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4">
          <Link to="/" className="flex items-center gap-3"><div className="flex size-10 items-center justify-center rounded-2xl bg-foreground text-background">M</div><div><p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">MathHWP</p><p className="text-sm">수식 이미지 작업실</p></div></Link>
          <div className="flex items-center gap-2">
            {isAuthenticated ? <><StudioHeaderStatus /><Button variant="outline" onClick={() => navigate("/workspace")}>내 작업실</Button><Button variant="ghost" onClick={() => { void logout(); navigate("/"); }}><LogOut data-icon="inline-start" />로그아웃</Button></> : <><Button variant="ghost" onClick={() => navigate("/pricing")}>가격</Button><Button onClick={() => navigate("/login")}>로그인</Button></>}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-8 lg:px-8"><Outlet /></main>
    </div>
  );
}
