# 极坐标与静态指标图验收

本轮从公开入口 `VChart(spec).to_png()` 验收六类基础图。每一行对应四个独立 JSON 输入，各有上游场景、PNG 和采集指纹。[输入和原图](../tests/cases) · [原批次计划](NEXT_POLAR_BATCH.md)

| 入口 | 已对照的四种变体 | 校验重点 |
|---|---|---|
| pie | 基础、环形、局部角域、全零 | 按值累计起止角、类别配色、环孔、零面积 |
| circularProgress | 中间值、零、满值、半环 | 独立的轨道与进度、共用角度域、透明度 |
| gauge | 默认、半圆、最小值、最大值 | 刻度文字和锚点、指针转角和缩放、转轴层次 |
| rose | 单系列、非零内径、分组、堆叠 | 类别角宽、组内偏移、累计起止半径 |
| radar | 闭合线、填充、宽画布、空集 | 径向网格密度、标签、折线和点、空集的外环 |
| liquid | 中间液位、零、满值、矩形容器 | 容器边界、裁剪形状、三层波形的控制数据和液位 |

场景坐标以画布左上为原点，角度为弧度，正方向顺时针。数据读取和数值映射沿用 VDataset、VScale 的按需模块。图表层负责圆心、角域和字段，VRender 适配层负责扇区和文字。水波的静态相位固定在上游关闭动画时的状态。Python 运行时直接绘制，Node 和无头 Chromium 用于生成参考数据。

## 验证结果

- VChart 2.2.1、Chromium 158、DPR 1。独立重采 24 份场景和 24 张原图，与保存的基准逐字节一致。
- Windows、CPython 3.13、Skia CPU。新增 24 例的几何和 RGBA 全部通过原有阈值，纯色区域误差像素数均为零。最大单通道差为 86，出现在仪表盘。比较器能拒绝交换扇区起止角、填实环孔、偏移指针、漏闭合雷达线和液面越界五种故障。
- 同一版本全量 19 个入口、81 个输入通过。旧 57 张 Python PNG 与上批输出逐字节一致。单独安装 wheel 后的 81 张输出与源码运行结果逐字节一致，19 项 unittest 全部通过。

## 复现和范围

```powershell
python tools/visual/check_cartesian.py --batch polar
python tools/visual/check_cartesian.py --batch cartesian
python tools/visual/check_cartesian.py --all
python -m unittest discover -s tests
```

全量运行生成 `test-runs/all-batch/index.html` 和 `report.json`。图库逐例并列展示原图、Python 输出和放大四倍的差异图。

当前覆盖非负扇区数据、单系列基础雷达、取值范围为 0 到 1 的单值指标，以及圆形和矩形液面。官网完整 demo 涉及的图例、中心指标、自定义轴、标签避让和多系列雷达仍待独立验收。交互、动画和 DOM 继续排除在移植范围之外。
