import { useState, useRef, useCallback, useEffect } from "react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import {
  Plus,
  Trash2,
  MousePointer2,
  Square,
  Type,
  Shapes,
  Blend,
  RotateCcw,
} from "lucide-react";
import type { Region, RegionType } from "../store/jobStore";

interface RegionEditorProps {
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  regions: Region[];
  onSaveRegions: (regions: Region[]) => Promise<void> | void;
  disabled?: boolean;
}

const regionTypeConfig: Record<
  RegionType,
  { label: string; color: string; icon: React.ComponentType<{ className?: string }> }
> = {
  text: { label: "텍스트", color: "#3b82f6", icon: Type },
  diagram: { label: "도형", color: "#8b5cf6", icon: Shapes },
  mixed: { label: "혼합", color: "#f59e0b", icon: Blend },
};

export function RegionEditor({
  imageUrl,
  imageWidth,
  imageHeight,
  regions: initialRegions,
  onSaveRegions,
  disabled = false,
}: RegionEditorProps) {
  const [regions, setRegions] = useState<Region[]>(initialRegions);
  const [drawing, setDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState<{ x: number; y: number } | null>(null);
  const [currentPoint, setCurrentPoint] = useState<{ x: number; y: number } | null>(null);
  const [selectedType, setSelectedType] = useState<RegionType>("mixed");
  const [tool, setTool] = useState<"select" | "draw">("draw");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setRegions(initialRegions);
  }, [initialRegions]);

  const getScaledPos = useCallback(
    (e: React.MouseEvent) => {
      const container = containerRef.current;
      if (!container) return { x: 0, y: 0 };
      const rect = container.getBoundingClientRect();
      const scaleX = imageWidth / rect.width;
      const scaleY = imageHeight / rect.height;
      return {
        x: Math.round((e.clientX - rect.left) * scaleX),
        y: Math.round((e.clientY - rect.top) * scaleY),
      };
    },
    [imageWidth, imageHeight]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (tool !== "draw" || disabled) return;
      const pos = getScaledPos(e);
      setDrawing(true);
      setStartPoint(pos);
      setCurrentPoint(pos);
    },
    [tool, disabled, getScaledPos]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!drawing) return;
      setCurrentPoint(getScaledPos(e));
    },
    [drawing, getScaledPos]
  );

  const handleMouseUp = useCallback(() => {
    if (!drawing || !startPoint || !currentPoint) return;
    setDrawing(false);

    const x1 = Math.min(startPoint.x, currentPoint.x);
    const y1 = Math.min(startPoint.y, currentPoint.y);
    const x2 = Math.max(startPoint.x, currentPoint.x);
    const y2 = Math.max(startPoint.y, currentPoint.y);

    // Min size check
    if (Math.abs(x2 - x1) < 20 || Math.abs(y2 - y1) < 20) {
      setStartPoint(null);
      setCurrentPoint(null);
      return;
    }

    const newRegion: Region = {
      id: `q${regions.length + 1}`,
      polygon: [
        [x1, y1],
        [x2, y1],
        [x2, y2],
        [x1, y2],
      ],
      type: selectedType,
      order: regions.length + 1,
    };

    setRegions((prev) => [...prev, newRegion]);
    setStartPoint(null);
    setCurrentPoint(null);
  }, [drawing, startPoint, currentPoint, regions.length, selectedType]);

  const removeRegion = (id: string) => {
    setRegions((prev) =>
      prev
        .filter((r) => r.id !== id)
        .map((r, i) => ({ ...r, order: i + 1 }))
    );
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveError(null);

    try {
      await onSaveRegions(regions);
    } catch (error) {
      const message = error instanceof Error ? error.message : "영역 저장 중 오류가 발생했습니다.";
      setSaveError(message);
    } finally {
      setIsSaving(false);
    }
  };

  const toPercent = (val: number, total: number) => `${(val / total) * 100}%`;

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
          
          <Button
            variant={tool === "draw" ? "default" : "ghost"}
            size="sm"
            onClick={() => setTool("draw")}
            disabled={disabled}
          >
            <Square className="w-3.5 h-3.5 mr-1" />
            영역 그리기
          </Button>
        </div>

        <div className="h-6 w-px bg-border" />

        <div className="flex items-center gap-1">
          {(Object.entries(regionTypeConfig) as [RegionType, typeof regionTypeConfig.text][]).map(
            ([type, cfg]) => {
              const Icon = cfg.icon;
              return (
                <Button
                  key={type}
                  variant={selectedType === type ? "outline" : "ghost"}
                  size="sm"
                  onClick={() => setSelectedType(type)}
                  disabled={disabled}
                  style={
                    selectedType === type
                      ? { borderColor: cfg.color, color: cfg.color }
                      : {}
                  }
                >
                  <Icon className="w-3.5 h-3.5 mr-1" />
                  {cfg.label}
                </Button>
              );
            }
          )}
        </div>

        <div className="h-6 w-px bg-border" />

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setRegions([])}
          disabled={disabled || regions.length === 0}
        >
          <RotateCcw className="w-3.5 h-3.5 mr-1" />
          초기화
        </Button>
      </div>

      {/* Canvas */}
      <div
        ref={containerRef}
        className="relative border rounded-xl overflow-hidden bg-muted cursor-crosshair select-none"
        style={{ aspectRatio: `${imageWidth}/${imageHeight}` }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => {
          if (drawing) {
            setDrawing(false);
            setStartPoint(null);
            setCurrentPoint(null);
          }
        }}
      >
        <img
          src={imageUrl}
          alt="uploaded"
          className="w-full h-full object-contain pointer-events-none"
          draggable={false}
        />

        {/* Existing regions */}
        {regions.map((region) => {
          const xs = region.polygon.map((p) => p[0]);
          const ys = region.polygon.map((p) => p[1]);
          const x1 = Math.min(...xs);
          const y1 = Math.min(...ys);
          const x2 = Math.max(...xs);
          const y2 = Math.max(...ys);
          const cfg = regionTypeConfig[region.type];

          return (
            <div
              key={region.id}
              className="absolute border-2 rounded-sm flex items-start justify-between"
              style={{
                left: toPercent(x1, imageWidth),
                top: toPercent(y1, imageHeight),
                width: toPercent(x2 - x1, imageWidth),
                height: toPercent(y2 - y1, imageHeight),
                borderColor: cfg.color,
                backgroundColor: `${cfg.color}15`,
              }}
            >
              <span
                className="text-[10px] text-white px-1.5 py-0.5 rounded-br-sm"
                style={{ backgroundColor: cfg.color }}
              >
                {region.id} ({cfg.label})
              </span>
              {!disabled && (
                <button
                  className="m-0.5 p-0.5 rounded hover:bg-red-100"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeRegion(region.id);
                  }}
                >
                  <Trash2 className="w-3 h-3 text-red-500" />
                </button>
              )}
            </div>
          );
        })}

        {/* Drawing preview */}
        {drawing && startPoint && currentPoint && (
          <div
            className="absolute border-2 border-dashed rounded-sm pointer-events-none"
            style={{
              left: toPercent(
                Math.min(startPoint.x, currentPoint.x),
                imageWidth
              ),
              top: toPercent(
                Math.min(startPoint.y, currentPoint.y),
                imageHeight
              ),
              width: toPercent(
                Math.abs(currentPoint.x - startPoint.x),
                imageWidth
              ),
              height: toPercent(
                Math.abs(currentPoint.y - startPoint.y),
                imageHeight
              ),
              borderColor: regionTypeConfig[selectedType].color,
              backgroundColor: `${regionTypeConfig[selectedType].color}20`,
            }}
          />
        )}
      </div>

      {/* Region list */}
      {regions.length > 0 && (
        <div className="space-y-2">
          <p className="text-[13px] text-muted-foreground">{regions.length}개 영역</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {regions.map((region) => {
              const cfg = regionTypeConfig[region.type];
              return (
                <div
                  key={region.id}
                  className="flex items-center gap-2 bg-accent/30 rounded-lg px-3 py-2"
                >
                  <div
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: cfg.color }}
                  />
                  <span className="text-[13px] flex-1 font-mono">{region.id}</span>
                  <Badge variant="outline" className="text-[10px]">
                    {cfg.label}
                  </Badge>
                  <span className="text-[11px] text-muted-foreground">
                    #{region.order}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Save button */}
      {!disabled && (
        <div className="flex flex-col items-end gap-2">
          {saveError && <p className="text-[12px] text-destructive">{saveError}</p>}
          <Button
            onClick={() => void handleSave()}
            disabled={regions.length === 0 || isSaving}
            className="gap-2"
          >
            <Plus className="w-4 h-4" />
            {isSaving ? "영역 저장 중..." : `영역 저장 (${regions.length}개)`}
          </Button>
        </div>
      )}
    </div>
  );
}
