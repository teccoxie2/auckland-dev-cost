import { isBrowserExtensionNoise, isExtensionHydrationNoise } from "./lib/browser_extension_noise";

function shouldIgnoreConsoleError(args: unknown[]): boolean {
  return isExtensionHydrationNoise(args) || args.some((arg) => isBrowserExtensionNoise(arg));
}

function ignoreExtensionEvent(event: Event) {
  event.preventDefault();
  event.stopImmediatePropagation();
}

window.addEventListener(
  "unhandledrejection",
  (event) => {
    if (isBrowserExtensionNoise(event.reason)) ignoreExtensionEvent(event);
  },
  true,
);

window.addEventListener(
  "error",
  (event) => {
    if (
      isBrowserExtensionNoise(event.error) ||
      isBrowserExtensionNoise(event.message) ||
      /^(chrome|moz|safari-web)-extension:\/\//.test(event.filename || "")
    ) {
      ignoreExtensionEvent(event);
    }
  },
  true,
);

try {
  const nativeConsoleError = console.error.bind(console);

  function wrapConsoleError(inner: (...args: unknown[]) => void) {
    return (...args: unknown[]) => {
      if (shouldIgnoreConsoleError(args)) return;
      inner(...args);
    };
  }

  let current: (...args: unknown[]) => void = wrapConsoleError(nativeConsoleError);

  Object.defineProperty(console, "error", {
    configurable: true,
    enumerable: true,
    get() {
      return current;
    },
    set(next: unknown) {
      if (typeof next !== "function") return;
      current = wrapConsoleError((next as (...args: unknown[]) => void).bind(console));
    },
  });
} catch {
  // 拦截失败时保持原 console.error，不阻断页面。
}
