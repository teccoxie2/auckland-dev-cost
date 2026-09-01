# 奥克兰住宅开发核算台

输入奥克兰地址后，系统读取公开地块面积、Unitary Plan 区划和 DEM 坡度，再用**最新公开航拍 / 历史镶嵌**和 LINZ 屋顶轮廓核对场地，给出**适合这块地的初版方案**。正式 **LIM 由客户上传**已购买的议会 PDF，系统只读文字层（污染、风区、土壤、洪水栏、地面径流、管网 LIR、许可编号），并按读到的字段写成中文**开发影响**，不贴 LIM 英文原文。扫描件或附图不做图像识别。你再选户型大小、厨房和卫生间数量，或上传 RC/BC 图纸按文字层套价。挡土墙、覆盖率和叠加层会写进建议；金额不由大模型生成。航拍不是直播，也不能改地籍数字。

## 能做什么

- 多项目屋主工作台（首页不公开列出全库查询；本机浏览器可看自己最近查过的地址）
- 地址 → 地块面积 / 区划 / 叠加层 / 坡度 → 客户上传正式 LIM PDF（文字层） → 公开航拍与屋顶轮廓核对 → 初版方案（许可 / 需 Resource Consent / 这块地放不下）
- 客户选装：套数、层数、卧室、卫生间、厨房、建筑面积，按已读地块重新套价
- 坡地建议：分台、挡土墙、E12 土方门槛（500m² / 250m³）；支撑建筑平台的墙按 surcharge 提示建筑许可
- 户型模板工程量（尺寸进入木材、空腔、屋面、石膏板、卫生间洁具数量）
- 分项总账按全包合同科目分组（前期准备 / 建筑主体 / 内装 / 室外 / 法定与专业费）。能核对到公开 SKU 的计入金额；对照后仍无单价的科目列为缺项，不编价
- 法定费用含建工许可押金、BRANZ/MBIE/BCA 征费、CCC 基础费、占道检查费；有资源许可时计入 RC 押金；IGC/DC 按净增单元
- 第二阶段：在项目页上传 RC / BC PDF，按文字层门窗表和面积套同一价库（扫描件无文字层会失败）
- 图纸物料验证页 `/drawing-takeoff`：不经过选址，上传 RC/BC 后按页读文字层。门窗表、面积表、覆盖率表按行列抽出并在页面上列出每一行；几乎无文字的图页会标出且**不做 OCR**。正则与大模型结果合并；送给模型时优先保留表页，证据核对应全文。数量由服务器按公式、窗表或原文件数重算，单价只走价库。扫描件没有文字层或未配置 `OPENAI_API_KEY` / `CPA_API_KEY` 会失败。

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
- Kaboodle 600mm 地柜：[$130.92](https://www.bunnings.co.nz/kaboodle-600mm-base-cabinet_p0303959)
- Kaboodle 600mm 吊柜：[$123.90](https://www.bunnings.co.nz/kaboodle-600mm-white-wall-carcase-kitset_p2662262)
- Kaboodle 600mm Sea Salt 门板：[$78](https://www.bunnings.co.nz/kaboodle-600mm-sea-salt-modern-cabinet-door_p0193379)
- Kaboodle 2400×600 台面：[$372](https://www.bunnings.co.nz/kaboodle-2400-x-600-x-38mm-square-edge-vanilla-cream-benchtop-2400-x-600mm_p0194541)
- Expol Tuff Pod 1100×1100×300：[$33.01](https://www.bunnings.co.nz/expol-flooring-1100-x-1100-x-300mm-tuff-pods_p0196164)
- Caroma Luna 淋浴混水阀：[$259](https://www.bunnings.co.nz/caroma-luna-bath-shower-mixer_p0131572)
- Caroma Luna 面盆龙头：[RRP $331](https://www.caroma.com/nz/product/caroma-luna-basin-mixer-lead-free-chrome-117128/)
- Crommelin 4L 砖下防水：[$109](https://www.bunnings.co.nz/crommelin-4l-under-tile-waterproofing-membrane_p0356888)
- H5 125×125 2.4m 锚桩：[$62.28](https://www.bunnings.co.nz/125-x-125mm-2-4m-square-h5-anchor-pile_p0276414)
- Strol GeoPlus 1×50m 土工布：[$140.50](https://www.bunnings.co.nz/strol-1-x-50m-geoplus-filter-cloth_p0571904)
- Hume Nexus 15 门扇 1980×860：[$525](https://www.bunnings.co.nz/hume-doors-1980-x-860-x-40mm-nexus-15-unglazed-entrance-door_p0213418)
- Mondella Concerto 单盆水槽：[$198](https://www.bunnings.co.nz/mondella-concerto-single-bowl-sink-and-drainer-with-overflow-kit_p0315490)
- Bellini 60cm 烤箱+电灶包：[$549](https://www.bunnings.co.nz/bellini-60cm-5-function-electric-oven-and-cooktop_p0013228)
- Mondella Resonance 厨房龙头：[$146](https://www.bunnings.co.nz/mondella-resonance-25mm-chrome-side-lever-dual-function-sink-mixer-wels-5-star-6l-min_p0717306)
- 新铝窗 1800×1200 双层中空：[$999](https://diysupply.nz/product/new-ironsand-double-glazed-1800w-x-1200h/)
- 新铝窗 1200×1200 双层中空：[$819](https://diysupply.nz/product/new-1200w-x-1200h-ironsand-window-double-glazed/)

人工与设计（公开区间或公司指引，不是签约报价）：

- 框架安装 [$25–$58/m² 不含 GST](https://tradietools.nz/articles/carpenter-pricing-guide-nz-2026.html)，价库取中位并加 GST
- 设计师费 [3%–5% 造价](https://ecoworkshop.co.nz/architectural-design-fees-nz-guide/)，价库取 5%
- 水管预埋/安装：[每个给排水点 $1,000；主进出水另 $1,000；马桶/淋浴/面盆 fit-off $400 / $450 / $400，含 GST](https://chambersplumbing.co.nz/blogs/news/how-much-does-a-plumbing-renovation-cost)
- 外围脚手架：[搭拆运 $18/m² + 周租 $1/m²/周，另加 GST，最低 1 周](https://skscaffold.co.nz/pages/faqs)

法定费用：

- [Auckland Council 建工许可押金与 levy](https://www.aucklandcouncil.govt.nz/en/building-and-consents/building-consents/building-control-fees.html)（2026-08-24 页面：$100k–$499k 档押金 $5,479）
- [CCC 基础费](https://www.aucklandcouncil.govt.nz/en/building-and-consents/building-consents/building-control-fees.html)（2026-09-01 页面：工程价值 ≥$20,000 为 $722）
- [街道损坏检查](https://www.aucklandcouncil.govt.nz/en/building-and-consents/building-consents/building-control-fees.html)（2026-09-01 页面：$124，代表 Auckland Transport）
- [Auckland Council 资源许可押金](https://www.aucklandcouncil.govt.nz/en/building-and-consents/resource-consents/resource-consent-fees-deposits.html)：住宅土地使用 $6,500
- [Watercare IGC 2026/27 都市区 $29,348.46 含 GST/单元](https://www.watercare.co.nz/builders-and-developers/tools-fees-and-resources/infrastructure-growth-charge)
- [DC Policy 2025](https://ourauckland.aucklandcouncil.govt.nz/media-centre/2025/may/new-development-contributions-policy-approved/)：Rest of Auckland $20,000/HUE，自 2026-07-01 加 2%
- [Auckland Council LIM](https://www.aucklandcouncil.govt.nz/en/buying-property/order-property-report/order-lim.html)（2026-08-25 页面：Standard $387，Urgent $522。客户自行购买后上传 PDF；订购费不计入本页造价）

规划数据：

- 地址：[Auckland Council AC_Address](https://services1.arcgis.com/n4yPwebTjJCmXB6W/arcgis/rest/services/AC_Address_Query/FeatureServer/0)（与 GeoMaps 同一套门牌；同一门牌多条记录时必须从下拉列表选择）
- 区划：[Unitary Plan Base Zone Open Data](https://services1.arcgis.com/n4yPwebTjJCmXB6W/arcgis/rest/services/Unitary_Plan_Base_Zone/FeatureServer/0)
- 地块：[Auckland Council AC_Property](https://services1.arcgis.com/n4yPwebTjJCmXB6W/arcgis/rest/services/AC_Property_Query/FeatureServer/0)
- 坡度：[LINZ NZ 8m DEM / OpenTopodata](https://www.opentopodata.org/datasets/nzdem/)
- 叠加层：Auckland Council UnitaryPlanManagementLayers
- 最新公开航拍：[Esri World Imagery](https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08fda2d9bc)（镶嵌，不是直播）
- 历史航拍：[Esri World Imagery Wayback](https://livingatlas.arcgis.com/wayback/)
- 屋顶轮廓：[LINZ NZ Building Outlines](https://data.linz.govt.nz/layer/101290-nz-building-outlines/)（与地块外包矩形相交，可能含邻户）
- 正式 LIM：客户上传议会 PDF，入口 `POST /projects/{id}/lim`，只读文字层
- 挡土墙许可：[MBIE Schedule 1 exemption 20](https://www.building.govt.nz/projects-and-consents/planning-a-successful-build/scope-and-design/check-if-you-need-consents/building-work-that-doesnt-need-a-building-consent/technical-requirements-for-exempt-building-work/13-support-structures/13-2-retaining-walls-up-to-1-5-metres-depth-of-ground)、[Auckland Council AC2231](https://www.aucklandcouncil.govt.nz/content/dam/ac/docs/building-and-consents/ac2231-retaining-walls.pdf)

替换价表：编辑 `server/app/data/pricebook.json` 与 `server/app/data/council_fees.json`，改完后重启 API（`pricebook()` 有缓存）。运行时只通过 `PriceProvider.get_rate(sku, qty, context)` 取单价：第一期是本地价表，设置 `PRICE_API_URL` 后会再问供应商 HTTP；接口失败或缺 SKU 一律标缺项，不编价。官方 Council / IGC / DC 走 `council_fees.json` 的版本化费率。

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

可选环境变量：

- `DATABASE_URL`：默认 SQLite `server/data/projects.sqlite`（关系表：项目、地块快照、方案、成本版本、图纸集、价表版本）。生产可改为 `postgresql+psycopg://…`；LangGraph checkpoint 在 Postgres 时需另装 `langgraph-checkpoint-postgres` 与 `psycopg`。共享给别人用时，先停 API 再运行 `./scripts/purge-query-data.sh`，避免上一轮查询的地址、LIM 和图纸留在磁盘上。`GET /projects` 不返回全库列表。
- `PM_HITL=1`：`pm_gate` 调用 `interrupt()`，把最终定价权留给项目经理（第一期屋主界面不画审核面板）。
- `PRICE_API_URL`：价源第二实现；未设置时只用价表。
- `ENGINE_URL`：前端服务端请求核算 API，默认 `http://127.0.0.1:8764`。
- `OPENAI_API_KEY`：可选（航拍视觉）/ 图纸物料验证也认这个密钥。航拍：设置后会把最多两张公开航拍送给视觉模型，只描述可见场地，**不得改面积/区划/坡度，不得定价**。
- `CPA_BASE_URL` / `CPA_API_KEY`：本地 [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI)（管理页如 `http://192.168.52.81:8317/management.html`）。核算台会改写成 OpenAI 兼容入口 `…/v1`，用客户端密钥调 `/v1/models` 与 `/v1/chat/completions`。管理页登录密码不要当成模型密钥。图纸推导默认模型为 `gpt-5.6-luna`。
- `OPENAI_BASE_URL` / `SITE_VISION_MODEL` / `DRAWING_LLM_MODEL`：接口与模型名。`DRAWING_LLM_MODEL` 可覆盖默认的 `gpt-5.6-luna`。未走 CPA 时视觉默认 `https://api.openai.com/v1` 与 `gpt-4o-mini`。

浏览器打开 `http://127.0.0.1:43124`。输入 `55 Nelson Street` 会列出 Howick 与 Auckland Central 等多条议会地址，必须点选一条。输入 `115 Bruce Road Glenfield` 时议会已无整宗 115，只会列出拆分后的 115A–F；点选其中一户后，页面只显示该户的议会地籍，并筛掉需要整宗地的方案。本机安全软件（如 Bitdefender）若给 DOM 注入属性，开发态错误浮层会被拦截，不影响核算。

## 生产部署

演示入口：[https://demo-cost.vsense.co.nz](https://demo-cost.vsense.co.nz)。`www.vsense.co.nz` 带 `HSTS includeSubDomains`，子域必须走 Vercel 证书，不能 CNAME 到 `*.trycloudflare.com`。网关在 `demo-gateway/`，Microsoft 365 DNS（不要改 nameserver）：

- CNAME `demo-cost` → Vercel 项目给出的 `*.vercel-dns-013.com`（或 `cname.vercel-dns.com`）
- 若控制台要求验证：TXT `_vercel` → `vc-domain-verify=…`

先构建前端，再同时拉起 API 与 Next：

```bash
cd web && pnpm install && pnpm build && cd ..
./scripts/start-prod.sh
```

或使用 Docker（容器内 127.0.0.1:8764 给 Next 调用，对外只暴露 `$PORT`，默认 43124）：

```bash
docker build -t auckland-dev-cost .
docker run --rm -p 43124:43124 auckland-dev-cost
```

`ENGINE_URL` 默认 `http://127.0.0.1:8764`。不要把 GitHub PAT 或议会密钥写进镜像。

第二阶段在项目页上传 RC/BC PDF。正式 LIM 也在项目页由客户上传议会 PDF，只读文字层。仓库不附带某块地的批准图或 LIM；没有文字层的扫描件无法量尺寸或核对 LIR。门窗表对得上公开尺寸（例如 1800×1200、1200×1200 新铝窗，或 Hume 860 门扇）才计价，其余樘标缺项。

## 架构要点

LangGraph 地址流：`geocode → land → rules → lim → site_vision → typology → quantity → building_rules → cost → explain → pm_gate`。`land` 合并规划区划、地籍与 DEM，并写入 `captured_at` 快照。`lim` 节点只留下「等待客户上传正式 LIM」；不查询公开洪水图层，也不把议会订购费计入造价。客户在项目页上传 PDF 后，`POST /projects/{id}/lim` 读文字层，按 s44A 栏写入污染、风区、土壤、洪水说明、地面径流、LIR 和许可编号。附图不识别。读到的地面径流或 LIR 只驱动缺项专家工作，不编造评估单价，也不把区划可行方案标成 infeasible。LIM 地址必须与当前项目门牌及郊区一致。`site_vision` 读取公开航拍与 LINZ 屋顶轮廓；失败只记 note，不让整图失败。hints 只影响方案排序与说明。`typology` 只做户型硬过滤；`cost` 才走 PriceProvider，并行节点不得写总价。选装走 `POST /projects/{id}/configure`，不再重新查 GIS。图纸流：`parse_drawings → drawing_template → drawing_cost → drawing_explain`，入口为 `POST /projects/{id}/drawings`。独立验证页 `POST /drawings/verify` 调用大模型读文字层并套同一价库。`pm_gate` 默认自动通过；`PM_HITL=1` 时 `interrupt()`。说明节点只写中文，不改金额。

## 开发要求

**不允许使用假数据。** 这是硬性要求，不是可选风格。

- 地址、坐标、地籍、区划、叠加层、DEM、航拍 URL、屋顶轮廓必须来自奥克兰议会 / LINZ / Esri 等公开接口；选址必须从 `AC_Address` 下拉点选。正式 LIM 只认客户上传的议会 PDF 文字层，不能用公开洪水图或流域污染多边形冒充。
- 金额必须来自带链接与取价日期的价表或官方费率表；禁止大模型定价，禁止编造单价或总价。视觉模型不得改写地籍面积、区划或坡度数字。LIM 订购费由客户在议会支付，不计入本页造价。图纸物料验证页可以把文字层送给大模型抽取字段/门窗表并选择已有 SKU，但**数量必须由服务器按公式或窗表重算**，模型输出的金额一律丢弃。
- 没有可核对来源的科目标成缺项（`missing`），不要用估算、经验值、mock、默认地块或缓存值把页面凑完整。
- 图纸和 LIM 只读 PDF 文字层；读不到面积就不要套户型模板的 110 m²，读不到厨卫就不要套模板洁具；读不到 LIM 栏就标未写明，不要用附图识别。
- 单测可以给纯函数喂显式数字或**标明来源的正式 LIM 正文摘录**；不得把假 GIS / 假价源当成议会或供应商返回值。

Agent 实现时遵守 `.cursor/rules/no-fake-data.mdc` 与 `cursor_project_rules/development-requirements.mdc`。
