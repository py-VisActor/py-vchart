# 基础散点图验收

已验收顶层 `type: "scatter"` 的单系列静态圆点图。默认底轴采用分类带，即使输入类别为数字也会等距排列；要比较 X 方向上的真实数值距离，指定 `axes: [{"orient":"bottom","type":"linear"}]`。数值 Y 轴、绘图区和点样式分别复用公共坐标轴与圆点模块。

## 对照与边界

参考为 VChart npm 2.2.1、Chromium 158，Python 端为 Windows CPython 3.13 和 py-skia-canvas 0.1.0a19 CPU。8 个用例均独立重复采集了上游 PNG 和场景，并通过既有视觉阈值。逐例验证点的顺序、数量、中心坐标、轴与文字位置，所有上游纯色区域精确匹配。[输入与基准](../tests/cases/scatter)

| 案例 | 核验内容 |
| --- | --- |
| signed、positive | 数字类别等距，覆盖正负数与全正数 |
| dual-linear | 与 signed 相同的数据改用双数值轴，验证 X 比例与布局 |
| explicit | 双轴显式范围、隐藏轴、自定义圆点尺寸，PNG 像素精确相同 |
| overlap | 同坐标两条记录分别绘制，验证填充颜色与半透明叠加 |
| single、empty | 单点与空集，核查退化域及点数 |
| cars | 取官方汽车示例的全部 406 对油耗效率与马力观测，使用顶层 scatter 和 25% 填充透明度。此基准验证数据和几何；官方原页另用了 common 组合及轴标题。[数据来源与原示例](https://github.com/VisActor/VChart/blob/fdb63276cf8b71f5a6cca128c409e009cc94615a/docs/assets/examples/zh/scatter-chart/basic-scatter.md) |

运行 `python tools/visual/check_cartesian.py --type scatter` 生成候选图、差异图与报告。运行 `python -m unittest discover -s tests -v` 重跑三种图表。新增共享轴支持后，原有 8 个柱图与 6 个折线图候选 PNG 与上轮逐字节相同。

当前接收一个内联数据视图和有效坐标；支持常量尺寸、填充色与填充透明度。字段映射的气泡大小、多系列、非圆形符号、轴标题及回归线需后续单独迁移。
