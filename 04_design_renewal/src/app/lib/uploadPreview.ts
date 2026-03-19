const ALLOWED_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/jpg"]);
const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024;

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
