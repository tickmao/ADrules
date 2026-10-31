# 源选型与评分机制

这个库收录什么、不收录什么，用一套可复核的打分决定，而不是凭印象。本文说明评分维度、准入规则、本轮结论和自动化流程。当前的实时数据在 [sources-report.md](sources-report.md)（每周自动生成）。

## 1. 两条硬约束

1. **单点故障不能造成覆盖缺口**：同一个拦截维度至少有 2–3 个互相独立的来源，且每个源本身要有多端点（镜像）回退。
2. **体积可控**：单个订阅的预算是 5MB。超过就需要不可替代的理由，否则进候选池。

「精致」在这里的定义是：**每一条都值得订阅，且没有一条是另一条的马甲。**

## 2. 评分维度

| 维度 | 权重 | 怎么测 | 满分条件 |
| --- | --- | --- | --- |
| 活跃度 activity | 30% | 最近一次内容更新时间，依次取 HTTP `Last-Modified`、规则头 `Last modified`/`Version`、GitHub `pushed_at` | ≤ 2 天 |
| 维护度 maintenance | 20% | 近 30 天提交数；带 `Checksum`/`Diff-Path` 等自动生成头加 0.5；上游 archived 扣 2 | 30 天内 ≥ 8 次提交 |
| 口碑 reputation | 25% | EasyList / AdGuard / uBlock Origin / Fanboy / anti-AD / pgl.yoyo 等官方维护者直接满分；其余按 GitHub stars 分档 | 官方，或 ≥ 10k stars |
| 维度覆盖 coverage | 10% | 该源实际拦截的维度数（ads / tracker / annoyance / cookie / malware / mobile） | ≥ 5 个维度 |
| 独立来源 originality | 10% | 上游作者自维护 = 5；二次聚合 = 2.5 | 非聚合 |
| 可用性 compatibility | 5% | ABP/uBO 语法可用、体积 ≤ 5MB、非注释行 ≥ 200、许可证明确 | 全部满足 |

加权求和后分档：**S ≥ 4.2、A ≥ 3.4、B ≥ 2.6、C < 2.6**。

## 3. 准入规则

- **A 级及以上**才能进 `scripts/config.yaml` 的 `sources`。
- 每个拦截维度至少 **2 个独立来源**；只有 1 个来源时报告会标「单点风险」。
- B 级及以下、体积超标、或与现有源重复的，只写进 `scripts/candidates.yaml` 并注明理由。
- 聚合源（把别人的规则再打一次包）默认降权，除非它能提供别人没有的维度。

## 4. 本轮结论（2026-10-31）

收录 18 个源。相较上一版新增 10 个，都是为了补覆盖维度或补单点风险：

| 新增 | 类别 | 补的是什么 |
| --- | --- | --- |
| AdGuard Base Filter | ads / global | 独立于 EasyList 的通用广告规则，官方维护 |
| AdGuard Chinese Filter | ads / cn | 中文广告的第二个官方来源，与社区规则互补 |
| AWAvenue 秋风广告规则 | ads / cn | 轻量中文规则（23KB），移动端与 App 内广告，误杀低 |
| yoyo.org Ad Server List | ads / global | 极小体积（69KB）的服务器名单，低误杀备选 |
| uBlock filters – Privacy | privacy / global | 隐私维度第二个独立来源（EasyPrivacy 之外） |
| AdGuard Annoyances Filter | annoyance / global | 中文之外的干扰清理，同时覆盖 Cookie 横幅 |
| EasyList Cookie List | cookie / global | 替换已停更的 I don't care about cookies |
| uBlock filters – Badware risks | security / global | 恶意与钓鱼站点拦截 |
| NoCoin Filter List | security / global | 浏览器挖矿脚本，16KB |
| AdGuard Mobile Ads Filter | mobile / global | 移动端广告，补齐 mobile 维度 |

**淘汰与观察**（完整清单与理由见 `scripts/candidates.yaml`）：

- `AdGuard Tracking Protection`：实测 13MB / 38 万条，与 EasyPrivacy 目的重合，体积代价超过收益。
- `HaGeZi TIF`：36MB，直接否决；`HaGeZi Pro` 4.5MB 留在候选池。
- `uBlock Quick fixes`：规则带过期时间，不适合做长期订阅。
- `217heidai/adblockfilters`、`BlueSkyXN`、`REIJI007`（75MB）等聚合：与本库已有源重复。
- `I don't care about cookies`：2023 年起对任何 UA 返回 403，上游已停止分发 ABP 订阅。
- `neodevhost`、`Google 中文搜索结果屏蔽`：分别是 hosts 与 uBlacklist 语法，不是 ABP。

## 5. 多端点策略

每个源的 `urls` 是**有序**列表，前一个不可达时自动降级到下一个，日志会记录实际生效的端点。

- GitHub 托管的源：`raw.githubusercontent.com` → `cdn.jsdelivr.net`（国内通常只有后者可用）。
- uBlock Origin 的源：`ublockorigin.github.io` → `raw.githubusercontent.com` → jsDelivr 三端点。
- AdGuard 官方 `filters.adtidy.org` 没有公开镜像，属于已知单点风险，只能靠候选池里的等价源兜底。

用户自己订阅时同样建议用 jsDelivr 域名，README 里给的就是这个。

## 6. 自动化流程

```
GitHub Actions（6h）  update.py     ── 拉取 → 内容哈希比对 → 校验 → 原子写入 → 提交
GitHub Actions（周）   discover.py   ── 探测 → 评分 → 维度覆盖 → 写 docs/sources-report.md
```

`discover.py` 的两种能力：

- **体检**：探测全部正式源与候选池，标出不可达、超过 30 天未更新、体积异常，并给出同类别替代建议。
- **发现**（`--search`）：用 GitHub 搜索（topic / 关键词 / 中英文）找出最近 90 天内活跃、stars ≥ 100 的仓库，再在仓库里自动定位可疑的订阅文件并探测。结果只作为线索写进报告。

发现结果保留人工一环是刻意的：能否被订阅取决于语法格式、许可证和体积，机器只能给线索，判断留在 `candidates.yaml`。

本地运行：

```bash
pip install -r scripts/requirements-dev.txt
python scripts/discover.py --no-github        # 只体检，不需要 gh 登录
python scripts/discover.py --search --json /tmp/sources.json
```

## 7. 已知风险

| 风险 | 现状 | 处理 |
| --- | --- | --- |
| 乘风规则 225 天未更新 | C 级，仍在正式源 | 保留（历史价值与用户基数），报告持续标记 |
| CJX / NoCoin 接近 30 天阈值 | B 级 | 报告每周复查，超阈值会报警 |
| 中文隐私维度只有 2 个来源 | 偏少 | 候选池已备 `uniartisan's Privacy List`（13MB） |
| AdGuard 三条源无镜像 | 单端点 | 依赖官方 CDN，候选池有 `HaGeZi Pro` 等价替代 |
| 国内直连 raw.githubusercontent 常失败 | 已缓解 | 库内源与用户订阅都提供 jsDelivr 端点 |
