import type { ProjectRecord } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SiteSnapshot({ project }: { project: ProjectRecord }) {
  const site = project.result.site;
  const rules = project.result.rules;
  const snapshot = site?.snapshot;
  const captured = snapshot?.captured_at || site?.captured_at;
  const overlays = (site?.overlays || []).filter((item) => item.present);
  const cluster = site?.subdivision;
  const parcel = site?.parcel;
  const coverageCap =
    parcel?.found && parcel.area_m2 && rules?.coverage ? `本户约 ${Math.round(parcel.area_m2 * rules.coverage)} m² 占地` : null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>地块快照</CardTitle>
        <p className="mt-1 text-xs text-[#7b8474]">
          {captured ? `查询时刻 ${new Date(captured).toLocaleString("zh-CN")}` : "尚未写入查询时刻"}
          {snapshot?.region ? ` · ${snapshot.region}` : ""}
        </p>
      </CardHeader>
      <CardContent className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <SnapshotField label="规范地址" value={site?.geo.display_name || "未读到"} href={site?.geo.source_url} />
        <SnapshotField label="Unitary Plan 区划" value={site?.zone?.zone_name || "未读到"} href={site?.zone?.source_url} />
        <SnapshotField
          label="本户地块"
          value={parcel?.found && parcel.area_m2 ? `${parcel.area_m2} m²` : parcel?.note || "未读到"}
          href={parcel?.source_url}
        />
        {cluster?.found ? (
          <SnapshotField
            label="议会现址"
            value={
              cluster.selected_unit
                ? `${cluster.selected_unit}${cluster.unit_count ? ` · 同号 ${cluster.unit_count} 户需分别点选` : ""}`
                : cluster.note || "—"
            }
            href={cluster.source_url}
          />
        ) : null}
        <SnapshotField
          label="DEM 坡度"
          value={
            site?.terrain?.slope_deg != null
              ? `${site.terrain.slope_deg}° · ${site.terrain.height_range_m} m`
              : site?.terrain?.note || "未读到"
          }
          href={site?.terrain?.source_url}
        />
        <SnapshotField label="许可套数" value={`${rules?.permitted_dwellings ?? "—"} 套`} />
        <SnapshotField
          label="覆盖率上限"
          value={coverageCap || (rules?.coverage != null ? `${Math.round(rules.coverage * 100)}%` : "—")}
        />
        <SnapshotField
          label="叠加层命中"
          value={overlays.length ? overlays.map((item) => item.key).join("、") : "抽查层未命中"}
        />
        <SnapshotField label="地籍" value={parcel?.legal_description || parcel?.formatted_address || "—"} />
      </CardContent>
    </Card>
  );
}

function SnapshotField({ label, value, href }: { label: string; value: string; href?: string }) {
  return (
    <div>
      <p className="text-xs text-[#7b8474]">{label}</p>
      <p className="mt-1 font-medium leading-6">{value}</p>
      {href ? (
        <a href={href} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-[#2f4a32]">
          数据源
        </a>
      ) : null}
    </div>
  );
}
