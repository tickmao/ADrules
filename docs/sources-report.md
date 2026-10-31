# 源健康与发现报告

- 生成时间：2026-10-31 02:16 UTC
- 正式源：18 个，其中健康 15 个
- 候选池：20 个（仅观察，不参与订阅）

评分机制见 [sources.md](sources.md)：活跃度 30%、维护度 20%、口碑 25%、维度覆盖 10%、独立来源 10%、可用性 5%。

## 正式源

| 源 | 类别 | 区域 | 等级 | 评分 | 状态 | 最近更新 | 体积 | 端点 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EasyList Cookie List | cookie | global | S | 4.80 | ok | 刚刚 | 0.86MB | 1 |
| EasyList China | ads | cn | S | 4.40 | ok | 刚刚 | 0.48MB | 1 |
| uBlock filters – Privacy | privacy | global | S | 4.40 | ok | 刚刚 | 0.18MB | 3 |
| uBlock filters – Badware risks | security | global | S | 4.30 | ok | 刚刚 | 0.26MB | 3 |
| AdGuard Base Filter | ads | global | S | 4.20 | ok | 刚刚 | 4.15MB | 1 |
| AdGuard Chinese Filter | ads | cn | S | 4.20 | ok | 刚刚 | 0.68MB | 1 |
| AdGuard Annoyances Filter | annoyance | global | S | 4.20 | ok | 刚刚 | 3.97MB | 1 |
| AdGuard Mobile Ads Filter | mobile | global | S | 4.20 | ok | 刚刚 | 0.50MB | 1 |
| anti-AD | ads | cn | A | 4.15 | ok | 刚刚 | 1.97MB | 1 |
| EasyList | ads | global | A | 4.10 | ok | 刚刚 | 1.93MB | 1 |
| EasyPrivacy | privacy | global | A | 4.10 | ok | 刚刚 | 1.44MB | 1 |
| yoyo.org Ad Server List | ads | global | A | 4.00 | ok | 1 天前 | 0.07MB | 1 |
| AWAvenue 秋风广告规则 | ads | cn | A | 3.92 | ok | 5 天前 | 0.02MB | 2 |
| AdRules | ads | cn | A | 3.60 | ok | 刚刚 | 5.12MB | 2 |
| HalfLife | comprehensive | cn | A | 3.48 | ok | 5 天前 | 0.55MB | 2 |
| CJX's Annoyance List | annoyance | cn | B | 2.83 | stale | 30 天前 | 0.05MB | 2 |
| NoCoin Filter List | security | global | B | 2.73 | stale | 49 天前 | 0.02MB | 2 |
| 乘风广告过滤规则 | ads | cn | C | 2.27 | stale | 225 天前 | 0.03MB | 2 |

## 维度覆盖

| 维度 | 覆盖源数 | 来源 | 冗余判断 |
| --- | --- | --- | --- |
| ads | 12 | EasyList, AdGuard Base Filter, yoyo.org Ad Server List, EasyList China, AdGuard Chinese Filter, anti-AD, AdRules, 乘风广告过滤规则, AWAvenue 秋风广告规则, CJX's Annoyance List, AdGuard Mobile Ads Filter, HalfLife | 充分 |
| annoyance | 6 | AdGuard Chinese Filter, AWAvenue 秋风广告规则, CJX's Annoyance List, AdGuard Annoyances Filter, EasyList Cookie List, HalfLife | 充分 |
| cookie | 2 | AdGuard Annoyances Filter, EasyList Cookie List | 偏少 |
| malware | 5 | anti-AD, AdRules, AWAvenue 秋风广告规则, uBlock filters – Badware risks, NoCoin Filter List | 充分 |
| mobile | 2 | AWAvenue 秋风广告规则, AdGuard Mobile Ads Filter | 偏少 |
| privacy | 2 | EasyPrivacy, uBlock filters – Privacy | 偏少 |
| tracker | 7 | EasyList, AdGuard Base Filter, anti-AD, AdRules, EasyPrivacy, uBlock filters – Privacy, HalfLife | 充分 |

## 需要关注

- **乘风广告过滤规则** 已 225 天前 未更新（阈值 30 天），先确认上游是否仍在维护
- **CJX's Annoyance List** 已 30 天前 未更新（阈值 30 天），先确认上游是否仍在维护
- **NoCoin Filter List** 已 49 天前 未更新（阈值 30 天），先确认上游是否仍在维护

## 候选池

| 源 | 状态 | 等级 | 评分 | 最近更新 | 体积 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| uBlock filters | ok | S | 4.30 | 刚刚 | 0.45MB | uBO 自有规则，与 EasyList 高度重叠；AdGuard 用户价值更大，暂列候选 |
| uBlock filters – Quick fixes | ok | S | 4.30 | 刚刚 | 0.09MB | 带过期时间的临时补丁，规则会自然失效，不适合做长期订阅，否决 |
| AdGuard DNS Filter | ok | S | 4.25 | 刚刚 | 4.51MB | 官方 DNS 层规则，覆盖 App 内广告；4.5MB，与 ads 类重叠较多，暂列候选 |
| HaGeZi's Pro DNS Blocklist | ok | A | 4.15 | 刚刚 | 4.52MB | 社区口碑极好（28k stars），体积 4.5MB；适合 AdGuard Home 用户 |
| AdGuard Tracking Protection Filter | ok | A | 4.10 | 刚刚 | 12.42MB | 实测 13MB / 38 万条规则，与 EasyPrivacy 目的重合但体积代价过高，否决 |
| AdGuard Social Media Filter | ok | A | 4.10 | 刚刚 | 0.90MB | 社交按钮屏蔽，需求窄且与 AdGuard Annoyances 部分重合，否决 |
| Fanboy's Annoyance List | ok | A | 4.10 | 刚刚 | 2.08MB | EasyList 体系的干扰清理，与 AdGuard Annoyances 二选一即可 |
| HaGeZi's Threat Intelligence Feeds | ok | A | 3.90 | 刚刚 | 36.52MB | 唯一实测体积 36MB，远超本库对单个订阅的体积预算，否决 |
| REIJI007 Adblock-Rule-Collection | ok | A | 3.65 | 刚刚 | 72.24MB | 实测 75MB 的全量聚合，许可证不明确，否决 |
| 217heidai AdBlock Filters | ok | A | 3.58 | 2 天前 | 5.72MB | 7.7k stars，聚合 anti-AD / EasyList China 等；适合只订阅一条的用户，但与本库已有源大量重叠 |
| uniartisan's Privacy List | ok | A | 3.55 | 1 天前 | 12.73MB | 中文隐私与追踪规则，实测 13MB；可作为 privacy 维度的第三来源，但体积代价高 |
| GOODBYEADS | ok | A | 3.42 | 7 天前 | 8.97MB | 近 2k stars 的中文综合规则，实测 9.4MB；体积偏大，暂列候选 |
| Silentely AdBlock-Acceleration | ok | A | 3.40 | 刚刚 | 6.12MB | 内容为 AdGuard Base 的再分发，与已收录源重复，否决 |
| NEO DEV HOST | ok | B | 3.30 | 刚刚 | 2.99MB | 只有 hosts 格式，浏览器订阅无法直接使用，否决 |
| OISD Big | ok | B | 3.02 | 刚刚 | 4.86MB | 以低误杀著称的 DNS 合集；纯域名格式，体积 4.9MB |
| 1Hosts Lite | stale | C | 2.58 | 58 天前 | 2.24MB | 移动端与 IoT 场景常用；更新节奏较慢（近 2 个月无提交） |
| Google 中文搜索结果屏蔽 | unreachable | C | 2.08 | 236 天前 | - | uBlacklist 语法，不是 ABP/uBO 过滤规则，否决 |
| ADgk 手机广告过滤 | unreachable | C | 2.05 | - | - | 仓库与订阅地址均已不可达，否决 |
| I don't care about cookies | unreachable | C | 1.95 | - | - | 自 2023 年起对任何 UA 都返回 403，上游已停止分发 ABP 订阅；改用 EasyList Cookie，仓库中保留旧文件仅为兼容历史订阅 |
| BlueSkyXN AdGuardHomeRules | unreachable | C | 1.78 | 312 天前 | - | 本质是对本库同款上游的再镜像，无新增维度，且近 2 年无提交，否决 |

## 自动搜索发现

以下条目由 GitHub 搜索自动产生，未经人工审核，仅作线索：

| 仓库 | Stars | 最近提交 | 探测到的订阅文件 |
| --- | --- | --- | --- |
| ZingyAwesome/easylists-for-pihole | 176 | 2026-10-31 | https://raw.githubusercontent.com/ZingyAwesome/easylists-for-pihole/HEAD/easylist.txt |
| List-KR/List-KR | 246 | 2026-10-30 | https://raw.githubusercontent.com/List-KR/List-KR/HEAD/filterslists/adblocking/filters-share/specific_ELEMHIDE.txt |
| blocklistproject/Lists | 5177 | 2026-10-27 | https://raw.githubusercontent.com/blocklistproject/Lists/HEAD/adguard/malware-ags.txt |
| yokoffing/filterlists | 3644 | 2026-10-12 | - |
| Stevoisiak/Stevos-AI-Blocklist | 1041 | 2026-10-30 | - |
| ukrainianfilters/lists | 116 | 2026-09-08 | - |
| Johnshall/Shadowrocket-ADBlock-Rules-Forever | 31696 | 2026-10-30 | - |
| zhouzhouprogram/Shadowrocket-ADBlock-Rules | 877 | 2026-10-30 | - |
