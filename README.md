# py-vchart

[VisActor VChart](https://github.com/VisActor/VChart) 的原生 Python 二维静态渲染实现，提供 68 个图表类型。
默认通过公开 `py-skia-canvas` API 测量和绘制；运行时不需要浏览器或 Node，支持 PNG、JPEG、WebP、SVG、PDF。

## 安装

```sh
python -m pip install py-visactor-vchart==0.1.2
```

需要 CPython 3.13，当前原生依赖面向 Windows x86-64 与 Linux x86-64。
发行名为 `py-visactor-vchart`，导入名为 `py_vchart`。

## 最小示例

```python
from pathlib import Path
from py_vchart import VChart

chart = VChart({
    "type": "bar", "width": 400, "height": 240,
    "data": [{"values": [{"month": "Jan", "value": 8}, {"month": "Feb", "value": -3}]}],
    "xField": "month", "yField": "value",
}, backend="cpu").render()
Path("bar.png").write_bytes(chart.to_png())
Path("bar.svg").write_bytes(chart.to_buffer("svg"))
```

## 能力与边界

包含笛卡尔、极坐标、层级、关系、地图、词云、序列及统计图；`VChart.supported_types()` 返回当前注册名称。
支持实例离线地图/SVG 资源，以及向宿主 Canvas 的 `draw_to()` 合成。
类型存在不表示完整兼容其全部 JS 高级字段；当前 Venn 限三个单集合，Treemap 使用 binary 分割。
3D、动画和浏览器交互不属于二维静态接口。不同字体/平台不承诺逐像素一致。

## 文档

- [用户文档](https://github.com/py-VisActor/py-vchart/blob/main/docs/README.md)：使用指南、API 与图表边界。
- [更新记录](https://github.com/py-VisActor/py-vchart/blob/main/docs/CHANGELOG.md) · [问题反馈](https://github.com/py-VisActor/py-vchart/issues)
- [维护者与 AI agent 入口](https://github.com/py-VisActor/py-vchart/blob/main/docs/development/README.md)

MIT License；上游 VChart 与随附算法、配色的许可文件随仓库保留。
