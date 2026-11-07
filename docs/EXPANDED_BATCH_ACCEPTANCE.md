# 二维扩展与统计图批量验收

前一批补齐最后 13 个二维图表入口，本轮扩展其中四类图表的静态规格。扩展包和统计包的图表均使用 Python 的 `VChart(spec).render().to_png()`。原生 JavaScript 只用于生成对照图。项目范围为二维静态输出，排除全部三维图、交互、动画和 DOM。

| 批量清单 | 已通过基础静态验收 | 前一批新增入口 |
| --- | ---: | ---: |
| 二维词云 | 1 / 1 | 0 |
| 二维扩展 | 14 / 14 | 10 |
| 统计规格 | 28 / 28 | 3 |

整库共 68 个公开类型名。统计规格中的 histogram 和 boxPlot 分别与核心图共享一个类型名，通过输入结构选择渲染流程。

## 已验收的输入

| 类型 | 已校验的静态行为 |
| --- | --- |
| combinationCandlestick | 主图 OHLC 和下方预览面板，复用 K 线绘制 |
| rankingBar | 时间排序后的首帧、前 N 项、条形和播放控件外观 |
| storyline | 横向交替排列的文字及图片卡片、连接线和节点，宽图与竖图的居中适配和裁切 |
| sequence | 共享横轴的柱图和折线分面 |
| sequenceAnalysis | step 模式下按用户排列的事件泳道 |
| sequenceScatterLink | neighborhood 数据的首帧散点和节点标注 |
| sequenceScatterKDE | 首帧分类散点和逐类核密度背景 |
| sequenceScatterPixel | 固定 300 × 300 画布、首帧散点、RGB 像素背景 |
| pictogram | 注册本地 SVG，按视口缩放，支持嵌套组变换、旋转、曲线、复合路径、椭圆及折线 |
| imageCloud | 内嵌图片的螺旋排布与重复填充 |
| pairPlot | 分组和无分组观测、逐面板处理缺失值、对角线直方图、变量换序和自定义分箱数 |
| hexbinPlot | 六边形分箱与计数，包括重复坐标和自定义分箱密度 |
| shapBeeswarmPlot | 按特征排列的蜂群、重叠避让与连续色标 |

## 本轮新增的 14 个原生对照

| 类型 | 新用例 | 重点 |
| --- | ---: | --- |
| pairPlot | 3 | 逐组直方图共用分箱边界，散点面板和图例共用分组色域；覆盖组在某面板全部缺失、自定义配色，以及上游三变量、40 条观测的完整分组示例 |
| storyline | 2 | 同一组卡片内使用不同宽高比的嵌入图片，验证 contain 和 cover，核对文字、连接线与图片叠放顺序 |
| pictogram | 2 | 组的平移、缩放和旋转与复合路径组合；原生 2.2.1 在转换图元时忽略 URL 填充，沿用相同行为 |
| wordCloud | 7 | 快速布局的菱形、可见几何蒙版、文字蒙版、内嵌 PNG 蒙版、跨两个分离区域排词、单轮填充和默认多轮填充 |

几何或文字轮廓用 `maskShape` 对象指定，`wordMask.visible` 可显示轮廓。位图使用内嵌 data URI，透明和白色像素作为空白区域。将 `wordCloudShapeConfig.fillingTimes` 设为 0 可单独绘制主词。默认多轮填充样例逐词核对了 135 个文字图元的内容、位置、字号和角度。验收覆盖固定主词旋转和默认蒙版布局，其他布局策略仍需单独建立对照。

## 原图、差异与回归

基准使用 VChart 2.2.1、固定 Chromium 和 DPR 1。每个用例在 `tests/cases/<类型>/<用例>/` 保存输入、原生 PNG、场景及带哈希的采集记录。多面板以各系列所属区域计算坐标。图片用例等待资源解码后再导出，排名图固定首帧时钟。pictogram 的 SVG 源文件与用例同目录。

ROC 曲线修复了中西文轴标题，混淆矩阵和相关矩阵修复了矩阵文字的字形定位与抗锯齿。三者均通过既有阈值，平坦区域的差异像素均为 0。本轮沿用已有图片判定规则。原有 162 个核心用例的 Python 输出与上次验收的 PNG 逐文件字节一致。

全库验收共 **68 个公开类型、225 个用例**。场景与图片均通过。新增 14 个用例均独立重采原图并比较 PNG 字节与场景。此前 211 个用例中，203 个 Python 输出与上一轮逐字节相同；其余 8 个涉及 pairPlot 和 hexbinPlot 的公共面板文字、pictogram 的 SVG 绘制，以及 wordCloud 的字形渲染，均通过原阈值。storyline 和 pictogram 的自定义图元外观主要由整图 PNG 覆盖。

在安装渲染与测试依赖的 CPython 3.13 环境运行：

```sh
python -m unittest discover -s tests
python tools/visual/check_cartesian.py --all
```

全量报告位于 `test-runs/all-batch/index.html`，同目录的 `report.json` 包含每一用例的误差数据。字体和像素验收环境为 Windows。
