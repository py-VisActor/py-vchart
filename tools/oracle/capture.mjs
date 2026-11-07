import { createHash } from 'node:crypto';
import { mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, extname, resolve } from 'node:path';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';

const require = createRequire(import.meta.url);
const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    family: { type: 'string' },
    geojson: { type: 'string' },
    svg: { type: 'string' },
    scene: { type: 'string' },
    output: { type: 'string' },
    width: { type: 'string' },
    height: { type: 'string' },
    bundle: { type: 'string' },
    browser: { type: 'string' },
    help: { type: 'boolean' }
  }
});
const usage = 'node capture.mjs <demo.md|demo.js|spec.json> --output chart.png [--width 640 --height 480] [--bundle index.min.js] [--browser chrome.exe]';

function dimension(name, fallback) {
  const value = Number(values[name] ?? fallback);
  if (!Number.isInteger(value) || value < 1 || value > 8192) {
    throw new Error(`--${name} must be an integer between 1 and 8192`);
  }
  return value;
}

function readDemo(filename, source) {
  switch (extname(filename).toLowerCase()) {
    case '.json':
      return { spec: JSON.parse(source) };
    case '.js':
      return { script: source };
    case '.md': {
      const demos = [...source.matchAll(/^\x60{3}(?:js|javascript)\s+livedemo[^\r\n]*\r?\n([\s\S]*?)^\x60{3}[ \t]*\r?$/gm)];
      if (demos.length !== 1) throw new Error('Expected one JavaScript livedemo block; supply the selected block as .js');
      return { script: demos[0][1] };
    }
    default:
      throw new Error(usage);
  }
}

async function capture() {
  if (positionals.length !== 1 || !values.output || extname(values.output).toLowerCase() !== '.png') {
    throw new Error(usage);
  }
  const input = resolve(positionals[0]);
  const source = await readFile(input, 'utf8');
  const demo = readDemo(input, source.replace(/^\uFEFF/, ''));
  const svgSource = values.svg ? await readFile(values.svg, 'utf8') : undefined;
  if (svgSource !== undefined) {
    if (demo.spec?.type !== 'pictogram') throw new Error('--svg requires a pictogram spec');
    demo.svg = svgSource;
  }
  const geoSource = values.geojson ? await readFile(values.geojson, 'utf8') : undefined;
  if (geoSource !== undefined) {
    if (demo.spec?.type !== 'map') throw new Error('--geojson requires a map JSON spec');
    demo.geojson = JSON.parse(geoSource);
  }
  const fixedPixelCanvas = demo.spec?.type === 'sequenceScatterPixel';
  const width = fixedPixelCanvas ? 300 : dimension('width', demo.spec?.width ?? 640);
  const height = fixedPixelCanvas ? 300 : dimension('height', demo.spec?.height ?? 480);
  const bundlePath = values.bundle ?? require.resolve('@visactor/vchart/build/index.min.js');
  const bundle = await readFile(bundlePath);
  let addon;
  if (values.family) {
    if (!['extension', 'statplots'].includes(values.family)) throw new Error('Unknown oracle family');
    if (values.family === 'extension') {
      const { build } = await import('esbuild');
      const result = await build({
        stdin: { contents: "export * from '@visactor/vchart-extension'", resolveDir: dirname(require.resolve('./package.json')) },
        bundle: true, format: 'iife', globalName: 'VChartExtension', write: false, minify: true,
        plugins: [{name: 'shared-chart', setup(build) {
          build.onResolve({ filter: /^@visactor\/vchart$/ }, () => ({ path: 'core', namespace: 'native' }));
          build.onLoad({ filter: /.*/, namespace: 'native' }, () => ({ contents: 'module.exports = globalThis.VChart' }));
        }}]
      });
      addon = Buffer.from(result.outputFiles[0].contents);
    } else addon = await readFile(require.resolve(`@visactor/vchart-${values.family}/build/index.min.js`));
    demo.family = values.family;
  }
  const browser = await chromium.launch({ headless: true, executablePath: values.browser });
  const timer = setTimeout(() => { void browser.close().catch(() => {}); }, 30_000);
  try {
    const context = await browser.newContext({
      viewport: { width, height }, deviceScaleFactor: 1, locale: 'en-US', timezoneId: 'UTC',
      reducedMotion: 'reduce', serviceWorkers: 'block'
    });
    const errors = [];
    await context.route(/^https?:/, async route => {
      errors.push('External resource: ' + route.request().url());
      await route.abort();
    });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.setContent('<meta charset="utf-8"><style>*{box-sizing:border-box}html,body,#chart{width:100%;height:100%;margin:0}</style><div id="chart"></div>');
    if (demo.spec?.type === "rankingBar") await page.clock.setFixedTime(new Date("2020-01-01T00:00:00Z"));
    await page.addScriptTag({ content: bundle.toString('utf8') });

    if (addon) {
      await page.addScriptTag({ content: addon.toString('utf8') });
    }
    const exported = await page.evaluate(async ({ demo, width, height, includeScene }) => {
      const mod = globalThis.VChart;
      const Native = mod?.default ?? mod;
      if (typeof Native !== 'function') throw new Error('Expected a VChart browser bundle');
      let chart;
      class DemoChart extends Native {
        constructor(spec, options = {}) {
          if (chart) throw new Error('Expected one VChart instance per demo');
          super({ ...spec, width, height, animation: false }, {
            ...options, dom: 'chart', dpr: 1, animation: false,
            onError(error) { throw error; }
          });
          chart = this;
        }
      }
      try {
        if (demo.script !== undefined) {
          const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
          await new AsyncFunction('VChart', 'CONTAINER_ID', 'VCHART_MODULE', demo.script)(DemoChart, 'chart', mod);
        } else {
          if (demo.spec?.type === 'mosaic') mod.registerMosaicChart();
          if (demo.spec?.type === 'venn') mod.registerVennChart();
          if (demo.spec?.type === 'liquid') mod.registerLiquidChart();
          if (demo.geojson) Native.registerMap(demo.spec.map, demo.geojson);
          let spec = demo.spec;
          if (demo.family === 'extension') {
            const key = spec.type;
            const prefix = 'register' + key[0].toUpperCase() + key.slice(1);
            const register = globalThis.VChartExtension[prefix + 'Chart'] ?? globalThis.VChartExtension[prefix];
            if (typeof register !== 'function') throw new Error('Missing extension registration for ' + key);
            register({ VChart: Native });
            if (demo.svg) globalThis.VChartExtension.registerSVGSource(spec.svg, demo.svg);
          }
          if (demo.family === 'statplots') {
            globalThis.VChartStatPlots.registerStatPlots();
            const {width, height, ...semantic} = spec;
            spec = globalThis.VChartStatPlots.compileStatPlot(semantic);
          }
          new DemoChart(spec);
        }
        if (!chart) throw new Error('The script must create a chart with new VChart(spec, options)');
        const bitmapMask = demo.spec?.type === 'wordCloud' && demo.spec.maskShape?.startsWith?.('data:image/');
        const layoutReady = bitmapMask && new Promise((resolve, reject) => {
          const timer = setTimeout(() => reject(new Error('Timed out waiting for word cloud mask')), 8000);
          chart.on('afterWordcloudShapeDraw', () => {clearTimeout(timer); resolve();});
        });
        if (!chart.getChart()) chart.renderSync();
        if (layoutReady) await layoutReady;
        const firstFrame = Object.keys(demo.spec?.data ?? {})[0];
        const pixelBackground = demo.spec?.type === 'sequenceScatterPixel' && demo.spec.backgroundColors?.[firstFrame];
        if (demo.spec?.type === 'imageCloud' || (demo.spec?.type === 'storyline' && demo.spec.data.some(block => block.image)) || pixelBackground) {
          const deadline = performance.now() + 8000;
          for (;;) {
            const images = chart.getStage().findAll(g => g.type === 'image' && g.attribute.visible !== false, true);
            if (images.length && images.every(g => g.resources?.get(g.attribute.image)?.state === 'success')) break;
            if (performance.now() > deadline) throw new Error('Timed out waiting for decoded image marks');
            await new Promise(resolve => requestAnimationFrame(resolve));
          }
        }
        await document.fonts.ready;
        const url = await chart.getDataURL();
        if (!url?.startsWith('data:image/png;base64,')) throw new Error('VChart.getDataURL() did not return PNG data');
        let scene;
        if (includeScene) {
          const model = chart.getChart();
          const type = chart.getSpec().type;

          const region = model.getAllRegions()[0];
          const pos = region.getLayoutStartPoint();
          const size = region.getLayoutRect();
          const axes = model.getAllComponents().filter(c => typeof c.getScale === 'function');
          scene = {
            plot: [pos.x, pos.y, size.width, size.height],
            labels: chart.getStage().findAll(g => g.name === 'axis-label', true).map(g => ({
              text: String(g.attribute.text), x: g.globalTransMatrix.e, y: g.globalTransMatrix.f,
              align: g.attribute.textAlign, baseline: g.attribute.textBaseline
            })).sort((a, b) => a.x - b.x || a.y - b.y),
            axes: axes.map(a => ({orient: a.getSpec().orient, domain: a.getScale().domain(), range: a.getScale().range()})),
          };
          if (type === 'bar') {
            scene.bars = model.getAllSeries().flatMap(s => s.getSeriesMark().getGraphics().map(g => {
              const b = g.globalAABBBounds;
              return [b.x1, b.y1, b.x2, b.y2];
            }));
          } else if (type === 'line' || type === 'scatter') {
            if (type === 'line') scene.segments = [];
            scene.points = [];
            for (const series of model.getAllSeries()) {
              for (const mark of series.getMarks()) {
                for (const g of mark.getGraphics()) {
                  if (g.attribute.visible === false) continue;
                  const { e, f } = g.globalTransMatrix;
                  if (g.type === 'symbol' && Number.isFinite(e) && Number.isFinite(f)) {
                    scene.points.push([e, f]);
                  }
                  if (g.type === 'line') {
                    let segment = [];
                    for (const p of g.attribute.points ?? []) {
                      if (p.defined !== false) segment.push([p.x + e, p.y + f]);
                      else if (segment.length) {
                        scene.segments.push(segment);
                        segment = [];
                      }
                    }
                    if (segment.length) scene.segments.push(segment);
                  }
                }
              }
            }
          } else {
            scene.marks = {};
            if (type === 'waterfall') {
              scene.marks.stackLabel = chart.getStage().findAll(g => g.type === 'text' && g.name !== 'axis-label', true)
                .map(g => [String(g.attribute.text), g.globalTransMatrix.e, g.globalTransMatrix.f]);
            }

            for (const [i, series] of model.getAllSeries().entries()) {
              for (const mark of series.getMarks()) {
                const prefix = type === 'common' ? i + '.' : '';
                const name = mark.name;
                if (!['image', 'polygon', 'dot', 'word', 'candlestick', 'bar', 'track', 'progress', 'area', 'point', 'cell', 'boxPlot', 'outlier', 'line', 'pie', 'rose', 'pinBackground', 'pointer', 'pin', 'liquid', 'sunburst', 'leaf', 'nonLeaf', 'circlePacking', 'circle', 'overlap', 'nodePoint', 'centerPoint', 'ripplePoint', 'node', 'link', 'funnel', 'transform'].includes(name)) continue;
                const values = [];
                for (const g of mark.getGraphics()) {
                  const a = g.attribute;
                  if (a.visible === false) continue;
                  const { x, y } = series.getRegion().getLayoutStartPoint();
                  if (type === 'imageCloud' && g.type === 'image') {
                    values.push([x+a.x, y+a.y, a.width, a.height]);
                  } else if (type === 'wordCloud' && name === 'word') {
                    values.push([a.text, x+a.x, y+a.y, a.fontSize, a.angle ?? 0]);
                  } else if (name === 'candlestick') {
                    values.push([x+a.x, a.boxWidth, ...['open','high','low','close'].map(k => y+a[k])]);
                  } else if (type === 'map' && name === 'area') {
                    const rings = a.path.split('Z').filter(Boolean).map(ring =>
                      ring.slice(1).split('L').map(pair => {
                        const [u, v] = pair.split(',').map(Number);
                        return [x + u, y + v];
                      }));
                    values.push([rings, a.fill.toLowerCase()]);
                  } else if (type === 'venn' && name === 'overlap') {
                    values.push((a.arcs ?? []).map(arc => [String(arc.setId), x+arc.p1.x, y+arc.p1.y,
                      x+arc.p2.x, y+arc.p2.y, arc.radius, Number(arc.largeArcFlag)])
                      .sort((a, b) => a[0] < b[0] ? -1 : Number(a[0] > b[0])));
                  } else if (type === 'correlation') {
                    const {e, f} = g.globalTransMatrix;
                    if (name === 'ripplePoint') {
                      values.push(...g.getSubGraphic().map(layer =>
                        [e, f, layer.attribute.size, layer.attribute.fillOpacity]));
                    } else {
                      values.push([e, f, a.size]);
                    }
                  } else if (type === 'sankey' && name === 'link') {
                    values.push([x+a.x0, y+a.y0, x+a.x1, y+a.y1, a.thickness]);
                  } else if (g.type === 'polygon') {
                    values.push(a.points.map(p => [x+p.x, y+p.y]));
                  } else if (g.type === 'arc') {
                    values.push([x+a.x, y+a.y, a.innerRadius, a.outerRadius, a.startAngle, a.endAngle]);
                  } else if (type === 'gauge' && g.type === 'path') {
                    values.push([x+a.x, y+a.y, a.scaleX, a.angle ?? 0]);
                  } else if (name === 'liquid') {
                    const {e, f} = g.globalTransMatrix;
                    let ancestor = g.parent;
                    while (ancestor && !ancestor.attribute.path?.length) ancestor = ancestor.parent;
                    const clip = ancestor.attribute.path[0];
                    const b = clip.AABBBounds;
                    values.push([e, f, a.height, clip.type, x+b.x1, y+b.y1, x+b.x2, y+b.y2]);
                    scene.marks.waves = g.getSubGraphic().map(layer =>
                      layer.attribute.points.map(p => [e+p.x, f+p.y, f+p.y1]));
                  } else if (g.type === 'rect') {
                    const x0 = x + (a.x ?? 0), y0 = y + (a.y ?? 0);
                    const x1 = a.x1 == null ? x0 + a.width : x + a.x1;
                    const y1 = a.y1 == null ? y0 + a.height : y + a.y1;
                    values.push([Math.min(x0,x1), Math.min(y0,y1), Math.max(x0,x1), Math.max(y0,y1)]);
                  } else if (g.type === 'line' || g.type === 'area') {
                    for (const p of a.points ?? []) {
                      if (p.defined === false) continue;
                      values.push(g.type === 'line' ? [x+p.x,y+p.y] : [x+p.x,y+p.y,x+p.x1,y+p.y1]);
                    }
                  } else if (g.type === 'symbol' && mark.type !== 'cell') {
                    if (Number.isFinite(a.x) && Number.isFinite(a.y)) values.push([x+a.x,y+a.y]);
                  } else if (mark.type === 'cell') {
                    const [w,h] = a.size;
                    values.push([x+a.x-w/2,y+a.y-h/2,x+a.x+w/2,y+a.y+h/2]);
                  } else if (mark.type === 'boxPlot') {
                    const horiz = series.getSpec().direction === 'horizontal';
                    values.push([horiz ? y+a.y : x+a.x, horiz ? a.boxHeight : a.boxWidth,
                      ...['min','q1','median','q3','max'].map(k => a[k]+(horiz?x:y))]);
                  }
                }
                scene.marks[prefix+name] = values;
              }
            }
          }
        }
        return { scene, base64: url.slice(url.indexOf(',') + 1), version: Native.version };
      } finally {
        chart?.release();
      }
    }, { demo, width, height, includeScene: Boolean(values.scene) });
    if (errors.length) throw new Error(errors.join('\n'));
    const png = Buffer.from(exported.base64, 'base64');
    if (png.length < 24 || png.readBigUInt64BE() !== 0x89504e470d0a1a0an ||
        png.readUInt32BE(16) !== width || png.readUInt32BE(20) !== height) {
      throw new Error('Unexpected PNG signature or dimensions');
    }
    const output = resolve(values.output);
    await mkdir(dirname(output), { recursive: true });
    const temporary = output + '.' + process.pid + '.tmp';
    try {
      await writeFile(temporary, png);
      await rename(temporary, output);
    } finally {
      await rm(temporary, { force: true });
    }
    if (values.scene) await writeFile(values.scene, JSON.stringify(exported.scene, null, 2) + '\n');
    const sha256 = data => createHash('sha256').update(data).digest('hex');
    console.log(JSON.stringify({
      input, output, width, height, dpr: 1, browser: browser.version(),
      vchart: exported.version ?? (values.bundle ? null : require('@visactor/vchart/package.json').version), bundle: resolve(bundlePath), bundleSha256: sha256(bundle),
       ...(addon ? { family: values.family, addonSha256: sha256(addon) } : {}),
      ...(svgSource === undefined ? {} : { svgSha256: sha256(svgSource) }),
      ...(geoSource === undefined ? {} : { geojsonSha256: sha256(geoSource) }),
      inputSha256: sha256(source), pngSha256: sha256(png)
    }, null, 2));
  } finally {
    clearTimeout(timer);
    await browser.close();
  }
}

if (values.help) console.log(usage);
else capture().catch(error => { console.error(error.message); process.exitCode = 1; });
