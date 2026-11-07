"""Two reviewed native-font occupancy contracts, never reference-pixel waivers.

Fixed VChart 2.2.1 fixtures identify the inputs byte-for-byte. Source:
tools/oracle/node_modules/@visactor/vlayouts/es/wordcloud-shape/layout.js
initFillingWordsFontSize (380-410), filling.js filling/filling1Time (3-66),
VChart esm/series/word-cloud/base.js font-size scale, and fixed source scenes.
The corresponding port is chart/word_cloud.py:111-125 and
vlayouts/word_mask.py:357-450; it is not called to calculate expectations. The independent
diamond is its four radius=min(width//2,height//2) vertices. Direct public
Canvas alpha masks below deliberately do not call any py_vchart helper.
Reference strings/structure mismatches remain mismatches in the caller.
"""
from collections import Counter
import hashlib
from io import BytesIO
import json
import math

from PIL import Image


SPEC_SHA256={
    'wordCloud/default-filling':'56fb5935e1ab6b82091368934451b5d19d0f016e9492149e17ac64377e2530e5',
    'wordCloud/filled-mask':'a353efa0f100b564aae19042202ba2dd599e3ecf85959f93145c78315609c480',
}


def _alpha(text,size,x,y,width,height,*,family='Arial',weight='normal'):
    """Independent public API reference, local owner handles, no product import."""
    from py_skia_canvas import Canvas
    canvas=Canvas(width,height,{'textContrast':0});canvas.gpu=False
    context=canvas.getContext('2d')
    numeric_weight={'normal':400,'bold':700}.get(weight,weight)
    context.font=f'normal {numeric_weight} {size:g}px {family}'
    context.fontHinting=True
    context.textAlign='center';context.textBaseline='alphabetic'
    context.fillStyle='black';context.fillText(text,x,round(y))
    return bytes(context.getImageData(0,0,width,height).data)[3::4]


def _fill_sizes(spec,radius,word_count):
    options=spec.get('wordCloudShapeConfig',{})
    size=options.get('fillingInitialFontSize');delta=options.get('fillingDeltaFontSize')
    if not size or not delta:
        # Fixed geometric diamond's allowed raster area is source-observable.
        # Its mask includes every non-white antialiased edge pixel: the integer
        # polygon spans 2*r*r + 2*r cells (verified against the fixed source
        # mask grid rule, not fitted to the native word count).
        area=2*radius*(radius+1)
        lengths=[sum(1 if '\u4e00'<=c<='\u9fff' else .53 for c in str(row[spec['nameField']]))
                 for row in spec['data']['values']]
        mean=sum(v for v in lengths if v<=math.ceil(math.sqrt(area)/4))/word_count
        initial=math.sqrt(options.get('fillingRatio',.7)*area*.002/mean) if mean else 8
        size=int(initial);delta=initial*options.get('fillingDeltaFontSizeFactor',.2)
    result=[]
    for _ in range(options.get('fillingTimes',4)):
        result.append(float(size))
        size=max(size-delta if size>delta else delta,options.get('minFillFontSize',2))
    return result


def check(case_id,spec_bytes,scene,png,reference_scene):
    """Return JSON-only PASS/FAIL evidence; unknown input has no policy waiver.

    Glyph tests are actual PNG vs independent public fillText high-alpha masks.
    Tiny filling words are checked for visible ink individually and >=8 pixels
    jointly outside the primary glyph support, not eight pixels per 2px word.
    """
    digest=hashlib.sha256(spec_bytes).hexdigest()
    result={'schema':'py-vchart-native-wordcloud-policy/v1','caseId':case_id,
            'specSha256':digest,'status':'FAIL','errors':[],
            'policy':'reviewed-native-font-occupancy-v1','glyphs':[]}
    errors=result['errors']
    if case_id not in SPEC_SHA256 or digest!=SPEC_SHA256[case_id]:
        errors.append('No reviewed native-font policy for this case ID/spec SHA');return result
    try:
        spec=json.loads(spec_bytes)
        width,height=spec['width'],spec['height']
        image=Image.open(BytesIO(png));image.load()
        if image.size!=(width,height):raise ValueError('PNG dimensions changed')
        if image.format!='PNG':raise ValueError('Actual PNG required')
        pixels=list(image.convert('RGB').getdata())
        blue={i for i,(r,g,b) in enumerate(pixels) if b>r+8 and b>g+8 and b>20}
        # Source fixed padding=20 and diamond centered in its plot rectangle.
        px,py,pw,ph=20,20,width-40,height-40
        if list(scene['plot'])!=[px,py,pw,ph]:errors.append('Independent plot rectangle changed')
        cx,cy=px+pw//2,py+ph//2;radius=min(pw//2,ph//2)
        outside=[i for i in blue if abs(i%width+.5-cx)+abs(i//width+.5-cy)>radius+2]
        if outside:errors.append('Blue glyph pixels escape independent diamond +2px AA budget')
        if not blue:errors.append('No actual blue glyph pixels')
        rows=spec['data']['values'];field=spec['nameField'];value=spec['valueField']
        ordered=sorted(rows,key=lambda r:r[value],reverse=True)
        values=[r[value] for r in rows];lo,hi=min(values),max(values)
        lower,upper=spec['fontSizeRange'];minimum=spec.get('wordCloudShapeConfig',{}).get('minInitFontSize',10)
        expected=[]
        for row in ordered:
            t=(math.sqrt(row[value])-math.sqrt(lo))/(math.sqrt(hi)-math.sqrt(lo))
            expected.append((str(row[field]),max(minimum,int(lower+t*(upper-lower))),0))
        marks=scene['marks']['word']
        if len(marks)<=len(expected):errors.append('Missing primary or all decorative filling words')
        if len(marks)>10000:raise ValueError('Word budget exceeded')
        allowed_names={str(row[field]) for row in rows}
        allowed_fill=_fill_sizes(spec,radius,len(rows))
        primary_support=set();filler_support=set()
        for index,mark in enumerate(marks):
            if len(mark)!=5:raise ValueError('Word mark must be [text,x,y,size,rotation]')
            text,x,y,size,rotation=mark
            if not all(type(v) in (int,float) and math.isfinite(v) for v in (x,y,size,rotation)):
                raise ValueError('Non-finite word geometry')
            if text not in allowed_names:errors.append(f'Unknown input/filler word at {index}')
            if rotation!=0:errors.append(f'Undeclared rotation at {index}')
            if not (0<=x<width and 0<=y<height and 0<size<=max(upper,14)):
                raise ValueError('Word geometry outside budget')
            if index<len(expected):
                name,expected_size,expected_angle=expected[index]
                if (text,size,rotation)!=(name,expected_size,expected_angle):
                    errors.append(f'Primary input order/weight size/rotation changed at {index}')
                style=spec.get('word',{}).get('style',{})
            else:
                if not any(math.isclose(size,v,rel_tol=0,abs_tol=1e-9) for v in allowed_fill):
                    errors.append(f'Filling size not in independent source pass sequence at {index}')
                style=spec.get('fillingWord',{}).get('style',{})
            alpha=_alpha(str(text),size,x,y,width,height,family=style.get('fontFamily','Arial'),
                         weight=style.get('fontWeight','normal'))
            support={i for i,a in enumerate(alpha) if a>0}
            if index<len(expected):
                core={i for i,a in enumerate(alpha) if a>=224}
                coverage=len(core & blue)/len(core) if core else 0
                result['glyphs'].append({'index':index,'text':text,'corePixels':len(core),'blueCoverage':coverage})
                if len(core)<8 or coverage<.95:errors.append(f'Missing actual primary glyph core at {index}')
                primary_support.update(support)
            else:
                if not support.intersection(blue):errors.append(f'Missing actual filler glyph ink at {index}')
                filler_support.update(support)
        fill_blue=(filler_support-primary_support)&blue
        if len(fill_blue)<8:errors.append('Missing independent non-primary filling ink (minimum 8 pixels)')
        reference=reference_scene['marks']['word']
        result.update({'primaryExpected':[list(v) for v in expected],'fillingSizePasses':allowed_fill,
            'bluePixels':len(blue),'outsideDiamondPixels':len(outside),'nonPrimaryFillingBluePixels':len(fill_blue),
            'referenceWordCount':len(reference),'nativeWordCount':len(marks),
            'referenceWords':dict(Counter(m[0] for m in reference)),
            'nativeWords':dict(Counter(m[0] for m in marks)),
            'exactRepeatedWordMultiset':Counter(m[0] for m in reference)==Counter(m[0] for m in marks)})
    except Exception as exc:
        errors.append(type(exc).__name__+': '+str(exc))
    result['status']='PASS' if not errors else 'FAIL'
    return result
