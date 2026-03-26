import { ImageIcon, KeyRound, LogOut, Settings } from "lucide-react";
import { Link, Outlet, useLocation, useNavigate } from "react-router";

import { useAuth } from "../context/AuthContext";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";

/** 인증/온보딩 화면 상단의 계정 메뉴를 공통 드롭다운으로 렌더링한다. */
function AuthHeaderMenu() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  if (!user) {
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="rounded-full">{user.avatarInitials}</Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>{user.name}<p className="mt-1 text-xs font-normal text-muted-foreground">{user.email}</p></DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem asChild><Link to="/connect-openai"><Settings />설정</Link></DropdownMenuItem>
          <DropdownMenuItem asChild><Link to="/pricing"><ImageIcon />이미지 구매</Link></DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" onClick={() => { void logout(); navigate("/"); }}><LogOut />로그아웃</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** 인증 헤더의 남은 이미지와 OpenAI 연결 상태를 배지 조합으로 렌더링한다. */
function AuthHeaderStatus() {
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

/** 로그인, 결제, OpenAI 연결 화면에 쓰는 공통 헤더와 중앙 정렬 레이아웃을 렌더링한다. */
export function AuthLayout() {
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const isLoginPage = location.pathname === "/login";

  return (
    <div className="flex min-h-screen flex-col bg-muted/20">
      <header className="border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4">
          <Link to={isAuthenticated ? "/workspace" : "/"} className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-2xl bg-foreground text-background">M</div>
            <div><p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">MathHWP</p><p className="text-sm">AI 기반 수식 OCR 작업실</p></div>
          </Link>
          {isAuthenticated && !isLoginPage ? <div className="flex items-center gap-3"><AuthHeaderStatus /><AuthHeaderMenu /></div> : null}
        </div>
      </header>
      <main className="flex flex-1 items-center justify-center px-4 py-12"><Outlet /></main>
      <footer className="border-t bg-background/80 py-4 text-center text-xs text-muted-foreground">MathHWP · AI 기반 수식 OCR과 수식 한글 변환 workflow</footer>
    </div>
  );
}
