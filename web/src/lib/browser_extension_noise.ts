const EXTENSION_MARKERS = [
  "chrome-extension://",
  "moz-extension://",
  "safari-web-extension://",
  "bis_skin_checked",
  "bis_register",
  "__processed_",
];

export function errorText(value: unknown): string {
  if (value instanceof Error) return `${value.name}: ${value.message}\n${value.stack || ""}`;
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value) || String(value);
  } catch {
    return String(value);
  }
}

export function isBrowserExtensionNoise(value: unknown): boolean {
  const text = errorText(value);
  if (/reading ['"]M_ID['"]/.test(text)) return true;
  return EXTENSION_MARKERS.some((marker) => text.includes(marker));
}

export function isExtensionHydrationNoise(args: unknown[]): boolean {
  const text = args.map(errorText).join("\n");
  const isHydration =
    text.includes("hydrated but some attributes") ||
    text.includes("Hydration failed") ||
    text.includes("react.dev/link/hydration-mismatch");
  if (!isHydration) return false;
  return EXTENSION_MARKERS.some((marker) => text.includes(marker));
}
