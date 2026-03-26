import { CheckCircle2, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "../ui/badge";
import { Card, CardContent } from "../ui/card";
import { Progress } from "../ui/progress";
import { PageIntro } from "./PageIntro";

interface PipelineProgressHeaderProps {
  title: string;
  subtitle: string;
  backHref: string;
  backLabel: string;
  badge?: ReactNode;
  steps: Array<{ key: string; label: string }>;
  currentStep: number;
  running?: boolean;
  progress?: number;
  progressLabel?: string;
}

/** 진행 단계 점 하나를 현재 상태에 맞는 시각 표현으로 렌더링한다. */
function PipelineStepDot({ index, currentStep, running }: { index: number; currentStep: number; running?: boolean }) {
  if (index < currentStep) return <div className="flex size-7 items-center justify-center rounded-full bg-emerald-500 text-white"><CheckCircle2 className="size-4" /></div>;
  if (index === currentStep && running) return <div className="flex size-7 items-center justify-center rounded-full bg-primary text-primary-foreground"><Loader2 className="size-4 animate-spin" /></div>;
  return <div className={`flex size-7 items-center justify-center rounded-full text-xs ${index === currentStep ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>{index + 1}</div>;
}

/** 작업 상세 상단 소개와 단계 진행 상태를 공통 헤더 패턴으로 렌더링한다. */
export function PipelineProgressHeader({
  title,
  subtitle,
  backHref,
  backLabel,
  badge,
  steps,
  currentStep,
  running,
  progress,
  progressLabel,
}: PipelineProgressHeaderProps) {
  return (
    <div className="space-y-6">
      <PageIntro title={title} description={subtitle} backHref={backHref} backLabel={backLabel} badge={typeof badge === "string" ? <Badge variant="outline">{badge}</Badge> : badge} />
      <Card><CardContent className="space-y-4 pt-6"><div className="flex items-center gap-2">{steps.map((step, index) => <div key={step.key} className="flex flex-1 items-center gap-2"><div className="flex items-center gap-2"><PipelineStepDot index={index} currentStep={currentStep} running={running} /><span className={`hidden text-xs sm:inline ${index === currentStep ? "text-foreground" : "text-muted-foreground"}`}>{step.label}</span></div>{index < steps.length - 1 ? <div className={`h-px flex-1 ${index < currentStep ? "bg-emerald-500" : "bg-border"}`} /> : null}</div>)}</div>{running ? <div className="space-y-2"><Progress value={progress} className="h-1.5" />{progressLabel ? <p className="text-xs text-muted-foreground">{progressLabel}</p> : null}</div> : null}</CardContent></Card>
    </div>
  );
}
