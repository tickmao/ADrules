# ADrules

精选的广告过滤规则集合，自动更新，保持最新。

本项目汇总了口碑最好的广告过滤规则，每 6 小时自动从源站拉取最新版本，确保规则始终保持最新状态。所有规则保留原作者署名，方便追溯和交流。

## 特性

- ✓ 自动更新 - 每 6 小时自动检查并更新规则
- ✓ 精选规则 - 只收录口碑最好、维护活跃的规则源
- ✓ 模块化设计 - 保持各规则独立，方便按需选择
- ✓ 保留署名 - 尊重原作者，保留完整的来源信息
- ✓ 浏览器友好 - 适用于 uBlock Origin、AdGuard 等主流插件

## 规则列表

### 国际通用规则

| 规则名称 | 订阅链接 | 更新频率 | 说明 |
|---------|---------|---------|------|
| **EasyList** | [订阅](https://raw.githubusercontent.com/tickmao/ADrules/master/Easylist.txt) | 4 天 | 最主流的国际广告过滤规则 |
| **EasyPrivacy** | [订阅](https://raw.githubusercontent.com/tickmao/ADrules/master/EasyPrivacy.txt) | 4 天 | 隐私保护和反跟踪规则 |

### 中国特化规则

| 规则名称 | 订阅链接 | 更新频率 | 说明 |
|---------|---------|---------|------|
| **EasyList China** | [订阅](https://raw.githubusercontent.com/tickmao/ADrules/master/EasyListChina.txt) | 4 天 | EasyList 中国补充规则 |
| **anti-AD** | [订阅](https://raw.githubusercontent.com/tickmao/ADrules/master/anti-AD.txt) | 1 天 | 国内流行的反广告规则 |
| **乘风规则** | [订阅](https://raw.githubusercontent.com/tickmao/ADrules/master/ChengFeng.txt) | 2 天 | 卡饭论坛维护的广告过滤规则 |

### 功能性规则

| 规则名称 | 订阅链接 | 更新频率 | 说明 |
|---------|---------|---------|------|
| **I don't care about cookies** | [订阅](https://raw.githubusercontent.com/tickmao/ADrules/master/I-Dont-Care-About-Cookies.txt) | 3 天 | 自动处理 Cookie 同意提示 |
| **CJX's Annoyance** | [订阅](https://raw.githubusercontent.com/tickmao/ADrules/master/Cjx-Annoyance.txt) | 4 天 | 去除页面干扰元素 |

### 综合规则

| 规则名称 | 订阅链接 | 更新频率 | 说明 |
|---------|---------|---------|------|
| **HalfLife** | [订阅](https://raw.githubusercontent.com/tickmao/ADrules/master/HalfLife.txt) | 1 周 | 综合性广告过滤规则集（移动端优化） |

## 推荐组合

根据不同使用场景，推荐以下组合方案：

### 轻量组合（推荐新手）
适合追求简洁、对性能敏感的用户
- EasyList
- EasyList China

### 标准组合（推荐日常使用）
平衡拦截效果和性能
- EasyList
- EasyList China
- EasyPrivacy
- anti-AD

### 完整组合（推荐进阶用户）
全面拦截广告和干扰元素
- EasyList
- EasyList China
- EasyPrivacy
- anti-AD
- I don't care about cookies
- CJX's Annoyance

### 极致组合（一键搞定）
如果不想选择，直接用这个
- HalfLife（已包含多个规则集）

## 使用方法

### 在 uBlock Origin 中使用

1. 打开 uBlock Origin 设置
2. 进入「过滤器列表」标签
3. 滚动到底部「自定义」区域
4. 点击「导入」
5. 粘贴上方表格中的订阅链接
6. 点击「应用更改」

### 在 AdGuard 中使用

1. 打开 AdGuard 设置
2. 进入「过滤器」→「自定义过滤器」
3. 点击「添加自定义过滤器」
4. 粘贴上方表格中的订阅链接
5. 点击「添加」

### 在其他插件中使用

大部分广告拦截插件都支持通过 URL 订阅规则，具体方法请参考对应插件的文档。

## 自动更新说明

本项目使用 GitHub Actions 自动更新规则：

- **更新频率**：每 6 小时检查一次
- **更新策略**：仅当规则版本变化时才更新
- **质量保证**：自动验证规则格式和完整性
- **透明可追溯**：所有更新记录在 Git 提交历史中

如果发现规则未及时更新，可以在 [Actions](https://github.com/tickmao/ADrules/actions) 页面手动触发更新。

## 规则来源

所有规则均来自以下开源项目，感谢这些优秀的维护者：

- [EasyList](https://easylist.to/) - GPL-3.0 / CC BY-SA 3.0
- [EasyList China](https://github.com/easylist/easylistchina/) - GPL-3.0 / CC BY-SA 3.0
- [anti-AD](https://anti-ad.net/) - CC BY-NC-SA 4.0
- [乘风规则](https://github.com/xinggsf/Adblock-Plus-Rule) - CC BY-NC-SA 4.0
- [I don't care about cookies](https://www.i-dont-care-about-cookies.eu/) - GPL-3.0
- [CJX's Annoyance List](https://github.com/cjx82630/cjxlist) - GPL-3.0
- [HalfLife](https://github.com/o0HalfLife0o/list) - GPL-3.0

## 贡献指南

欢迎提交 Issue 和 Pull Request！

### 添加新规则源

如果你想添加新的规则源，请确保：

1. 规则源有良好的口碑和活跃的维护
2. 规则源提供稳定的订阅链接
3. 规则源有明确的开源协议

然后编辑 `scripts/config.yaml` 文件，添加新的规则配置即可。

### 报告问题

如果发现规则失效、误拦截或其他问题，请在 [Issues](https://github.com/tickmao/ADrules/issues) 中反馈。

## 许可证

本项目采用 MIT 许可证，但请注意各规则源有各自的许可证，使用时请遵守相应的许可证条款。

## 作者

ADrules © [Tickmao](https://blog.tickmao.com)

Blog @ [Tickmao](https://blog.tickmao.com) · GitHub @ [Tickmao](https://github.com/tickmao) · Twitter @ [Tickmao](https://twitter.com/tickmao)
