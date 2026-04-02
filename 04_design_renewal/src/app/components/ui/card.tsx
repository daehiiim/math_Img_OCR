import * as React from "react";

import { cn } from "./utils";

/** 리퀴드 글라스 표면의 기본 카드 래퍼를 제공한다. */
function Card({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card"
      className={cn(
        "bg-card text-card-foreground flex flex-col gap-5 overflow-hidden rounded-[28px] border border-white/70 shadow-[0_24px_48px_-36px_rgba(86,118,164,0.22)]",
        className,
      )}
      {...props}
    />
  );
}

/** 카드 상단의 제목과 액션 배치를 일정한 간격으로 정리한다. */
function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-2 px-5 pt-5 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-5 sm:px-6 sm:pt-6",
        className,
      )}
      {...props}
    />
  );
}

/** 카드 제목의 밀도를 비홈 리퀴드 화면에 맞게 통일한다. */
function CardTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <h4
      data-slot="card-title"
      className={cn("text-[15px] leading-none tracking-[-0.02em]", className)}
      {...props}
    />
  );
}

/** 카드 설명 텍스트를 보조 정보 밀도로 맞춘다. */
function CardDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <p
      data-slot="card-description"
      className={cn("text-[13px] leading-6 text-muted-foreground", className)}
      {...props}
    />
  );
}

/** 카드 우측 상단 액션 슬롯을 유지한다. */
function CardAction({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-action"
      className={cn(
        "col-start-2 row-span-2 row-start-1 self-start justify-self-end",
        className,
      )}
      {...props}
    />
  );
}

/** 카드 본문 여백을 리퀴드 보드 밀도에 맞춘다. */
function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-content"
      className={cn("px-5 [&:last-child]:pb-5 sm:px-6 [&:last-child]:sm:pb-6", className)}
      {...props}
    />
  );
}

/** 카드 하단 액션 영역의 기본 정렬과 패딩을 제공한다. */
function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex items-center px-5 pb-5 [.border-t]:pt-5 sm:px-6 sm:pb-6 [.border-t]:sm:pt-6", className)}
      {...props}
    />
  );
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
};
