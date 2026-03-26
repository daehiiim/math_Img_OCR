import type { ReactNode } from "react";
import { ArrowLeft } from "lucide-react";
import { Link } from "react-router";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { cn } from "../ui/utils";

interface PageIntroProps {
  title: string;
  description?: string;
  badge?: ReactNode;
  backHref?: string;
  backLabel?: string;
  actions?: ReactNode;
  align?: "start" | "center";
  eyebrow?: string;
  meta?: ReactNode;
}

/** 문자열 배지는 공통 Badge 스타일로 감싼다. */
function IntroBadge({ badge }: { badge?: ReactNode }) {
  if (!badge) {
    return null;
  }

  return typeof badge === "string" ? <Badge variant="secondary">{badge}</Badge> : <>{badge}</>;
}

/** 페이지 상단의 뒤로가기 링크를 일관된 버튼 스타일로 렌더링한다. */
function IntroBackLink({ backHref, backLabel }: Pick<PageIntroProps, "backHref" | "backLabel">) {
  if (!backHref || !backLabel) {
    return null;
  }

  return (
    <Button asChild variant="ghost" size="sm" className="w-fit gap-2 px-0 text-muted-foreground">
      <Link to={backHref}>
        <ArrowLeft data-icon="inline-start" />
        {backLabel}
      </Link>
    </Button>
  );
}

/** 페이지 제목, 설명, 상태 배지와 보조 액션을 공통 헤더 패턴으로 묶는다. */
export function PageIntro({
  title,
  description,
  badge,
  backHref,
  backLabel,
  actions,
  align = "start",
  eyebrow,
  meta,
}: PageIntroProps) {
  const centered = align === "center";

  return (
    <div className={cn("flex flex-col gap-4", centered && "items-center text-center")}>
      <IntroBackLink backHref={backHref} backLabel={backLabel} />
      <div className={cn("flex flex-col gap-4", !centered && "sm:flex-row sm:items-start sm:justify-between")}>
        <div className="flex flex-col gap-2">
          {eyebrow ? <p className="text-sm font-medium text-muted-foreground">{eyebrow}</p> : null}
          <div className={cn("flex flex-wrap items-center gap-2", centered && "justify-center")}>
            <h1>{title}</h1>
            <IntroBadge badge={badge} />
          </div>
          {description ? <p className="max-w-3xl text-sm text-muted-foreground">{description}</p> : null}
          {meta}
        </div>
        {actions ? <div className={cn("flex shrink-0", centered && "justify-center")}>{actions}</div> : null}
      </div>
    </div>
  );
}
