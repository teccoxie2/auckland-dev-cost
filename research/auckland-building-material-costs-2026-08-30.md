# 奥克兰建材公开成本清单

- **检索日**：2026-08-30
- **货币**：NZD
- **未写入核算台网页**，也未改 `server/app/data/pricebook.json`（除非另行要求）
- **禁止编造单价**：下列数字均来自当日能打开或能从商品页摘要核到的公开标价。核不到的写在「缺项」里，不填数字。

## 口径与限制

1. **不是「整个奥克兰每一家贸易商的全部 SKU」**。PlaceMakers、ITM、Carters 的贸易价多数要登录；Firth / Allied 商品混凝土不公布全国统一立方价。公开网上能稳定核到的，主要是 **Bunnings NZ 全国零售标价**、少数专营店零售、以及人工/脚手架的公开指引。
2. **Bunnings 全国零售 ≠ 奥克兰某店结账价 ≠ PlaceMakers/ITM 贸易价**。奥克兰门店库存、Special Order、运费会改实付。
3. **含 GST**：Bunnings、Diy Supply、Metroscaff、Chambers、Warehouse Building Supplies 页面标价按含 GST 记录。SK Scaffold FAQ 的 $18/m² 与 $1/m²/周 **另加 GST**。设计师百分比另加 GST。
4. **人工、设计、脚手架**不是建材 SKU，但住宅造价里会用到，单独成表。不是签约报价。
5. 检索方式：商品页标题/价格块（Bunnings 部分页被 Cloudflare 拦截时，用同一商品页的公开摘要核价）。Diy Supply 本机 IP 被拦，价格来自该站商品页公开摘要。

对照价库版本：`pricebook.json` **2026-08-24**。

---

## 一、结构木材（Bunnings NZ）

| 品名 | 规格 | SKU / I/N | 标价 | 折合单价 | 含 GST | 相对 08-24 价库 | 来源 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SG8 H1.2 KD 辐射松结构材 | 90×45mm，5.4m | 0616224 | $40.01 / 根 | **$7.41 / 延米** | 是 | 持平 | [商品页](https://www.bunnings.co.nz/90-x-45mm-sg8-h1-2-kd-treated-radiata-timber-framing-5-4m_p0616224) |
| SG8 H3.2 湿材（室外） | 90×45mm，5.4m | 0616340 | $55.94 / 根 | **$10.36 / 延米** | 是 | 价库未收此 SKU | [商品页](https://www.bunnings.co.nz/90-x-45mm-sg8-h3-2-treated-green-radiata-timber-framing-5-4m_p0616340) |
| SG8 H1.2 KD | 140×45mm，4.8m | 0616436 | $66.46 / 根 | **$13.85 / 延米** | 是 | 持平 | [商品页](https://www.bunnings.co.nz/140-x-45mm-sg8-h1-2-kd-treated-radiata-timber-framing-4-8m_p0616436) |
| SG8 H1.2 KD | 140×45mm，6.0m | 0616348 | $83.08 / 根 | **$13.85 / 延米** | 是 | 同规格加长，延米同 | [商品页](https://www.bunnings.co.nz/140-x-45mm-sg8-h1-2-kd-treated-radiata-timber-framing-6m_p0616348) |
| SG8 H3.2 KD | 140×45mm，4.8m | 0616335 | $75.35 / 根 | **$15.70 / 延米** | 是 | 价库未收 | [商品页](https://www.bunnings.co.nz/140-x-45mm-sg8-h3-2-kd-treated-radiata-timber-framing-4-8m_p0616335) |
| SG8 H3.2 KD | 140×45mm，5.4m | 0616400 | $84.77 / 根 | **$15.70 / 延米** | 是 | 价库未收 | [商品页](https://www.bunnings.co.nz/140-x-45mm-sg8-h3-2-kd-treated-radiata-timber-framing-5-4m_p0616400) |
| SG8 H3.2 KD | 140×45mm，6.0m | 0616343 | $94.19 / 根 | **$15.70 / 延米** | 是 | 价库未收 | [商品页](https://www.bunnings.co.nz/140-x-45mm-sg8-h3-2-kd-treated-radiata-timber-framing-6m_p0616343) |
| H1.2 天花垫条 | 73×34mm，5.4m | 0605267 | $32.98 / 根 | **$6.11 / 延米** | 是 | 价库未收 | [商品页](https://www.bunnings.co.nz/73-x-34mm-5-4m-h1-2-treated-pine-gauge-ceiling-batten_p0605267) |
| H1.2 天花垫条 | 72×34mm，4.8m | 0605265 | $28.46 / 根 | **$5.93 / 延米** | 是 | 价库未收 | [商品页](https://www.bunnings.co.nz/72-x-34-h1-2-treated-pine-gauge-ceiling-batten-4-8m_p0605265) |
| H1.2 天花垫条 | 71×34mm，4.2m | 0605277 | $24.91 / 根 | **$5.93 / 延米** | 是 | 价库未收 | [商品页](https://www.bunnings.co.nz/71-x-34-h1-2-treated-pine-gauge-ceiling-batten-4-2m_p0605277) |
| H3.1 空腔垫条 | 45×20mm，4.8m | 0605294 | $14.50 / 根 | **$3.02 / 延米** | 是 | 持平 | [商品页](https://www.bunnings.co.nz/45-x-20-h3-1-treated-pine-gauge-batten-4-8m_p0605294) |

其他渠道（同规格、不同处理/产地，**不能当同一 SKU**）：

| 品名 | 渠道 | 标价 | 含 GST | 来源 |
| --- | --- | --- | --- | --- |
| 90×45 H3.2 TW SG8（多长度变体；5.4m 当日标售罄） | Rangitikei Timber | 例：4.8m **$27.36**/根；按延米变体 **$5.70**/m | 是（Taxes included） | [商品页](https://rangitikeitimber.co.nz/products/90x45-h3-2-tw-sg8-framing) |
| Radiata SG8 H3.2 KD 5.4m 100×50（90×45） | KiwiPro Building Supplies | **$48.74**/根 | 是 | [商品页](https://www.kiwiprosupplies.co.nz/products/radiata-structural-timber-sg8-h32-kd-mg-54m-100x50-90x45) |

PlaceMakers Cavibat 1200×45×18mm（SKU 3373447）页面出现 **$8.79**，同时要求登录查 **Trade Price**。不能当作已确认的奥克兰贸易成交价。  
[PlaceMakers 商品页](https://www.placemakers.co.nz/online/fastenings-general-hardware/fastenings/ties-soakers/soakers/cavity-batten-system-1200-x-45-x-18mm/p/3373447)

---

## 二、板材、保温、屋面、包膜

| 品名 | 规格 | SKU / I/N | 标价 | 折合 | 含 GST | 相对价库 | 来源 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GIB Standard 10mm | 2400×1200 | 0299316 | **$37.42**/张（仅店内） | $12.99/m²（÷2.88） | 是 | 持平 | [商品页](https://www.bunnings.co.nz/gib-10x2400x1200mm-standard-plasterboard-2400mm_p0299316) |
| GIB Standard 10mm TE/SE | 2400×1200 | 0319508 | **$38.21**/张 | $13.27/m² | 是 | 价库用的是 0299316 | [商品页](https://www.bunnings.co.nz/gib-10x2400x1200mm-te-se-standard-plasterboard_p0319508) |
| GIB Standard 13mm | 2400×1200 | （分类页列出） | **$45.45**/张 | — | 是 | 价库未收 | [分类页](https://www.bunnings.co.nz/products/building-hardware/building-boards/plaster-accessories/plasterboards-cladding) |
| ProRoc 10mm 石膏板 | 2400×1200 | （分类页列出） | **$32.63**/张 | — | 是 | 价库未收 | 同上分类页 |
| Pink Batts Classic R2.2 | 13.4 m² 包，90mm 墙 | 0054834 | **$151.48**/包 | $11.30/m²（÷13.4） | 是 | 持平 | [分类/商品](https://www.bunnings.co.nz/products/building-hardware/insulation/insulation-batts) |
| Pink Batts Narrow R2.2 | 9 m² | — | **$88.35**/包 | $9.82/m² | 是 | 价库未收 | 同上 |
| Pink Batts Ultra R2.6 | 9.6 m² | — | **$160.31**/包 | $16.70/m² | 是 | 价库未收 | 同上 |
| Armorsteel 彩色波纹屋面 | 845×0.4mm Grey Friars，按延米 | 0065119 | **$30.35**/延米 | 有效覆盖宽约 0.762m | 是 | 持平 | [商品页](https://www.bunnings.co.nz/armorsteel-845-x-0-4mm-grey-friars-corrugated-roofing-steel-l-m_p0065119) |
| Armorsteel 同规格 Karaka | 845×0.4mm | 0065122 | **$30.35**/延米 | — | 是 | 同价不同色 | [商品页](https://www.bunnings.co.nz/armorsteel-845-x-0-4mm-karaka-corrugated-roofing-steel-l-m_p0065122) |
| Armorsteel 锌波纹 | 845×0.4mm | 0065123 | **$22.15**/延米 | — | 是 | 价库未收 | [商品页](https://www.bunnings.co.nz/armorsteel-845-x-0-4mm-zinc-corrugate-roofing-steel_p0065123) |
| Thermakraft 215 油毡底衬 | 1250mm×40m，约 50 m² | 0552872 | **$157.50**/卷 | $3.15/m² | 是 | 价库未收 | [商品页](https://www.bunnings.co.nz/thermakraft-roof-underlay-215-1250mmx40m-50m2_p0552872) |
| Thermakraft Covertek 407 | 1250mm×40m，50 m² | 0282200 | **$476.11**/卷（Special Order） | $9.52/m² | 是 | 价库未收 | [商品页](https://www.bunnings.co.nz/thermakraft-covertek-407-1250mmx40m-50m-underlay_p0282200) |
| IBuilt CD H3.2 结构胶合板 | 12×1200×2400mm | 0327742 | **$90.50**/张 | $31.42/m² | 是 | 价库未收 | [商品页](https://www.bunnings.co.nz/ibuilt-12-x-1200-x-2400mm-cd-h3-2-structural-plywood_p0327742) |

其他渠道：

| 品名 | 渠道 | 标价 | GST | 来源 |
| --- | --- | --- | --- | --- |
| GIB Standard 10mm 2400×1200 | SaveBuild NZ | **$29.50 不含 GST**（含 GST ≈ $33.93） | 标「excl. GST」 | [商品页](https://savebuild.co.nz/products/10mm-gib-standard-plasterboard) |
| GIB Standard 10mm 2.4×1.2m | ITM Stratford（**非奥克兰**，对照用） | **$45.16**/张含 GST；Priority Card $42.15 | 是 | [商品页](https://www.itmstratford.co.nz/product/gib-standard-10mm-2-4-x-1-2m/) |
| Pink Batts Classic R2.2 13.4 m² | Elite Insulation（奥克兰仓，可同日取货） | **$130.85**/包含 GST；奥克兰货运另 **$14.40**/包 | 是 | [商品页](https://www.eliteinsulation.co.nz/shop/product/pink-batts-classic-r2.2-wall-insulation---1140mm-x-560mm-x-90mm,-13.4m%C2%B2-per-bale/) |
| Ecoply CD H3.2 12mm 2400×1200 | Mitre 10 | **$101**/张 | 页面未逐条写 GST；按零售惯例视为含 GST | [商品页](https://www.mitre10.co.nz/shop/ecoply-structural-plywood-cd-h3-2-treated-2400-x-1200-x-12mm-green/p/434140) |
| ARAUCOPLY CD H3.2 12mm 2400×1200 | Warehouse Building Supplies（自称奥克兰唯一贸易仓店） | **$79.99**/张含 GST（划线 $86.95） | 是 | [商品页](https://www.warehousebuildingsupplies.co.nz/shop/102025-ply-h32-cd-f8-structural-2400x1200x12mm-30198) |

屋面安装综述（**不是 SKU**，[Roofing Expert](https://roofingexpert.co.nz/blog/colorsteel-roofing-cost-nz/)）：Colorsteel 材料约 $18–$35/m²；奥克兰含铺装约 $90–$140/m²。只作区间，不能当核算单价。

---

## 三、基础、混凝土、挡土

| 品名 | 规格 | SKU | 标价 | 含 GST | 相对价库 | 来源 |
| --- | --- | --- | --- | --- | --- | --- |
| Expol Tuff Pod | 1100×1100×300mm | 0196164 | **$33.01**/块（Special Order，仅店内） | 是 | 持平 | [商品页](https://www.bunnings.co.nz/expol-flooring-1100-x-1100-x-300mm-tuff-pods_p0196164) |
| H4 挡土枕木 | 200×50mm，2.4m | 0608743 | $25.44 / 根，**$10.60 / 延米** | 是 | 持平 | [商品页](https://www.bunnings.co.nz/200-x-50mm-rad-h4-treated-retaining-timber-2-4m_p0608743) |
| 同上 | 3.0m | 0608741 | $31.80，**$10.60 / 延米** | 是 | — | [商品页](https://www.bunnings.co.nz/200-x-50mm-rad-h4-treated-retaining-timber-3m_p0608741) |
| 同上 | 3.6m | 0608746 | $38.16，**$10.60 / 延米** | 是 | — | [商品页](https://www.bunnings.co.nz/200-x-50mm-rad-h4-treated-retaining-timber-3-6m_p0608746) |
| 同上 | 4.2m | 0608748 | $44.52，**$10.60 / 延米** | 是 | — | [商品页](https://www.bunnings.co.nz/200-x-50mm-rad-h4-treated-retaining-timber-4-2m_p0608748) |
| 同上 | 4.8m | 0608754 | $45.53，**$9.49 / 延米** | 是 | 加长更便宜 | [商品页](https://www.bunnings.co.nz/200-x-50mm-rad-h4-treated-retaining-timber-4-8m_p0608754) |
| H5 方锚桩 | 125×125mm，2.4m | 0276414 | **$62.28**/根（约 $25.95/m） | 是 | 持平 | [商品页](https://www.bunnings.co.nz/125-x-125mm-2-4m-square-h5-anchor-pile_p0276414) |
| Strol GeoPlus 滤布 | 1×50m | 0571904 | **$140.50**/卷 | 是 | 持平 | [商品页](https://www.bunnings.co.nz/strol-1-x-50m-geoplus-filter-cloth_p0571904) |
| Cemix 低碳水泥 | 20kg | 0581734 | **$10.97**/袋 | 是 | 价库未收 | [商品页](https://www.bunnings.co.nz/cemix-20kg-low-carbon-cement_p0581734) |
| Cemix Ecostrong 低碳水泥 | 20kg | （分类页） | **$11.59**/袋 | 是 | 与上款不同 SKU | [分类页](https://www.bunnings.co.nz/products/building-hardware/cement-concreting/cement) |
| Cemix Fastcrete | 20kg | 0241402 | **$11.94**/袋（分类页） | 是 | 桩孔用，非筏板 | [分类页](https://www.bunnings.co.nz/products/building-hardware/cement-concreting/concrete) |
| Cemix Super Strength Fastcrete | 20kg | 0341405 | **$16.75**/袋（商品页；分类页曾列 $15.39，以商品页为准） | 是 | 桩孔 30MPa，非结构浇筑 | [商品页](https://www.bunnings.co.nz/cemix-20kg-super-strength-fastcrete_p0341405) |
| Cemix No Steel Concrete | 20kg | — | **$14.64**/袋（分类页） | 是 | — | [分类页](https://www.bunnings.co.nz/products/building-hardware/cement-concreting) |

其他渠道：

| 品名 | 渠道 | 标价 | GST | 来源 |
| --- | --- | --- | --- | --- |
| 聚苯乙烯垫块 1100×1100×300 | Quality Steel Supplies | **$23.28 不含 GST**（含 GST ≈ $26.77） | 否 | [商品页](https://qualitysteelsupplies.co.nz/product/polystyrene-pods-300mm/) |
| H5 125×125 2.4m 锚桩 | Warehouse Building Supplies | **$45.00** | 页面写 RETAIL | [商品页](https://www.warehousebuildingsupplies.co.nz/shop/107128-anchor-pile-125mm-square-h5-2-4mtr-30627) |
| 同上 | ITM Stratford（非奥克兰） | **$55.79** 含 GST；Priority $51.81 | 是 | [商品页](https://www.itmstratford.co.nz/product/anchor-pile-125-x-125-2-4m-h5-sawn/) |
| 同上 | Mitre 10 | **$79.50**/根 | 零售页 | [商品页](https://www.mitre10.co.nz/shop/pine-products-125x125-anchor-pile-h5-treated-2400mm/p/2053026) |
| Strol GeoPlus 1×50m | Mitre 10 | **$154**/卷 | 零售页 | [商品页](https://www.mitre10.co.nz/shop/strol-cirtex-geoplus-geotextile-filter-fabric-1m-x-50m-white/p/223961) |

### 商品混凝土（无全国 SKU）

- **Firth / Allied 不公布奥克兰 $ /m³ 价目表**，只接受询价。
- Firth 自 **2026-08-10** 对 Certified Concrete 加收燃油附加费 **$6.00 / m³**（2026-08-06 更新）。[来源](https://www.firth.co.nz/temporary-fuel-surcharge)
- Allied 燃油附加费按周浮动；检索到的公开叙述称 2026-08-24 当周 **$6.93 / m³**（需以 Allied 当周通知为准）。
- 价库 08-24 引用的 Rotorua Concrete Services 综述页 **当日请求超时**，**不能把 $210–$250/m³ 当作 2026-08-30 已重新核对的现价**。

---

## 四、外墙（Linea）与紧固件

| 品名 | 规格 | SKU | 标价 | 含 GST | 来源 |
| --- | --- | --- | --- | --- | --- |
| James Hardie Linea 外墙板 | 4200×150×16mm | 0288097 | **$56**/根（仅店内） | 是 | [商品页](https://www.bunnings.co.nz/james-hardie-linea-4200-x-150-x-16mm-weatherboard_p0288097) |
| James Hardie Linea 外墙板 | 4200×180×16mm | 0558011 | **$68.72**/根 | 是 | [商品页](https://www.bunnings.co.nz/james-hardie-linea-4200-x-180-x-16mm-weatherboard_p0558011) |
| Linea 镀锌钉 | 60×3.15mm，5kg | 0548531 | **$85.55**/盒 | 是 | [商品页](https://www.bunnings.co.nz/nz-nails-60-x-3-15mm-galvanised-linea-jolt-head-nail-5kg-box_p0548531) |

150mm 板 4.2m → 约 **$13.33 / 延米**；180mm 板 → 约 **$16.36 / 延米**。空腔、包膜、油漆、安装未含。

---

## 五、门窗

| 品名 | 规格 | SKU | 标价 | 含 GST | 相对价库 | 来源 |
| --- | --- | --- | --- | --- | --- | --- |
| Hume Nexus 15 入户门扇（无玻璃） | 1980×860×40mm | 0213418 | **$525**（Special Order） | 是 | 持平 | [商品页](https://www.bunnings.co.nz/hume-doors-1980-x-860-x-40mm-nexus-15-unglazed-entrance-door_p0213418) |
| Hume Nexus 15 | 1980×810×40mm | 0213401 | **$525** | 是 | — | [商品页](https://www.bunnings.co.nz/hume-doors-1980-x-810-x-40mm-nexus-15-unglazed-entrance-door_p0213401) |
| 新铝窗 双层中空 Ironsand | 1800×1200 | — | **$999** | 是 | 持平 | [Diy Supply](https://diysupply.nz/product/new-ironsand-double-glazed-1800w-x-1200h/) |
| 新铝窗 双层中空 Ironsand | 1200×1200 | — | **$819** | 是 | 持平 | [Diy Supply](https://diysupply.nz/product/new-1200w-x-1200h-ironsand-window-double-glazed/) |
| 新铝窗 双层中空 Ironsand | 1800×600 | — | **$769** | 是 | 价库未收 | [Diy Supply](https://diysupply.nz/product/new-1800w-x-600h-ironsand-aluminium-window/) |

Diy Supply 在 Hamilton 取货，运到奥克兰的运费未标。Low-E / 磨砂 / 着色玻璃另加价。  
The Doorshed Nexus NEX15R 1980×860 无玻璃：**$529**（缺货）。[来源](https://doorshed.co.nz/products/nexus-nex15r)

---

## 六、厨卫洁具、柜体、防水

| 品名 | 规格 | SKU | 标价 | 含 GST | 相对价库 | 来源 |
| --- | --- | --- | --- | --- | --- | --- |
| Stein Ero 背墙马桶套装 | WELS 4 星 4.5/3L | 0251660 | **$719**（Special Order） | 是 | **价库 08-24 为 $742，下调 $23** | [商品页](https://www.bunnings.co.nz/stein-wels-4-star-4-5-3l-min-ero-back-to-wall-toilet-suite_p0251660) |
| Stein Georgia 整体淋浴 750 | 750×2000 白 3S | 0380960 | **$645** | 是 | 持平 | [商品页](https://www.bunnings.co.nz/stein-750-x-2000mm-white-georgia-3s-square-flat-wall-package_p0380960) |
| Stein Georgia 铬 3S | 750×2000 | 0380961 | **$645** | 是 | — | [商品页](https://www.bunnings.co.nz/stein-750-x-2000mm-chrome-georgia-3s-square-flat-wall-package_p0380961) |
| Stein Vida 淋浴包 | 900×1830 铬 | 0154725 | **$494** | 是 | 价库未收 | [商品页](https://www.bunnings.co.nz/stein-900-x-1830mm-chrome-vida-square-flat-wall-shower-package_p0154725) |
| Caroma Luna 浴/淋混水阀 | 铬 | 0131572 | **$259** | 是 | 持平 | [商品页](https://www.bunnings.co.nz/caroma-luna-bath-shower-mixer_p0131572) |
| Caroma Luna 浴/淋 拉丝镍 | — | — | **$268**（分类页） | 是 | — | [分类页](https://www.bunnings.co.nz/products/bathroom-plumbing/bathroom/bathroom-tapware/shower-mixer-taps) |
| Caroma Luna 面盆龙头（无铅铬） | 68181C6AF | — | **RRP $331.00** | RRP | 持平 | [Caroma NZ](https://www.caroma.com/nz/product/caroma-luna-basin-mixer-lead-free-chrome-117128/) |
| Kaboodle 600 地柜柜体 | — | 0303959 | **$130.92** | 是 | 持平 | [商品页](https://www.bunnings.co.nz/kaboodle-600mm-base-cabinet_p0303959) |
| Kaboodle 600 吊柜柜体 | 白 | 2662262 | **$123.90** | 是 | 持平 | [商品页](https://www.bunnings.co.nz/kaboodle-600mm-white-wall-carcase-kitset_p2662262) |
| Kaboodle 600 转角吊柜 | — | 2662265 | **$127** | 是 | — | [商品页](https://www.bunnings.co.nz/kaboodle-kitset-600mm-corner-wall-cabinet-carcase_p2662265) |
| Kaboodle 600 Sea Salt 门板 | Modern | 0193379 | **$78**（Special Order） | 是 | 持平 | [商品页](https://www.bunnings.co.nz/kaboodle-600mm-sea-salt-modern-cabinet-door_p0193379) |
| Kaboodle 450 Sea Salt 门板 | Modern | 0193378 | **$61** | 是 | — | [商品页](https://www.bunnings.co.nz/kaboodle-450mm-sea-salt-modern-cabinet-door_p0193378) |
| Kaboodle 层压台面 | 2400×600×38 Vanilla Cream | 0194541 | **$372** | 是 | 持平 | [商品页](https://www.bunnings.co.nz/kaboodle-2400-x-600-x-38mm-square-edge-vanilla-cream-benchtop-2400-x-600mm_p0194541) |
| Mondella Concerto 单盆水槽 | 860×500×200 | 0315490 | **$198** | 是 | 持平 | [商品页](https://www.bunnings.co.nz/mondella-concerto-single-bowl-sink-and-drainer-with-overflow-kit_p0315490) |
| Mondella Resonance 圆盆 | — | 5090441 | **$129** | 是 | — | [商品页](https://www.bunnings.co.nz/mondella-resonance-sink-bowl-round-with-overflow-kit_p5090441) |
| Mondella Resonance 厨房龙头 | 双出水，WELS 5 星 6L/min | 0717306 | **$146** | 是 | 持平 | [商品页](https://www.bunnings.co.nz/mondella-resonance-25mm-chrome-side-lever-dual-function-sink-mixer-wels-5-star-6l-min_p0717306) |
| Bellini 60cm 烤箱+电灶包 | builders pack | 0013228 | **$549** | 是 | 持平 | [商品页](https://www.bunnings.co.nz/bellini-60cm-5-function-electric-oven-and-cooktop_p0013228) |
| Bellini 60cm 电灶 | — | — | **$198** | 是 | — | [品牌页](https://www.bunnings.co.nz/brands/b/bellini) |
| Bellini 60cm 洗碗机 | — | — | **$250** | 是 | — | 同上 |
| Crommelin 砖下防水 | 4L | 0356888 | **$109** | 是 | 持平 | [商品页](https://www.bunnings.co.nz/crommelin-4l-under-tile-waterproofing-membrane_p0356888) |
| Crommelin 淋浴防水套装 | 4L kit | 0964050 | **$124** | 是 | — | [商品页](https://www.bunnings.co.nz/crommelin-4l-shower-waterproofing-kit_p0964050) |
| Crommelin 室外可刷防水 | 4L | 0961599 | **$107.64** | 是 | — | [商品页](https://www.bunnings.co.nz/crommelin-4l-exterior-grade-brushable-waterproofer_p0961599) |
| Crommelin PRO-500 | 15kg | — | **$187** | 是 | — | [品牌页](https://www.bunnings.co.nz/brands/c/crommelin) |

Caroma Luna 浴/淋混水阀其他零售（对照，不是 Bunnings）：Plumbing Plus **$228** 含 GST；The Blue Space **$242**；The Tile Collection **$229**。面盆龙头：The Blue Space **$307**；The Tile Collection **$287.50**。RRP 仍是 $331。

---

## 七、人工、脚手架、设计（公开指引，不是建材 SKU）

### 木工（TradieTools，2026-05 市场综述，**不含 GST**）

来源：[NZ Carpenter Hourly Rates 2026](https://tradietools.nz/articles/carpenter-pricing-guide-nz-2026.html)

| 项目 | 公开区间 | 备注 |
| --- | --- | --- |
| 持牌 LBP 木工对外工时 | $72–$95 / 小时 | 奥克兰/惠灵顿靠区间上沿。价库取 $85 + GST = $97.75 |
| 合格木工（有证） | $58–$78 / 小时 | |
| 单层轻木框架安装 | $25–$40 / m² 建筑面积 | 价库框架项取 $25–$58 中位再加 GST |
| 二层框架 | $38–$58 / m² | |
| 复杂屋面/挑空 | $60–$90 / m² | |
| 挂门（含框、预装） | $130–$220 / 樘 | |
| 踢脚/门套 | $18–$30 / 延米 | |
| 橱柜安装 | $900–$2,400 / 套人工 | |

### 水管（Chambers Plumbing guideline，**含 GST**）

来源：[How much does a plumbing renovation cost?](https://chambersplumbing.co.nz/blogs/news/how-much-does-a-plumbing-renovation-cost)

| 项目 | 标价 | 相对价库 |
| --- | --- | --- |
| 预埋：每个给排水点 | $1,000 | 持平 |
| 预埋：主进出水 | $1,000 | 持平 |
| 马桶 fit-off 附加 | $400 | 持平 |
| 淋浴 fit-off 附加 | $450 | 持平 |
| 面盆/龙头 fit-off 附加 | $400 | 持平 |
| 厨房水槽 fit-off 附加 | $600 | 价库故意不套（台面常由其他工种装） |
| 洗衣槽 fit-off | $600 | 户型无洗衣房时不套 |
| 热水器安装附加（示例 Rheem 180L） | $2,655.29 | 不套 |

官网写明是 guideline，正式报价另出。

### 脚手架

**Metroscaff（奥克兰，Snells Beach 自提；含 GST）**  
[周租页](https://www.metroscaff.co.nz/store/p/mobile-scaffolding-weekly-hire)

| 项目 | 标价 |
| --- | --- |
| 1m 平台周租 | $50 |
| 2m | $95 |
| 3m | $140（价库持平） |
| 4m | $185 |
| 5m | $230（价库持平） |
| 送装+收回一口价 | $255（价库持平） |
| 最低租期 | 1 周 |
| 平台尺寸 | 1.4×2.4m，含护栏 |

这是移动塔，不是整栋外围脚手架。

**SK Scaffold（奥克兰/Northland；网页价另加 GST，indicative）**  
[FAQ](https://skscaffold.co.nz/pages/faqs)

| 项目 | 标价 |
| --- | --- |
| 搭拆运 | $18 / m² 脚手架立面，一次性 |
| 周租 | $1 / m² / 周，最低 1 周 |
| 周检 | $75 / 次（价库不编检查次数） |
| 收缩膜工程签章 | $2,000（另计） |

例：60 m² × 4 周 = $1,080 + $240 = $1,320 + GST。

### 设计费

[Eco Workshop 指南](https://ecoworkshop.co.nz/architectural-design-fees-nz-guide/)（2026-05-08）：新住宅设计师概念到建工许可图常见 **3%–5%** 造价；注册建筑师全服务常见 **8%–12%**。价库取 5%，另加 GST。这是全国口径文章，不是奥克兰某事务所报价单。

---

## 八、与 2026-08-24 价库对照（仅已复核 SKU）

| 价库 id | 08-24 | 08-30 | 变化 |
| --- | --- | --- | --- |
| timber_sg8_90x45_h12 | $7.41/m | $7.41/m | 无 |
| timber_sg8_140x45_h12 | $13.85/m | $13.85/m | 无 |
| cavity_batten_h31_45x20 | $3.02/m | $3.02/m | 无 |
| gib_std_10mm | $37.42/张 | $37.42/张 | 无 |
| pink_batts_r22_wall | $151.48/包 | $151.48/包 | 无 |
| roofing_corrugate_colour_845 | $30.35/m | $30.35/m | 无 |
| retaining_sleeper_h4_200x50 | $10.60/m | $10.60/m | 无 |
| toilet_stein_ero | **$742** | **$719** | **- $23** |
| shower_stein_georgia_750 | $645 | $645 | 无 |
| kaboodle_* / sink / oven / kitchen tap | 原价 | 原价 | 无 |
| window 1800 / 1200 | $999 / $819 | $999 / $819 | 无 |
| door_hume_nexus15_860 | $525 | $525 | 无 |
| expol_tuffpod_1100x300 | $33.01 | $33.01 | 无 |
| tap_caroma_luna_shower / basin RRP | $259 / $331 | $259 / $331 | 无 |
| membrane / pile / geotextile | 原价 | 原价 | 无 |
| Metroscaff / SK Scaffold / Chambers / 木工区间 | 原价 | 原价 | 无 |
| concrete_readymix_20mpa $245 | 区间中位 | **08-30 未能重核综述页** | 不更新数字 |

---

## 九、网上渠道里仍然缺、因此不填数字

| 缺项 | 原因 |
| --- | --- |
| PlaceMakers / ITM / Carters 贸易价全表 | 要 Trade 账号；页面「Check your price」 |
| Firth / Allied 20–30 MPa 送达立方价 | 只接受询价；仅核到燃油附加费 |
| 奥克兰骨料、级配碎石、回填吨价 | 按料场报价，无全国统一零售 |
| 钢过梁 / UB | Bunnings 无公开 UB 标价 |
| Colorsteel Endura/Maxx 按项目卷材 | 零售可核的是 Armorsteel 波纹延米 |
| 未命中 Diy Supply 尺寸的铝窗/推拉门 | 1500、2100 窗及 2100/2400/3000 门仍须厂商报价 |
| 整樘铝入户门（含框五金） | 仅核到 Hume 门扇 |
| 钢筋网、混凝土砌块 20 系列单块零售 | Firth 无公开块价 |
| 电工 30A 硬接线工时 | 无公开工时表 |
| 涂料整栋外墙系统（底漆+面漆按 m² 系统价） | 只有单罐零售，未在本清单展开 |

---

## 十、使用注意

- 奥克兰住宅开发若走贸易商，Bunnings 零售通常高于 PlaceMakers/ITM 成交价；没有登录就不要把零售价说成贸易价。
- 同一截面不同长度，延米价可以差一截（例如 H4 200×50：2.4–4.2m 为 $10.60/m，4.8m 为 $9.49/m）。
- 马桶 SKU 0251660 已从 $742 降到 $719。若要把核算台价库改成 08-30，需要另一次改 `pricebook.json`（本次按要求只整理清单，不改引擎、不加网页）。
