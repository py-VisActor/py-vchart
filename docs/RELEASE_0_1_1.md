# 0.1.1 发行记录

> 最新：0.1.1 已正式发布 [PyPI](https://pypi.org/project/py-visactor-vchart/0.1.1/)。工作流42337813981第2次尝试6个job全部成功；下文invalid-publisher为第1次尝试的历史，原失败与资产保留。

2026-11-07，开始从已发布 GitHub `v0.1.0` / `f1ae8a7910b94cd4d2e9ef675ed7607b40b9eb57` 准备独立 0.1.1。旧 tag/asset 不改写。原始工作树干净；源码与发布工具修改分别由会话 owner 负责。

源码实现与验证分开：下列计划与早期状态保留；实际 GitHub 正式发行及 PyPI 阻塞见“实际交付”。旧 reference 严格 225 例保留，新默认 Canvas 单独验证全部 68 类型、累计原输入、可读内容/几何、三后端、多格式与资源隔离。Canvas 字形差异不冒充 reference 像素一致。

本地联合证据保存在相邻 py-mermaid 的独立标准日志目录（均未覆盖历史运行）：

- `VCHART-P3-batch-20261107T034344Z-94957548`：首次完整分组运行，FAILED；运行期间双方生产源码未变。保留真实 Treemap 颜色缺口、原输入词法差异与原生词云重复数差。
- `VCHART-P3-batch-20261107T035511Z-365b9ec8`：实际 225 原生输入 × CPU/auto/GPU 全部通过，68 规格 API、138 消费者方法、42 原版输入和七语法三后端通过；旧 reference 225 严门禁通过。运行 FAILED 仅剩测试选到 bar/empty 的非数据代表，原失败完整保留。
- `VCHART-P3-record-20261107T035857Z-796debc5`：只修 source 非零代表选择后 26 native host 方法通过；未修改任何产品代码。

两例 `wordCloud/default-filling`、`wordCloud/filled-mask` 的装饰重复数量受字形占用影响，逐字节绑定 spec 的原生契约位于 `tools/native_wordcloud_policy.py`：源权重/名字/字号、独立公开 Canvas 字形核心、解析式 diamond 边界与真实填词墨迹检查，另有 10 项缺主词/未知填词/错字号/擦字留黑蒙版等正负控制。报告保留 exact multiset/structure 的实际不一致，不把它们改成相等；不改变 reference 像素阈值。其余 223 例仍要求原场景文字/图元结构一致。

发布工具：`tools/release_artifacts.py` 构建、哈希与仓库外 wheel/sdist 安装；`tools/release_github.py` 只上传已核对的原文件，拒绝覆盖不同既有 asset；`.github/workflows/publish-pypi.yml` 在 Windows/Linux × Canvas a18/a19 验证同组字节后通过 PyPI Trusted Publishing 上传，再核实际 PyPI 文件哈希和仓库外安装。

PyPI 项目 `py-visactor-vchart`，GitHub owner/repo `py-VisActor/py-vchart`，workflow `publish-pypi.yml`，environment `pypi`。账户 Pending Publisher 尚待确认；无 token 时不通过其他项目凭据绕过配置。实际 CI、PyPI 回读及发布 URL 在通过后追加，不能由源码/本地记录推定已发布。

首次 CI [42336972587](https://github.com/py-VisActor/py-vchart/actions/runs/42336972587) 因采集输入的 Git EOL 规范化失败，四组均如实保留失败。原本地采集 spec 是 CRLF，旧 `.gitattributes` 却将 Git blob 改成 LF，使检出字节与原 `capture.json` 哈希不符。修复仅将 SHA 锁定的 spec/GeoJSON/SVG 标为 `-text` 并保存原已采集字节；没有改任何基准哈希、图片、预期或产品代码。先逐例核对原 SHA，再验证 Git blob 与原始文件完全一致。

失败候选 `v0.1.1` / `0cb6040` 和资产保持原样。正式候选改用独立 tag `py-visactor-vchart-v0.1.1`，Python 包版本仍为尚未上 PyPI 的 `0.1.1`；新构建和新的完整验收单独记录，不以旧失败当作通过。

## 实际交付

正式源码提交 `ff16c91d38ab61e57d03b58579d5bf1beb2a1840`；[GitHub 正式发行](https://github.com/py-VisActor/py-vchart/releases/tag/py-visactor-vchart-v0.1.1) 已确认 `draft=false`、`prerelease=false`。此前失败候选仍单列保留。

- [CI 42337813981](https://github.com/py-VisActor/py-vchart/actions/runs/42337813981)：Windows 2025 / Ubuntu 24.04 × Canvas a18 / a19 四组全部验证通过；每组分别仓库外安装 wheel/sdist、36 原生接口/字形负控方法及 225 图例。PyPI publish 步骤单独失败，不能把整个 run 冒称全绿。
- 本机功能检查 `VCHART-P4-batch-20261107T041705Z-6c07df8d` 全部 SUCCESS，双方源码运行期未变；67 供应方测试、138 消费者方法、原生 225 ×三后端、旧 reference 225、原版 42 输入、Mermaid 30 正例/10 真负例/2 明确限制 ×三后端与 11 组旧回归均通过。
- `VCHART-P4-FINAL-install-a18-batch-20261107T041705Z-f605c70c`、`VCHART-P4-FINAL-install-a19-batch-20261107T041705Z-eb17ef56`：本机两种 Canvas 的 wheel/sdist 四次真实仓库外安装通过。

正式 wheel SHA-256：`45b66f82d0c74a8d15306b117d93ad2d88c26d2997719306336bcc92b7ce49e2`；源码包 SHA-256：`fee51a35d75b7f8572e76b0028d63c833f6e01c670c7ea41dc412386b3bcef7f`。原始 manifest 与文件一起发布，不覆盖历史资产。

**PyPI 尚未发布**：实际上传返回 `invalid-publisher`。需在 PyPI 添加项目 `py-visactor-vchart` 的 Publisher，owner `py-VisActor`、repo `py-vchart`、workflow `publish-pypi.yml`、environment `pypi`；配置后可重跑失败的 publish job，复用同组已验收字节，再执行 PyPI 下载哈希/安装复核。GitHub 正式发行和安装不依赖该账户操作。

消费者 py-mermaid 的七类 Mermaid 语法是独立验收范围；上述功能运行后人工看图发现宿主标题/配色/柱宽/描边边界问题，已另开集中修复与新同候选运行。不能把供应方正式发布或这份早期功能检查当作消费者最终视觉验收。供应方已发布文件和 tag 不因宿主修复而改写。


## 消费方最终收口

2026-11-07，py-mermaid 最终本机同候选 `VCHART-P4-batch-20261107T045154Z-dd03474c` SUCCESS，两侧源码运行期不变；2283 方法（供应方67、接入156、旧回归2060）、原生225×三后端、reference225、68规格API、七语法42输入×三后端通过。30张最终CPU原图实际查看，原版同SHA图绑定先前实际查看记录；两次消费方全新环境 wheel/sdist 正常解析正式GitHub wheel并核SHA、68类型/数学/实际ELK/SVG/PDF通过。Treemap原版透明白字缺陷作为明确差异，本端补可读默认文字，未降低墨迹门禁。其余高级限制与既有22条Mermaid分支缺口保留。

报告本机地址：`http://127.0.0.1:8765/VCHART-P5-delivery-20261107T045848Z-3903b480/index.html`；335条记录/29页，2537附件与HTTP SHA、桌面/窄屏QA通过。机器汇总保存在相邻消费者仓库的 `references/vchart-verification-summary.json`。以上属于消费方本地接入，不是发布 py-mermaid 包，也不代表 PyPI 已上传。


## PyPI 正式发布收口

用户完成Trusted Publisher后，仅重跑失败publish/verify。第2次尝试上传成功，实际PyPI元数据与下载字节证实wheel SHA `45b66f82d0c74a8d15306b117d93ad2d88c26d2997719306336bcc92b7ce49e2`、sdist SHA `fee51a35d75b7f8572e76b0028d63c833f6e01c670c7ea41dc412386b3bcef7f` 与原验收完全相同，没有重新构建或替换文件。CI从PyPI下载后在两个新环境分别完成225例、68类型、36原生方法；PyPI核验ZIP原字节SHA `17d3174cf896e54893bae789f759fb610d379c08929eb4bddec3737573e49f21`，保存于 `test-runs/vchart-pypi-ci-42337813981-attempt2/`。

消费者已改为 `py-visactor-vchart==0.1.1` 正常PyPI依赖；其wheel/sdist两个新环境的68类型、SVG/PDF、数学与ELK均通过，补充184方法通过。消费者渲染源码与先前完整验收逐字节一致，仅包装依赖/说明变更。补充证明为相邻py-mermaid仓库 `references/vchart-pypi-verification.json`，当前发布状态不再受invalid-publisher阻塞。
