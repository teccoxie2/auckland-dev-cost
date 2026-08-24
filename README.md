# 奥克兰住宅开发核算台（第一期 MVP）

输入奥克兰地址后，系统读取公开地块与 Unitary Plan 区划，生成多种开发方案（3 房 2 卫、3 房 3 卫、4 房 4 卫、双拼、三联排、主屋+minor dwelling），并用**可核对的公开报价源**核算成本。金额不由大模型生成。

## 能做什么

- 多项目屋主工作台
- 地址 → 区划 / 叠加层 → 方案过滤（许可 / 需 Resource Consent / 不可行）
- 户型模板工程量（尺寸进入木材、空腔、屋面、石膏板等数量）
- 分项总账带报价源链接、SKU、取价日期
- 厨房、铝窗整樘、EPS 垫块、脚手架等无公开总价的科目标为缺项，不填假数

## 报价源（2026-08-24 检索）

材料（Bunnings NZ 全国零售标价，奥克兰门店结账可能不同，不等于贸易价）：

- SG8 H1.2 90×45 结构材 5.4m：[$7.41/m](https://www.bunnings.co.nz/90-x-45mm-sg8-h1-2-kd-treated-radiata-timber-framing-5-4m_p0616224)
- SG8 H1.2 140×45 4.8m：[$13.85/m](https://www.bunnings.co.nz/140-x-45mm-sg8-h1-2-kd-treated-radiata-timber-framing-4-8m_p0616436)
- H3.1 45×20 空腔垫条：[$3.02/m](https://www.bunnings.co.nz/45-x-20-h3-1-treated-pine-gauge-batten-4-8m_p0605294)
- GIB 10mm 2400×1200：[$37.42/张](https://www.bunnings.co.nz/gib-10x2400x1200mm-standard-plasterboard-2400mm_p0299316)
- Pink Batts Classic R2.2 13.4m²：[$151.48/包](https://www.bunnings.co.nz/pink-batts-13-4m-classic-r2-2-glasswool-wall-insulation_p0054834)
- Armorsteel 彩色波纹屋面：[$30.35/延米](https://www.bunnings.co.nz/armorsteel-845-x-0-4mm-grey-friars-corrugated-roofing-steel-l-m_p0065119)

人工与设计（公开区间，不是签约报价）：

- 框架安装 [$25–$58/m² 不含 GST](https://tradietools.nz/articles/carpenter-pricing-guide-nz-2026.html)，价库取中位并加 GST
- 设计师费 [3%–5% 造价](https://ecoworkshop.co.nz/architectural-design-fees-nz-guide/)，价库取 5%

法定费用：

- [Auckland Council 建工许可押金与 levy 2025/26](https://www.aucklandcouncil.govt.nz/en/building-and-consents/building-consents/building-control-fees.html)
- [Watercare IGC 2026/27 都市区 $29,348.46 含 GST/单元](https://www.watercare.co.nz/builders-and-developers/tools-fees-and-resources/infrastructure-growth-charge)
- [DC Policy 2025](https://ourauckland.aucklandcouncil.govt.nz/media-centre/2025/may/new-development-contributions-policy-approved/)：Rest of Auckland $20,000/HUE，自 2026-07-01 加 2%

规划数据：

- 地址：[OpenStreetMap Nominatim](https://nominatim.openstreetmap.org/)
- 区划：[Unitary Plan Base Zone Open Data](https://services1.arcgis.com/n4yPwebTjJCmXB6W/arcgis/rest/services/Unitary_Plan_Base_Zone/FeatureServer/0)
- 叠加层：Auckland Council UnitaryPlanManagementLayers

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

浏览器打开 `http://127.0.0.1:43124`，先试 `115 Bruce Road, Glenfield, Auckland`（Mixed Housing Urban）。

## 架构要点

LangGraph 节点：`geocode → planning → rules → options → explain → pm_gate`。`pm_gate` 第一期自动通过，预留以后 `interrupt()` 给项目经理。核算在 `costing.py`，模型只写中文说明。
