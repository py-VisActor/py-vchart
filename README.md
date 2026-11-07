# py-vchart

[VisActor VChart](https://github.com/VisActor/VChart) 的原生 Python 二维静态渲染实现，提供 68 个图表类型。0.1.1 使用公开 py-skia-canvas 绘制、测量与导出，不需要浏览器或 skia-python。旧 0.1.0 的 225 个严格场景/像素对照结果保留于[批量移植验收记录](https://github.com/py-VisActor/py-vchart/blob/main/docs/EXPANDED_BATCH_ACCEPTANCE.md)，新版 Canvas 与 reference 模式分别验证，详见 [0.1.1 发行说明](https://github.com/py-VisActor/py-vchart/blob/main/docs/releases/0.1.1.md)。分类型的既有范围见[笛卡尔图](https://github.com/py-VisActor/py-vchart/blob/main/docs/CARTESIAN_BATCH_ACCEPTANCE.md)、[极坐标](https://github.com/py-VisActor/py-vchart/blob/main/docs/POLAR_BATCH_ACCEPTANCE.md)、[专用几何](https://github.com/py-VisActor/py-vchart/blob/main/docs/GEOMETRY_BATCH_ACCEPTANCE.md)与[地图](https://github.com/py-VisActor/py-vchart/blob/main/docs/MAP_ACCEPTANCE.md)。

## 安装

在 CPython 3.13 的 Windows x86-64 或 Linux x86-64 环境安装正式版 wheel：

```sh
python -m pip install py-visactor-vchart==0.1.1
```

## 本地开发

在项目根目录创建 CPython 3.13 虚拟环境，然后运行：

```sh
python -m pip install -e '.[test,reference]'
python -c "import py_vchart; print(py_vchart.__version__)"
python -m unittest discover -s tests
```

Python 包源码位于 `src/py_vchart/`，测试位于 `tests/`。发行包名为 `py-visactor-vchart`，导入名为 `py_vchart`。

## 绘制基础柱状图

安装后执行：

```python
from pathlib import Path
from py_vchart import VChart

chart = VChart({
    "type": "bar", "width": 400, "height": 240,
    "data": [{"values": [{"month": "Jan", "value": 8}, {"month": "Feb", "value": -3}]}],
    "xField": "month", "yField": "value",
}).render()
Path("bar.png").write_bytes(chart.to_png())
Path("bar.svg").write_bytes(chart.to_buffer("svg"))
Path("bar.pdf").write_bytes(chart.to_buffer("pdf"))
```

将上例的 `type` 改为 `line` 即可绘制折线。验收范围见[柱状图](https://github.com/py-VisActor/py-vchart/blob/main/docs/BAR_ACCEPTANCE.md)、[折线图](https://github.com/py-VisActor/py-vchart/blob/main/docs/LINE_ACCEPTANCE.md)与[散点图](https://github.com/py-VisActor/py-vchart/blob/main/docs/SCATTER_ACCEPTANCE.md)。

`VChart.supported_types()` 返回完整注册清单；静态规格与支持的选项沿用各类型文档，不表示完整 VChart JS 高级选项兼容。`VChart(spec, backend="auto")` 保留 Canvas 默认设备；`cpu` 为独立图表 API 的历史默认值，`gpu` 在无 GPU 时明确失败。`to_buffer()` 支持 PNG、JPEG、WebP、SVG、PDF；SVG/PDF 保留实际绘制的矢量图元，图片/蒙版本身仍可能为栅格资源。

通过 `maps={"name": geojson}`、`svgs={"name": svg_text}` 向实例提供离线资源，与其他实例隔离。旧静态注册方法继续保留；显式传入实例资源时不会读取其他实例的资源。`draw_to(canvas, x=0, y=0)` 可把图表绘制到调用者的公开 Canvas，供 py-mermaid 合成静态文字与标注。Canvas 及字体对象均属于创建线程。

开发者需要重现旧严格像素对照时，安装 `.[reference]` 并显式指定 `text_engine="reference"`。此模式包含原有的校准栅格字形，不是默认运行依赖；旧像素阈值不变，不能把 reference 通过等同于新 Canvas 字形逐像素相同。

## 移植参考

- [静态移植范围、代码结构与图种迭代计划](https://github.com/py-VisActor/py-vchart/blob/main/docs/PORTING_PLAN.md)
- [逐图迁移、测试用例与图片对比规程](https://github.com/py-VisActor/py-vchart/blob/main/docs/PORTING_WORKFLOW.md)

- [VChart 架构、依赖与渲染流程](https://github.com/py-VisActor/py-vchart/blob/main/docs/VCHART_ARCHITECTURE.md)
- [上游图表类型清单](https://github.com/py-VisActor/py-vchart/blob/main/docs/CHART_TYPES.md)
- [原生 PNG 导出工具与运行示例](https://github.com/py-VisActor/py-vchart/blob/main/tools/oracle/README.md)
