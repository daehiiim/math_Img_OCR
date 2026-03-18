const ALLOWED_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/jpg"]);
const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024;

function decodeDataUrlBody(dataUrl: string): Uint8Array {
  const [header, body] = dataUrl.split(",", 2);
  const isBase64 = header.includes(";base64");

  if (!body) {
    throw new Error("유효하지 않은 data url입니다.");
  }

  if (!isBase64) {
    return new TextEncoder().encode(decodeURIComponent(body));
  }

  const decoded = atob(body);
  return Uint8Array.from(decoded, (char) => char.charCodeAt(0));
}

function readMimeType(dataUrl: string): string {
  const [header] = dataUrl.split(",", 1);
  const mimeType = header.replace(/^data:/, "").split(";")[0];
  return mimeType || "application/octet-stream";
}

// 업로드 가능한 이미지인지 확인하고 오류 메시지를 반환한다.
export function validateImageFile(file: File): string | null {
  if (!ALLOWED_IMAGE_TYPES.has(file.type)) {
    return "지원되지 않는 파일 형식입니다.";
  }

  if (file.size > MAX_IMAGE_SIZE_BYTES) {
    return "파일 크기가 제한을 초과했습니다.";
  }

  return null;
}

// 데모용 data url을 브라우저 File 객체로 변환한다.
export function dataUrlToFile(dataUrl: string, fileName: string): File {
  const bytes = Uint8Array.from(decodeDataUrlBody(dataUrl));

  return new File([bytes], fileName, {
    type: readMimeType(dataUrl),
  });
}
