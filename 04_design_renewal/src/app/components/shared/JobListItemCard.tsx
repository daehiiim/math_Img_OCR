import type { ComponentType } from "react";
import { Eye, Trash2 } from "lucide-react";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";

interface JobListItemCardProps {
  fileName: string;
  imageUrl: string;
  regionCount: number;
  createdLabel: string;
  jobIdLabel: string;
  statusLabel: string;
  statusVariant: "default" | "secondary" | "outline" | "destructive";
  statusIcon: ComponentType<{ className?: string }>;
  isRunning?: boolean;
  onOpen: () => void;
  onDelete: () => void;
}

/** 최근 작업 카드 한 줄을 썸네일, 상태, 액션 조합으로 렌더링한다. */
export function JobListItemCard({
  fileName,
  imageUrl,
  regionCount,
  createdLabel,
  jobIdLabel,
  statusLabel,
  statusVariant,
  statusIcon: StatusIcon,
  isRunning,
  onOpen,
  onDelete,
}: JobListItemCardProps) {
  return (
    <Card className="cursor-pointer transition-shadow hover:shadow-md" onClick={onOpen}>
      <CardContent className="flex items-center gap-4 py-4">
        <div className="size-14 overflow-hidden rounded-lg bg-muted"><img src={imageUrl} alt={fileName} className="size-full object-cover" /></div>
        <div className="min-w-0 flex-1 space-y-2"><div className="flex items-center gap-2"><p className="truncate text-sm">{fileName}</p><Badge variant={statusVariant}><StatusIcon className={isRunning ? "animate-spin" : undefined} />{statusLabel}</Badge></div><div className="flex flex-wrap gap-3 text-xs text-muted-foreground"><span className="font-mono">{jobIdLabel}</span><span>{regionCount}개 영역</span><span>{createdLabel}</span></div></div>
        <div className="flex items-center gap-1">
          <Button type="button" variant="ghost" size="icon" onClick={(event) => { event.stopPropagation(); onOpen(); }}><Eye /></Button>
          <Button type="button" variant="ghost" size="icon" onClick={(event) => { event.stopPropagation(); onDelete(); }}><Trash2 className="text-destructive" /></Button>
        </div>
      </CardContent>
    </Card>
  );
}
