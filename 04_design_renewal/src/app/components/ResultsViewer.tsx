import { Tabs, TabsList, TabsTrigger, TabsContent } from "./ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import {
  FileText,
  Image,
  Code,
  CheckCircle2,
  Loader2,
  Clock,
  Copy,
  Check,
} from "lucide-react";
import { Button } from "./ui/button";
import { useState } from "react";
import type { Region, RegionType } from "../store/jobStore";
import { copyToClipboard } from "../utils/clipboard";

interface ResultsViewerProps {
  regions: Region[];
}

const regionTypeColors: Record<RegionType, string> = {
  text: "#3b82f6",
  diagram: "#8b5cf6",
  mixed: "#f59e0b",
};

const statusIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  pending: Clock,
  running: Loader2,
  completed: CheckCircle2,
};

export function ResultsViewer({ regions }: ResultsViewerProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const copyText = (text: string, id: string) => {
    copyToClipboard(text).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  if (regions.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <FileText className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p className="text-[14px]">영역이 없습니다</p>
        <p className="text-[12px]">먼저 영역을 지정하고 파이프라인을 실행하세요.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {regions.map((region) => {
        const StatusIcon = statusIcons[region.status || "pending"];
        const color = regionTypeColors[region.type];

        return (
          <Card key={region.id}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-[14px] flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  {region.id}
                  <Badge variant="outline" className="text-[10px]">
                    {region.type}
                  </Badge>
                </CardTitle>
                <Badge
                  variant={region.status === "completed" ? "secondary" : "outline"}
                  className="gap-1 px-[8px] py-[2px]"
                >
                  
                  {region.status === "completed"
                    ? "완료"
                    : region.status === "running"
                    ? "처리 중"
                    : "대기"}
                </Badge>
              </div>
            </CardHeader>
            {region.status === "completed" && (
              <CardContent>
                <Tabs defaultValue="ocr">
                  <TabsList>
                    <TabsTrigger value="ocr" className="gap-1.5">
                      <FileText className="w-3.5 h-3.5" />
                      OCR 결과
                    </TabsTrigger>
                    <TabsTrigger value="svg" className="gap-1.5">
                      <Image className="w-3.5 h-3.5" />
                      SVG 벡터
                    </TabsTrigger>
                    <TabsTrigger value="raw" className="gap-1.5">
                      <Code className="w-3.5 h-3.5" />
                      Raw
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="ocr" className="mt-3">
                    <div className="bg-muted/50 rounded-lg p-4 relative">
                      <pre className="text-[13px] whitespace-pre-wrap font-mono">
                        {region.ocrText}
                      </pre>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="absolute top-2 right-2"
                        onClick={() =>
                          copyText(region.ocrText || "", `ocr-${region.id}`)
                        }
                      >
                        {copiedId === `ocr-${region.id}` ? (
                          <Check className="w-3.5 h-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </Button>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-2">
                      ⓘ Mock OCR 결과입니다. 실제 엔진(PaddleOCR/Tesseract) 연결 시 실 인식 결과로
                      대체됩니다.
                    </p>
                  </TabsContent>

                  <TabsContent value="svg" className="mt-3">
                    <div className="bg-white border rounded-lg p-4 flex items-center justify-center">
                      <div
                        className="w-full max-w-md"
                        dangerouslySetInnerHTML={{
                          __html: region.svgData || "",
                        }}
                      />
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-2">
                      ⓘ Polygon 기반 mock SVG입니다. OpenCV contour 벡터화로 향후 개선 예정입니다.
                    </p>
                  </TabsContent>

                  <TabsContent value="raw" className="mt-3">
                    <div className="bg-muted/50 rounded-lg p-4 relative overflow-x-auto">
                      <pre className="text-[11px] font-mono text-muted-foreground">
                        {JSON.stringify(
                          {
                            region_id: region.id,
                            type: region.type,
                            polygon: region.polygon,
                            order: region.order,
                            status: region.status,
                            outputs: {
                              ocr: `outputs/${region.id}.txt`,
                              svg: `outputs/${region.id}.svg`,
                              crop: `outputs/${region.id}_crop.txt`,
                            },
                          },
                          null,
                          2
                        )}
                      </pre>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="absolute top-2 right-2"
                        onClick={() =>
                          copyText(
                            JSON.stringify(region, null, 2),
                            `raw-${region.id}`
                          )
                        }
                      >
                        {copiedId === `raw-${region.id}` ? (
                          <Check className="w-3.5 h-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </Button>
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