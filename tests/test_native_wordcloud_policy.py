"""Actual PNG positive/negative controls for two byte-locked native contracts.

The unchanged reference suite retains exact upstream decorative repeat counts.
These tests never use a product text helper to generate their glyph reference.
"""
from copy import deepcopy
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
specification=importlib.util.spec_from_file_location('native_wordcloud_policy',ROOT/'tools/native_wordcloud_policy.py')
POLICY=importlib.util.module_from_spec(specification);specification.loader.exec_module(POLICY)


def encode(image):
    stream=BytesIO();image.save(stream,format='PNG');return stream.getvalue()


class NativeWordcloudPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from py_vchart import VChart
        cls.cases={}
        for key in POLICY.SPEC_SHA256:
            directory=ROOT/'tests/cases'/key
            raw=(directory/'spec.json').read_bytes()
            reference=json.loads((directory/'expected.scene.json').read_text('utf8'))
            chart=VChart(json.loads(raw),backend='cpu',text_engine='canvas',maps={},svgs={}).render()
            cls.cases[key]=(raw,chart.scene,chart.to_png(),reference)

    def check(self,key,*,scene=None,png=None,raw=None):
        original,actual,image,reference=self.cases[key]
        return POLICY.check(key,original if raw is None else raw,
                            actual if scene is None else scene,image if png is None else png,reference)

    def test_two_reviewed_cases_have_actual_primary_and_filling_pixels(self):
        for key in self.cases:
            with self.subTest(case=key):
                result=self.check(key)
                self.assertEqual(result['status'],'PASS',result)
                self.assertEqual([x[1] for x in result['primaryExpected']],[32,25,18])
                self.assertGreaterEqual(result['nonPrimaryFillingBluePixels'],8)
                self.assertTrue(all(g['blueCoverage']>=.95 and g['corePixels']>=8 for g in result['glyphs']))
                self.assertEqual(result['outsideDiamondPixels'],0)
                # Actual mismatching repeat counts remain visible evidence.
                self.assertIn('exactRepeatedWordMultiset',result)

    def test_only_exact_reviewed_spec_bytes_and_ids_are_eligible(self):
        key=next(iter(self.cases));raw,scene,png,reference=self.cases[key]
        self.assertEqual(self.check(key,raw=raw+b' ')['status'],'FAIL')
        self.assertEqual(POLICY.check('wordCloud/weighted',raw,scene,png,reference)['status'],'FAIL')

    def test_missing_primary_word_metadata_is_rejected(self):
        for key,(_,scene,_,_) in self.cases.items():
            faulty=deepcopy(scene);del faulty['marks']['word'][0]
            self.assertEqual(self.check(key,scene=faulty)['status'],'FAIL')

    def test_unknown_filling_text_is_rejected(self):
        key=next(iter(self.cases));faulty=deepcopy(self.cases[key][1])
        faulty['marks']['word'][3][0]='NotAnInputWord'
        self.assertEqual(self.check(key,scene=faulty)['status'],'FAIL')

    def test_wrong_filling_size_or_primary_weight_is_rejected(self):
        key=next(iter(self.cases))
        for index,size in ((0,18),(3,17)):
            faulty=deepcopy(self.cases[key][1]);faulty['marks']['word'][index][3]=size
            self.assertEqual(self.check(key,scene=faulty)['status'],'FAIL')

    def test_black_diamond_without_glyphs_cannot_pass(self):
        for key,(_,_,png,_) in self.cases.items():
            image=Image.open(BytesIO(png)).convert('RGB')
            image.putdata([(0,0,0) if b>r+8 and b>g+8 and b>20 else (r,g,b)
                           for r,g,b in image.getdata()])
            result=self.check(key,png=encode(image))
            self.assertEqual(result['status'],'FAIL')
            self.assertTrue(any('primary glyph core' in e for e in result['errors']),result)

    def test_lost_primary_pixels_with_unchanged_scene_are_rejected(self):
        key=next(iter(self.cases));_,scene,png,_=self.cases[key]
        text,x,y,size,angle=scene['marks']['word'][0]
        image=Image.open(BytesIO(png)).convert('RGB')
        # Erase a fixed central stripe across the source 32px primary body;
        # scene text/name/size are untouched and all other picture data stays.
        for py in range(round(y)-26,round(y)):
            for px in range(round(x)-12,round(x)+12):image.putpixel((px,py),(0,0,0))
        self.assertEqual(self.check(key,png=encode(image))['status'],'FAIL')

    def test_actual_blue_pixels_outside_diamond_are_rejected(self):
        key=next(iter(self.cases));image=Image.open(BytesIO(self.cases[key][2])).convert('RGB')
        image.putpixel((1,1),(22,100,255))
        result=self.check(key,png=encode(image))
        self.assertEqual(result['status'],'FAIL');self.assertEqual(result['outsideDiamondPixels'],1)

    def test_declared_fillers_with_only_actual_primary_ink_are_rejected(self):
        from py_skia_canvas import Canvas
        key=next(iter(self.cases));raw,scene,_,_=self.cases[key];spec=json.loads(raw)
        w,h=spec['width'],spec['height'];canvas=Canvas(w,h,{'textContrast':0});canvas.gpu=False
        ctx=canvas.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,w,h)
        cx,cy=w//2,h//2;r=min((w-40)//2,(h-40)//2)
        ctx.beginPath();ctx.moveTo(cx,cy-r);ctx.lineTo(cx+r,cy);ctx.lineTo(cx,cy+r);ctx.lineTo(cx-r,cy)
        ctx.closePath();ctx.fillStyle='black';ctx.fill()
        ctx.textAlign='center';ctx.textBaseline='alphabetic';ctx.fontHinting=True
        for text,x,y,size,angle in scene['marks']['word'][:3]:
            ctx.font=f'normal 400 {size:g}px Arial';ctx.fillStyle='#1664ff';ctx.fillText(text,x,round(y))
        result=self.check(key,png=canvas.toBufferSync('png'))
        self.assertEqual(result['status'],'FAIL',result)
        self.assertTrue(all(g['blueCoverage']>=.95 for g in result['glyphs']),result)
        self.assertLess(result['nonPrimaryFillingBluePixels'],8)

    def test_empty_independent_font_mask_is_failure_not_missing_font_waiver(self):
        key=next(iter(self.cases));spec=json.loads(self.cases[key][0])
        with patch.object(POLICY,'_alpha',return_value=bytes(spec['width']*spec['height'])):
            result=self.check(key)
        self.assertEqual(result['status'],'FAIL')
        self.assertTrue(any('primary glyph core' in e for e in result['errors']))


if __name__=='__main__':unittest.main()
