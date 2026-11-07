# 0.1.1 发行记录

2026-11-07，开始从已发布 GitHub `v0.1.0` / `f1ae8a7910b94cd4d2e9ef675ed7607b40b9eb57` 准备独立 0.1.1。旧 tag/asset 不改写。原始工作树干净；源码与发布工具修改分别由会话 owner 负责。

源码实现与验证分开：P3 本地实现与修复已收口，当前准备 P4 同候选发行文件验收，尚未声明 PyPI 发布成功。旧 reference 严格 225 例保留，新默认 Canvas 单独验证全部 68 类型、累计原输入、可读内容/几何、三后端、多格式与资源隔离。Canvas 字形差异不冒充 reference 像素一致。

本地联合证据保存在相邻 py-mermaid 的独立标准日志目录（均未覆盖历史运行）：

- `VCHART-P3-batch-20261107T034344Z-94957548`：首次完整分组运行，FAILED；运行期间双方生产源码未变。保留真实 Treemap 颜色缺口、原输入词法差异与原生词云重复数差。
- `VCHART-P3-batch-20261107T035511Z-365b9ec8`：实际 225 原生输入 × CPU/auto/GPU 全部通过，68 规格 API、138 消费者方法、42 原版输入和七语法三后端通过；旧 reference 225 严门禁通过。运行 FAILED 仅剩测试选到 bar/empty 的非数据代表，原失败完整保留。
- `VCHART-P3-record-20261107T035857Z-796debc5`：只修 source 非零代表选择后 26 native host 方法通过；未修改任何产品代码。

两例 `wordCloud/default-filling`、`wordCloud/filled-mask` 的装饰重复数量受字形占用影响，逐字节绑定 spec 的原生契约位于 `tools/native_wordcloud_policy.py`：源权重/名字/字号、独立公开 Canvas 字形核心、解析式 diamond 边界与真实填词墨迹检查，另有 10 项缺主词/未知填词/错字号/擦字留黑蒙版等正负控制。报告保留 exact multiset/structure 的实际不一致，不把它们改成相等；不改变 reference 像素阈值。其余 223 例仍要求原场景文字/图元结构一致。

发布工具：`tools/release_artifacts.py` 构建、哈希与仓库外 wheel/sdist 安装；`tools/release_github.py` 只上传已核对的原文件，拒绝覆盖不同既有 asset；`.github/workflows/publish-pypi.yml` 在 Windows/Linux × Canvas a18/a19 验证同组字节后通过 PyPI Trusted Publishing 上传，再核实际 PyPI 文件哈希和仓库外安装。

PyPI 项目 `py-visactor-vchart`，GitHub owner/repo `py-VisActor/py-vchart`，workflow `publish-pypi.yml`，environment `pypi`。账户 Pending Publisher 尚待确认；无 token 时不通过其他项目凭据绕过配置。实际 CI、PyPI 回读及发布 URL 在通过后追加，不能由源码/本地记录推定已发布。
