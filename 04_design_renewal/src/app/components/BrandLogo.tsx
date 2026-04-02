import { cn } from "./ui/utils";

type BrandLogoProps = {
  alt?: string;
  className?: string;
  imageClassName?: string;
};

/** MathHWP 브랜드 로고 이미지를 공통 스타일로 렌더링한다. */
export function BrandLogo({
  alt = "MathHWP 로고",
  className,
  imageClassName,
}: BrandLogoProps) {
  return (
    <div className={cn("liquid-logo-mark overflow-hidden", className)}>
      <img
        alt={alt}
        src="/logo.png"
        draggable={false}
        className={cn("h-full w-full bg-white object-cover", imageClassName)}
      />
    </div>
  );
}
