# 区域地图验收

先用 `VChart.register_map("local", geojson)` 注册本地 FeatureCollection，再用 `VChart(spec).to_png()` 导出。spec 中的 `map` 对应注册名；`nameField` 指定业务记录的名称字段，`nameProperty` 指定地理要素属性中的名称字段，默认为 `name`。按 `seriesField` 分类着色，无匹配记录的区域使用 `defaultFillColor`。可运行输入见 [joined](../tests/cases/map/joined)。

本轮支持默认 Mercator 投影的局部区域，要求经度跨度小于 180°、顶点纬度绝对值小于 85°。Polygon 与 MultiPolygon 均需闭环，外环顺时针、孔洞逆时针。地理路径在独立布局模块中投影、细分并适配画布。跨日期变更线或极区的裁剪、其他投影、TopoJSON、连续色阶和可见标签留待后续迭代。

## 对照与复现

7 个自建地理样例覆盖共享边界、有孔多边形与离岛、曲线细分、自定义名称关联、空业务数据、单系列和区域样式。无头浏览器加载 VChart 2.2.1，同一份 GeoJSON 经原生注册后调用 getDataURL()。对照绘图区、各区域各环的投影顶点、填充色和整幅 PNG。地理数据、spec、原生 PNG 的 SHA-256 随用例保存。本轮 7 幅地图的差异像素均为零。

在项目根目录运行：

```powershell
$d = 'tests/cases/map/joined'
node tools/oracle/capture.mjs "$d/spec.json" --geojson "$d/geo.json" --scene "$d/expected.scene.json" --output "$d/expected.png" > "$d/capture.json"
python tools/visual/check_cartesian.py --type map
python tools/visual/check_cartesian.py --all
```
