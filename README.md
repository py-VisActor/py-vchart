# py-vchart

[VisActor VChart](https://github.com/VisActor/VChart) 的原生 Python 静态渲染实现。已验收 68 个二维图表入口，覆盖 225 个静态对照用例。二维词云、扩展图和统计图的新增用例见[批量移植验收记录](docs/EXPANDED_BATCH_ACCEPTANCE.md)。项目只移植二维静态图。分图种的支持范围、图片对比和复现命令见[笛卡尔图与柱线组合](docs/CARTESIAN_BATCH_ACCEPTANCE.md)、[极坐标与静态指标图](docs/POLAR_BATCH_ACCEPTANCE.md)、[专用几何图](docs/GEOMETRY_BATCH_ACCEPTANCE.md)和[区域地图](docs/MAP_ACCEPTANCE.md)。

## 安装

在 CPython 3.13 的 Windows x86-64 或 Linux x86-64 环境安装正式版 wheel：

```sh
python -m pip install https://github.com/py-VisActor/py-vchart/releases/download/v0.1.0/py_visactor_vchart-0.1.0-py3-none-any.whl
```

## 本地开发

在项目根目录创建 CPython 3.13 虚拟环境，然后运行：

```sh
python -m pip install -e .
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
```

将上例的 `type` 改为 `line` 即可绘制折线。验收范围见[柱状图](docs/BAR_ACCEPTANCE.md)、[折线图](docs/LINE_ACCEPTANCE.md)与[散点图](docs/SCATTER_ACCEPTANCE.md)。

## 移植参考

- [静态移植范围、代码结构与图种迭代计划](docs/PORTING_PLAN.md)
- [逐图迁移、测试用例与图片对比规程](docs/PORTING_WORKFLOW.md)

- [VChart 架构、依赖与渲染流程](docs/VCHART_ARCHITECTURE.md)
- [上游图表类型清单](docs/CHART_TYPES.md)
- [原生 PNG 导出工具与运行示例](tools/oracle/README.md)
