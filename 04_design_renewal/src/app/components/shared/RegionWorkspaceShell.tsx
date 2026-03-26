import type { ReactNode } from "react";
import { RotateCcw } from "lucide-react";

import { Alert, AlertDescription } from "../ui/alert";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";

interface RegionWorkspaceShellProps {
  title: string;
  description?: string;
  fileName: string;
  imageMeta: string;
  regionCount: number;
  error?: string | null;
  resetLabel?: string;
  onReset?: () => void;
  children: ReactNode;
}

/** 영역 편집 헤더의 파일 메타 칩을 공통 형태로 렌더링한다. */
function RegionMetaChip({ children }: { children: ReactNode }) {
  return <span className="rounded-full border bg-background px-3 py-1 text-xs text-muted-foreground">{children}</span>;
}

/** 영역 편집기 외곽 카드와 파일 메타 헤더를 공통 shell로 렌더링한다. */
export function RegionWorkspaceShell({
  title,
  description,
  fileName,
  imageMeta,
  regionCount,
  error,
  resetLabel = "다른 파일 선택",
  onReset,
  children,
}: RegionWorkspaceShellProps) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="gap-4 border-b bg-muted/20">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between"><div className="space-y-1"><CardTitle className="text-base">{title}</CardTitle>{description ? <CardDescription>{description}</CardDescription> : null}</div>{onReset ? <Button type="button" variant="outline" size="sm" className="self-start" onClick={onReset}><RotateCcw data-icon="inline-start" />{resetLabel}</Button> : null}</div>
        <div className="flex flex-wrap items-center gap-2"><RegionMetaChip>{fileName}</RegionMetaChip><RegionMetaChip>{imageMeta}</RegionMetaChip><RegionMetaChip>{`영역 ${regionCount}개`}</RegionMetaChip></div>
        {error ? <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert> : null}
      </CardHeader>
      <CardContent className="px-4 pb-6 pt-6 sm:px-6">{children}</CardContent>
    </Card>
  );
}
