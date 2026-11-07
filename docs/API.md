# Python API

公开入口：`from py_vchart import VChart, supported_types`。

| 入口 | 行为 |
| --- | --- |
| `VChart(spec, backend='cpu', text_engine='canvas', maps=None, svgs=None)` | 创建图表；实例资源在创建时复制。 |
| `VChart.supported_types()` / `supported_types()` | 返回当前注册 type 名称元组，大小写敏感。 |
| `VChart.spec_size(spec)` | 校验 type 与逻辑尺寸，返回 `(width, height)`。 |
| `chart.render()` | 实际创建并绘制自有 Canvas，更新 `scene`，返回自身。 |
| `chart.draw_to(canvas, *, x=0, y=0)` | 在宿主公开 Canvas 上绘制并裁剪，更新纯数据 `scene`，返回自身。 |
| `chart.to_png()` | PNG 编码 `bytes`。 |
| `chart.to_buffer(format='png', options=None)` | 编码为 PNG/JPEG/WebP/SVG/PDF 的 `bytes`。未有自有画布时先渲染。 |
| `chart.export_size(format='png', options=None)` | 校验导出预算，返回实际导出尺寸。 |
| `chart.width` / `chart.height` | 逻辑尺寸。 |
| `chart.engine` | 实际 Canvas 设备信息字典；尚未绘制时会先渲染。 |
| `chart.scene` | 渲染后可读的纯数据场景，结构按类型不同。 |

## 尺寸与格式

默认逻辑尺寸为 640×480；`sequenceScatterPixel` 使用固定 300×300。
普通 `width`/`height` 必须为 1～8192 的整数。格式支持 `png`、`jpg`/`jpeg`、`webp`、`svg`、`pdf`。

`to_buffer()` 选项名称包括 `quality`、`density`、`matte`、`outline`、`downsample`、`msaa`、`colorType`；格式相关含义由公开 Canvas 编码 API 决定。
`density` 为正整数，仅影响栅格像素尺寸；栅格导出还受边长和总像素预算约束。

## 设备、文本与资源

- `backend`：`cpu`、`auto`、`gpu`；GPU 不可用时明确失败，不默默替换所选模式。
- `text_engine='canvas'`：默认原生文字路径。`reference` 为需额外安装的历史离屏回归路径，不能用于 `draw_to()`。
- `maps`、`svgs`：按名称显式提供实例资源。传入空字典可禁止读取旧全局注册表；省略时快照旧兼容注册状态。
- `VChart.register_map(name, source)`、`VChart.register_svg_source(name, source)`：兼容全局注册入口；实例隔离应用推荐显式映射。

`scene` 可跨线程传递；实际 Canvas、Context 和字体对象不可跨线程共享。
未提供通用交互/动画或浏览器 DOM API。

## 纯布局适配

`py_vchart.layouts` 提供面向宿主绘图器的纯数据入口，不分配 Canvas；宿主自行绘制文字、图例和导出。它们复用图表内部的实际比例尺/series/专用算法，不是完整 spec API 的替代品。

| 函数 | 主要输入与输出 |
| --- | --- |
| `pie(values, radius=1, inner_radius=0)` | 返回 `(start, end, inner, outer)` 弧段；角度为 Canvas 弧度。 |
| `scatter(points, width, height, x_domain=(0,1), y_domain=(0,1))` | 按实际数值域投影散点。 |
| `position(kind, domain, extent, value, *, reverse=False)` | band 中心或 linear 数值投影。 |
| `cartesian(kind, rows, width, height, x_domain, y_domain, *, x_kind='band', horizontal=False, category_padding=0)` | `kind` 为 line/bar，返回局部线段或柱体边界。 |
| `radar(values, minimum, maximum, *, center=(0,0), radius=1)` | 雷达多边形顶点。 |
| `sankey(node_ids, links, width, height, *, node_width=10, node_gap=12, alignment='justify')` | 节点边界与边厚度/端点记录；link 为 `(source, target, value)`。 |
| `treemap(rows, width, height, *, key='id', value='value', padding=10, header=25)` | binary 分割下的层级边界及 parent/section 记录。 |
| `venn(areas, width, height, *, padding=15)` | 最多三个单集合的圆与区域几何；area 为 `(sets, size)`。 |

返回普通 Python 数据。专用算法的输入范围与错误边界仍适用，不因此获得额外图种/任意布局兼容。
