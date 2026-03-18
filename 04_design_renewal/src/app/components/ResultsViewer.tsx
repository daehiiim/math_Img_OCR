import { Suspense, Component, lazy, useState } from "react";
import { Check, Copy, FileText, Image, Loader2, Pencil } from "lucide-react";

import type { Region, RegionType } from "../store/jobStore";
import { buildAssetPreviewUrl } from "../lib/assetPreviewUrl";
import { copyToClipboard } from "../utils/clipboard";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";

interface ResultsViewerProps {
  regions: Region[];
  onSaveEditedSvg: (regionId: string, svg: string) => Promise<void>;
  onLoadRegionSvg: (regionId: string) => Promise<string>;
}

const regionTypeColors: Record<RegionType, string> = {
  text: "#3b82f6",
  diagram: "#8b5cf6",
  mixed: "#f59e0b",
};

function getRegionColor(type: string | undefined): string {
  if (type === "text" || type === "diagram" || type === "mixed") {
    return regionTypeColors[type];
  }

  return regionTypeColors.mixed;
}

class SvgEditorErrorBoundary extends Component<
  { children: React.ReactNode; onError: (message: string) => void },
  { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode; onError: (message: string) => void }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    this.props.onError(error.message || "SVG 편집기 오류가 발생했습니다.");
  }

  render() {
    if (this.state.hasError) {
      return null;
    }

    return this.props.children;
  }
}

const LazySvgCanvasEditor = lazy(() => import("./SvgCanvasEditor"));

export function ResultsViewer({ regions, onSaveEditedSvg, onLoadRegionSvg }: ResultsViewerProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [editingRegionId, setEditingRegionId] = useState<string | null>(null);
  const [editingSvgText, setEditingSvgText] = useState("");
  const [svgEditorError, setSvgEditorError] = useState<string | null>(null);
  const [svgLoading, setSvgLoading] = useState(false);

  const copyText = (text: string, id: string) => {
    copyToClipboard(text).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  const startEditSvg = async (region: Region) => {
    if (!region.svgUrl && !region.editedSvgUrl) {
      setSvgEditorError("편집할 SVG가 없습니다.");
      return;
    }

    setSvgEditorError(null);
    setSvgLoading(true);

    try {
      const text = await onLoadRegionSvg(region.id);
      if (!text || !text.trim()) {
        setSvgEditorError("SVG 내용이 비어 있습니다.");
        return;
      }

      setEditingSvgText(text);
      setEditingRegionId(region.id);
    } catch (error) {
      const message = error instanceof Error ? error.message : "SVG 불러오기에 실패했습니다.";
      setSvgEditorError(message);
    } finally {
      setSvgLoading(false);
    }
  };

  const cancelEditSvg = () => {
    setEditingRegionId(null);
    setEditingSvgText("");
    setSvgEditorError(null);
  };

  const saveEditedSvg = async (regionId: string, svg: string) => {
    setSvgEditorError(null);

    try {
      await onSaveEditedSvg(regionId, svg);
      setEditingRegionId(null);
      setEditingSvgText("");
    } catch (error) {
      const message = error instanceof Error ? error.message : "SVG 저장에 실패했습니다.";
      setSvgEditorError(message);
    }
  };

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
        const color = getRegionColor(region.type);
        const isEditing = editingRegionId === region.id;
        const previewUrl = region.editedSvgUrl
          ? buildAssetPreviewUrl(region.editedSvgUrl, region.editedSvgVersion)
          : region.svgUrl;

        return (
          <Card key={region.id}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-[14px]">
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
                  {region.id}
                  <Badge variant="outline" className="text-[10px]">
                    {region.type}
                  </Badge>
                  {region.editedSvgUrl && <Badge className="text-[10px]">SVG 수정본</Badge>}
                </CardTitle>
                <Badge
                  variant={region.status === "completed" ? "secondary" : "outline"}
                  className="gap-1 px-[8px] py-[2px]"
                >
                  {region.status === "completed" ? "완료" : region.status === "running" ? "처리 중" : "대기"}
                </Badge>
              </div>
            </CardHeader>

            {region.status === "failed" && (
              <CardContent>
                <p className="text-[12px] text-destructive">
                  영역 처리 실패: {region.errorReason || "원인 미상"}
                </p>
              </CardContent>
            )}

            {region.status === "completed" && (
              <CardContent>
                <Tabs defaultValue="ocr">
                  <TabsList>
                    <TabsTrigger value="ocr" className="gap-1.5">
                      <FileText className="h-3.5 w-3.5" />
                      OCR 결과
                    </TabsTrigger>
                    <TabsTrigger value="svg" className="gap-1.5">
                      <Image className="h-3.5 w-3.5" />
                      SVG 벡터
                    </TabsTrigger>
                    <TabsTrigger value="explain" className="gap-1.5">
                      <FileText className="h-3.5 w-3.5" />
                      해설
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="ocr" className="mt-3">
                    <div className="relative rounded-lg bg-muted/50 p-4">
                      <pre className="whitespace-pre-wrap font-mono text-[13px]">{region.ocrText}</pre>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="absolute right-2 top-2"
                        onClick={() => copyText(region.ocrText || "", `ocr-${region.id}`)}
                      >
                        {copiedId === `ocr-${region.id}` ? (
                          <Check className="h-3.5 w-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </Button>
                    </div>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      ⓘ 백엔드 OCR 결과를 그대로 표시합니다.
                    </p>
                  </TabsContent>

                  <TabsContent value="svg" className="mt-3 space-y-3">
                    <div className="flex items-center justify-center rounded-lg border bg-white p-4">
                      {previewUrl ? (
                        <img
                          src={previewUrl}
                          alt={`${region.id} svg`}
                          className="w-full max-w-md"
                        />
                      ) : (
                        <p className="text-[12px] text-muted-foreground">SVG 결과가 없습니다.</p>
                      )}
                    </div>

                    {!isEditing ? (
                      <Button
                        variant="outline"
                        className="gap-2"
                        disabled={svgLoading}
                        onClick={() => void startEditSvg(region)}
                      >
                        {svgLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Pencil className="h-4 w-4" />}
                        {svgLoading ? "SVG 불러오는 중..." : "SVG 도형 편집"}
                      </Button>
                    ) : (
                      <SvgEditorErrorBoundary
                        key={editingRegionId}
                        onError={(message) => {
                          setSvgEditorError(message);
                          setEditingRegionId(null);
                          setEditingSvgText("");
                        }}
                      >
                        <Suspense fallback={<div className="p-3 text-[12px] text-muted-foreground">SVG 편집기를 불러오는 중입니다...</div>}>
                          <LazySvgCanvasEditor
                            initialSvg={editingSvgText}
                            onCancel={cancelEditSvg}
                            onSave={async (svg) => {
                              await saveEditedSvg(region.id, svg);
                            }}
                          />
                        </Suspense>
                      </SvgEditorErrorBoundary>
                    )}

                    {svgEditorError && <p className="text-[12px] text-destructive">{svgEditorError}</p>}
                    <p className="text-[11px] text-muted-foreground">
                      ⓘ SVG 편집기로 수정 후 저장하면 HWPX 내보내기에 반영됩니다.
                    </p>
                  </TabsContent>

                  <TabsContent value="explain" className="mt-3">
                    <div className="rounded-lg bg-muted/50 p-4">
                      <pre className="whitespace-pre-wrap font-mono text-[13px]">{region.explanation || "해설 없음"}</pre>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            )}
          </Card>
        );
      })}
    </div>
  );
}
