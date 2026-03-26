import { FileText, Image } from "lucide-react";

import type { Region } from "../../store/jobStore";
import { parseMathMarkupPreview } from "../../lib/mathMarkupPreview";
import { Badge } from "../ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";

interface ResultRegionCardProps {
  region: Region;
}

/** 문서에 포함 가능한 텍스트가 있는지 판단한다. */
function isExportableRegion(region: Region): boolean {
  return Boolean(region.problemMarkdown?.trim() || region.explanationMarkdown?.trim() || region.ocrText?.trim() || region.explanation?.trim());
}

/** 검증 경고 메시지를 정리해 반환한다. */
function getVerificationWarnings(region: Region): string[] {
  return (region.verificationWarnings ?? []).map((warning) => warning.trim()).filter(Boolean);
}

/** 검증 경고가 있는 영역인지 판단한다. */
function hasVerificationWarning(region: Region): boolean {
  return region.verificationStatus === "warning" || region.verificationStatus === "unverified" || getVerificationWarnings(region).length > 0;
}

/** 문제 탭에 표시할 우선순위 본문을 고른다. */
function getProblemPreviewValue(region: Region): string | undefined {
  return region.problemMarkdown?.trim() ? region.problemMarkdown : region.ocrText;
}

/** 해설 탭에 표시할 우선순위 본문을 고른다. */
function getExplanationPreviewValue(region: Region): string | undefined {
  return region.explanationMarkdown?.trim() ? region.explanationMarkdown : region.explanation;
}

/** 화면에 표시할 상태 라벨을 계산한다. */
function getRegionStatusLabel(region: Region): string {
  if (region.status === "completed") return "완료";
  if (region.status === "failed") return isExportableRegion(region) ? "부분 완료" : "실패";
  return region.status === "running" ? "처리 중" : "대기";
}

/** 수식 마크업을 읽기 좋은 미리보기 텍스트로 렌더링한다. */
function MathMarkupPreview({ value, emptyLabel }: { value?: string; emptyLabel: string }) {
  if (!value || !value.trim()) return <p className="text-sm text-muted-foreground">{emptyLabel}</p>;
  const lines = parseMathMarkupPreview(value);
  return <div className="space-y-1 text-sm leading-6 text-foreground">{lines.map((segments, lineIndex) => <p key={`${lineIndex}-${segments.length}`} className="min-h-[1.5rem] whitespace-pre-wrap break-words">{segments.length > 0 ? segments.map((segment, segmentIndex) => segment.kind === "formula" ? <span key={`${lineIndex}-${segmentIndex}-${segment.value}`} className="mx-[1px] inline rounded-md border border-amber-300/70 bg-amber-100/80 px-1.5 py-0.5 font-semibold text-amber-950">{segment.value}</span> : <span key={`${lineIndex}-${segmentIndex}-${segment.value}`}>{segment.value}</span>) : <span className="whitespace-pre"> </span>}</p>)}</div>;
}

/** 이미지 카드 하나를 렌더링한다. */
function PreviewImageCard({ title, src, alt }: { title: string; src: string; alt: string }) {
  return <div className="space-y-2 rounded-xl border bg-card p-3"><p className="text-xs font-medium text-foreground">{title}</p><div className="flex min-h-[180px] items-center justify-center overflow-hidden rounded-lg border bg-white p-3"><img src={src} alt={alt} className="max-h-[240px] w-full object-contain" /></div></div>;
}

/** 결과 영역 카드 하나를 검증 경고, 탭, 이미지 미리보기 조합으로 렌더링한다. */
export function ResultRegionCard({ region }: ResultRegionCardProps) {
  const exportable = isExportableRegion(region);
  const verificationWarnings = getVerificationWarnings(region);
  const verificationWarningVisible = hasVerificationWarning(region);

  return (
    <Card>
      <CardHeader className="pb-3"><div className="flex items-center justify-between"><CardTitle className="flex items-center gap-2 text-sm"><div className="h-3 w-3 rounded-full bg-primary/70" />{region.id}</CardTitle><div className="flex items-center gap-2">{verificationWarningVisible ? <Badge variant="outline" className="border-amber-300 bg-amber-50 text-amber-800">검증 경고</Badge> : null}<Badge variant={region.status === "completed" || exportable ? "secondary" : "outline"}>{getRegionStatusLabel(region)}</Badge></div></div></CardHeader>
      {region.status === "failed" ? <CardContent><p className="text-xs text-destructive">{`영역 처리 ${exportable ? "경고" : "실패"}: ${region.errorReason || "원인 미상"}`}</p></CardContent> : null}
      {verificationWarningVisible ? <CardContent className="pt-0"><div className="rounded-xl border border-amber-200 bg-amber-50 p-3"><div className="flex items-center gap-2"><Badge variant="outline" className="border-amber-300 bg-white text-[10px] text-amber-800">검증 경고</Badge><p className="text-xs font-medium text-amber-950">정답과 해설 일치 여부를 다시 확인하세요.</p></div><div className="mt-2 space-y-1">{verificationWarnings.length > 0 ? verificationWarnings.map((warning) => <p key={warning} className="text-xs text-amber-900">{warning}</p>) : <p className="text-xs text-amber-900">상세 경고가 제공되지 않았습니다.</p>}</div></div></CardContent> : null}
      {region.status === "completed" || exportable ? <CardContent><Tabs defaultValue="ocr"><TabsList><TabsTrigger value="ocr"><FileText />OCR 결과</TabsTrigger><TabsTrigger value="image-preview"><Image />이미지 미리보기</TabsTrigger><TabsTrigger value="explain"><FileText />해설</TabsTrigger></TabsList><TabsContent value="ocr" className="mt-3"><div className="rounded-lg bg-muted/50 p-4"><MathMarkupPreview value={getProblemPreviewValue(region)} emptyLabel="OCR 결과 없음" /></div><p className="mt-2 text-xs text-muted-foreground">ⓘ 화면에서는 수식 마크업을 숨긴 미리보기만 보여주며, HWPX 내보내기 원본은 그대로 유지됩니다.</p></TabsContent><TabsContent value="image-preview" className="mt-3">{region.cropUrl || region.imageCropUrl || region.styledImageUrl ? <div className="grid gap-3 md:grid-cols-3">{region.cropUrl ? <PreviewImageCard title="문제 영역 크롭" src={region.cropUrl} alt={`${region.id} 문제 영역 크롭`} /> : null}{region.imageCropUrl ? <PreviewImageCard title="이미지 추출 원본" src={region.imageCropUrl} alt={`${region.id} 이미지 추출 원본`} /> : null}{region.styledImageUrl ? <PreviewImageCard title="이미지 생성 결과" src={region.styledImageUrl} alt={`${region.id} 이미지 생성 결과`} /> : null}</div> : <div className="rounded-lg border border-dashed bg-muted/30 p-6 text-center"><p className="text-xs text-muted-foreground">변환 대상 이미지가 없어 미리보기를 생성하지 않았습니다.</p></div>}</TabsContent><TabsContent value="explain" className="mt-3"><div className="rounded-lg bg-muted/50 p-4"><MathMarkupPreview value={getExplanationPreviewValue(region)} emptyLabel="해설 없음" /></div></TabsContent></Tabs></CardContent> : null}
    </Card>
  );
}
