import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

const tones = {
  default: "bg-[#f3eee4] text-[#5c6754]",
  ok: "bg-[#e4f0e6] text-[#2f6b4f]",
  warn: "bg-[#f4ead4] text-[#9a6b12]",
  bad: "bg-[#f4e4dc] text-[#8a3b1d]",
};

export function Badge({
  className,
  tone = "default",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof tones }) {
  return (
    <span
      className={cn("inline-flex rounded-full px-2 py-0.5 text-xs", tones[tone], className)}
      {...props}
    />
  );
}
