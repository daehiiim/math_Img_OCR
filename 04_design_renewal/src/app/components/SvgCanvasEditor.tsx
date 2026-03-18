import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "./ui/button";
import { Move, Type, Minus, Undo2, Redo2, Trash2, Save, X, Spline } from "lucide-react";

interface SvgCanvasEditorProps {
  initialSvg: string;
  onSave: (svg: string) => Promise<void>;
  onCancel: () => void;
}

type ToolMode = "select" | "line" | "line-dashed" | "curve" | "curve-dashed" | "text";
const CANVAS_HEIGHT = 420;

// ─── SVG helpers ─────────────────────────────────────────────────────────────

function parseSvgRoot(svgText: string): SVGSVGElement {
  const parser = new DOMParser();
  const doc = parser.parseFromString(svgText, "image/svg+xml");
  const root = doc.documentElement;
  if (!root || root.tagName.toLowerCase() !== "svg") {
    throw new Error("유효한 SVG 문서가 아닙니다.");
  }
  return root as unknown as SVGSVGElement;
}

function setEditorStyles(svg: SVGSVGElement) {
  if (!svg.getAttribute("viewBox")) {
    const width = Number(svg.getAttribute("width") || 1200);
    const height = Number(svg.getAttribute("height") || 800);
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  }
  const origWidth = svg.getAttribute("width");
  const origHeight = svg.getAttribute("height");
  svg.dataset.origWidth = origWidth || "";
  svg.dataset.origHeight = origHeight || "";
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", `${CANVAS_HEIGHT}px`);
  svg.style.background = "#fff";
  svg.style.border = "1px solid #e5e7eb";
  svg.style.cursor = "crosshair";
  svg.style.userSelect = "none";
  (svg.style as any).webkitUserSelect = "none";
  svg.style.touchAction = "none";
}

function toSvgPoint(svg: SVGSVGElement, clientX: number, clientY: number): { x: number; y: number } {
  const pt = svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  const ctm = svg.getScreenCTM();
  if (!ctm) return { x: clientX, y: clientY };
  return pt.matrixTransform(ctm.inverse());
}

function getNumericAttr(el: Element, name: string, fallback = 0): number {
  const value = Number(el.getAttribute(name));
  return Number.isFinite(value) ? value : fallback;
}

function setNumericAttr(el: Element, name: string, value: number): void {
  el.setAttribute(name, String(value));
}

function parsePoints(pointsText: string | null): Array<{ x: number; y: number }> {
  if (!pointsText) return [];
  return pointsText
    .trim()
    .split(/\s+/)
    .map((pair) => {
      const [xRaw, yRaw] = pair.split(',');
      return { x: Number(xRaw), y: Number(yRaw) };
    })
    .filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y));
}

function stringifyPoints(points: Array<{ x: number; y: number }>): string {
  return points.map((p) => `${p.x},${p.y}`).join(' ');
}

function getPointsCenter(points: Array<{ x: number; y: number }>): { x: number; y: number } {
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  return {
    x: (Math.min(...xs) + Math.max(...xs)) / 2,
    y: (Math.min(...ys) + Math.max(...ys)) / 2,
  };
}

// Parse quadratic bezier path "M x1 y1 Q cx cy x2 y2"
function parseBezierPath(d: string | null): { x1: number; y1: number; cx: number; cy: number; x2: number; y2: number } | null {
  if (!d) return null;
  const m = d.match(/M\s*([\d.+-]+)\s+([\d.+-]+)\s+Q\s*([\d.+-]+)\s+([\d.+-]+)\s+([\d.+-]+)\s+([\d.+-]+)/i);
  if (!m) return null;
  return {
    x1: Number(m[1]), y1: Number(m[2]),
    cx: Number(m[3]), cy: Number(m[4]),
    x2: Number(m[5]), y2: Number(m[6]),
  };
}

function makeBezierD(x1: number, y1: number, cx: number, cy: number, x2: number, y2: number): string {
  return `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;
}

// ─── Translation ──────────────────────────────────────────────────────────────

function translateFromSnapshot(target: SVGElement, snapshot: SVGElement, globalDx: number, globalDy: number): boolean {
  let ldx = globalDx;
  let ldy = globalDy;

  try {
    const transformList = (snapshot as SVGGraphicsElement).transform.baseVal;
    if (transformList.numberOfItems > 0) {
      const matrix = transformList.consolidate()?.matrix;
      if (matrix) {
        const inv = matrix.inverse();
        ldx = globalDx * inv.a + globalDy * inv.c;
        ldy = globalDx * inv.b + globalDy * inv.d;
      }
    }
  } catch (e) {}

  const transform = snapshot.getAttribute('transform');
  if (transform) {
    const newTransform = transform.replace(/rotate\(\s*([\d.+-]+)(?:\s*,\s*([\d.+-]+)\s*,\s*([\d.+-]+))?\s*\)/g, (match, deg, cx, cy) => {
      if (cx !== undefined && cy !== undefined) {
        return `rotate(${deg},${(Number(cx) + ldx).toFixed(2)},${(Number(cy) + ldy).toFixed(2)})`;
      }
      return match;
    });
    target.setAttribute('transform', newTransform);
  }

  const dx = ldx;
  const dy = ldy;
  const tag = target.tagName.toLowerCase();

  if (tag === 'line') {
    setNumericAttr(target, 'x1', getNumericAttr(snapshot, 'x1') + dx);
    setNumericAttr(target, 'y1', getNumericAttr(snapshot, 'y1') + dy);
    setNumericAttr(target, 'x2', getNumericAttr(snapshot, 'x2') + dx);
    setNumericAttr(target, 'y2', getNumericAttr(snapshot, 'y2') + dy);
    return true;
  }

  if (tag === 'path') {
    const bezier = parseBezierPath(snapshot.getAttribute('d'));
    if (bezier) {
      target.setAttribute('d', makeBezierD(
        bezier.x1 + dx, bezier.y1 + dy,
        bezier.cx + dx, bezier.cy + dy,
        bezier.x2 + dx, bezier.y2 + dy,
      ));
      return true;
    }
    return false;
  }

  if (tag === 'text') {
    setNumericAttr(target, 'x', getNumericAttr(snapshot, 'x') + dx);
    setNumericAttr(target, 'y', getNumericAttr(snapshot, 'y') + dy);
    return true;
  }

  if (tag === 'rect') {
    setNumericAttr(target, 'x', getNumericAttr(snapshot, 'x') + dx);
    setNumericAttr(target, 'y', getNumericAttr(snapshot, 'y') + dy);
    return true;
  }

  if (tag === 'circle') {
    setNumericAttr(target, 'cx', getNumericAttr(snapshot, 'cx') + dx);
    setNumericAttr(target, 'cy', getNumericAttr(snapshot, 'cy') + dy);
    return true;
  }

  if (tag === 'ellipse') {
    setNumericAttr(target, 'cx', getNumericAttr(snapshot, 'cx') + dx);
    setNumericAttr(target, 'cy', getNumericAttr(snapshot, 'cy') + dy);
    return true;
  }

  if (tag === 'polygon' || tag === 'polyline') {
    const points = parsePoints(snapshot.getAttribute('points')).map((p) => ({ x: p.x + dx, y: p.y + dy }));
    if (points.length === 0) return false;
    target.setAttribute('points', stringifyPoints(points));
    return true;
  }

  return false;
}

// ─── Bounding-box helpers ────────────────────────────────────────────────────

interface BBox { x: number; y: number; width: number; height: number }

function bboxesIntersect(a: BBox, b: BBox): boolean {
  return !(a.x + a.width < b.x || b.x + b.width < a.x || a.y + a.height < b.y || b.y + b.height < a.y);
}

function getElementBBox(el: SVGElement, svg?: SVGSVGElement | null): BBox | null {
  try {
    if (svg) {
      const rect = el.getBoundingClientRect();
      const ctm = svg.getScreenCTM();
      if (ctm) {
        const inv = ctm.inverse();
        const pts = [
          { x: rect.left, y: rect.top },
          { x: rect.right, y: rect.top },
          { x: rect.right, y: rect.bottom },
          { x: rect.left, y: rect.bottom },
        ];
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        pts.forEach(p => {
          const pt = svg.createSVGPoint();
          pt.x = p.x; pt.y = p.y;
          const transformed = pt.matrixTransform(inv);
          if (transformed.x < minX) minX = transformed.x;
          if (transformed.x > maxX) maxX = transformed.x;
          if (transformed.y < minY) minY = transformed.y;
          if (transformed.y > maxY) maxY = transformed.y;
        });
        const w = maxX - minX;
        const h = maxY - minY;
        if (w === 0 && h === 0) return null;
        return { x: minX, y: minY, width: w, height: h };
      }
    }
    const b = (el as SVGGraphicsElement).getBBox();
    if (b.width === 0 && b.height === 0) return null;
    return { x: b.x, y: b.y, width: b.width, height: b.height };
  } catch {
    return null;
  }
}

function getUnifiedBBox(elements: SVGElement[], svg?: SVGSVGElement | null): BBox | null {
  const boxes = elements.map((el) => getElementBBox(el, svg)).filter((b): b is BBox => b !== null);
  if (boxes.length === 0) return null;
  const minX = Math.min(...boxes.map((b) => b.x));
  const minY = Math.min(...boxes.map((b) => b.y));
  const maxX = Math.max(...boxes.map((b) => b.x + b.width));
  const maxY = Math.max(...boxes.map((b) => b.y + b.height));
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}

// ─── Handle overlay ───────────────────────────────────────────────────────────

const HANDLE_SIZE = 8; // half-size of corner handle square
const ROTATE_OFFSET = 22; // distance above bounding box top

/** 8 resize corner/edge handles + 1 rotate handle */
type HandleKind =
  | 'nw' | 'n' | 'ne'
  | 'w'  |       'e'
  | 'sw' | 's' | 'se'
  | 'rotate';

interface HandleInfo {
  kind: HandleKind;
  cx: number; // center in SVG coords
  cy: number;
}

function computeHandles(bbox: BBox): HandleInfo[] {
  const { x, y, width: w, height: h } = bbox;
  const mx = x + w / 2;
  const my = y + h / 2;
  return [
    { kind: 'nw',     cx: x,      cy: y },
    { kind: 'n',      cx: mx,     cy: y },
    { kind: 'ne',     cx: x + w,  cy: y },
    { kind: 'w',      cx: x,      cy: my },
    { kind: 'e',      cx: x + w,  cy: my },
    { kind: 'sw',     cx: x,      cy: y + h },
    { kind: 's',      cx: mx,     cy: y + h },
    { kind: 'se',     cx: x + w,  cy: y + h },
    { kind: 'rotate', cx: mx,     cy: y - ROTATE_OFFSET },
  ];
}

function cursorForHandle(kind: HandleKind): string {
  const map: Record<HandleKind, string> = {
    nw: 'nw-resize', n: 'n-resize', ne: 'ne-resize',
    w: 'w-resize',                   e: 'e-resize',
    sw: 'sw-resize', s: 's-resize', se: 'se-resize',
    rotate: 'grab',
  };
  return map[kind];
}



// ─── Component ────────────────────────────────────────────────────────────────

export default function SvgCanvasEditor({ initialSvg, onSave, onCancel }: SvgCanvasEditorProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const selectedRef = useRef<SVGElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [mode, setMode] = useState<ToolMode>("select");
  const [selectedEl, setSelectedEl] = useState<SVGElement | null>(null);
  const [undoStack, setUndoStack] = useState<string[]>([]);
  const [redoStack, setRedoStack] = useState<string[]>([]);
  const [svgReadyTick, setSvgReadyTick] = useState(0);
  const [strokeWidth, setStrokeWidth] = useState(3);

  // Drawing refs
  const drawLineRef = useRef<SVGLineElement | null>(null);
  const drawCurveRef = useRef<{ path: SVGPathElement; x1: number; y1: number } | null>(null);

  // Drag-to-move ref
  const dragRef = useRef<{ element: SVGElement; snapshot: SVGElement; startX: number; startY: number } | null>(null);
  const multiSelectedRef = useRef<SVGElement[]>([]);
  const [multiSelectedEls, setMultiSelectedEls] = useState(0);
  const selectionStartRef = useRef<{ x: number; y: number } | null>(null);
  const selectionRectElRef = useRef<SVGRectElement | null>(null);
  const multiDragRef = useRef<{ elements: SVGElement[]; snapshots: SVGElement[]; startX: number; startY: number } | null>(null);
  const suppressClickRef = useRef(false);

  // Handle overlay refs (stored in SVG, keyed by data-editor-handle)
  const handleEls = useRef<SVGElement[]>([]);
  const activeHandleRef = useRef<{
    kind: HandleKind;
    bbox: BBox;
    startClientX: number;
    startClientY: number;
    startSvgX: number;
    startSvgY: number;
    snapshotTransform: string;
  } | null>(null);

  const tools = useMemo(
    () => [
      { id: "select" as ToolMode,       label: "선택",       icon: Move },
      { id: "line" as ToolMode,         label: "선",         icon: Minus },
      { id: "line-dashed" as ToolMode,  label: "점선",       icon: Minus },
      { id: "curve" as ToolMode,        label: "곡선(실선)", icon: Spline },
      { id: "curve-dashed" as ToolMode, label: "곡선(점선)", icon: Spline },
      { id: "text" as ToolMode,         label: "텍스트",     icon: Type },
    ],
    []
  );

  // ── restore ──────────────────────────────────────────────────────────────

  const restoreSvg = (svgText: string) => {
    const host = hostRef.current;
    if (!host) return;
    host.innerHTML = "";
    const svg = parseSvgRoot(svgText);
    setEditorStyles(svg);
    host.appendChild(svg);
    svgRef.current = svg;
    selectedRef.current = null;
    dragRef.current = null;
    multiSelectedRef.current = [];
    selectionStartRef.current = null;
    selectionRectElRef.current = null;
    multiDragRef.current = null;
    drawLineRef.current = null;
    drawCurveRef.current = null;
    handleEls.current = [];
    activeHandleRef.current = null;
    setSelectedEl(null);
    setMultiSelectedEls(0);
    setSvgReadyTick((tick) => tick + 1);
  };

  const snapshot = () => {
    const svg = svgRef.current;
    if (!svg) return;
    setUndoStack((prev) => [...prev, svg.outerHTML]);
    setRedoStack([]);
  };

  // ── handle overlay ────────────────────────────────────────────────────────

  const clearHandles = () => {
    handleEls.current.forEach((h) => { if (h.parentNode) h.parentNode.removeChild(h); });
    handleEls.current = [];
  };

  const buildHandles = (el: SVGElement) => {
    const svg = svgRef.current;
    if (!svg) return;
    clearHandles();

    const bbox = getElementBBox(el, svgRef.current);
    if (!bbox) return;

    const handles = computeHandles(bbox);

    // Dashed bounding-box outline
    const outline = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    outline.setAttribute("x", String(bbox.x));
    outline.setAttribute("y", String(bbox.y));
    outline.setAttribute("width", String(bbox.width));
    outline.setAttribute("height", String(bbox.height));
    outline.setAttribute("fill", "transparent");
    outline.setAttribute("stroke", "#2563eb");
    outline.setAttribute("stroke-width", "1");
    outline.setAttribute("stroke-dasharray", "4 3");
    outline.setAttribute("pointer-events", "all");
    outline.setAttribute("data-editor-handle", "bbox");
    outline.setAttribute("cursor", "move");
    svgRef.current!.appendChild(outline);
    handleEls.current.push(outline);

    handles.forEach((h) => {
      let node: SVGElement;
      if (h.kind === 'rotate') {
        const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        c.setAttribute("cx", String(h.cx));
        c.setAttribute("cy", String(h.cy));
        c.setAttribute("r", "6");
        c.setAttribute("fill", "#f59e0b");
        c.setAttribute("stroke", "#111827");
        c.setAttribute("stroke-width", "1.5");
        c.setAttribute("cursor", cursorForHandle(h.kind));
        node = c;
      } else {
        const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        r.setAttribute("x", String(h.cx - HANDLE_SIZE / 2));
        r.setAttribute("y", String(h.cy - HANDLE_SIZE / 2));
        r.setAttribute("width", String(HANDLE_SIZE));
        r.setAttribute("height", String(HANDLE_SIZE));
        r.setAttribute("fill", "#2563eb");
        r.setAttribute("stroke", "#fff");
        r.setAttribute("stroke-width", "1.5");
        r.setAttribute("cursor", cursorForHandle(h.kind));
        node = r;
      }
      node.setAttribute("data-editor-handle", h.kind);
      svg.appendChild(node);
      handleEls.current.push(node);
    });
  };

  const buildMultiHandles = (elements: SVGElement[]) => {
    const svg = svgRef.current;
    if (!svg) return;
    clearHandles();
    const bbox = getUnifiedBBox(elements, svgRef.current);
    if (!bbox) return;

    const outline = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    outline.setAttribute("x", String(bbox.x));
    outline.setAttribute("y", String(bbox.y));
    outline.setAttribute("width", String(bbox.width));
    outline.setAttribute("height", String(bbox.height));
    outline.setAttribute("fill", "transparent");
    outline.setAttribute("stroke", "#2563eb");
    outline.setAttribute("stroke-width", "1");
    outline.setAttribute("stroke-dasharray", "4 3");
    outline.setAttribute("pointer-events", "all");
    outline.setAttribute("data-editor-handle", "bbox");
    outline.setAttribute("cursor", "move");
    svg.appendChild(outline);
    handleEls.current.push(outline);
  };

  const refreshHandles = (el: SVGElement) => {
    clearHandles();
    buildHandles(el);
  };

  // ── selection ─────────────────────────────────────────────────────────────

  const clearSelection = () => {
    const prev = selectedRef.current;
    if (prev) prev.style.outline = "";
    selectedRef.current = null;
    setSelectedEl(null);
    multiSelectedRef.current = [];
    setMultiSelectedEls(0);
    if (selectionRectElRef.current?.parentNode) {
      selectionRectElRef.current.parentNode.removeChild(selectionRectElRef.current);
    }
    selectionStartRef.current = null;
    selectionRectElRef.current = null;
    multiDragRef.current = null;
    clearHandles();
  };

  const selectElement = (target: SVGElement | null) => {
    clearSelection();
    if (target && target !== svgRef.current) {
      selectedRef.current = target;
      setSelectedEl(target);
      buildHandles(target);
    }
  };

  const selectMultiple = (elements: SVGElement[]) => {
    clearSelection();
    if (elements.length === 0) return;
    multiSelectedRef.current = elements;
    setMultiSelectedEls(elements.length);
    buildMultiHandles(elements);
  };

  // ── Delete key ────────────────────────────────────────────────────────────

  const deleteSelected = () => {
    if (!svgRef.current) return;

    if (multiSelectedRef.current.length > 0) {
      snapshot();
      multiSelectedRef.current.forEach((el) => {
        if (el !== svgRef.current) el.remove();
      });
      clearSelection();
      return;
    }

    const el = selectedRef.current;
    if (!el || el === svgRef.current) return;
    snapshot();
    el.remove();
    clearSelection();
  };

  useEffect(() => {
    if (multiSelectedRef.current.length > 0) {
      multiSelectedRef.current = [];
      setMultiSelectedEls(0);
      clearHandles();
    }
  }, [mode]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        // Don't fire while user is typing in a text input
        const tag = (document.activeElement as HTMLElement | null)?.tagName?.toLowerCase();
        if (tag === 'input' || tag === 'textarea') return;
        deleteSelected();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── init SVG ──────────────────────────────────────────────────────────────

  useEffect(() => {
    try {
      restoreSvg(initialSvg);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "SVG 초기화 실패");
    }
  }, [initialSvg]);

  // ── main pointer event effect ─────────────────────────────────────────────

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const isDrawingMode = (m: ToolMode) =>
      m === 'line' || m === 'line-dashed' || m === 'curve' || m === 'curve-dashed' || m === 'text';

    svg.style.cursor = isDrawingMode(mode) ? "crosshair" : "default";

    // ── onClick (text placement) ───────────────────────────────────────────
    const onClick = (event: MouseEvent) => {
      const root = svgRef.current;
      if (!root) return;

      if (suppressClickRef.current) {
        // Consume the flag: blocks exactly one click after a drag/action
        suppressClickRef.current = false;
        return;
      }

      const target = event.target as SVGElement;

      if (mode === "select") {
        const isHandle = target.hasAttribute?.("data-editor-handle");
        // If the user clicked the root background, clear selection
        if (!isHandle && target === root) {
          clearSelection();
        }
        return;
      }

      if (mode === "text") {
        const value = window.prompt("텍스트를 입력하세요", "") || "";
        if (!value.trim()) return;
        snapshot();
        const p = toSvgPoint(root, event.clientX, event.clientY);
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", String(p.x));
        text.setAttribute("y", String(p.y));
        text.setAttribute("font-size", "24");
        text.setAttribute("font-family", "serif");
        text.setAttribute("fill", "black");
        text.textContent = value;
        root.appendChild(text);
        selectElement(text);
      }
    };

    // ── onMouseDown ───────────────────────────────────────────────────────
    const onMouseDown = (event: MouseEvent) => {
      const root = svgRef.current;
      if (!root) return;
      const target = event.target as SVGElement;

      // ── Handle drag (resize / rotate) ────────────────────────────────
      if (mode === "select") {
        const handleKind = target.getAttribute?.("data-editor-handle") as HandleKind | string | null;
        
        if (handleKind && handleKind !== 'bbox' && handleKind !== 'selection-rect' && selectedRef.current) {
          const bbox = getElementBBox(selectedRef.current, svgRef.current);
          if (bbox) {
            const startPt = toSvgPoint(root, event.clientX, event.clientY);
            activeHandleRef.current = {
              kind: handleKind as HandleKind,
              bbox,
              startClientX: event.clientX,
              startClientY: event.clientY,
              startSvgX: startPt.x,
              startSvgY: startPt.y,
              snapshotTransform: selectedRef.current.getAttribute('transform') || '',
            };
            event.preventDefault();
            return;
          }
        }

        if (handleKind === 'bbox') {
          if (multiSelectedRef.current.length > 0) {
            snapshot();
            const p = toSvgPoint(root, event.clientX, event.clientY);
            multiDragRef.current = {
              elements: [...multiSelectedRef.current],
              snapshots: multiSelectedRef.current.map((el) => el.cloneNode(true) as SVGElement),
              startX: p.x,
              startY: p.y,
            };
            dragRef.current = null;
            suppressClickRef.current = true;
            event.preventDefault();
            return;
          } else if (selectedRef.current) {
            snapshot();
            const p = toSvgPoint(root, event.clientX, event.clientY);
            dragRef.current = {
              element: selectedRef.current,
              snapshot: selectedRef.current.cloneNode(true) as SVGElement,
              startX: p.x,
              startY: p.y,
            };
            multiDragRef.current = null;
            suppressClickRef.current = true;
            event.preventDefault();
            return;
          }
        }

        // ── Rubber-band selection ───────────────────────────────────────
        if (!target || target === root) {
          clearSelection();
          selectionStartRef.current = toSvgPoint(root, event.clientX, event.clientY);
          const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
          rect.setAttribute("x", String(selectionStartRef.current.x));
          rect.setAttribute("y", String(selectionStartRef.current.y));
          rect.setAttribute("width", "0");
          rect.setAttribute("height", "0");
          rect.setAttribute("fill", "#2563eb");
          rect.setAttribute("fill-opacity", "0.15");
          rect.setAttribute("stroke", "#2563eb");
          rect.setAttribute("stroke-width", "1");
          rect.setAttribute("stroke-dasharray", "4 3");
          rect.setAttribute("pointer-events", "none");
          rect.setAttribute("data-editor-handle", "selection-rect");
          root.appendChild(rect);
          handleEls.current.push(rect);
          selectionRectElRef.current = rect;
          suppressClickRef.current = true;
          dragRef.current = null;
          multiDragRef.current = null;
          event.preventDefault();
          return;
        }
        if ((target as SVGElement).hasAttribute?.("data-editor-handle")) {
          return;
        }

        // ── Drag multiple selected elements ─────────────────────────────
        const multi = multiSelectedRef.current;
        if (multi.length > 0 && multi.includes(target)) {
          snapshot();
          const p = toSvgPoint(root, event.clientX, event.clientY);
          multiDragRef.current = {
            elements: [...multi],
            snapshots: multi.map((el) => el.cloneNode(true) as SVGElement),
            startX: p.x,
            startY: p.y,
          };
          dragRef.current = null;
          suppressClickRef.current = true;
          event.preventDefault();
          return;
        }

        if (multi.length > 0 && !multi.includes(target)) {
          multiSelectedRef.current = [];
          setMultiSelectedEls(0);
        }

        selectElement(target);
        snapshot();
        const p = toSvgPoint(root, event.clientX, event.clientY);
        dragRef.current = {
          element: target,
          snapshot: target.cloneNode(true) as SVGElement,
          startX: p.x,
          startY: p.y,
        };
        event.preventDefault();
        return;
      }

      // ── Line drawing ──────────────────────────────────────────────────
      if (mode === "line" || mode === "line-dashed") {
        snapshot();
        const p = toSvgPoint(root, event.clientX, event.clientY);
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", String(p.x));
        line.setAttribute("y1", String(p.y));
        line.setAttribute("x2", String(p.x));
        line.setAttribute("y2", String(p.y));
        line.setAttribute("stroke", "black");
        line.setAttribute("stroke-width", String(strokeWidth));
        if (mode === "line-dashed") {
          line.setAttribute("stroke-dasharray", "8 4");
        }
        root.appendChild(line);
        drawLineRef.current = line;
        event.preventDefault();
        return;
      }

      // ── Curve drawing ─────────────────────────────────────────────────
      if (mode === "curve" || mode === "curve-dashed") {
        snapshot();
        const p = toSvgPoint(root, event.clientX, event.clientY);
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", makeBezierD(p.x, p.y, p.x, p.y, p.x, p.y));
        path.setAttribute("stroke", "black");
        path.setAttribute("stroke-width", String(strokeWidth));
        path.setAttribute("fill", "none");
        if (mode === "curve-dashed") {
          path.setAttribute("stroke-dasharray", "8 4");
        }
        root.appendChild(path);
        drawCurveRef.current = { path, x1: p.x, y1: p.y };
        event.preventDefault();
        return;
      }
    };

    // ── onMouseMove ───────────────────────────────────────────────────────
    const onMouseMove = (event: MouseEvent) => {
      const root = svgRef.current;
      if (!root) return;

      // Line preview
      const line = drawLineRef.current;
      if (line && (mode === "line" || mode === "line-dashed")) {
        const p = toSvgPoint(root, event.clientX, event.clientY);
        line.setAttribute("x2", String(p.x));
        line.setAttribute("y2", String(p.y));
        return;
      }

      // Curve preview: control point follows mouse midway
      const curve = drawCurveRef.current;
      if (curve && (mode === "curve" || mode === "curve-dashed")) {
        const p = toSvgPoint(root, event.clientX, event.clientY);
        const cx = (curve.x1 + p.x) / 2;
        const cy = Math.min(curve.y1, p.y) - Math.abs(p.x - curve.x1) * 0.25;
        curve.path.setAttribute("d", makeBezierD(curve.x1, curve.y1, cx, cy, p.x, p.y));
        return;
      }

      // Handle drag: resize or rotate
      const ah = activeHandleRef.current;
      const sel = selectedRef.current;
      if (ah && sel) {
        if (ah.kind === 'rotate') {
          const bbox = ah.bbox;
          const centerX = bbox.x + bbox.width / 2;
          const centerY = bbox.y + bbox.height / 2;
          const p = toSvgPoint(root, event.clientX, event.clientY);
          const startAngle = Math.atan2(ah.startSvgY - centerY, ah.startSvgX - centerX) * 180 / Math.PI;
          const currentAngle = Math.atan2(p.y - centerY, p.x - centerX) * 180 / Math.PI;
          const deltaDeg = currentAngle - startAngle;

          const transformStr = `translate(${centerX},${centerY}) rotate(${deltaDeg.toFixed(2)}) translate(${-centerX},${-centerY}) ${ah.snapshotTransform}`;
          sel.setAttribute('transform', transformStr.trim());
          refreshHandles(sel);
        } else {
          const bbox = ah.bbox;
          const dx = event.clientX - ah.startClientX;
          const dy = event.clientY - ah.startClientY;

          const scaleX = bbox.width > 0 ? 1 + dx / bbox.width : 1;
          const scaleY = bbox.height > 0 ? 1 + dy / bbox.height : 1;

          let sx = 1, sy = 1;
          const k = ah.kind;
          if (k === 'se') { sx = scaleX; sy = scaleY; }
          else if (k === 'sw') { sx = 1 - scaleX + 1; sy = scaleY; }
          else if (k === 'ne') { sx = scaleX; sy = 1 - scaleY + 1; }
          else if (k === 'nw') { sx = 1 - scaleX + 1; sy = 1 - scaleY + 1; }
          else if (k === 'e')  { sx = scaleX; sy = 1; }
          else if (k === 'w')  { sx = 1 - scaleX + 1; sy = 1; }
          else if (k === 's')  { sx = 1; sy = scaleY; }
          else if (k === 'n')  { sx = 1; sy = 1 - scaleY + 1; }

          let originX = bbox.x + bbox.width / 2;
          let originY = bbox.y + bbox.height / 2;
          
          if (k === 'se') { originX = bbox.x; originY = bbox.y; }
          else if (k === 'sw') { originX = bbox.x + bbox.width; originY = bbox.y; }
          else if (k === 'ne') { originX = bbox.x; originY = bbox.y + bbox.height; }
          else if (k === 'nw') { originX = bbox.x + bbox.width; originY = bbox.y + bbox.height; }
          else if (k === 'e') { originX = bbox.x; }
          else if (k === 'w') { originX = bbox.x + bbox.width; }
          else if (k === 's') { originY = bbox.y; }
          else if (k === 'n') { originY = bbox.y + bbox.height; }

          const transformStr = `translate(${originX},${originY}) scale(${sx.toFixed(3)},${sy.toFixed(3)}) translate(${-originX},${-originY}) ${ah.snapshotTransform}`;
          sel.setAttribute('transform', transformStr.trim());
          refreshHandles(sel);
        }
        return;
      }

      // Rubber-band selection rect update
      const selectionStart = selectionStartRef.current;
      const selectionRectEl = selectionRectElRef.current;
      if (selectionStart && selectionRectEl && mode === "select") {
        const p = toSvgPoint(root, event.clientX, event.clientY);
        const x = Math.min(selectionStart.x, p.x);
        const y = Math.min(selectionStart.y, p.y);
        const width = Math.abs(p.x - selectionStart.x);
        const height = Math.abs(p.y - selectionStart.y);
        selectionRectEl.setAttribute("x", String(x));
        selectionRectEl.setAttribute("y", String(y));
        selectionRectEl.setAttribute("width", String(width));
        selectionRectEl.setAttribute("height", String(height));
        return;
      }

      // Drag multiple elements
      const multiDrag = multiDragRef.current;
      if (multiDrag && mode === "select") {
        const p = toSvgPoint(root, event.clientX, event.clientY);
        const dx = p.x - multiDrag.startX;
        const dy = p.y - multiDrag.startY;
        multiDrag.elements.forEach((el, idx) => {
          translateFromSnapshot(el, multiDrag.snapshots[idx], dx, dy);
        });
        buildMultiHandles(multiDrag.elements);
        return;
      }

      // Drag element to move
      const drag = dragRef.current;
      if (drag && mode === "select") {
        const p = toSvgPoint(root, event.clientX, event.clientY);
        const dx = p.x - drag.startX;
        const dy = p.y - drag.startY;
        translateFromSnapshot(drag.element, drag.snapshot, dx, dy);
        refreshHandles(drag.element);
      }
    };

    // ── onMouseUp ─────────────────────────────────────────────────────────
    const onMouseUp = (event: MouseEvent) => {
      const root = svgRef.current;
      if (!root) return;

      const selectionStart = selectionStartRef.current;
      if (selectionStart) {
        const end = toSvgPoint(root, event.clientX, event.clientY);
        const selectionBox: BBox = {
          x: Math.min(selectionStart.x, end.x),
          y: Math.min(selectionStart.y, end.y),
          width: Math.abs(end.x - selectionStart.x),
          height: Math.abs(end.y - selectionStart.y),
        };

        const selected: SVGElement[] = [];
        Array.from(root.children).forEach((child) => {
          const el = child as SVGElement;
          if (el.hasAttribute("data-editor-handle")) return;
          const bbox = getElementBBox(el, svgRef.current);
          if (!bbox) return;
          if (bboxesIntersect(selectionBox, bbox)) {
            selected.push(el);
          }
        });

        if (selectionRectElRef.current?.parentNode) {
          selectionRectElRef.current.parentNode.removeChild(selectionRectElRef.current);
        }
        selectionRectElRef.current = null;
        selectionStartRef.current = null;

        if (selected.length > 1) {
          selectMultiple(selected);
        } else if (selected.length === 1) {
          selectElement(selected[0]);
        } else {
          clearSelection();
        }
        
        // suppressClickRef stays true — it will be consumed by the next onClick
      }

      // dragRef/multiDragRef: suppressClickRef stays true — consumed by onClick


      if (drawLineRef.current && (mode === "line" || mode === "line-dashed")) {
        selectElement(drawLineRef.current);
        setMode("select");
      }
      if (drawCurveRef.current && (mode === "curve" || mode === "curve-dashed")) {
        selectElement(drawCurveRef.current.path);
        setMode("select");
      }

      drawLineRef.current = null;
      drawCurveRef.current = null;
      dragRef.current = null;
      multiDragRef.current = null;
      activeHandleRef.current = null;
    };

    // Prevent native browser drag (image ghosting / text selection)
    const onDragStart = (e: Event) => e.preventDefault();

    // Use pointer events for reliable capture across SVG boundary
    const onPointerDown = (event: PointerEvent) => {
      svg.setPointerCapture(event.pointerId);
      onMouseDown(event);
    };
    const onPointerMove = (event: PointerEvent) => {
      onMouseMove(event);
    };
    const onPointerUp = (event: PointerEvent) => {
      svg.releasePointerCapture(event.pointerId);
      onMouseUp(event);
    };

    svg.addEventListener("click", onClick);
    svg.addEventListener("pointerdown", onPointerDown);
    svg.addEventListener("pointermove", onPointerMove);
    svg.addEventListener("pointerup", onPointerUp);
    svg.addEventListener("dragstart", onDragStart);

    return () => {
      svg.removeEventListener("click", onClick);
      svg.removeEventListener("pointerdown", onPointerDown);
      svg.removeEventListener("pointermove", onPointerMove);
      svg.removeEventListener("pointerup", onPointerUp);
      svg.removeEventListener("dragstart", onDragStart);
    };
  }, [mode, svgReadyTick, strokeWidth]);

  // ── Undo / Redo ───────────────────────────────────────────────────────────

  const doUndo = () => {
    const svg = svgRef.current;
    if (!svg || undoStack.length === 0) return;
    const prev = undoStack[undoStack.length - 1];
    setUndoStack((s) => s.slice(0, -1));
    setRedoStack((s) => [...s, svg.outerHTML]);
    restoreSvg(prev);
  };

  const doRedo = () => {
    const svg = svgRef.current;
    if (!svg || redoStack.length === 0) return;
    const next = redoStack[redoStack.length - 1];
    setRedoStack((s) => s.slice(0, -1));
    setUndoStack((s) => [...s, svg.outerHTML]);
    restoreSvg(next);
  };

  // ── Save ──────────────────────────────────────────────────────────────────

  const handleSave = async () => {
    const svg = svgRef.current;
    if (!svg) return;
    setSaving(true);
    setError(null);
    try {
      const clone = svg.cloneNode(true) as SVGSVGElement;
      clone.querySelectorAll("[data-editor-handle]").forEach((node) => node.remove());
      
      const origWidth = svg.dataset.origWidth;
      const origHeight = svg.dataset.origHeight;
      if (origWidth) clone.setAttribute("width", origWidth);
      else clone.removeAttribute("width");
      if (origHeight) clone.setAttribute("height", origHeight);
      else clone.removeAttribute("height");
      
      clone.style.background = "";
      clone.style.border = "";
      clone.style.cursor = "";
      clone.removeAttribute("data-orig-width");
      clone.removeAttribute("data-orig-height");

      await onSave(clone.outerHTML);
    } catch (e) {
      setError(e instanceof Error ? e.message : "SVG 저장 실패");
    } finally {
      setSaving(false);
    }
  };

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {tools.map((tool) => {
          const Icon = tool.icon;
          const isDashed = tool.id === "line-dashed" || tool.id === "curve-dashed";
          return (
            <Button
              key={tool.id}
              variant={mode === tool.id ? "default" : "outline"}
              size="sm"
              className="gap-1"
              onClick={() => {
                clearSelection();
                setMode(tool.id);
              }}
              style={isDashed && mode !== tool.id ? { borderStyle: "dashed" } : undefined}
            >
              <Icon className="w-3.5 h-3.5" />
              {tool.label}
            </Button>
          );
        })}
        <span className="flex items-center gap-1 text-xs text-muted-foreground border rounded px-2 py-1">
          굵기
          <input
            type="range"
            min={1}
            max={12}
            step={1}
            value={strokeWidth}
            onChange={(e) => {
              const w = Number(e.target.value);
              setStrokeWidth(w);
              const sel = selectedRef.current;
              if (sel) {
                const tag = sel.tagName.toLowerCase();
                if (['line','path','polyline','polygon','rect','circle','ellipse'].includes(tag)) {
                  snapshot();
                  sel.setAttribute('stroke-width', String(w));
                }
              }
            }}
            className="w-20 accent-blue-600"
          />
          <span className="w-4 text-center font-mono">{strokeWidth}</span>
        </span>
        <Button variant="outline" size="sm" className="gap-1" onClick={doUndo} disabled={undoStack.length === 0}><Undo2 className="w-3.5 h-3.5" />Undo</Button>
        <Button variant="outline" size="sm" className="gap-1" onClick={doRedo} disabled={redoStack.length === 0}><Redo2 className="w-3.5 h-3.5" />Redo</Button>
        <Button variant="outline" size="sm" className="gap-1" onClick={deleteSelected} disabled={!selectedEl && multiSelectedEls === 0}><Trash2 className="w-3.5 h-3.5" />삭제</Button>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-1" onClick={onCancel}><X className="w-3.5 h-3.5" />취소</Button>
          <Button size="sm" className="gap-1" onClick={() => void handleSave()} disabled={saving || !!error || !svgRef.current}><Save className="w-3.5 h-3.5" />{saving ? "저장 중..." : "수정 SVG 저장"}</Button>
        </div>
      </div>
      <div className="border rounded-md bg-white p-2">
        <div ref={hostRef} data-testid="svg-editor-canvas" className="w-full overflow-hidden" style={{ minHeight: CANVAS_HEIGHT, userSelect: 'none', WebkitUserSelect: 'none', touchAction: 'none' }} />
      </div>
      {error && <p className="text-[12px] text-destructive">{error}</p>}
      <p className="text-[11px] text-muted-foreground">
        선/점선/곡선 추가, 텍스트 추가, 단일 선택 핸들 편집, 영역 선택(러버밴드)으로 다중 이동/삭제, Delete 키, Undo/Redo 지원
      </p>
    </div>
  );
}
