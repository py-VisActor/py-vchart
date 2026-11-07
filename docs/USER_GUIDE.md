# 使用指南

安装见[项目首页](../README.md)。需要 CPython 3.13，发行名 `py-visactor-vchart`，导入名 `py_vchart`。

## 数据与最小图表

```python
from pathlib import Path
from py_vchart import VChart

spec = {
    "type": "bar", "width": 400, "height": 240,
    "data": [{"values": [{"month": "Jan", "value": 8},
                          {"month": "Feb", "value": -3}]}],
    "xField": "month", "yField": "value",
}
chart = VChart(spec, backend="cpu").render()
Path("bar.png").write_bytes(chart.to_png())
```

常见类别/数值图使用 `data[].values` 与 `xField`/`yField`。将上例 `type` 改为 `line` 可绘制同数据折线。
各类型有自己的字段与静态选项；例如饼图使用 `categoryField`/`valueField`，层级图使用嵌套 `children`，桑基图使用节点和边。
不能将一种图的数据格式无条件用于另一种图。[图表目录](CHARTS.md)给出类型及主要边界。

## 后端与输出

```python
Path("bar.svg").write_bytes(chart.to_buffer("svg"))
Path("bar.pdf").write_bytes(chart.to_buffer("pdf"))
Path("bar@2x.webp").write_bytes(
    chart.to_buffer("webp", {"density": 2, "quality": 0.9})
)
```

支持 PNG、JPEG、WebP、SVG、PDF。SVG/PDF 保留实际绘制的矢量图元；图片、词云蒙版等资源仍可能为栅格。
`density` 为正整数，只放大栅格导出的像素尺寸，不改变逻辑 spec 大小。导出预算校验会拒绝过大尺寸。

`VChart` 默认 `backend="cpu"`。`auto` 使用公开 Canvas 的设备策略；`gpu` 要求真实 GPU，创建失败时明确报错。
`chart.engine` 返回实际设备信息。生产默认 `text_engine="canvas"`，不需要浏览器或 skia-python。

`chart.scene` 在渲染后保存纯数据元信息，可辅助读取布局与图元；具体字段按图表类型不同，不是统一的浏览器 DOM。
变更 spec 后再次调用 `render()` 重新绘制；不要把已导出的旧图片当成新 spec 的结果。

## 离线地图和 SVG 资源

```python
from py_vchart import VChart

geojson = {
    "type": "FeatureCollection",
    "features": [{"type": "Feature", "properties": {"name": "A"},
                  "geometry": {"type": "Polygon", "coordinates": [
                      [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
                  ]}}],
}
chart = VChart({
    "type": "map", "map": "local", "width": 400, "height": 240,
    "data": [{"values": [{"name": "A", "value": 1}]}],
    "nameField": "name", "valueField": "value",
}, maps={"local": geojson})
```

`maps={name: geojson}`、`svgs={name: svg_text}` 提供实例离线资源。显式传入的资源映射与其他实例隔离，并在实例初始化时复制。
旧 `VChart.register_map()`、`register_svg_source()` 保留兼容；新应用优先使用实例资源，避免隐式全局状态。
图片/地图应按实际支持格式明确提供，不依赖浏览器页面自动加载资源。

## 合成到已有 Canvas

```python
from py_skia_canvas import Canvas
from py_vchart import VChart

canvas = Canvas(600, 400)
chart = VChart(spec)
chart.draw_to(canvas, x=20, y=20)
```

`draw_to()` 在调用方 Canvas 上绘制并裁剪到图表逻辑区域；返回该 `VChart` 实例。设备由宿主 Canvas 决定，不读取私有绘图表面。
Canvas、上下文及字体对象必须留在创建线程。若随后调用 `to_buffer()`，图表会渲染自己的导出画布，不会导出宿主整幅画布。

## 错误与范围

无效 type、尺寸或当前不支持的选项会触发异常，常见为 `ValueError`；应保留字段路径或错误消息用于定位。
注册类型存在不代表兼容其全部 JS 高级字段。当前 Venn 限三个声明单集合，Treemap 使用 binary 分割；其他限制见[图表目录](CHARTS.md)。
3D、动画、事件和浏览器交互不属于此二维静态接口。不同字体/平台之间不承诺逐像素相等。
