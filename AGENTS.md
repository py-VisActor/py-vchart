# py-vchart：AI agent 工作规范

## 1. 适用范围与职责

本文件适用于本仓库。当前用户任务优先于历史计划和状态说明。
发行名 `py-visactor-vchart`，导入 `py_vchart`。
负责实际已实现的二维静态类型、原生算法与导出，不扩大为完整浏览器图表宿主。
完整规程见[开发指南](docs/development/WORKFLOW.md)和[来源验证规程](docs/PORTING_WORKFLOW.md)。

## 2. 开始工作

先运行 `git status --short`，辨认并保留用户及其他 owner 的修改。
按任务读取[开发索引](docs/development/README.md)及相关 chart、算法和测试来源。
用户用法查 [docs/README.md](docs/README.md)，API 以当前源码和用户 API 文档交叉核实。
版本读取 `pyproject.toml`；阶段和结果读取当前任务指定的状态文件/运行记录。
旧移植计划、发行说明和验收不自动恢复旧任务、授权或新的兼容结论。
多人/跨仓任务先明确文件 owner；公共 API、布局或资源合同变更先协调。

## 3. 仓库地图

- `src/py_vchart/core/`：`VChart`、设备、资源和导出入口。
- `src/py_vchart/chart/`：类型专用 spec 消费与静态绘制。
- `src/py_vchart/_deps/`、`layouts.py`：原生数据、比例尺、布局和绘制适配。
- `tests/`、`tests/cases/`：断言和版本控制的 spec/参考图。
- `docs/README.md`：用户目录；`docs/development/`：维护者/agent 目录。
- `tools/`、`test-runs/`：开发 oracle、发行工具与闭合证据。

## 4. 常用命令

在仓库根目录、受支持的 CPython 环境执行；依赖以 `pyproject.toml` 为准。
先复用已有环境；任务确需开发依赖时使用：

```sh
python -m pip install -e '.[test]'
```

文档改动检查本地链接、示例语法、API 和元数据，不因此构建或发布。
实现改动先编译并跑相关组；下列为命令示例：

```sh
python -m compileall -q src/py_vchart
python -m unittest discover -s tests -p test_native_host.py
python -m unittest discover -s tests
```

最后一条为全量单测；原版采图、CPU/auto/GPU 和发行验证由当前计划另行指定。
复现旧字形才用 `.[reference]` 与 `text_engine='reference'`，不能等同默认 Canvas 结果。

## 5. 修改约束

默认生产使用公开 `py-skia-canvas` API 和 NumPy，不引入浏览器、Node/JS、DOM 或私有 Canvas 表面。
`reference` 仅为显式可选历史回归模式，不改为隐式生产后备。
固定 VChart 2.2.1 来源；提交、依赖和文件哈希以版本控制来源记录为准。
移植算法、配色和资源保留许可证；新增外部材料核清归属。
Canvas、Context 和字体对象留在创建线程；跨线程只传纯数据和 bytes。
3D、动画和交互不在二维静态范围；类型注册不代表全部 JS 字段兼容。
未知/不支持选项明确诊断，不用空图、换图种或删字段掩盖缺失。
预期独立取源，不用候选输出生成原版基准，不覆盖首轮失败或闭合证据。
不重置脏树；跨文件共享变更先核 owner，保留用户及同事改动。

## 6. 验证与完成条件

按当前任务区分文档、源码、独立测试、首跑修复和同候选验证阶段。
记录实际命令、环境、来源/候选哈希、退出码和失败；未做的验证明确写出。
相关组通过后，按共享消费者影响决定额外或全量回归，不重复无关大批测试。
绘制变化核原图内容、值、轴、关系、边界和可读性，不只看非空图或 trace。
默认 Canvas 与 reference/浏览器字体差异单列，不能批量放宽像素门禁。
完成报告写明变化、证据和未覆盖项，不把旧验收统计当新候选兼容率。
公共 README/PyPI 只放安装、用法和真实边界，历史资料在开发索引分类保留。
按任务需要自主完成可逆的本地准备和检查；不要为纯文档任务额外安装、构建或跑绘图矩阵。
提交、推送和发布依据当前用户授权；历史记录不扩大权限，也不重复请求已有授权。
