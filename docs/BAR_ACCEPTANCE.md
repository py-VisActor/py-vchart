# 第一轮 bar 静态迁移验收

状态为基础单系列已验收。VChart spec 经过 Python 的数据视图、分类带与数值映射、轴布局及静态图元绘制，使用 py-skia-canvas 导出 PNG。JS 和 Chromium 仅在制备基准时使用。

## 用例与实测结果

数据和上游基准位于 [tests/cases/bar](../tests/cases/bar)。每例的 capture.json 记录发行版本、Chromium 版本、输入及浏览器构建和 PNG 的 SHA-256。expected.scene.json 独立取自运行中的 JS 图表，保存绘图区、轴域及范围、刻度文字及锚点、柱体全局边界。8 例在同机 Windows、CPython 3.13、py-skia-canvas 0.1.0a19 和 Chromium 158 环境通过。

| 用例 | 验收行为 |
| --- | --- |
| signed-baseline | 两类正负值共享零线，默认上下留白、底部分类轴与左侧数值轴 |
| horizontal | 字段对调、水平数值轴及从上至下的分类带 |
| narrow | 宽度从 400 改为 280 后重新计算带宽和坐标 |
| hidden-axes | 两轴显式隐藏，指定数值域，仍计算数据位置 |
| empty | 空数据保留数值轴，无柱体 |
| zero | 零值使用退化高度与数值域 [0, 1] |
| negative | 单个负值，单类别带的居中与宽度 |
| positive | 三条正值，不同类别与柱高 |

几何对照使用 1e-6 逻辑像素绝对误差；文字、图元数、轴方向、顺序精确匹配。图片以原尺寸 RGBA 比对，当前 8 例均为不透明白背景。Chromium 与 Skia 在文字笔画及细线、柱边缘的抗锯齿存在残差。上游 3×3 邻域颜色完全一致的区域要求零差异。在本环境，对上述基础图采用同一组边缘上限：单通道最大差 120，通道差超过 32 的像素占比至多 0.2%，每像素最大通道差的全图均值至多 0.4（0–255）。本轮实际最大值分别为 87、0.084% 以下及 0.193 以下。删除柱、改色、平移一像素的故障注入均被拒绝。更换字体、后端或系统时重新校准并保存独立记录。

## 实现依据与边界

- 数据：单个内联 values 视图，单个分类字段和有限数值字段。场景重新渲染后反映新数据或新尺寸。
- 比例尺：使用分类顺序、默认内外间距、连续线性映射与零基线，单类别按实际有效间距居中。本批对照的数值轴使用默认刻度数。参考 @visactor/vscale 的 band-scale、utils/tick-sample 和 VChart 的 linear-axis-mixin。
- 渲染：验证 Windows 的 Microsoft YaHei 字体环境、底部与左侧默认轴及显隐、单色柱。图形填充、对齐和绘制顺序来自[上游柱系列](https://github.com/VisActor/VChart/blob/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/series/bar/bar.ts)及[笛卡尔轴](https://github.com/VisActor/VChart/tree/fdb63276cf8b71f5a6cca128c409e009cc94615a/packages/vchart/src/component/axis/cartesian)。Python 采用按需行为实现。图片参考使用工具锁定的 npm 2.2.1 构建。
- 后续覆盖分组、堆叠、柱端数据标签、轴标签避让、主题、多视图与复杂轴配置。此前官网带柱端数值标签的品牌排行 demo 仍属后续范围。首轮不承诺任意数据与尺寸的自动刻度和布局均能达到上游视觉一致。

## 复现

在项目根目录的 CPython 3.13 环境运行：

```powershell
python -m pip install -e ".[render,test]"
python -m unittest discover -s tests -v
python tools/visual/check_bar.py --output test-runs/bar
```

输出包含每例的 actual.scene.json、actual.png、四倍放大的通道差值 diff.png 和汇总 report.json。重取基准时先按[工具说明](../tools/oracle/README.md)安装 Chromium，再用同一个 spec 导出到独立目录：

```powershell
node tools/oracle/capture.mjs tests/cases/bar/signed-baseline/spec.json --output test-runs/repeat/expected.png --scene test-runs/repeat/expected.scene.json
```
