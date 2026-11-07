# 专用几何图验收

本轮按计划顺序新增三个入口。公开调用仍为 `VChart(spec).to_png()`。测试使用 npm VChart 2.2.1、无头 Chromium 158、DPR 1 的静态输出作为参考。每个用例保存输入、采集指纹、原图和场景。[固定用例](../tests/cases)

| 图种 | 用例 | 已验收行为 |
|---|---:|---|
| funnel | 7 | 默认梯形、水平靠边与间距、反向平底、右向百分比和像素宽度、带转换层的矩形阶段、全零、空集 |
| treemap | 5 | 单层、多根嵌套、单根嵌套、宽画布和自定义节点留白、空集。核对二分布局的叶节点边界和根类别配色 |
| sunburst | 5 | 单层、多根嵌套、单根完整圆盘、宽画布和自定义内外半径、空集。核对逐层半径、兄弟节点的角域和轮廓 |

层级权重、矩形划分、层级扇区分配位于 [VLayouts 按需模块](../src/py_vchart/_deps/vlayouts/hierarchy.py)。图表层负责字段、配色和图元组织。漏斗沿用 VDataset 的记录读取及 VRender 的多边形绘制。旭日图复用支持描边的扇区，完整圆盘的轮廓单独闭合。

## 校验

17 份参考场景和原图经独立重采，逐字节一致。Python 的 17 份场景全部通过；16 例与参考图逐像素一致，单根旭日图有 59 个抗锯齿差异像素，沿用既有阈值通过。19 项 unittest 通过，包括全量图像回归。22 个入口、98 张图在源码和独立安装 wheel 后分别通过，两个环境输出逐字节一致。此前 81 张 PNG 另与上一轮 wheel 输出比对，逐字节一致。

```powershell
python tools/visual/check_cartesian.py --batch geometry
python tools/visual/check_cartesian.py --all
python -m unittest discover -s tests
```

全量图库位于 `test-runs/all-batch/index.html`。本轮层级输入使用非负权重；矩形树图采用 binary 布局。旭日图须显式设置 `"label": {"visible": false}`。可见系列标签、其他树图分割算法与逐层自定义旭日样式仍待验收。

## 圆打包图

公开入口为 `circlePacking`。布局复用层级权重，按权重稳定降序排列同级节点，将叶面积映射到数值，再将相切的圆组缩放到绘图区。支持统一间距和按层间距，按根类别着色。本轮要求显式设置 `"label": {"visible": false}`。全零树保留场景图元，圆心和半径记录为 null，画布呈现背景色。[布局实现](../src/py_vchart/_deps/vlayouts/circle_packing.py) · [固定输入与参考图](../tests/cases/circlePacking)

10 个用例覆盖空数据、单节点、全零、零权重叶、同级圆、零间距、14 个等权圆、嵌套、宽画布分层留白，以及含 35 个同级叶节点的三层自定义字段输入。使用原生 VChart 2.2.1 和 VLayouts 1.0.28，独立重采的 10 对 PNG 和场景均逐字节一致。Python 场景与参考的坐标、半径按 1e−6 精度核对，10 例像素对比均通过原有阈值，纯色区域误差为零，最大单通道差为 15。

源码和独立安装 wheel 后均通过 23 个入口的 108 例，两个环境的 PNG 逐字节一致；原有 98 张图另与上一轮 wheel 输出逐字节比对通过。可运行 `python tools/visual/check_cartesian.py --type circlePacking` 单独复核该图种。

## 桑基图

公开入口为 `sankey`。VLayouts 负责有向无环图分层、按流量确定节点高度和连线宽度，以及分配流入和流出端点。横向和纵向共用一套布局，以同一组端点生成贝塞尔带。绘制时先取整带的一侧，再由该边和流量宽度求另一侧；场景保留未取整的逻辑坐标。[布局实现](../src/py_vchart/_deps/vlayouts/sankey.py) · [图表入口](../src/py_vchart/chart/sankey.py)

本轮验收显式节点和连线、非负流量、默认静态布局、隐藏标签。输入可使用索引或节点键，也可在一个数据视图内分别列出标记为 nodes 和 links 的记录。16 例覆盖分流汇流、跨层、平行边、横纵向、百分比节点宽度、零流量、孤立节点、空图、自定义字段与布局对齐。层级树输入、可见标签、显式迭代优化和交互效果在本轮范围之外。[固定输入、参考场景与原图](../tests/cases/sankey)

能源流向用例沿用官网示例的 48 个节点与 68 条连线，在 820×540 画布上单独验证流图几何和颜色。输入数据来源为示例注明的 Department of Energy & Climate Change via Tom Counsell。[固定版本官网示例](https://github.com/VisActor/VChart/blob/fdb63276cf8b71f5a6cca128c409e009cc94615a/docs/assets/examples/en/sankey-chart/basic-sankey.md)

16 例的原生场景及 PNG 均经独立重采并逐字节匹配。Python 的节点边界、连线端点和宽度通过 1e−6 精度校验，14 张图与原图逐像素一致；能源流向图只有 10 个像素相差 1 个色阶。执行 `python tools/visual/check_cartesian.py --type sankey` 可单独复核。全量 24 个入口、124 例通过，独立安装 wheel 后逐张输出一致，既有 108 张 PNG 也与上一轮 wheel 输出逐字节一致。

## 关联关系图

公开入口为 `correlation`。按上游流程，VDataset 将每条记录的数值映射到轨道半径，按角度序列与绘图区边界选取节点位置；独立的 sizeField 可用于直径编码。固定值域的轨道取内外半径中点，固定大小值域取 sizeRange 的上限。支持像素或百分比轨道半径、数值圆心、局部角域、系列配色和静态波纹。圆形图元沿用 VRender 适配层。[数据变换](../src/py_vchart/_deps/vdataset/correlation.py) · [图表入口](../src/py_vchart/chart/correlation.py)

13 个输入覆盖默认布局、空集、单点、等值、独立大小字段、偏移圆心与反向角域、系列、样式和波纹相位、隐藏中心、记录自带 x/y/size、搜索耗尽以及跨多轮角度分配。官网关键词用例保留全部 30 条记录、尺寸字段及半径配置，在 640×480 画布上关闭文字，核对节点、中心点和三层波纹。当前须显式设置节点标签 `label.visible=false`，中心标签采用默认空文本或 `centerLabel.visible=false`。可见文字与动画仍在验收范围之外。[测试输入和原图](../tests/cases/correlation) · [上游示例](https://github.com/VisActor/VChart/blob/fdb63276cf8b71f5a6cca128c409e009cc94615a/docs/assets/examples/en/correlation-chart/correlation-chart.md)

运行 `python tools/visual/check_cartesian.py --type correlation` 可单独核对圆心、节点直径、波纹层次与 PNG。官网关键词图的几何通过 1e−6 绝对误差校验，7 个像素存在差异，最大通道差为 7。

13 份参考场景和 PNG 独立重采均逐字节一致。全量 25 个入口、137 例在源码和独立安装 wheel 后均通过，输出逐字节一致。既有 124 张 Python 图与上一轮 wheel 输出也逐字节一致。

## 韦恩图

入口 `venn` 覆盖空输入及一至三个具名集合，单集合面积为正数，交集面积可为零。支持默认或自定义字段、集合和交集的填色与透明度，以及用空集合记录表示外层容器。本轮需显式设置 `label.visible=false` 和 `overlapLabel.visible=false`。四个及以上集合、空心描边变体、图例和可见文字尚待单独验收。

单集合面积确定各圆半径。布局先由两圆相交面积反求圆心距离，再按指定的两两及三重交集面积拟合位置，最后将相交分组定向并缩放到绘图区。三圆输入不一定能精确满足所有面积约束，验收比较上游拟合出的几何。快照核对各圆及交集边界的所属集合、端点、半径和长弧标记。完全包含时按闭合圆弧填充，三重交集绘制在两两交集上方。[布局](../src/py_vchart/_deps/vlayouts/venn.py) · [边界几何](../src/py_vchart/_deps/vlayouts/venn_geometry.py)

18 个输入覆盖普通交叠、等面积、互斥、完全重合、包含、长弧、分离簇、三重交集、外层容器、不同画布、字段和样式。官网基础示例保留三组单集合面积、三组两两交集和一组三重交集，隐藏图例和文字。运行 `python tools/visual/check_cartesian.py --type venn` 可单独复现。[固定用例](../tests/cases/venn) · [上游官网示例](https://github.com/VisActor/VChart/blob/fdb63276cf8b71f5a6cca128c409e009cc94615a/docs/assets/examples/en/venn-chart/venn-chart.md)

数值布局参照 VLayouts 的 venn 模块及 VUtils 的圆交集和单纯形计算，仅移植本批所需部分。原算法来源为 Ben Frederickson 的 venn.js 与 fmin，许可证随 wheel 分发。[venn.js 许可](../LICENSE-venn-js) · [fmin 许可](../LICENSE-fmin)

18 份场景和原生 PNG 均经独立重采并逐字节匹配。官网三集合示例的圆心、半径及交集圆弧通过 1e−6 精度校验，PNG 有 8 个像素存在差异，最大通道差为 3。全量 26 个入口、155 例在源码及独立安装 wheel 后均通过，输出逐字节一致。此前 137 张图另与上一轮 wheel 输出逐字节比对通过。
