# VChart 原生 PNG 导出

在 Node.js 22 或更新版本中运行。依赖及浏览器仅用于开发。进入本目录安装：

```powershell
npm ci
npx playwright install chromium --only-shell
```

从本目录导出上游真实 demo：

```powershell
node capture.mjs C:/code/VChart/docs/assets/examples/zh/bar-chart/basic-bar.md --output ../../test-runs/oracle-smoke/basic-bar.png
```

支持单个 JavaScript livedemo 代码块的 Markdown、创建单个图表的可信 JS 脚本以及 VChart JSON spec。JS 示例：

```js
const spec = {type: 'bar', data: [{values: [{x: 'A', y: 3}]}], xField: 'x', yField: 'y'};
const chart = new VChart(spec, {dom: CONTAINER_ID});
chart.renderSync();
```

工具在无头 Chromium 加载本地浏览器构建，执行示例并等待字体就绪，调用 VChart 实例的 `getDataURL()`。将返回的数据 URI 解码成 PNG 原始文件字节，验证签名和尺寸再写入输出路径。成功时标准输出给出输入、构建与 PNG 的 SHA-256，以及浏览器、画布和版本信息。可重定向为运行记录。

- 默认构建来自锁文件中的 npm 发行版 2.2.1。要为某个 Git 提交建立基准，先构建该提交，再传入 `--bundle C:/code/VChart/packages/vchart/build/index.min.js`。记录提交与输出中的构建哈希。
- 默认 640 × 480、DPR 1、关闭动画。JSON 中的宽高可作默认值；JS 和 Markdown 使用固定默认画布。用 `--width 800 --height 500` 显式覆盖。跨机器对比另需固定系统字体。
- 仅执行可信 demo。脚本中用注入的 `VChart` 构造器，支持 await。网络资源请求会导致失败；数据、图片和字体应提前内联。扩展图种需提供包含相应注册的构建或在脚本内注册。
- `--browser <可执行文件>` 可指定本地 Chromium 系浏览器；正式对照推荐使用随锁定 Playwright 安装的 Chromium。在浏览器执行阶段设置 30 秒运行上限。失败以非零状态结束，已有 PNG 仅在新图校验成功后替换。

已迁移的笛卡尔图种及 common 柱线组合可额外传入 `--scene 路径.json`，从同一上游实例提取绘图区、轴域、文字锚点和图种几何（例如面积上下沿、箱线统计量、格子边界、折线分段或散点中心）。

二维扩展图的 JSON 输入使用 `--family extension` 注册对应扩展。统计规格使用 `--family statplots` 调用上游编译器后再导出。二维词云使用核心入口。三类输入均可用 `--scene <文件>` 同时保存原生场景。

pictogram 的 JSON 规格需附带 `--svg source.svg`。Python 对应入口为 `VChart.register_svg_source(spec["svg"], svg_text)`。采集器在报告中记录 SVG 哈希。imageCloud 和含背景图的 sequenceScatterPixel 等待可见图片解码，rankingBar 使用固定首帧时钟。sequenceScatterPixel 按上游规则固定为 300 × 300。

含图片的 storyline 等待可见图片完成解码。使用位图蒙版的 wordCloud 等待原生 `afterWordcloudShapeDraw` 事件后再调用 `getDataURL()`，同时核对主词和填充词图元。
