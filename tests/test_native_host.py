"""Independent public Canvas host contracts for the native default.

Sources: py-skia-canvas public Canvas.toBufferSync/gpu/engine/Context.canvas,
measureText/fillText/Path2D; fixed VChart225 source fixture inputs and their
capture.json byte identities. These are native content/geometry checks, not a
replacement golden or relaxed OracleTests pixel gate. The old calibrated
reference gate remains separate and mandatory in the reference-extra job.

No native allocation, renderer, source oracle or test is invoked at import.
Both installed Canvas a18/a19 must run this suite in separate release jobs;
one process checks its actual version, never monkeypatches a version string.
"""
import builtins
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import is_dataclass
import hashlib
import io
import json
import math
from pathlib import Path
import re
import tomllib
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from PIL import Image,ImageChops

ROOT=Path(__file__).resolve().parents[1]
CASES=ROOT/'tests/cases'
SVG='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 20"><rect width="20" height="20" fill="#e02020"/><rect x="20" width="20" height="20" fill="#2040e0"/></svg>'


def pie_spec():
    return dict(type='pie',width=120,height=80,padding=0,categoryField='k',valueField='v',
                data={'values':[{'k':'a','v':1},{'k':'b','v':3}]})


@contextmanager
def forbid_skia():
    original=builtins.__import__
    def guarded(name,*args,**kwargs):
        if name=='skia' or name.startswith('skia.'):
            raise AssertionError('Default native path attempted skia-python import')
        return original(name,*args,**kwargs)
    with patch('builtins.__import__',side_effect=guarded):yield


def source_case(path):
    spec=json.loads((path/'spec.json').read_text('utf8'))
    capture=json.loads((path/'capture.json').read_text('utf8'))
    if hashlib.sha256((path/'spec.json').read_bytes()).hexdigest()!=capture['inputSha256']:
        raise AssertionError('Fixed source fixture bytes changed: '+str(path))
    resources={'maps':{},'svgs':{}}
    if spec['type']=='map':resources['maps'][spec['map']]=json.loads((path/'geo.json').read_text('utf8'))
    if spec['type']=='pictogram':resources['svgs'][spec['svg']]=(path/'source.svg').read_bytes()
    return spec,resources


def decode(data):
    image=Image.open(io.BytesIO(data));image.load();return image.convert('RGB')


def pure(test,value):
    if isinstance(value,dict):
        for k,v in value.items():
            test.assertIn(type(k),(str,int,float,bool,type(None)));pure(test,v)
    elif isinstance(value,(list,tuple)):
        for v in value:pure(test,v)
    else:
        test.assertIn(type(value),(str,int,float,bool,type(None)))
        if isinstance(value,float):test.assertTrue(math.isfinite(value))
    test.assertFalse(is_dataclass(value))


def glyph_ink(test,image):
    # Authored baseline/size on an otherwise white surface; no frames or axes
    # can stand in for missing glyphs in this exact region.
    roi=image.crop((8,12,210,58))
    test.assertGreater(sum(min(p)<150 for p in roi.getdata()),20)
    test.assertGreater(len(set(roi.getdata())),4)


def source_has_marks(scene):
    # Fixed line/bar/scatter captures predate the generic marks container.
    return (any(bool(v) for v in scene.get('marks',{}).values()) or
            any(bool(scene.get(k)) for k in ('bars','points','segments')))


def source_mark_content(test,image,expected_image,expected_scene,kind):
    # Source scenes prove that this is a nonempty representative. A solid
    # rectangle needs only background + one color; palette cardinality says
    # nothing about whether its content was painted.
    # Pictogram/storyline source captures have an empty marks dictionary even
    # though their independently captured SVG/card pixels are visible.
    if not source_has_marks(expected_scene):
        test.assertIn(kind,('pictogram','storyline'))
        test.assertEqual(expected_scene['marks'],{})
    background=expected_image.getpixel((0,0))
    test.assertIsNotNone(ImageChops.difference(
        expected_image,Image.new('RGB',expected_image.size,background)).getbbox())
    test.assertIsNotNone(ImageChops.difference(
        image,Image.new('RGB',image.size,background)).getbbox(),
        'Native omitted all independently nonempty source content')


class NativeHostContracts(unittest.TestCase):
    def test_default_dependency_metadata_has_optional_reference_only(self):
        project=tomllib.loads((ROOT/'pyproject.toml').read_text('utf8'))['project']
        self.assertFalse(any(d.lower().startswith('skia-python') for d in project['dependencies']))
        self.assertTrue(any(d.lower().startswith('skia-python') for d in project['optional-dependencies']['reference']))
        self.assertTrue(any(d.lower().startswith('numpy') for d in project['dependencies']))

    def test_actual_canvas_release_is_one_of_the_two_reviewed_api_versions(self):
        import py_skia_canvas
        self.assertIn(py_skia_canvas.__version__,('0.1.0a18','0.1.0a19'))
        for name in ('Canvas','Path2D','Image','FontLibrary'):
            self.assertTrue(hasattr(py_skia_canvas,name))

    def test_all_68_fixed_source_types_render_native_without_skia_import(self):
        from py_vchart import VChart,supported_types
        chosen={}
        for file in sorted(CASES.glob('**/spec.json')):
            kind=json.loads(file.read_text('utf8'))['type']
            expected_scene=json.loads((file.parent/'expected.scene.json').read_text('utf8'))
            if not source_has_marks(expected_scene) and kind not in ('pictogram','storyline'):continue
            expected_image=decode((file.parent/'expected.png').read_bytes())
            if ImageChops.difference(expected_image,Image.new('RGB',expected_image.size,
                    expected_image.getpixel((0,0)))).getbbox() is None:continue
            if kind not in chosen or file.parent.name=='first-frame':chosen[kind]=file.parent
        self.assertEqual(len(chosen),68)
        self.assertEqual(set(chosen),set(supported_types()))
        for kind,path in chosen.items():
            with self.subTest(kind=kind,source=str(path)),forbid_skia():
                spec,resources=source_case(path);chart=VChart(spec,**resources).render()
                self.assertEqual(chart.text_engine,'canvas')
                self.assertEqual(chart.engine['renderer'],'CPU')
                image=decode(chart.to_png())
                self.assertEqual(image.size,VChart.spec_size(spec))
                expected_scene=json.loads((path/'expected.scene.json').read_text('utf8'))
                expected_image=decode((path/'expected.png').read_bytes())
                source_mark_content(self,image,expected_image,expected_scene,kind)
                # A lost renderer remains a failure even for a two-color
                # imageCloud or three-color progress bar.
                with self.assertRaises(AssertionError):
                    source_mark_content(self,Image.new('RGB',image.size,
                        expected_image.getpixel((0,0))),expected_image,expected_scene,kind)
                pure(self,chart.scene)

    def test_native_glyph_has_real_pixels_and_lost_text_fault_fails(self):
        from py_skia_canvas import CanvasRenderingContext2D
        from py_vchart._deps.vrender import Surface
        from py_vchart._deps.vrender.text import glyph_run
        def draw():
            surface=Surface(220,70,backend='cpu');surface.rect((0,0,220,70),'white')
            glyph_run(surface,'Visible 123',10,45,24,'#202030',family='Arial')
            return decode(surface.png())
        with forbid_skia():good=draw()
        glyph_ink(self,good)
        with patch.object(CanvasRenderingContext2D,'fillText',lambda *_:None):bad=draw()
        with self.assertRaises(AssertionError):glyph_ink(self,bad)

    def test_native_transformed_glyph_obeys_clip_alpha_and_state(self):
        from py_vchart._deps.vrender import Surface
        from py_vchart._deps.vrender.text import glyph_run
        from py_skia_canvas import Path2D
        surface=Surface(180,90,backend='cpu');ctx=surface.ctx
        surface.rect((0,0,180,90),'white');ctx.save()
        clip=Path2D();clip.rect(30,10,60,60);ctx.clip(clip);ctx.translate(40,30);ctx.rotate(.2)
        ctx.globalAlpha=.5;ctx.fillStyle='#123456';before=(ctx.font,str(ctx.fillStyle),ctx.globalAlpha)
        with forbid_skia():glyph_run(surface,'MMMMMMMMM',0,12,22,'black',italic=True,family='Arial')
        self.assertEqual((ctx.font,str(ctx.fillStyle),ctx.globalAlpha),before);ctx.restore()
        image=decode(surface.png());inside=image.crop((30,10,90,70))
        self.assertGreater(sum(min(p)<240 for p in inside.getdata()),10)
        self.assertGreaterEqual(min(min(p) for p in inside.getdata()),110,'Parent alpha lost')
        for box in [(0,0,30,90),(90,0,180,90),(30,70,90,90)]:
            self.assertEqual(image.crop(box).getextrema(),((255,255),)*3)

    def test_native_word_mask_and_rotated_glyph_occupancy_without_skia(self):
        from py_vchart._deps.vlayouts.word_mask import raster_mask,glyph_offsets,MaskBoard
        with forbid_skia():
            _,allowed=raster_mask({'type':'text','text':'MASK','fontFamily':'Arial','fill':'black'},160,70)
            board=MaskBoard(allowed)
            self.assertGreater(board.area,100);self.assertLess(board.area,160*70)
            y,x=glyph_offsets('Word','Arial',400,20,60,.3,2)
            self.assertGreater(len(x),20);self.assertEqual(len(x),len(y))
            self.assertGreater(max(x)-min(x),10);self.assertGreater(max(y)-min(y),8)

    def test_explicit_cpu_auto_and_gpu_are_actual_or_explicitly_unavailable(self):
        from py_vchart import VChart
        self.assertEqual(VChart(pie_spec(),backend='cpu').render().engine['renderer'],'CPU')
        self.assertIn(VChart(pie_spec(),backend='auto').render().engine['renderer'],('CPU','GPU'))
        try:gpu=VChart(pie_spec(),backend='gpu').render()
        except RuntimeError as exc:
            self.assertRegex(str(exc).lower(),r'gpu|vulkan|device|driver')
        else:self.assertEqual(gpu.engine['renderer'],'GPU','Explicit GPU silently fell back')

    def test_five_actual_encoders_and_density_physical_sizes(self):
        from py_vchart import VChart
        chart=VChart(pie_spec()).render()
        for fmt in ('png','jpeg','webp','svg','pdf'):
            with self.subTest(format=fmt):
                data=chart.to_buffer(fmt,{'density':2})
                if fmt in ('png','jpeg','webp'):
                    im=Image.open(io.BytesIO(data));im.load()
                    self.assertEqual(im.format,{'png':'PNG','jpeg':'JPEG','webp':'WEBP'}[fmt])
                    self.assertEqual(im.size,(240,160));self.assertGreater(len(set(im.convert('RGB').getdata())),3)
                elif fmt=='svg':
                    root=ET.fromstring(data);self.assertTrue(root.tag.endswith('svg'))
                    self.assertAlmostEqual(float(re.match(r'[\d.]+',root.attrib['width'])[0]),120)
                    self.assertTrue(any(e.tag.endswith('path') for e in root.iter()))
                    self.assertFalse(any(e.tag.endswith('image') for e in root.iter()),'Vector pie replaced by PNG')
                else:
                    self.assertTrue(data.startswith(b'%PDF-'));self.assertIn(b'%%EOF',data[-100:])
                    media=re.search(rb'/MediaBox\s*\[([^]]+)\]',data);self.assertIsNotNone(media)
                    self.assertEqual(tuple(map(float,media[1].split())),(0,0,120,80))
                    self.assertNotIn(b'/Subtype /Image',data,'Pure vector pie encoded as bitmap')
                self.assertEqual(chart.export_size(fmt,{'density':2}),(240,160) if fmt in ('png','jpeg','webp') else (120,80))

    def test_export_budget_rejects_before_owned_canvas_allocation(self):
        from py_vchart import VChart
        from py_skia_canvas import Canvas
        chart=VChart(pie_spec()|{'width':8192,'height':8192})
        self.assertEqual((chart.width,chart.height),(8192,8192))
        with patch.object(Canvas,'__init__',side_effect=AssertionError('Must reject before Canvas')):
            for density in (2,10**100):
                with self.subTest(density=str(density)),self.assertRaises(ValueError):chart.to_buffer('png',{'density':density})
        for bad in (0,-1,1.5,True):
            with self.subTest(density=bad),self.assertRaises(ValueError):chart.export_size('webp',{'density':bad})

    def test_owner_thread_exports_refuse_native_transfer(self):
        from py_vchart import VChart
        chart=VChart(pie_spec()).render()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(RuntimeError):pool.submit(chart.to_buffer,'png').result()
        self.assertTrue(chart.to_png().startswith(b'\x89PNG'))

    def test_encoder_quality_contract_rejects_nonfinite_or_out_of_range(self):
        from py_vchart import VChart
        chart=VChart(pie_spec()).render()
        for quality in (-.1,1.1,float('nan'),float('inf'),True,'high'):
            with self.subTest(quality=quality),self.assertRaisesRegex(TypeError,'quality'):
                chart.to_buffer('jpg',{'quality':quality})

    def test_scene_metadata_is_pure_and_rerender_reads_current_data(self):
        from py_vchart import VChart
        spec=pie_spec();chart=VChart(spec).render();before=deepcopy(chart.scene);pure(self,before)
        spec['data']['values'][0]['v']=3
        chart.render();pure(self,chart.scene);self.assertNotEqual(chart.scene,before)
        self.assertEqual(chart.scene,VChart(spec).render().scene)

    def test_unknown_modes_formats_and_unsupported_properties_are_explicit(self):
        from py_vchart import VChart
        for kwargs in ({'backend':'browser'},{'text_engine':'implicit-fallback'}):
            with self.assertRaises(ValueError):VChart(pie_spec(),**kwargs)
        chart=VChart(pie_spec())
        with self.assertRaises(ValueError):chart.to_buffer('gif')
        with self.assertRaises(ValueError):chart.to_buffer('png',{'networkFallback':True})


class NativeResourcesAndBorrowedCanvas(unittest.TestCase):
    def map_input(self):return source_case(CASES/'map/joined')
    def image_input(self):return source_case(CASES/'pictogram/first-frame')

    def test_explicit_empty_maps_does_not_inherit_legacy_global(self):
        from py_vchart import VChart
        spec,res=self.map_input();name='native-host-global-map';geo=next(iter(res['maps'].values()))
        VChart.register_map(name,geo);spec['map']=name
        with self.assertRaisesRegex(ValueError,'registered'):VChart(spec,maps={},svgs={}).render()
        self.assertGreater(len(VChart(spec,maps=None,svgs={}).to_png()),100)

    def test_explicit_empty_svgs_does_not_inherit_legacy_global(self):
        from py_vchart import VChart
        spec,_=self.image_input();name='native-host-global-svg';VChart.register_svg_source(name,SVG);spec['svg']=name
        with self.assertRaisesRegex(ValueError,'Unregistered'):VChart(spec,maps={},svgs={}).render()
        self.assertGreater(len(VChart(spec,maps={},svgs=None).to_png()),100)

    def test_explicit_resource_mapping_replaces_other_global_entries(self):
        from py_vchart import VChart
        spec,res=self.image_input();VChart.register_svg_source('native-global-other',SVG)
        spec['svg']='native-global-other'
        with self.assertRaises(ValueError):VChart(spec,svgs={'different':SVG},maps={}).render()

    def test_instance_resources_are_deep_snapshots(self):
        from py_vchart import VChart
        spec,res=self.map_input();chart=VChart(spec,**res)
        next(iter(res['maps'].values()))['features'].clear()
        first=chart.to_png();self.assertEqual(chart.render().to_png(),first)
        spec,res=self.image_input();chart=VChart(spec,**res)
        res['svgs'].clear();self.assertGreater(len(chart.to_png()),100)

    def test_instance_svg_styles_do_not_mutate_other_instances(self):
        from py_vchart import VChart
        spec,_=self.image_input();name=spec['svg']
        a=VChart(spec,svgs={name:SVG},maps={})
        b=VChart(spec|{'pictogram':{'style':{'fill':'#00ff00'}}},svgs={name:SVG},maps={})
        original=a.to_png();b.to_png();self.assertEqual(a.render().to_png(),original)

    def test_embedded_pictogram_has_real_offline_red_blue_halves(self):
        from py_vchart import VChart
        spec,_=self.image_input();spec=spec|{'width':160,'height':100,'padding':10}
        im=decode(VChart(spec,svgs={spec['svg']:SVG},maps={}).to_png())
        self.assertGreater(sum(r>b*2 for r,g,b in im.getdata()),100)
        self.assertGreater(sum(b>r*2 for r,g,b in im.getdata()),100)

    def test_external_svg_payloads_cannot_implicitly_load_resources(self):
        from py_vchart import VChart
        spec,_=self.image_input()
        bad=['<svg viewBox="0 0 10 10"><image href="https://example.invalid/x.png"/></svg>',
             '<svg viewBox="0 0 10 10"><style>rect{fill:url(https://example.invalid/a)}</style></svg>',
             '<svg viewBox="0 0 10 10"><script>run()</script></svg>',
             '<!DOCTYPE svg [<!ENTITY x "x">]><svg viewBox="0 0 10 10"/>']
        for svg in bad:
            with self.subTest(source=svg),self.assertRaises(ValueError):VChart(spec,svgs={spec['svg']:svg},maps={}).render()
        # A MIME label cannot hide SVG bytes behind a UTF-8 BOM. Refuse them
        # before native decoding, including the independent public chart path.
        import base64
        from py_skia_canvas import Image as CanvasImage
        for svg in bad:
            uri='data:image/png;base64,'+base64.b64encode(b'\xef\xbb\xbf'+svg.encode('utf-8')).decode('ascii')
            chart={'type':'imageCloud','urlField':'uri','data':{'values':[{'uri':uri}]}}
            with self.subTest(disguised=svg),patch.object(CanvasImage,'__init__',side_effect=AssertionError('Unsafe decode')):
                with self.assertRaises(ValueError):VChart(chart,maps={},svgs={}).render()

    def test_draw_to_preserves_host_device_size_state_and_clips(self):
        from py_vchart import VChart
        from py_skia_canvas import Canvas
        canvas=Canvas(200,150);canvas.gpu=False;ctx=canvas.getContext('2d')
        ctx.fillStyle='#ff00ff';ctx.fillRect(0,0,200,150);ctx.translate(3,4)
        ctx.globalAlpha=.4;ctx.lineWidth=7;ctx.font='italic 400 17px Arial';ctx.setLineDash([2,3]);ctx.fillStyle='#102030'
        def state():
            m=ctx.getTransform();return (ctx.globalAlpha,ctx.lineWidth,ctx.font,str(ctx.fillStyle),tuple(ctx.getLineDash()),tuple(getattr(m,k) for k in ('a','b','c','d','e','f')))
        before=state();engine=dict(canvas.engine)
        with patch.object(Canvas,'__init__',side_effect=AssertionError('draw_to allocated owned Canvas')):
            chart=VChart(pie_spec(),maps={},svgs={}).draw_to(canvas,x=20,y=30)
        self.assertEqual(state(),before);self.assertEqual(dict(canvas.engine),engine)
        self.assertEqual((canvas.width,canvas.height),(200,150));pure(self,chart.scene)
        im=decode(canvas.toBufferSync('png'))
        for point in ((0,0),(22,40),(144,40),(50,115),(199,149)):
            self.assertEqual(im.getpixel(point),(255,0,255),'Paint escaped authored chart clip')
        self.assertNotEqual(im.getpixel((24,35)),(255,0,255))
        svg=ET.fromstring(canvas.toBufferSync('svg'))
        self.assertFalse(any(e.tag.endswith('image') for e in svg.iter()))

    def test_draw_to_failure_restores_host_state_and_resource_scope(self):
        from py_vchart import VChart
        from py_vchart.core import RENDERERS
        from py_skia_canvas import Canvas
        canvas=Canvas(200,150);canvas.gpu=False;ctx=canvas.getContext('2d');ctx.globalAlpha=.7;ctx.fillStyle='#123456'
        def state():
            m=ctx.getTransform();return (ctx.globalAlpha,str(ctx.fillStyle),tuple(getattr(m,k) for k in ('a','b','c','d','e','f')))
        before=state()
        def fault(*args):raise RuntimeError('injected renderer failure')
        with patch.dict(RENDERERS,{'pie':fault}):
            with self.assertRaisesRegex(RuntimeError,'injected'):VChart(pie_spec()).draw_to(canvas,x=5,y=7)
        self.assertEqual(state(),before)
        from py_vchart._deps.vrender._state import map_sources,svg_sources,active_context
        self.assertIsNone(map_sources.get());self.assertIsNone(svg_sources.get());self.assertIsNone(active_context.get())

    def test_borrowed_canvas_export_is_not_mislabeled_host_image(self):
        from py_vchart import VChart
        from py_skia_canvas import Canvas
        canvas=Canvas(300,200);canvas.gpu=False
        chart=VChart(pie_spec()).draw_to(canvas,x=10,y=10)
        self.assertEqual(decode(chart.to_buffer('png')).size,(120,80))

    def test_reference_mode_is_explicit_and_not_borrowed_vector_drawing(self):
        from py_vchart import VChart
        from py_skia_canvas import Canvas
        canvas=Canvas(120,80);canvas.gpu=False
        with self.assertRaisesRegex(ValueError,'reference|canvas'):
            VChart(pie_spec(),text_engine='reference').draw_to(canvas)


class PureEmbeddingLayouts(unittest.TestCase):
    def test_all_public_pure_layouts_allocate_no_canvas_or_skia(self):
        from py_vchart import layouts,VChart
        from py_skia_canvas import Canvas
        with forbid_skia(),patch.object(Canvas,'__init__',side_effect=AssertionError('Pure geometry allocated Canvas')):
            self.assertEqual(VChart.spec_size(pie_spec()),(120,80))
            self.assertEqual(VChart.spec_size({'type':'sequenceScatterPixel','width':999,'height':999}),(300,300))
            arcs=layouts.pie([1,3],radius=10);self.assertEqual(len(arcs),2)
            self.assertAlmostEqual(arcs[0][1]-arcs[0][0],math.pi/2)
            self.assertAlmostEqual(sum(b-a for a,b,*_ in arcs),2*math.pi)
            self.assertEqual(layouts.scatter([(0,0),(1,1)],100,80),((0,80),(100,0)))
            self.assertAlmostEqual(layouts.position('linear',(0,10),(10,110),5),60)
            data=layouts.cartesian('bar',[('a',1),('b',2)],100,80,['a','b'],[0,2])
            self.assertEqual(len(data['bars']),2)
            radar=layouts.radar([0,10,5],0,10,center=(50,50),radius=20)
            self.assertEqual(radar[0],(50,50));self.assertAlmostEqual(radar[1][0],50+10*math.sqrt(3));self.assertAlmostEqual(radar[1][1],60)
            nodes,edges=layouts.sankey(['A','B'],[('A','B',3)],100,80)
            self.assertEqual({n['id'] for n in nodes},{'A','B'});self.assertEqual(len(edges),1);self.assertGreater(edges[0]['width'],0)
            tiles=layouts.treemap([{'id':'a','value':1},{'id':'b','value':3}],100,80,padding=0,header=0)
            areas={n['id']:(n['box'][2]-n['box'][0])*(n['box'][3]-n['box'][1]) for n in tiles}
            self.assertAlmostEqual(sum(areas.values()),8000);self.assertAlmostEqual(areas['b']/areas['a'],3)
            venn=layouts.venn([(('A',),4),(('B',),4),(('A','B'),1)],160,100)
            self.assertEqual(len(venn['circles']),2);self.assertEqual(len(venn['regions']),3)
            pure(self,venn)

    def test_pure_layout_invalid_numeric_contracts_do_not_construct_canvas(self):
        from py_vchart import layouts
        from py_skia_canvas import Canvas
        with patch.object(Canvas,'__init__',side_effect=AssertionError('Must reject before native')):
            for value in (0,-1,float('inf'),float('nan')):
                with self.subTest(radius=value),self.assertRaises(ValueError):layouts.pie([1],radius=value)
            with self.assertRaises(ValueError):layouts.radar([1],2,2)
