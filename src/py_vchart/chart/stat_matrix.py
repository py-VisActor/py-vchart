"""Static matrix plots with categorical axes and shared statistical color ramps."""

from collections import Counter
from .._deps.vrender.text import glyph_run as text_at
from math import ceil,floor
from statistics import correlation
from .cartesian import check_keys
from .statplots import draw_legend
from .._deps.vscale.stat_colors import VIRIDIS, RDBU_R


def matrix_data(spec):
    kind = spec["type"]
    if kind=="confusionMatrix":
        records = spec["data"]
        if not isinstance(records,list):
            raise ValueError("confusionMatrix requires class records")
        names = spec.get("classOrder",list(dict.fromkeys(v for r in records for v in (r["actual"],r["predicted"]))))
        counts = Counter((r["actual"],r["predicted"]) for r in records)
        by_row = Counter(r["actual"] for r in records)
        by_col = Counter(r["predicted"] for r in records)
        mode = spec.get("normalization","none")
        cells = []
        for y in names:
            for x in names:
                div = {"actual":by_row[y],"predicted":by_col[x],"all":len(records),"none":1}[mode]
                cells.append((x,y,counts[y,x]/div if div else None))
        return names,names,cells
    names = spec["variables"]
    rows = spec["data"]["observations"]
    if kind=="missingValueMatrix":
        return names,[r["id"] for r in rows],[(x,r["id"],r["values"][x] is None) for r in rows for x in names]
    if spec.get("method","pearson")!="pearson":
        raise ValueError("correlationMatrix currently requires Pearson correlation")
    cells = []
    for i,y in enumerate(names):
        for j,x in enumerate(names):
            if spec.get("triangle")=="upper" and i>j or spec.get("triangle")=="lower" and i<j:
                continue
            pairs = [(r["values"][x],r["values"][y]) for r in rows if r["values"][x] is not None and r["values"][y] is not None]
            v = None
            if len(pairs)>=spec.get("minSamples",2):
                xs,ys = zip(*pairs)
                if len(set(xs))>1 and len(set(ys))>1:
                    v = correlation(xs,ys)
            cells.append((x,y,v))
    return names,names,cells


def ramp(colors,t):
    p = min(1,max(0,t))*(len(colors)-1)
    i = int(p)
    a,b = colors[i],colors[min(i+1,len(colors)-1)]
    rgb = [floor(int(a[j:j+2],16)*(1+i-p)+int(b[j:j+2],16)*(p-i)+.5) for j in (1,3,5)]
    return '#%02x%02x%02x'%tuple(rgb)


def colorbar(surface,rect,colors,ticks,lo,hi,title,percent):
    x,y,w,h = rect
    x += w+16
    length = min(h*.6,h-24)
    y += (h-length-24)/2
    text_at(surface,title,x,y+10.55,11,"#21252c")
    y += 24
    ctx = surface.ctx
    g = ctx.createLinearGradient(x,y+length,x,y)
    for i,color in enumerate(colors):
        g.addColorStop(i/(len(colors)-1),color)
    ctx.fillStyle = g
    ctx.fillRect(x,y,12,length)
    for t in ticks:
        cy = y+(hi-t)/(hi-lo)*length
        surface.line(x+12,cy,x+16,cy,"#21252c")
        label = f"{t*100:g}%" if percent else f"{t:g}".replace("-","−")
        text_at(surface,label,x+22,cy+4.5,11,"#21252c")


def render_matrix(spec,surface,width,height):
    kind = spec["type"]
    missing = kind=="missingValueMatrix"
    corr = kind=="correlationMatrix"
    fields = {"variables","method","minSamples","triangle"} if corr else {"variables"} if missing else {"classOrder","normalization"}
    check_keys(spec,fields|{"type","data","width","height"},kind)
    xs,ys,cells = matrix_data(spec)
    if not xs or not ys or not cells:
        raise ValueError("Matrix requires nonempty axes and data")
    titles = ("变量","观测") if missing else ("","") if corr else ("预测类别","实际类别")
    label_w = max(surface.measure(y) for y in ys)
    left = round((32 if corr else 56)+label_w) if not corr else round(28+label_w)
    if kind=="confusionMatrix":
        left = ceil(56+label_w)
    top = 52 if missing else 16
    bottom = height-60+(24 if corr else 0)
    w,h = width-16-left,bottom-top
    if not missing:
        w=h=min(w-96,h)
    rect = [left,top,w,h]
    col = {k:i for i,k in enumerate(xs)}
    row = {k:i for i,k in enumerate(ys)}
    dw,dh = w/len(xs),h/len(ys)
    colors = RDBU_R if corr else VIRIDIS
    lo = -1 if corr else 0
    percent = spec.get("normalization","none")!="none"
    hi = 1 if corr or percent or missing else max(1,max(v for _,_,v in cells if v is not None))
    surface.rect([0,0,width,height],"white")
    marks = {"0.cell":[]}
    if not missing:
        marks["1.cell"] = []
    for x,y,v in cells:
        a,b = left+dw*col[x],top+dh*row[y]
        box = [a,b,a+dw,b+dh]
        if missing:
            box[1],box[3] = floor(box[1]+.5),floor(box[3]+.5)
        color = "#bcc1cb" if v is None or missing and v else "#0173b2" if missing else ramp(colors,(v-lo)/(hi-lo))
        surface.rect(box,color)
        marks["1.cell" if v is None else "0.cell"].append(box)
        if not missing:
            surface.outline(box,"white")
            label = "NA" if v is None else f"{v:.2f}" if corr else f"{v*100:.1f}%" if percent else f"{v:g}"
            lum = sum(w*((int(color[i:i+2],16)/255+.055)/1.055)**2.4 for i,w in [(1,.2126),(3,.7152),(5,.0722)])
            ink = "#21252c" if v is None else "#fff" if lum<.175 else "#000"
            text_at(surface,label,a+dw/2,b+dh/2+4.5,11,ink,"center")
    if missing:
        for i in range(len(xs)):
            a = left+dw*i
            surface.line(a,top,a,top+h,"white")
        labels = list(dict.fromkeys("缺失" if v else "已观测" for _,_,v in cells))
        draw_legend(surface,width,labels,"rect",["#bcc1cb" if t=="缺失" else "#0173b2" for t in labels])
    else:
        ticks = [-1,-.5,0,.5,1] if corr else [0,.25,.5,.75,1] if percent else list(range(0,int(hi),ceil(hi/4)))+[hi]
        colorbar(surface,rect,colors,ticks,lo,hi,"Pearson r" if corr else "比例" if percent else "计数",percent)
    for x,i in col.items():
        px,py = left+(i+.5)*dw,top+h+8
        surface.labels.append(dict(text=str(x),x=px,y=py,align="center",baseline="top"))
        text_at(surface,x,px,py+11,12,"#89909d","center")
    for y,i in row.items():
        px,py = left-12,top+(i+.5)*dh
        surface.labels.append(dict(text=str(y),x=px,y=py,align="right",baseline="middle"))
        text_at(surface,y,px,py+5,12,"#89909d","right")
    if titles[0]:
        text_at(surface,titles[0],left+w/2,top+h+40.8,12,"#606773","center")
        ctx = surface.ctx
        ctx.save()
        ctx.translate(left-24-label_w,top+h/2)
        ctx.rotate(-1.5707963267948966)
        text_at(surface,titles[1],0,-3.2,12,"#606773","center")
        ctx.restore()
    return dict(plot=rect,labels=sorted(surface.labels,key=lambda r:(r["x"],r["y"])),axes=[
        dict(orient="bottom",domain=xs,range=[0,w]),dict(orient="left",domain=ys,range=[0,h])],marks=marks)
