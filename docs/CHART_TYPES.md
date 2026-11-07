# VChart 图表类型清单

依据上游 develop 分支的提交 fdb63276cf8b71f5a6cca128c409e009cc94615a（核心包版本 2.2.1）整理。下表记录上游能力，供 Python 移植核对。类型名区分大小写。

## 核心包：28 个顶层 spec.type

默认入口注册其中 25 个类型。表中带 ＊ 的三个类型需要显式注册。分类按图表用途整理。

| 类别 | 类型与含义 |
| --- | --- |
| 比较与趋势 | `bar` 柱状／条形图、`line` 折线图、`area` 面积图、`waterfall` 瀑布图 |
| 区间与分布 | `rangeColumn` 区间柱、`rangeArea` 区间面积、`histogram` 直方图、`boxPlot` 箱线图、`scatter` 散点图、`heatmap` 热力图 |
| 占比与极坐标 | `pie` 饼图／环图、`rose` 玫瑰图、`radar` 雷达图、`mosaic`＊ 马赛克图 |
| 指标与进度 | `linearProgress` 线性进度、`circularProgress` 环形进度、`gauge` 仪表盘、`liquid`＊ 水波图 |
| 层级 | `treemap` 矩形树图、`sunburst` 旭日图、`circlePacking` 层级圆打包图 |
| 流向、关系与集合 | `sankey` 桑基图、`funnel` 漏斗图、`correlation` 关联关系图、`venn`＊ 韦恩图 |
| 地理与文本 | `map` 地图、`wordCloud` 词云 |
| 组合 | `common` 组合图，在 series 中指定各系列类型，例如柱线组合 |

分组柱、堆叠柱和横向条形图共用 `bar`；环图通过 `pie` 的内半径配置。形状词云有专门的注册函数，但沿用 `wordCloud` 类型。移植时可将这些变体作为同一类型下的兼容用例。

[类型枚举](https://github.com/VisActor/VChart/blob/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/chart/interface/type.ts) · [默认注册入口](https://github.com/VisActor/VChart/blob/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/vchart-all.ts) · [按需导出入口](https://github.com/VisActor/VChart/blob/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/chart/index.ts)

## 扩展包：上游 20 个图表类型，Python 迁移 14 个二维类型

| 类别 | 扩展类型 |
| --- | --- |
| 三维（全部排除） | `bar3d`、`rangeColumn3d`、`histogram3d`、`pie3d`、`funnel3d`、`wordCloud3d` |
| 金融 | `candlestick`、`combinationCandlestick` |
| 排名与转化 | `rankingBar`、`rankingList`、`conversionFunnel` |
| 时间与序列 | `timeline`、`storyline`、`sequence`、`sequenceAnalysis`、`sequenceScatterLink`、`sequenceScatterKDE`、`sequenceScatterPixel` |
| 图形与图像 | `pictogram`、`imageCloud` |

[扩展包导出入口](https://github.com/VisActor/VChart/blob/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart-extension/src/index.ts) · [各扩展实现](https://github.com/VisActor/VChart/blob/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart-extension/src/charts)

## 统计绘图包：28 个高层规格

`compileStatPlot` 接收下列统计图规格并生成 VChart 规格。这里的 type 属于编译器输入，单独统计。例如，核心包和统计绘图包都有 `histogram`。

| 用途 | 统计规格 type |
| --- | --- |
| 分布与汇总 | `histogram`、`kdePlot`、`ecdfPlot`、`boxPlot`、`violinPlot`、`stripPlot`、`countPlot`、`qqPlot` |
| 关系与比较 | `scatterPlot`、`pairPlot`、`hexbinPlot`、`correlationMatrix`、`pairedComparisonPlot`、`pointIntervalPlot` |
| 时间序列 | `timeSeriesPlot`、`seasonalPlot`、`autocorrelationPlot` |
| 模型评估与解释 | `rocCurve`、`precisionRecallCurve`、`calibrationCurve`、`confusionMatrix`、`residualPlot`、`learningCurve`、`featureImportancePlot`、`shapBeeswarmPlot` |
| 降维与数据质量 | `embeddingPlot`、`screePlot`、`missingValueMatrix` |

[统计图编译分派](https://github.com/VisActor/VChart/blob/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart-statplots/src/compile.ts)
