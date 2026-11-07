# VChart 架构与 Python 移植准备

分析基线为上游 `develop@fdb63276cf8b71f5a6cca128c409e009cc94615a`，核心包版本 2.2.1。本地上游检出位于 `C:\code\VChart`。前四节描述此提交的源码行为，第五节是 Python 实现建议。各图表的类型名和注册范围见[图表类型清单](CHART_TYPES.md)。

## 1. 系统边界

调用方交给 VChart 一份声明式 spec。Chart 把其中的数据、系列和组件组织起来，Series 决定如何把每条数据编码为视觉属性，Mark 把这些属性应用到具体图形，最后由 VRender Stage 绘制。一个 Chart 可以有多个 Series，一个 Series 可以使用多种 Mark；例如柱线组合可以让两种系列共享绘图区和轴。

| 层 | 输入 → 输出 | 职责与源码入口 |
| --- | --- | --- |
| 入口与注册 | 类型名 → 构造器或注册函数 | 默认入口组合所需能力；Factory 分别查找 Chart、Series、Mark、组件和布局实现。按需入口可加载较小的组合。[默认入口](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/vchart-all.ts) · [Factory](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/core/factory.ts) |
| 实例与配置 | 原始 spec、选项、主题 → 工作 spec 和模型描述 specInfo | VChart 管理尺寸、数据集、编译器、事件和插件；图表 transformer 展开简写，模型 transformer 继续处理各模型配置。显式值、主题和默认值的合并会影响最终图形。[实例](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/core/vchart.ts) · [图表 transformer](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/chart/base/base-chart-transformer.ts) · [模型 transformer](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/model/base-model-transformer.ts) |
| Chart 与 Region | 工作 spec → 模型及其关联 | Chart 管理全局比例尺、数据和布局；Region 表示一块绘图区。Series 归属 Region，轴、图例等组件参与测量或编码，多区域配置需要保留这些关联。[BaseChart](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/chart/base/base-chart.ts) · [Region](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/region/region.ts) |
| 数据与比例尺 | 原始记录 → 派生记录、定义域 → 坐标或颜色 | DataView 支持解析和变换；系列消费视图。数据决定定义域，布局决定轴的像素范围，轴辅助对象供系列查询位置。堆叠还需要同区域内多个系列的数据。[数据模块](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/data) · [全局比例尺](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/scale/global-scale.ts) · [堆叠](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/chart/stack.ts) |
| Series、组件与 Mark | 字段、比例尺、状态、主题 → 图元树和属性 | Series 选择矩形、线、点等 Mark 并定义编码。组件也有绘制和布局职责。Mark 保存编码、数据绑定及图形状态，一个矩形 Mark 可以产生多根柱子。[Series](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/series/base/base-series.ts) · [组件](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/component) · [BaseMark](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/mark/base/base-mark.ts) |
| 编译与运行时 | 模型及 Mark → VRender 图形树 → 画布 | Compiler 管理 Stage、根图元、布局状态和绘制调度；事件分发、交互触发器、动画时间线共用实例与场景信息。[Compiler](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/compile/compiler.ts) · [Stage 适配](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/compile/stage-app.ts) · [事件](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/event) |

## 2. 依赖方向与替代成本

仓库内的 React、Taro、小程序等适配包面向不同宿主。扩展图表包消费核心包的注册接口；统计绘图包把高层统计规格编译成核心 spec。Python 端可以先建立同一份 spec 的无窗口执行入口，随后分别接入扩展或宿主。[仓库包目录](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages) · [扩展入口](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart-extension/src/index.ts) · [统计规格编译器](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart-statplots/src/compile.ts)

| 核心包直接依赖 | 上游用途 | Python 移植边界 |
| --- | --- | --- |
| `@visactor/vutils`、`@visactor/vutils-extension` | 通用函数、配置和主题合并。前者声明为 ~1.0.28，后者为工作区 2.2.1 | 优先以实例验证缺省键、显式 null、数组和嵌套样式的合并结果；Python 的 dict.update 只能覆盖一层。 |
| `@visactor/vdataset`、`@visactor/vscale`（均 ~1.0.28） | DataSet/DataView 管理源数据和派生数据；比例尺处理 domain、range、带宽和映射 | 先支持具名记录集、有序分类和连续数值；保存原始记录与派生记录，分别核对类别顺序、零基线、反向像素范围与刻度。 |
| `@visactor/vlayouts`（~1.0.28） | 为桑基、矩形树、旭日、圆打包、词云等计算专用几何 | VChart 自身的页面布局先给出绘图区，专用算法再消费数据及可用空间。按图种建立算法测试；同目录 py-elk 的图布局需单独验证几何语义后才能复用。 |
| `@visactor/vrender`、`vrender-core`、`vrender-kits`（均 1.1.14，同一作用域） | Stage、图形节点、绘图环境和图元注册 | Python 保留分组、变换、裁剪、绘制次序及文本测量等语义。可用 py-skia-canvas 承担底层绘制，场景树及数据键到节点的映射仍需实现。 |
| `@visactor/vrender-components`、`@visactor/vrender-animate`（均 1.1.14） | 轴、标签等复合图形和动画执行 | 静态轴也需要测量文本并反馈占位。动画另行验证入场、更新和退出节点的生命周期。 |

版本以[核心包清单](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/package.json)为准。依赖落点可查[配置合并](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/chart/cartesian/cartesian-transformer.ts)、[层级布局变换](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/data/transforms/treemap.ts)和[图元注册](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/mark/rect.ts)。当前提交的实际绘制链路直接抵达 VRender；源码里仍带 VGrammar 名称的性能钩子应按 Compiler 的实际调用解释。

### 四个库各自负责什么

| 依赖 | 接收什么 | 交给下一层什么 | Python 移植的首个对照点 |
| --- | --- | --- | --- |
| **VDataset**（数据视图与更新） | 原始记录或上游 DataView，以及已注册的解析器和变换 | DataSet 管理具名视图、解析器和变换；DataView 按顺序解析和变换，系列从 `latestData` 读取结果。派生视图可以订阅上游变化。 | 替换同一 ID 的数据后，派生视图应读到新结果；清空再恢复时核对类别顺序和记录数。 |
| **VScale**（视觉映射） | 输入域 domain、输出范围 range，以及间距、方向等参数 | band 比例尺给出类别的位置和带宽，linear 比例尺将连续值映射到坐标，ordinal 比例尺可把类别映射到颜色。轴组件使用比例尺生成或定位刻度，并负责标签格式和排布。 | 固定分类顺序核对带宽；给定数值域和反向像素范围，核对零点及正负值坐标。 |
| **VLayouts**（图种专用布局） | 层级、网络或词条数据，绘图区边界和算法参数 | 桑基布局输出节点边界、连线位置与宽度；矩形树布局输出各层矩形；词云布局输出词的位置等属性。VChart 决定标题、轴和 Region 的占位，再把可用空间交给算法。 | 固定节点、流量和绘图区，核对节点边界、连线端点与宽度；改变绘图区后再次对照。 |
| **VRender**（场景与绘制） | VChart Mark 生成的矩形、路径、文本、分组及其视觉属性 | 图形节点挂到 Stage，运行时处理变换、裁剪、边界、绘制次序和命中测试，Stage 将场景绘到目标画布。配套组件和动画包提供复合图形及动画。 | 固定几何和字体，先核对文字测量、裁剪与叠放顺序，再比像素；交互阶段另验命中对象。 |

**柱状图。** 对每月销售额，VDataset 交付月份和数值记录。VChart 的轴组件确定域与绘图区范围，调用 VScale 获取月份带宽、销售额和零点的像素位置；柱系列用这些值定义矩形。VRender 绘制矩形和轴文字，测量结果还会影响轴占位。普通柱图通过比例尺和系列编码即可得到几何。[分类轴](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/component/axis/cartesian/band-axis.ts) · [数值轴](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/component/axis/cartesian/linear-axis.ts) · [柱系列](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/series/bar/bar.ts) · [绘制入口](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/compile/compiler.ts)

**桑基图。** 节点、连线及流量进入 DataView。VChart 在数据变换中调用 `SankeyLayout.layout(data, view)`；VLayouts 同时考虑节点之间的关系、流量和可用空间。计算结果回到数据流，系列再派生节点视图和连线视图，分别编码为矩形与带状路径，最后交给 VRender。这里 **VDataset 负责何时重算、如何传递结果，VLayouts 负责怎样算出几何**。更新数据或绘图区尺寸都可能改变布局结果。[桑基变换](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/data/transforms/sankey.ts) · [桑基系列与派生视图](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/series/sankey/sankey.ts)

## 3. 一张柱状图如何到达画布

以下输入也可作为首个跨语言对照样例。负值让基线和纵轴方向都能在同一张图里验证。

```json
{"type":"bar","width":400,"height":240,"animation":false,
 "data":[{"id":"sales","values":[{"month":"Jan","value":8},{"month":"Feb","value":-3}]}],
 "xField":"month","yField":"value"}
```

1. **装配能力。** 默认入口调用注册函数。`registerBarChart` 注册柱系列以及相关交互；`registerBarSeries` 注册矩形 Mark；`registerRectMark` 把矩形类型与 VRender 的 createRect 对应起来。这个依赖链描述了增加一种图表时需要接通的各层。[Chart 注册](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/chart/bar/bar.ts) · [Series 注册](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/series/bar/bar.ts) · [Rect 注册](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/mark/rect.ts)
2. **准备运行时并展开 spec。** VChart 构造时准备 Compiler、视图、事件分发、DataSet 和插件。首次 renderSync 经 _beforeRender 调用 _initChartSpec，按 type 创建 transformer。柱图继承笛卡尔配置转换，将顶层 xField、yField 等传入系列并补齐缺省轴，再由 transformModelSpec 产生 specInfo。随后 Factory.createChart 创建 BarChart。[调用入口](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/core/vchart.ts) · [柱图转换](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/chart/bar/bar-transformer.ts) · [笛卡尔转换](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/chart/cartesian/cartesian-transformer.ts)
3. **建立数据与模型。** BaseChart.created 解析 sales，创建全局比例尺、背景和布局，再依次创建 Region、Series、Component。init 在各模型都存在后依次初始化它们，设置堆叠并触发 reDataFlow。柱系列在 initMark 和 initMarkStyle 中定义柱体及位置、尺寸、样式的计算规则。此时可以知道两行记录对应两根柱，但它们的最终像素位置依赖绘图区。[模型生命周期](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/chart/base/base-chart.ts) · [柱系列编码](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/series/bar/bar.ts)
4. **编译图元。** Compiler.compile 调用 chart.compile 和 chart.afterCompile。BaseChart 按背景、布局尺寸、区域、系列、组件编译。compileLayout 此处把画布尺寸交给 Compiler；轴与绘图区的实际布局在后续 onLayout 中发生。[模型编译](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/chart/base/base-chart.ts) · [编译器](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/compile/compiler.ts)
5. **布局、求值并绘制。** Compiler.renderMarks 检查待更新的 Mark 和布局标记；先求值有变更的图元，需要布局时调用 chart.onLayout；布局改变范围后，再对有变更的图元求值。对本例，分类带决定两根柱的横向位置与宽度，纵轴将 8、0、−3 映射到像素，正负柱从同一个零点向相反方向延伸。BaseMark 把编码结果应用到图形节点，Compiler._doRender(true) 调用 stage.render()。[布局与绘制顺序](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/compile/compiler.ts) · [节点求值](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/mark/base/base-mark.ts)

## 4. 首帧之后的行为

| 操作 | 源码中的路径 | 移植时需要保持的可见行为 |
| --- | --- | --- |
| 替换数据 | updateDataSync 按 id 定位数据；首次绘制前更新 spec，已有图表时调用 chart.updateData 更新数据和比例尺，再调用 compiler.render。批量入口集中更新后绘制。 | 对 sales 依次替换为新增类别、空数组、恢复数据，观察柱子数量、轴域、标签和旧图形清除。 |
| 修改配置 | _updateSpec 合并模型的更新结果；同类型可重新转换配置并在模型内更新。改变顶层 type 会标记 reMake、reTransformSpec，后续重建。 | 更新颜色、改变尺寸、切换图表类型分别验收。即使早期版本统一重算，也应和直接用新配置创建图表得到同一静态结果。 |
| 改变尺寸 | 新尺寸送入布局和 Compiler，布局可能改变轴范围、文字占位及图元坐标。 | 用窄图和长标签验证重新测量、绘图区边界与裁剪。 |
| 交互与释放 | 事件分发连接 Stage 与模型；状态变化驱动 Mark 重新编码。release 释放 Chart、事件分发器和 Compiler 等资源。 | 静态里程碑可关闭交互与动画；验证重复创建、释放后的资源回收。 |

[实例更新与释放](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/core/vchart.ts) · [图表数据与布局](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/chart/base/base-chart.ts) · [Mark 状态](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/mark/base/base-mark.ts)

## 5. Python 移植顺序与验收

当前执行范围与批次以[静态移植计划](PORTING_PLAN.md)为准。上文的命中测试、交互、动画与 DOM 仅用于说明上游架构。

以下是实施建议。先做一条可和上游逐层对照的静态路径，再沿图种扩展。当前工作的依据是源码阅读，尚未运行上游生成几何或像素基准。

| 阶段 | 建议实现范围 | 完成条件 |
| --- | --- | --- |
| 1. 固定对照基线 | 用上述 spec 在固定版本上游生成工作 spec、系列与区域关系、轴域、绘图区、柱体包围盒和 PNG。记录尺寸、字体文件、像素比、主题、动画开关。 | 同一输入重复运行结果可复现；忽略生成的内部 ID，保留类别顺序和图形层次。参考[上游柱图单测](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/__tests__/unit/chart/bar.test.ts)与[视觉用例](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/__tests__/visual)。 |
| 2. 打通静态柱图 | 配置使用兼容上游字段名的 Python 字典。先实现具名数据、一个 Region、band/linear 比例尺、轴与矩形编码。将文字测量和绘制封装在同一后端接口。 | 先比标准化字段和 domain，再比轴刻度、绘图区及柱体坐标，最后比图像。覆盖正负值、空数据、长标签、横向柱。几何误差与字体像素差分别记录。 |
| 3. 验证复用边界 | 增加 line、scatter、area，随后做分组、堆叠和 common 柱线组合。将数据更新、resize 与首次绘制使用同一计算路径。 | 单系列与组合图可以共用轴和 Region；修改数据或尺寸后的静态输出与全新实例一致；正负堆叠逐段起止值可核对。 |
| 4. 扩展坐标与算法 | 加入 pie 的角度与圆弧，再扩展极坐标轴、层级、流向和地理系列。按功能选择布局、地图解析及文字排布依赖。 | 新图种分别对照角度、父子包含关系、节点与连线几何等中间结果。扩展包与统计编译器另设静态兼容用例。 |

**后端选择。** 同目录 py-skia-canvas 提供 Canvas 2D、文字测量和 PNG 导出，适合作为首个离屏适配器。其当前包要求 CPython 3.13，py-vchart 骨架声明 Python ≥3.11。建议先用 3.13 做渲染验证，将后端设为可选依赖；核心 spec、数据和几何测试可独立运行。引入强制依赖前应确定支持范围。[py-skia-canvas 项目](https://github.com/xuanhun/py-skia-canvas)

**兼容范围。** 首批对照使用可序列化 spec。JS 配置还能携带函数，如格式化器和样式回调，迁移到 Python callable 时需要约定入参、调用时机及异常行为。动画、拾取和浏览器宿主属于静态移植范围外。复制上游实现或测试素材前，按文件核对许可证及第三方声明。
