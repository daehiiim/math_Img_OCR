import type { InputDevice } from "../store/jobStore";

export interface ImagePoint {
  x: number;
  y: number;
}

export interface RegionRect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export type ResizeHandle = "nw" | "ne" | "se" | "sw";

export const POINTER_MIN_REGION_SIZE = 24;

/** 표시 좌표를 원본 이미지 좌표로 변환한다. */
export function getImagePointFromClient(
  clientX: number,
  clientY: number,
  rect: DOMRect,
  imageWidth: number,
  imageHeight: number
): ImagePoint {
  const scaleX = imageWidth / rect.width;
  const scaleY = imageHeight / rect.height;
  return clampPoint(
    {
      x: Math.round((clientX - rect.left) * scaleX),
      y: Math.round((clientY - rect.top) * scaleY),
    },
    imageWidth,
    imageHeight
  );
}


/** 포인트를 이미지 경계 안으로 제한한다. */
export function clampPoint(point: ImagePoint, imageWidth: number, imageHeight: number): ImagePoint {
  return {
    x: Math.max(0, Math.min(point.x, imageWidth)),
    y: Math.max(0, Math.min(point.y, imageHeight)),
  };
}


/** 두 점으로 사각형 경계를 만든다. */
export function buildRectFromPoints(start: ImagePoint, end: ImagePoint): RegionRect {
  return {
    left: Math.min(start.x, end.x),
    top: Math.min(start.y, end.y),
    right: Math.max(start.x, end.x),
    bottom: Math.max(start.y, end.y),
  };
}


/** polygon을 다루기 쉬운 사각형으로 변환한다. */
export function getRectFromPolygon(polygon: number[][]): RegionRect {
  const xs = polygon.map((point) => point[0]);
  const ys = polygon.map((point) => point[1]);
  return {
    left: Math.min(...xs),
    top: Math.min(...ys),
    right: Math.max(...xs),
    bottom: Math.max(...ys),
  };
}


/** 사각형을 저장용 polygon으로 변환한다. */
export function buildPolygonFromRect(rect: RegionRect): number[][] {
  return [
    [rect.left, rect.top],
    [rect.right, rect.top],
    [rect.right, rect.bottom],
    [rect.left, rect.bottom],
  ];
}


/** 손가락/펜에서 너무 작은 영역이 저장되지 않도록 검사한다. */
export function isRectLargeEnough(rect: RegionRect, minimumSize: number): boolean {
  return rect.right - rect.left >= minimumSize && rect.bottom - rect.top >= minimumSize;
}


/** 리사이즈 핸들에 따라 반대편 모서리를 고정한 새 사각형을 만든다. */
export function resizeRectFromHandle(
  rect: RegionRect,
  handle: ResizeHandle,
  point: ImagePoint,
  minimumSize: number
): RegionRect {
  const nextRect = { ...rect };
  if (handle === "nw" || handle === "sw") {
    nextRect.left = Math.min(point.x, rect.right - minimumSize);
  }
  if (handle === "nw" || handle === "ne") {
    nextRect.top = Math.min(point.y, rect.bottom - minimumSize);
  }
  if (handle === "ne" || handle === "se") {
    nextRect.right = Math.max(point.x, rect.left + minimumSize);
  }
  if (handle === "sw" || handle === "se") {
    nextRect.bottom = Math.max(point.y, rect.top + minimumSize);
  }
  return nextRect;
}


/** PointerEvent의 pointerType을 앱 내부 입력 장치 타입으로 정규화한다. */
export function normalizeInputDevice(pointerType: string): InputDevice {
  if (pointerType === "touch" || pointerType === "pen") {
    return pointerType;
  }
  return "mouse";
}


/** 터치/펜일수록 더 큰 최소 영역을 적용한다. */
export function resolveMinimumRegionSize(inputDevice: InputDevice): number {
  return inputDevice === "mouse" ? POINTER_MIN_REGION_SIZE : 32;
}
