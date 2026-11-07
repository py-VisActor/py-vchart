# 支持的图表与边界

下表为当前 Python 注册入口，共 68 个唯一 `type` 名称，大小写敏感。
这是类型目录，不代表原版 VChart 所有字段和组合均兼容。运行时可用 `VChart.supported_types()` 查询。

| 用途 | Python type |
| --- | --- |
| 笛卡尔与组合 | `bar`、`line`、`scatter`、`area`、`rangeArea`、`rangeColumn`、`waterfall`、`histogram`、`boxPlot`、`heatmap`、`mosaic`、`linearProgress`、`common` |
| 极坐标与指标 | `pie`、`rose`、`radar`、`gauge`、`circularProgress`、`liquid` |
| 层级与关系 | `funnel`、`treemap`、`sunburst`、`circlePacking`、`sankey`、`correlation`、`venn` |
| 扩展图表 | `storyline`、`sequenceAnalysis`、`sequence`、`combinationCandlestick`、`pictogram`、`imageCloud`、`candlestick`、`conversionFunnel`、`rankingList`、`rankingBar`、`timeline`、`sequenceScatterPixel`、`sequenceScatterKDE`、`sequenceScatterLink` |
| 地理与文本 | `map`、`wordCloud` |
| 统计图 | `learningCurve`、`seasonalPlot`、`timeSeriesPlot`、`autocorrelationPlot`、`residualPlot`、`pairedComparisonPlot`、`kdePlot`、`violinPlot`、`countPlot`、`screePlot`、`scatterPlot`、`embeddingPlot`、`qqPlot`、`stripPlot`、`ecdfPlot`、`calibrationCurve`、`rocCurve`、`precisionRecallCurve`、`shapBeeswarmPlot`、`pairPlot`、`hexbinPlot`、`featureImportancePlot`、`pointIntervalPlot`、`missingValueMatrix`、`correlationMatrix`、`confusionMatrix` |

`histogram`、`boxPlot` 还有统计输入分支，复用相同 type；不会重复计为新类型。

## 选择数据规格

常见二维类别/数值图使用 `data[].values` 与字段映射；不同专用图有不同输入结构。
本仓库 [tests/cases/](../tests/cases/) 中版本控制的 `spec.json` 可作为具体类型的静态输入示例；测试期望、像素基准和验收计划属于维护者资料，不是 API 必填项。

## 主要边界

- 只提供二维静态绘制；不包括 3D、动画、事件、浏览器宿主或任意 JS 回调。
- 默认原生 Canvas 文本与浏览器/reference 字形可能有正常度量和栅格差异；不承诺跨后端逐像素相同。
- 专用图的字段、算法选项和边界会校验。当前 Venn 最多三个声明单集合；Treemap 的 `splitType` 目前要求 `binary`，不支持的格式选项不会变成任意布局兼容。
- `sequenceScatterPixel` 固定 300×300。地图/SVG 等离线资源由调用方明确提供；不会给缺失资源伪造成功图。
- 对外 type 目录不等于全部 JS spec 表面。遇到明确未支持字段，应报告具体输入与错误，而不是删除数据或改成别的图种。

面向上游研究的原始类型清单与架构资料已收录于[开发目录](development/README.md)。
