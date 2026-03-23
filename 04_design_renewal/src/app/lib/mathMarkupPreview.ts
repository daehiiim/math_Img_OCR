export type PreviewSegment = {
  kind: "text" | "formula";
  value: string;
};

const MATH_TAG_PATTERN = /<\/?math>/g;
const RAW_DELIMITER_PATTERN = /<\/?math>|\$\$|\$/g;
const INLINE_MATH_PATTERN = /<math>(.*?)<\/math>|\$\$(.+?)\$\$|\$(.+?)\$/g;

/** 수식 마크업 태그만 제거한 일반 텍스트를 반환한다. */
function stripMathTags(value: string): string {
  return value.replace(RAW_DELIMITER_PATTERN, "");
}

/** 태그 쌍이 정상적인 순서로 닫히는지 확인한다. */
function hasBalancedMathTags(value: string): boolean {
  let depth = 0;

  for (const match of value.matchAll(MATH_TAG_PATTERN)) {
    depth += match[0] === "<math>" ? 1 : -1;
    if (depth < 0 || depth > 1) {
      return false;
    }
  }

  return depth === 0;
}

/** 이스케이프되지 않은 달러 구분자 개수가 짝수인지 확인한다. */
function hasBalancedDollarDelimiters(value: string): boolean {
  let count = 0;

  for (let index = 0; index < value.length; index += 1) {
    if (value[index] !== "$" || value[index - 1] === "\\") {
      continue;
    }
    count += 1;
  }

  return count % 2 === 0;
}

/** 인접한 일반 텍스트를 하나의 세그먼트로 합친다. */
function pushTextSegment(segments: PreviewSegment[], value: string): void {
  if (!value) {
    return;
  }

  const lastSegment = segments[segments.length - 1];
  if (lastSegment?.kind === "text") {
    lastSegment.value += value;
    return;
  }

  segments.push({ kind: "text", value });
}

/** 한 줄의 수식 마크업을 안전한 미리보기 세그먼트로 변환한다. */
function parseMathMarkupLine(value: string): PreviewSegment[] {
  if (!value) {
    return [{ kind: "text", value: "" }];
  }

  if (!hasBalancedMathTags(value) || !hasBalancedDollarDelimiters(value)) {
    return [{ kind: "text", value: stripMathTags(value) }];
  }

  const segments: PreviewSegment[] = [];
  let lastIndex = 0;

  for (const match of value.matchAll(INLINE_MATH_PATTERN)) {
    const matchIndex = match.index ?? 0;
    pushTextSegment(segments, value.slice(lastIndex, matchIndex));

    const formulaValue = (match[1] ?? match[2] ?? match[3] ?? "").trim();
    if (formulaValue) {
      segments.push({ kind: "formula", value: formulaValue });
    }

    lastIndex = matchIndex + match[0].length;
  }

  pushTextSegment(segments, value.slice(lastIndex));
  return segments.length > 0 ? segments : [{ kind: "text", value: "" }];
}

/** 전체 본문을 줄 단위 수식 미리보기 세그먼트로 분리한다. */
export function parseMathMarkupPreview(value: string | null | undefined): PreviewSegment[][] {
  const normalizedValue = value ?? "";
  return normalizedValue.split("\n").map(parseMathMarkupLine);
}
