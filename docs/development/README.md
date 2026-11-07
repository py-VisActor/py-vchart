# 维护者与 AI agent 文档

用户入口在 [docs/README.md](../README.md)。开始修改先读 [AGENTS.md](../../AGENTS.md)，检查并保留工作区现有改动。

## 开发

CPython 3.13 开发环境：

```sh
python -m pip install -e '.[test]'
python -m unittest discover -s tests
```

`.[reference]` 仅用于复现旧校准文字路径，需显式 `text_engine="reference"`；不得把 reference 对照通过等同于原生 Canvas 逐像素一致。
以上命令仅说明工作流；安装、构建、下载、提交、发布遵守当前任务授权。

## 实现与来源规范

- [开发工作指南](WORKFLOW.md)：任务阅读、实现约束、验证与完成条件。
- [移植工作规程](../PORTING_WORKFLOW.md)：独立来源、首失败、几何与实际像素门禁。
- [架构分析](../VCHART_ARCHITECTURE.md) · [原始上游类型清单](../CHART_TYPES.md)
- [原版 PNG 捕获工具](../../tools/oracle/README.md)
- `src/py_vchart/core/` 提供公共 API；`chart/` 实现消费者；`_deps/` 为原生算法与绘制适配；`layouts.py` 提供公共纯布局函数。

固定上游基线为 VChart 2.2.1 / `fdb63276cf8b71f5a6cca128c409e009cc94615a`。原版 JS 仅用于开发 oracle，不进入 Python 生产路径。

## 历史计划、验收和发行索引

这些文档保留其原始候选、范围和证据；不是新候选自动通过的依据，也不是用户的主要 API 指南。

| 分类 | 资料 |
| --- | --- |
| 原计划 | [移植计划](../PORTING_PLAN.md)、[早期极坐标批次计划](../NEXT_POLAR_BATCH.md) |
| 基础图验收 | [Bar](../BAR_ACCEPTANCE.md)、[Line](../LINE_ACCEPTANCE.md)、[Scatter](../SCATTER_ACCEPTANCE.md) |
| 分组验收 | [笛卡尔](../CARTESIAN_BATCH_ACCEPTANCE.md)、[极坐标](../POLAR_BATCH_ACCEPTANCE.md)、[专用几何](../GEOMETRY_BATCH_ACCEPTANCE.md)、[地图](../MAP_ACCEPTANCE.md)、[扩展批次](../EXPANDED_BATCH_ACCEPTANCE.md) |
| 发行 | [发行说明目录](../releases/)、[0.1.1 发布证据](../RELEASE_0_1_1.md)、[用户更新摘要](../CHANGELOG.md) |
| 当前维护发行 | [0.1.2 说明](../releases/0.1.2.md)；旧发布证据保留原始版本口径 |
| 法律与来源 | [MIT](../../LICENSE)、[VChart](../../LICENSE-VChart)、[venn.js](../../LICENSE-venn-js)、[fmin](../../LICENSE-fmin)、[统计配色](../../LICENSE-statplot-palettes) |

保留既有基准与闭合 `test-runs/`，不要覆盖首轮失败或用当前 Python 输出生成“原版”预期。跨仓并行遵循明确的文件 owner，接口变更先协调。
## 文档分类索引

[逐文件受众清单](documentation-inventory.json)区分用户、开发、历史、证据与许可资料。旧路径保留来源上下文；清单不把旧验收提升为当前功能结论。
