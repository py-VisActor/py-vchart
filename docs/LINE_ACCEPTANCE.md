# 基础折线图迁移验收

本轮交付单系列 `type: "line"` 的分类轴与线性数值轴、直线连接、圆形点标记和离屏 PNG。使用同一个公开入口 `VChart(spec).render().to_png()`。多系列、平滑/阶梯曲线、采样和连续时间轴留待后续单独对照。

## 上游对照

以锁定的 VChart npm 2.2.1 和 Chromium 158 为基准。每个案例独立保存输入、采集指纹、原图和场景，二次采集逐字节重现。场景比较绘图区、轴、标签锚点、每段折线的顶点及可见圆点中心。数据缺失仍占分类位置，折线在此处分段。基准工具从上游实际图元读取 defined 标记及坐标。[用例目录](../tests/cases/line)

| 案例 | 验收内容 |
| --- | --- |
| basic-demo | 官方基础折线图的 9 个时刻。直接执行官方 Markdown demo 与用例 spec 生成的参考 PNG 字节一致。 |
| gaps | 两处 null 将折线分为三段，孤立样本保留圆点；单测另覆盖缺字段。 |
| horizontal | 交换分类轴与数值轴，一条路径跨越零点。 |
| single、empty | 单条记录绘制一个圆点，空集只显示坐标轴。 |
| styled | 自定义线宽、线色并隐藏圆点。 |

官方案例及系列模型可查[官方 demo](https://github.com/VisActor/VChart/blob/fdb63276cf8b71f5a6cca128c409e009cc94615a/docs/assets/examples/zh/line-chart/basic-line.md)和[上游 LineSeries](https://github.com/VisActor/VChart/blob/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/series/line/line.ts)。

## 对柱图和共享模块的影响

分类带、数值映射、布局计算、轴绘制和公共场景记录归入同一笛卡尔渲染流程。bar 负责从零线生成矩形，line 负责分段、路径和点标记。两者分别决定缺失值策略；bar 仍对缺少数值的记录报错。保留原有柱图基准与检查命令。[公共布局](../src/py_vchart/chart/cartesian.py) · [柱系列](../src/py_vchart/chart/bar.py) · [折线系列](../src/py_vchart/chart/line.py)

静态绘制固定使用 Skia CPU，并将居中基线的文字绘制高度对齐到最近设备像素（当前 DPR 1）。此改动会改变旧 PNG 的抗锯齿像素。变更前后逐一比较了 8 个柱图场景文件，内容逐字节一致；同机柱图与上游的差异像素数在每例均减少，隐藏轴案例达到零差异。

6 个折线案例和 8 个柱图案例通过同一几何与像素阈值。折线的纯色区域差异为零，最大通道差为 109，通道差超过 32 的像素占比各例低于 0.05%。运行环境为 Windows、CPython 3.13、py-skia-canvas 0.1.0a19。字体环境见[柱图验收说明](BAR_ACCEPTANCE.md)。

```powershell
python -m unittest discover -s tests -v
python tools/visual/check_cartesian.py --type line
python tools/visual/check_cartesian.py --type bar
```
