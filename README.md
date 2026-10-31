# ADrules

广告过滤规则订阅库。每 6 小时同步上游，当前收录 18 份规则，均保留原作者与许可证。

规则文件都在仓库根目录，可以直接当订阅地址用；仓库里另有源清单、更新脚本和每周生成的[源健康报告](docs/sources-report.md)。

## 使用方法

订阅地址统一用 jsDelivr 域名（`cdn.jsdelivr.net`），国内网络可以直接访问。如果你在海外或者更在意时效，把链接里的

```
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/
```

换成

```
https://raw.githubusercontent.com/tickmao/ADrules/master/
```

即可。jsDelivr 有缓存，新版本最多滞后几小时。

### uBlock Origin

打开 uBlock Origin 面板，点齿轮进设置 → 「过滤器列表」→ 滚到底部「自定义」→ 勾选「导入」→ 把订阅地址粘进去（一行一个）→ 「应用更改」。

### AdGuard 浏览器扩展

设置 → 「过滤器」→ 底部「自定义过滤器」→ 「添加自定义过滤器」→ 粘贴地址 → 「下一步」→ 「添加」。

### AdGuard Home

「过滤器」→ 「DNS 黑名单」→ 添加订阅地址。本库的规则是 ABP 语法，AdGuard Home 可以直接解析；如果你只需要域名层面的拦截，也可以看候选池里几个纯域名清单。

### 手机端

Shadowrocket、Surge、Quantumult X、Loon 之类工具都支持远程规则订阅，粘贴地址即可。手机上建议只订移动端那几条，体积小、耗电低。

## 推荐订阅

不知道订什么就按下面挑一组，链接直接复制。

**只订一条**：已经打包好的中文综合规则。

```
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/HalfLife.txt
```

**桌面日常**：通用广告 + 中文广告 + 反跟踪 + 国内域名库，拦截率和性能比较平衡。

```
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/Easylist.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/EasyListChina.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/EasyPrivacy.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/anti-AD.txt
```

**想拦得彻底**：再加上 AdGuard 官方基础规则、中文规则、干扰元素与 Cookie 横幅。体积会明显变大。

```
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/Easylist.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/AdGuard-Base.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/EasyListChina.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/AdGuard-Chinese.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/anti-AD.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/EasyPrivacy.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/AdGuard-Annoyances.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/EasyList-Cookie.txt
```

**手机端**：

```
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/AWAvenue-Ads-Rule.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/AdGuard-Mobile-Ads.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/EasyListChina.txt
```

**担心误杀正常页面**：只订体积小、规则保守的几条。

```
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/PeterLowe-List.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/EasyListChina.txt
https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/uBlock-Privacy.txt
```

## 规则列表

### 通用广告

| 规则 | 订阅链接 | 体积 | 说明 |
| --- | --- | --- | --- |
| EasyList | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/Easylist.txt) | 1.9 MB | 国际广告过滤的事实标准 |
| AdGuard Base Filter | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/AdGuard-Base.txt) | 4.1 MB | AdGuard 官方基础规则，已剔除 EasyList 部分 |
| yoyo.org Ad Server List | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/PeterLowe-List.txt) | 69 KB | 极小的服务器名单，低误杀 |

### 中文广告

| 规则 | 订阅链接 | 体积 | 说明 |
| --- | --- | --- | --- |
| EasyList China | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/EasyListChina.txt) | 0.48 MB | EasyList 的中文站补充 |
| AdGuard Chinese Filter | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/AdGuard-Chinese.txt) | 0.66 MB | AdGuard 官方中文过滤 |
| anti-AD | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/anti-AD.txt) | 2.0 MB | 国内使用最广的反广告域名库 |
| AdRules | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/AdRules.txt) | 5.1 MB | 中文广告、追踪器与恶意域名综合规则 |
| 乘风广告过滤规则 | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/ChengFeng.txt) | 27 KB | 视频与页面广告规则，上游已长期停更，见下文 |
| AWAvenue 秋风广告规则 | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/AWAvenue-Ads-Rule.txt) | 23 KB | 轻量，主打移动端与 App 内广告 |
| HalfLife | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/HalfLife.txt) | 0.55 MB | 整合多个中文规则，一条搞定 |

### 隐私与追踪

| 规则 | 订阅链接 | 体积 | 说明 |
| --- | --- | --- | --- |
| EasyPrivacy | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/EasyPrivacy.txt) | 1.4 MB | 反跟踪与隐私保护基准 |
| uBlock filters – Privacy | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/uBlock-Privacy.txt) | 0.18 MB | uBlock Origin 官方隐私规则 |

### 页面干扰与 Cookie

| 规则 | 订阅链接 | 体积 | 说明 |
| --- | --- | --- | --- |
| CJX's Annoyance List | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/Cjx-Annoyance.txt) | 55 KB | 中文站点浮层、弹窗、诱导按钮 |
| AdGuard Annoyances Filter | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/AdGuard-Annoyances.txt) | 3.9 MB | 弹窗、订阅提示、社交组件、Cookie 横幅 |
| EasyList Cookie List | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/EasyList-Cookie.txt) | 0.86 MB | 自动关掉 Cookie 同意横幅 |

### 安全

| 规则 | 订阅链接 | 体积 | 说明 |
| --- | --- | --- | --- |
| uBlock filters – Badware risks | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/uBlock-Badware.txt) | 0.26 MB | 恶意软件与钓鱼站点 |
| NoCoin Filter List | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/NoCoin.txt) | 16 KB | 浏览器挖矿脚本 |

### 移动端

| 规则 | 订阅链接 | 体积 | 说明 |
| --- | --- | --- | --- |
| AdGuard Mobile Ads Filter | [订阅](https://cdn.jsdelivr.net/gh/tickmao/ADrules@master/AdGuard-Mobile-Ads.txt) | 0.50 MB | 移动端页面与 App 内嵌广告 |

## 关于更新

所有规则每 6 小时检查一次，只有内容真的变化才提交，所以 commit 历史本身就是变更记录。

### 停更的源

库里有两类状态不同的规则，订阅前值得分清：

- **上游停止分发**：比如原来的 `I-Dont-Care-About-Cookies.txt`。上游从 2023 年起对任何请求都返回 403，内容永久冻结。文件保留只为不让老订阅变成 404，实际请改用 `EasyList-Cookie.txt`。
- **源本身没问题，但长期没更新**：比如乘风广告过滤规则（最后更新 2026-03）。它的规则是人工整理的视频/页面广告清单，长期有效，而且用的人不少，所以继续保留、继续提供订阅。这一类在[源健康报告](docs/sources-report.md)里会明确标成 `stale`，评分也会随之下调，但不会被悄悄删掉。

判断某个源是否还健康，看 `docs/sources-report.md`：里面有每个源的最近更新时间、体积、评分和状态。

## 常见问题

**同时订阅多条会冲突吗？**
不会。ABP 语法是规则并集，最多多一点重复规则的内存开销。唯一要注意的是别同时订阅「聚合包」和它的全部上游，例如 HalfLife 已经包含乘风与 EasyList China，再单独订就重复了。

**多久能拿到新规则？**
仓库每 6 小时更新一次；jsDelivr 有缓存，最迟几小时内生效。想立刻拿到最新版本就用 `raw.githubusercontent.com` 的地址。

**某个网站还有广告怎么办？**
先换成「想拦得彻底」那组；如果还是不行，开 issue 附网址和截图，我来判断是上游没覆盖还是需要本地自定义规则。

**订阅链接打不开？**
先试 jsDelivr。如果 `cdn.jsdelivr.net` 也不通，把它换成 `fastly.jsdelivr.net` 或 `gcore.jsdelivr.net`。

**会不会拖慢浏览器？**
参考体积列。全部规则合计约 22 MB，uBlock Origin 会把它编译成紧凑结构；内存敏感的设备只订「桌面日常」或「手机端」那一组就够。

## 维护

### 目录结构

```
*.txt                     规则本体，也就是用户订阅的文件
scripts/config.yaml       源清单：地址、镜像、类别、维度、文件名
scripts/candidates.yaml   候选与淘汰池，附入选/否决理由
scripts/update.py         拉取、比对、校验、原子写入
scripts/discover.py       探测、评分、维度覆盖、发现新源
docs/sources.md           源选型与评分机制
docs/sources-report.md    每周自动生成的源健康报告
```

### 自动化

| Workflow | 频率 | 做什么 |
| --- | --- | --- |
| `update-rules.yml` | 每 6 小时 | 拉取全部源，内容变化的写盘并提交；任一源失败则 job 标红 |
| `source-health.yml` | 每周 | 探测 + 评分 + 更新 `docs/sources-report.md` |
| `tests.yml` | 每次 push / PR | 跑 118 个离线单测 |

### 加新源

1. 对照 [docs/sources.md](docs/sources.md) 的评分维度，确认它在 A 级以上、且不是已有源的马甲
2. 在 `scripts/config.yaml` 的 `sources` 下追加一条：`id`、`name`、`filename`、`urls`（含镜像）、`category`、`region`、`kind`、`dimensions` 必填
3. 跑 `python scripts/update.py --dry-run` 和 `python -m pytest`
4. 提 PR，说明它补的是哪个维度

暂不收录但有价值的源写进 `scripts/candidates.yaml` 并注明理由，每周报告会持续复查。

### 许可

代码采用 MIT 许可；每条规则分别遵循其上游许可（GPL-3.0、CC BY-SA、CC BY-NC-SA、0BSD 等），详见下方来源列表。商业使用前请确认对应上游条款。

### 规则来源

- [EasyList](https://easylist.to/) · GPL-3.0 / CC BY-SA 3.0
- [AdGuard Filters](https://github.com/AdguardTeam/AdGuardFilters) · GPL-3.0
- [uBlock Origin uAssets](https://github.com/uBlockOrigin/uAssets) · GPL-3.0
- [anti-AD](https://github.com/privacy-protection-tools/anti-AD) · CC BY-NC-SA 4.0
- [Cats-Team/AdRules](https://github.com/Cats-Team/AdRules) · 0BSD
- [EasyList China](https://github.com/easylist/easylistchina/) · GPL-3.0 / CC BY-SA 3.0
- [乘风规则](https://github.com/xinggsf/Adblock-Plus-Rule) · CC BY-NC-SA 4.0
- [AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule) · GPL-3.0
- [CJX's Annoyance List](https://github.com/cjx82630/cjxlist) · LGPL-3.0
- [HalfLife](https://github.com/sbwml/halflife-list) · GPL-3.0
- [NoCoin](https://github.com/hoshsadiq/adblock-nocoin-list) · MIT
- [pgl.yoyo.org](https://pgl.yoyo.org/adservers/) · free for non-commercial use

---

ADrules © [Tickmao](https://blog.tickmao.com) · Blog [Tickmao](https://blog.tickmao.com) · GitHub [@tickmao](https://github.com/tickmao)
