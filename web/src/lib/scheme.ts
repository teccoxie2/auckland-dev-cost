export const KIND_LABEL_ZH: Record<string, string> = {
  standalone: "独栋",
  duplex: "双拼",
  terrace: "联排",
  minor_dwelling: "主屋 + 独立住宅",
};

export function kindLabelZh(kind?: string) {
  if (!kind) return "—";
  return KIND_LABEL_ZH[kind] || kind;
}
