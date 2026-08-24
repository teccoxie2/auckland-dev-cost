# 奥克兰住宅开发核算台（第一期 MVP）

输入奥克兰地址后，系统读取公开地块面积、Unitary Plan 区划和 DEM 坡度，给出**适合这块地的初版方案**。你再选户型大小、厨房和卫生间数量。挡土墙、覆盖率和叠加层会写进建议；金额不由大模型生成。

## 能做什么

- 多项目屋主工作台
- 地址 → 地块面积 / 区划 / 叠加层 / 坡度 → 初版方案（许可 / 需 Resource Consent / 这块地放不下）
- 客户选装：套数、层数、卧室、卫生间、厨房、建筑面积，按已读地块重新套价
- 坡地建议：分台、挡土墙、E12 土方门槛（500m² / 250m³）；支撑建筑平台的墙按 surcharge 提示建筑许可
- 户型模板工程量（尺寸进入木材、空腔、屋面、石膏板、卫生间洁具数量）
- 分项总账带报价源链接、SKU、取价日期
- 厨房定制、铝窗整樘、EPS 垫块、脚手架等无公开总价的科目标为缺项

## 报价源（2026-08-24 检索）

材料（Bunnings NZ 全国零售标价，奥克兰门店结账可能不同，不等于贸易价）：

- SG8 H1.2 90×45 结构材 5.4m：[$7.41/m](https://www.bunnings.co.nz/90-x-45mm-sg8-h1-2-kd-treated-radiata-timber-framing-5-4m_p0616224)
- SG8 H1.2 140×45 4.8m：[$13.85/m](https://www.bunnings.co.nz/140-x-45mm-sg8-h1-2-kd-treated-radiata-timber-framing-4-8m_p0616436)
- H3.1 45×20 空腔垫条：[$3.02/m](https://www.bunnings.co.nz/45-x-20-h3-1-treated-pine-gauge-batten-4-8m_p0605294)
- GIB 10mm 2400×1200：[$37.42/张](https://www.bunnings.co.nz/gib-10x2400x1200mm-standard-plasterboard-2400mm_p0299316)
- Pink Batts Classic R2.2 13.4m²：[$151.48/包](https://www.bunnings.co.nz/pink-batts-13-4m-classic-r2-2-glasswool-wall-insulation_p0054834)
- Armorsteel 彩色波纹屋面：[$30.35/延米](https://www.bunnings.co.nz/armorsteel-845-x-0-4mm-grey-friars-corrugated-roofing-steel-l-m_p0065119)
- H4 200×50 挡土枕木 2.4m：[$10.60/m](https://www.bunnings.co.nz/200-x-50mm-rad-h4-treated-retaining-timber-2-4m_p0608743)（只用于墙高≤1.2m 的材料；支撑房屋时仍须许可）
- Stein Ero 马桶套装：[$742](https://www.bunnings.co.nz/stein-wels-4-star-4-5-3l-min-ero-back-to-wall-toilet-suite_p0251660)
- Stein Georgia 750mm 淋浴房：[$645](https://www.bunnings.co.nz/stein-750-x-2000mm-white-georgia-3s-square-flat-wall-package_p0380960)

人工与设计（公开区间，不是签约报价）：

- 框架安装 [$25–$58/m² 不含 GST](https://tradietools.nz/articles/carpenter-pricing-guide-nz-2026.html)，价库取中位并加 GST
- 设计师费 [3%–5% 造价](https://ecoworkshop.co.nz/architectural-design-fees-nz-guide/)，价库取 5%

法定费用：

- [Auckland Council 建工许可押金与 levy 2025/26](https://www.aucklandcouncil.govt.nz/en/building-and-consents/building-consents/building-control-fees.html)
- [Watercare IGC 2026/27 都市区 $29,348.46 含 GST/单元](https://www.watercare.co.nz/builders-and-developers/tools-fees-and-resources/infrastructure-growth-charge)
- [DC Policy 2025](https://ourauckland.aucklandcouncil.govt.nz/media-centre/2025/may/new-development-contributions-policy-approved/)：Rest of Auckland $20,000/HUE，自 2026-07-01 加 2%

规划数据：

- 地址：[Auckland Council AC_Address](https://services1.arcgis.com/n4yPwebTjJCmXB6W/arcgis/rest/services/AC_Address_Query/FeatureServer/0)（与 GeoMaps 同一套门牌；同一门牌多条记录时必须从下拉列表选择）
- 区划：[Unitary Plan Base Zone Open Data](https://services1.arcgis.com/n4yPwebTjJCmXB6W/arcgis/rest/services/Unitary_Plan_Base_Zone/FeatureServer/0)
- 地块：[Auckland Council AC_Property](https://services1.arcgis.com/n4yPwebTjJCmXB6W/arcgis/rest/services/AC_Property_Query/FeatureServer/0)
- 坡度：[LINZ NZ 8m DEM / OpenTopodata](https://www.opentopodata.org/datasets/nzdem/)
- 叠加层：Auckland Council UnitaryPlanManagementLayers
- 挡土墙许可：[MBIE Schedule 1 exemption 20](https://www.building.govt.nz/projects-and-consents/planning-a-successful-build/scope-and-design/check-if-you-need-consents/building-work-that-doesnt-need-a-building-consent/technical-requirements-for-exempt-building-work/13-support-structures/13-2-retaining-walls-up-to-1-5-metres-depth-of-ground)、[Auckland Council AC2231](https://www.aucklandcouncil.govt.nz/content/dam/ac/docs/building-and-consents/ac2231-retaining-walls.pdf)

替换价表：编辑 `server/app/data/pricebook.json` 与 `server/app/data/council_fees.json`。后续可把 `pricing.get_item` 换成供应商 API。

## 本地运行

需要 Python 3.12+ 与 Node 22+。

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8764
```

另开终端：

```bash
cd web
pnpm install
pnpm dev
```

浏览器打开 `http://127.0.0.1:43124`。输入 `55 Nelson Street` 会列出 Howick 与 Auckland Central 等多条议会地址，必须点选一条。输入 `115 Bruce Road Glenfield` 会列出 115A–F；点选后再对比 `115D Bruce Road`（细分后的小地块，加密方案会被标成放不下）。

## 架构要点

LangGraph 节点：`geocode → planning → parcel → terrain → rules → advise → options → explain → pm_gate`。选装走 `POST /projects/{id}/configure`，不再重新查 GIS。`pm_gate` 第一期自动通过。核算在 `costing.py`，模型只写中文说明。

## 开发要求

**不允许使用假数据。** 这是硬性要求，不是可选风格。

- 地址、坐标、地籍、区划、叠加层、DEM 必须来自奥克兰议会 / LINZ 等公开接口；选址必须从 `AC_Address` 下拉点选。
- 金额必须来自带链接与取价日期的价表或官方费率表；禁止大模型定价，禁止编造单价或总价。
- 没有可核对来源的科目标成缺项（`missing`），不要用估算、经验值、mock、默认地块或缓存值把页面凑完整。
- 单测可以给纯函数喂显式数字；不得把假 GIS / 假价源当成议会或供应商返回值。

Agent 实现时遵守 `.cursor/rules/no-fake-data.mdc` 与 `cursor_project_rules/development-requirements.mdc`。
