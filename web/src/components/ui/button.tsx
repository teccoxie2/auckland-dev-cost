import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

const variants = {
  primary: "bg-[#2f4a32] text-white hover:bg-[#3f6b45]",
  outline: "border border-[#d9d0c0] bg-[#fffaf3] text-[#1c2416] hover:border-[#2f4a32]",
  ghost: "text-[#2f4a32] hover:bg-[#f3eee4]",
};

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof variants }) {
  return (
    <button
      className={cn(
        "inline-flex h-11 items-center justify-center rounded-xl px-5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-60",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
