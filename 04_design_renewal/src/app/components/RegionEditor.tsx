import { useCallback, useEffect, useRef, useState } from "react";
import { Plus, RotateCcw, Trash2 } from "lucide-react";

import {
  buildPolygonFromRect,
  buildRectFromPoints,
  getImagePointFromClient,
  getRectFromPolygon,
  isRectLargeEnough,
  normalizeInputDevice,
  resizeRectFromHandle,
  resolveMinimumRegionSize,
  type ImagePoint,
  type ResizeHandle,
  type RegionRect,
} from "../lib/regionGeometry";
import { AUTO_FULL_RISK_MESSAGE } from "../lib/regionSelection";
import type { InputDevice, Region } from "../store/jobStore";
import { Button } from "./ui/button";

interface RegionEditorProps {
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  regions: Region[];
  onSaveRegions: (regions: Region[]) => Promise<void> | void;
  onRegionsChange?: (regions: Region[]) => void;
  disabled?: boolean;
}

interface DrawInteraction {
  kind: "draw";
  pointerId: number;
  inputDevice: InputDevice;
  start: ImagePoint;
  current: ImagePoint;
}

interface ResizeInteraction {
  kind: "resize";
  pointerId: number;
  inputDevice: InputDevice;
  regionId: string;
  handle: ResizeHandle;
  baseRect: RegionRect;
  current: ImagePoint;
}

type PointerInteraction = DrawInteraction | ResizeInteraction;

const REGION_BORDER_COLOR = "#2563eb";
const REGION_FILL_COLOR = "rgba(37, 99, 235, 0.12)";
const REGION_LABEL_COLOR = "#1d4ed8";
const RESIZE_HANDLES: ResizeHandle[] = ["nw", "ne", "se", "sw"];

/** 새 수동 영역을 생성한다. */
function buildManualRegion(regions: Region[], rect: RegionRect, inputDevice: InputDevice): Region {
  return {
    id: `q${regions.length + 1}`,
    polygon: buildPolygonFromRect(rect),
    type: "mixed",
    order: regions.length + 1,
    selectionMode: "manual",
    inputDevice,
    warningLevel: "normal",
  };
}


/** 리사이즈 결과를 기존 영역에 반영한다. */
function applyManualRect(region: Region, rect: RegionRect, inputDevice: InputDevice): Region {
  return {
    ...region,
    polygon: buildPolygonFromRect(rect),
    selectionMode: "manual",
    inputDevice,
    warningLevel: "normal",
  };
}


/** 포인터 입력 중 화면에 보여줄 사각형을 계산한다. */
function getPreviewRect(interaction: PointerInteraction | null, regionId?: string): RegionRect | null {
  if (!interaction) {
    return null;
  }
  if (interaction.kind === "draw") {
    return buildRectFromPoints(interaction.start, interaction.current);
  }
  if (regionId && interaction.regionId !== regionId) {
    return null;
  }
  const minimumSize = resolveMinimumRegionSize(interaction.inputDevice);
  return resizeRectFromHandle(interaction.baseRect, interaction.handle, interaction.current, minimumSize);
}


/** 리사이즈 핸들의 절대 위치 클래스를 계산한다. */
function getHandleClassName(handle: ResizeHandle): string {
  const positionMap: Record<ResizeHandle, string> = {
    nw: "left-0 top-0 -translate-x-1/2 -translate-y-1/2 cursor-nwse-resize",
    ne: "right-0 top-0 translate-x-1/2 -translate-y-1/2 cursor-nesw-resize",
    se: "right-0 bottom-0 translate-x-1/2 translate-y-1/2 cursor-nwse-resize",
    sw: "left-0 bottom-0 -translate-x-1/2 translate-y-1/2 cursor-nesw-resize",
  };
  return positionMap[handle];
}


export function RegionEditor({
  imageUrl,
  imageWidth,
  imageHeight,
  regions: initialRegions,
  onSaveRegions,
  onRegionsChange,
  disabled = false,
}: RegionEditorProps) {
  const [regions, setRegions] = useState<Region[]>(() => initialRegions.map((region) => ({ ...region, type: "mixed" })));
  const [interaction, setInteraction] = useState<PointerInteraction | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const supportsTouchSelection = typeof window !== "undefined" && "PointerEvent" in window;

  useEffect(() => {
    setRegions(initialRegions.map((region) => ({ ...region, type: "mixed" })));
  }, [initialRegions]);

  /** 내부 영역 상태와 부모 draft 상태를 함께 갱신한다. */
  const updateRegions = useCallback(
    (updater: (regions: Region[]) => Region[]) => {
      setRegions((prev) => {
        const nextRegions = updater(prev);
        onRegionsChange?.(nextRegions);
        return nextRegions;
      });
    },
    [onRegionsChange]
  );

  /** 클라이언트 좌표를 이미지 원본 좌표로 바꾼다. */
  const getCanvasPoint = useCallback(
    (clientX: number, clientY: number) => {
      const container = containerRef.current;
      if (!container) {
        return { x: 0, y: 0 };
      }
      return getImagePointFromClient(clientX, clientY, container.getBoundingClientRect(), imageWidth, imageHeight);
    },
    [imageHeight, imageWidth]
  );

  /** 빈 캔버스에서 수동 영역 그리기를 시작한다. */
  const handleCanvasPointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (disabled || (event.pointerType === "mouse" && event.button !== 0)) {
        return;
      }
      const inputDevice = normalizeInputDevice(event.pointerType);
      const point = getCanvasPoint(event.clientX, event.clientY);
      event.preventDefault();
      event.currentTarget.setPointerCapture?.(event.pointerId);
      setInteraction({ kind: "draw", pointerId: event.pointerId, inputDevice, start: point, current: point });
    },
    [disabled, getCanvasPoint]
  );

  /** 리사이즈 핸들 드래그를 시작한다. */
  const handleResizePointerDown = useCallback(
    (event: React.PointerEvent<HTMLButtonElement>, regionId: string, handle: ResizeHandle) => {
      const region = regions.find((candidate) => candidate.id === regionId);
      if (!region || disabled) {
        return;
      }
      const inputDevice = normalizeInputDevice(event.pointerType);
      const point = getCanvasPoint(event.clientX, event.clientY);
      event.preventDefault();
      event.stopPropagation();
      containerRef.current?.setPointerCapture?.(event.pointerId);
      setInteraction({
        kind: "resize",
        pointerId: event.pointerId,
        inputDevice,
        regionId,
        handle,
        baseRect: getRectFromPolygon(region.polygon),
        current: point,
      });
    },
    [disabled, getCanvasPoint, regions]
  );

  /** 포인터 이동 중 draw/resize preview를 갱신한다. */
  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!interaction || interaction.pointerId !== event.pointerId) {
        return;
      }
      event.preventDefault();
      const point = getCanvasPoint(event.clientX, event.clientY);
      setInteraction((prev) => (prev && prev.pointerId === event.pointerId ? { ...prev, current: point } : prev));
    },
    [getCanvasPoint, interaction]
  );

  /** draw 또는 resize 결과를 영역 목록에 반영한다. */
  const commitInteraction = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!interaction || interaction.pointerId != event.pointerId) {
        return;
      }
      event.preventDefault();
      const point = getCanvasPoint(event.clientX, event.clientY);
      const minimumSize = resolveMinimumRegionSize(interaction.inputDevice);

      if (interaction.kind === "draw") {
        const rect = buildRectFromPoints(interaction.start, point);
        if (isRectLargeEnough(rect, minimumSize)) {
          updateRegions((prev) => [...prev, buildManualRegion(prev, rect, interaction.inputDevice)]);
        }
      }
      if (interaction.kind === "resize") {
        const rect = resizeRectFromHandle(interaction.baseRect, interaction.handle, point, minimumSize);
        updateRegions((prev) => prev.map((region) => (region.id === interaction.regionId ? applyManualRect(region, rect, interaction.inputDevice) : region)));
      }

      event.currentTarget.releasePointerCapture?.(event.pointerId);
      setInteraction(null);
    },
    [getCanvasPoint, interaction, updateRegions]
  );

  /** 취소된 포인터 상호작용을 즉시 정리한다. */
  const cancelInteraction = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (!interaction || interaction.pointerId !== event.pointerId) {
      return;
    }
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    setInteraction(null);
  }, [interaction]);

  /** 영역 하나를 삭제하고 순서를 다시 정렬한다. */
  const removeRegion = useCallback((id: string) => {
    updateRegions((prev) => prev.filter((region) => region.id !== id).map((region, index) => ({ ...region, order: index + 1 })));
  }, [updateRegions]);

  /** 현재 draft 영역을 부모로 저장한다. */
  const handleSave = useCallback(async () => {
    setIsSaving(true);
    setSaveError(null);
    try {
      await onSaveRegions(regions);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "영역 저장 중 오류가 발생했습니다.");
    } finally {
      setIsSaving(false);
    }
  }, [onSaveRegions, regions]);

  /** 이미지 좌표를 퍼센트 기반 스타일 값으로 바꾼다. */
  const toPercent = useCallback((value: number, total: number) => `${(value / total) * 100}%`, []);

  const draftRect = getPreviewRect(interaction);
  const saveButtonLabel = regions.length > 0 ? `영역 저장 (${regions.length}개)` : "영역 없이 저장";

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <div className="rounded-lg bg-muted px-3 py-1.5 text-[12px] text-muted-foreground">
          {supportsTouchSelection ? "마우스·손가락·펜 드래그 지원" : "마우스 드래그로 영역 지정"}
        </div>
        <Button variant="ghost" size="sm" onClick={() => updateRegions(() => [])} disabled={disabled || regions.length === 0}>
          <RotateCcw className="w-3.5 h-3.5 mr-1" />
          초기화
        </Button>
      </div>

      {regions.length === 0 ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-[12px] text-amber-950">
          <p>{AUTO_FULL_RISK_MESSAGE}</p>
          <p className="mt-1 text-amber-800">영역을 만든 뒤 모서리 핸들로 크기를 조절할 수 있습니다.</p>
        </div>
      ) : null}

      <div
        ref={containerRef}
        className="relative overflow-hidden rounded-xl border bg-muted select-none"
        style={{ aspectRatio: `${imageWidth}/${imageHeight}`, touchAction: "none" }}
        onPointerDown={handleCanvasPointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={commitInteraction}
        onPointerCancel={cancelInteraction}
      >
        <img src={imageUrl} alt="uploaded" className="w-full h-full object-contain pointer-events-none" draggable={false} />

        {regions.map((region) => {
          const previewRect = getPreviewRect(interaction, region.id) ?? getRectFromPolygon(region.polygon);
          return (
            <div
              key={region.id}
              className="absolute rounded-sm border-2"
              style={{
                left: toPercent(previewRect.left, imageWidth),
                top: toPercent(previewRect.top, imageHeight),
                width: toPercent(previewRect.right - previewRect.left, imageWidth),
                height: toPercent(previewRect.bottom - previewRect.top, imageHeight),
                borderColor: REGION_BORDER_COLOR,
                backgroundColor: REGION_FILL_COLOR,
              }}
            >
              <span
                className="absolute left-0 top-0 rounded-br-sm px-1.5 py-0.5 text-[10px] text-white"
                style={{ backgroundColor: REGION_LABEL_COLOR }}
              >
                {region.id}
              </span>

              {!disabled ? (
                <>
                  <button
                    type="button"
                    aria-label={`${region.id} 영역 삭제`}
                    className="absolute right-1 top-1 rounded bg-white/90 p-1 shadow-sm"
                    onClick={(event) => {
                      event.stopPropagation();
                      removeRegion(region.id);
                    }}
                  >
                    <Trash2 className="w-3 h-3 text-red-500" />
                  </button>

                  {RESIZE_HANDLES.map((handle) => (
                    <button
                      key={`${region.id}-${handle}`}
                      type="button"
                      aria-label={`${region.id} ${handle} 크기 조절`}
                      className={`absolute h-3.5 w-3.5 rounded-full border border-white bg-primary shadow-sm ${getHandleClassName(handle)}`}
                      onPointerDown={(event) => handleResizePointerDown(event, region.id, handle)}
                    />
                  ))}
                </>
              ) : null}
            </div>
          );
        })}

        {draftRect ? (
          <div
            className="pointer-events-none absolute rounded-sm border-2 border-dashed"
            style={{
              left: toPercent(draftRect.left, imageWidth),
              top: toPercent(draftRect.top, imageHeight),
              width: toPercent(draftRect.right - draftRect.left, imageWidth),
              height: toPercent(draftRect.bottom - draftRect.top, imageHeight),
              borderColor: REGION_BORDER_COLOR,
              backgroundColor: REGION_FILL_COLOR,
            }}
          />
        ) : null}
      </div>

      {regions.length > 0 ? (
        <div className="space-y-2">
          <p className="text-[13px] text-muted-foreground">{regions.length}개 영역</p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {regions.map((region) => (
              <div key={region.id} className="flex items-center gap-2 rounded-lg bg-accent/30 px-3 py-2">
                <div className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: REGION_BORDER_COLOR }} />
                <span className="flex-1 font-mono text-[13px]">{region.id}</span>
                <span className="text-[11px] text-muted-foreground">#{region.order}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {!disabled ? (
        <div className="flex flex-col items-end gap-2">
          {saveError ? <p className="text-[12px] text-destructive">{saveError}</p> : null}
          <Button onClick={() => void handleSave()} disabled={isSaving} className="gap-2">
            <Plus className="w-4 h-4" />
            {isSaving ? "영역 저장 중..." : saveButtonLabel}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
