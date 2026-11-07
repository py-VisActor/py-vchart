# 更新记录

## 0.1.2

文档维护发行：README/PyPI 简介聚焦安装、最小示例和范围；新增用户指南/API/图表目录，以及独立的维护者和 AI agent 导航。项目 Documentation URL 指向用户目录，新增问题与更新记录入口。

算法、图表实现及生产依赖约束不变；旧来源、验收和发行证据保留。

## 0.1.1

- 默认使用公开 `py-skia-canvas` API 完成二维静态绘制、文本和导出。
- 新增公开 `draw_to()`，可在调用方 Canvas 上合成图表；`scene` 保留纯数据元信息。
- PNG、JPEG、WebP、SVG、PDF 导出与 CPU/auto/GPU 设备选择。
- 实例 `maps`/`svgs` 离线资源隔离；旧全局注册方法保留兼容。
- `reference` 文本路径改为可选开发依赖，不是默认运行路径。

详见[0.1.1 发行说明](releases/0.1.1.md)。

## 0.1.0

初始二维静态 Python 图表实现；详见[0.1.0 发行说明](releases/0.1.0.md)。

历史构建、安装验证和发布证据从[开发目录](development/README.md)进入，不从本更新摘要推定新候选已验证。
