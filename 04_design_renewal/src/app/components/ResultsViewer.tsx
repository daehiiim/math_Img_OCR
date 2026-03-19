import { FileText, Image } from "lucide-react";

import type { Region } from "../store/jobStore";
import { parseMathMarkupPreview } from "../lib/mathMarkupPreview";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";

interface ResultsViewerProps {
  regions: Region[];
}

interface MathMarkupPreviewProps {
  value?: string;
  emptyLabel: string;
}

/** 문서에 포함 가능한 텍스트가 있는지 판단한다. */
function isExportableRegion(region: Region): boolean {
  return Boolean(region.ocrText?.trim() || region.explanation?.trim());
}

/** 화면에 표시할 상태 라벨을 계산한다. */
function getRegionStatusLabel(region: Region): string {
  if (region.status === "completed") {
    return "완료";
  }

  if (region.status === "failed") {
    return isExportableRegion(region) ? "부분 완료" : "실패";
  }

  return region.status === "running" ? "처리 중" : "대기";
}

/** 수식 마크업을 읽기 좋은 미리보기 텍스트로 렌더링한다. */
function MathMarkupPreview({ value, emptyLabel }: MathMarkupPreviewProps) {
  if (!value || !value.trim()) {
    return <p className="text-[13px] text-muted-foreground">{emptyLabel}</p>;
  }

  const lines = parseMathMarkupPreview(value);

  return (
    <div className="space-y-1 text-[13px] leading-6 text-foreground">
      {lines.map((segments, lineIndex) => (
        <p key={`${lineIndex}-${segments.length}`} className="min-h-[1.5rem] whitespace-pre-wrap break-words">
          {segments.length > 0 ? (
            segments.map((segment, segmentIndex) =>
              segment.kind === "formula" ? (
                <span
                  key={`${lineIndex}-${segmentIndex}-${segment.value}`}
                  className="mx-[1px] inline rounded-md border border-amber-300/70 bg-amber-100/80 px-1.5 py-0.5 font-semibold text-amber-950"
                >
                  {segment.value}
                </span>
              ) : (
                <span key={`${lineIndex}-${segmentIndex}-${segment.value}`}>{segment.value}</span>
              )
            )
          ) : (
            <span className="whitespace-pre"> </span>
          )}
        </p>
      ))}
    </div>
  );
}

/** 이미지 카드 하나를 렌더링한다. */
function PreviewImageCard({
  title,
  src,
  alt,
  badge,
}: {
  title: string;
  src: string;
  alt: string;
  badge?: string;
}) {
  return (
    <div className="space-y-2 rounded-xl border bg-card p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[12px] font-medium text-foreground">{title}</p>
        {badge ? (
          <Badge variant="outline" className="text-[10px]">
            {badge}
          </Badge>
        ) : null}
      </div>
      <div className="flex min-h-[180px] items-center justify-center overflow-hidden rounded-lg border bg-white p-3">
        <img src={src} alt={alt} className="max-h-[240px] w-full object-contain" />
      </div>
    </div>
  );
}

export function ResultsViewer({ regions }: ResultsViewerProps) {
  if (regions.length === 0) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        <FileText className="mx-auto mb-3 h-10 w-10 opacity-50" />
        <p className="text-[14px]">영역이 없습니다</p>
        <p className="text-[12px]">먼저 영역을 지정하고 파이프라인을 실행하세요.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {regions.map((region) => {
        const exportable = isExportableRegion(region);

        return (
          <Card key={region.id}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-[14px]">
                  <div className="h-3 w-3 rounded-full bg-primary/70" />
                  {region.id}
                  {region.styledImageModel ? (
                    <Badge className="text-[10px]">{region.styledImageModel}</Badge>
                  ) : null}
                </CardTitle>
                <Badge
                  variant={region.status === "completed" || exportable ? "secondary" : "outline"}
                  className="gap-1 px-[8px] py-[2px]"
                >
                  {getRegionStatusLabel(region)}
                </Badge>
              </div>
            </CardHeader>

            {region.status === "failed" ? (
              <CardContent>
                <p className="text-[12px] text-destructive">
                  영역 처리 {exportable ? "경고" : "실패"}: {region.errorReason || "원인 미상"}
                </p>
              </CardContent>
            ) : null}

            {(region.status === "completed" || exportable) ? (
              <CardContent>
                <Tabs defaultValue="ocr">
                  <TabsList>
                    <TabsTrigger value="ocr" className="gap-1.5">
                      <FileText className="h-3.5 w-3.5" />
                      OCR 결과
                    </TabsTrigger>
                    <TabsTrigger value="image-preview" className="gap-1.5">
                      <Image className="h-3.5 w-3.5" />
                      이미지 미리보기
                    </TabsTrigger>
                    <TabsTrigger value="explain" className="gap-1.5">
                      <FileText className="h-3.5 w-3.5" />
                      해설
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="ocr" className="mt-3">
                    <div className="rounded-lg bg-muted/50 p-4">
                      <MathMarkupPreview value={region.ocrText} emptyLabel="OCR 결과 없음" />
                    </div>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      ⓘ 화면에서는 수식 태그를 숨긴 미리보기만 보여주며, HWPX 내보내기 원본은 그대로 유지됩니다.
                    </p>
                  </TabsContent>

                  <TabsContent value="image-preview" className="mt-3">
                    {region.imageCropUrl || region.styledImageUrl ? (
                      <div className="grid gap-3 md:grid-cols-2">
                        {region.imageCropUrl ? (
                          <PreviewImageCard
                            title="원본 크롭"
                            src={region.imageCropUrl}
                            alt={`${region.id} original image`}
                          />
                        ) : null}
                        {region.styledImageUrl ? (
                          <PreviewImageCard
                            title="Nano Banana 결과"
                            src={region.styledImageUrl}
                            alt={`${region.id} styled image`}
                            badge={region.styledImageModel}
                          />
                        ) : null}
                      </div>
                    ) : (
                      <div className="rounded-lg border border-dashed bg-muted/30 p-6 text-center">
                        <p className="text-[12px] text-muted-foreground">
                          변환 대상 이미지가 없어 미리보기를 생성하지 않았습니다.
                        </p>
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="explain" className="mt-3">
                    <div className="rounded-lg bg-muted/50 p-4">
                      <MathMarkupPreview value={region.explanation} emptyLabel="해설 없음" />
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            ) : null}
          </Card>
        );
      })}
    </div>
  );
}
