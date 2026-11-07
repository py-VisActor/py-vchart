"""Single-series statistical specifications sharing the native Cartesian renderer."""

from .._deps.vrender.text import glyph_run
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import groupby
from math import ceil, exp, isfinite, log10, log2, pi, sqrt
from statistics import NormalDist, mean, median, pstdev, stdev, linear_regression

from .._deps.vscale import bands
from .cartesian import Axis, CartesianFrame, AXIS, GRID, check_keys, frame_scene
from .layout_helpers import field, number


@dataclass
class Plot:
    points: list
    mark: str
    titles: tuple
    category: bool = False
    xlim: tuple = ()
    ylim: tuple = ()
    step: str = ""
    reference: str = ""
    legend: tuple = ()


def density_curve(spec, rows, default_cut):
    values = [number(r,"value") for r in rows]
    estimation = spec.get("estimation",{})
    sampling = spec.get("sampling",{})
    check_keys(estimation,{"bandwidth","bandwidthAdjust"},"kdePlot.estimation")
    check_keys(sampling,{"points","cut"},"kdePlot.sampling")
    h = estimation.get("bandwidth","scott")
    if h == "scott":
        h = stdev(values)*len(values)**(-.2) if len(values)>1 else 0
    h *= estimation.get("bandwidthAdjust",1)
    n,cut = sampling.get("points",256),sampling.get("cut",default_cut)
    if not isinstance(h,(int,float)) or h<=0 or type(n) is not int or not 2<=n<=4096 or cut<0:
        raise ValueError("Invalid KDE bandwidth or sampling range")
    lo,hi = min(values)-cut*h,max(values)+cut*h
    if lo>=hi:
        raise ValueError("KDE requires a nonempty sampling interval")
    samples = [lo+(hi-lo)*i/(n-1) for i in range(n)]
    density = [(x,sum(exp(-.5*((x-v)/h)**2) for v in values)/(len(values)*h*sqrt(2*pi))) for x in samples]
    return density


def summary(spec, rows):
    kind = spec["type"]
    if kind == "learningCurve":
        mode = spec.get("input")
        values = []
        if mode=="folds":
            groups = {}
            for r in rows:
                key = (number(r,"trainSize"),field(r,"split"))
                groups.setdefault(key,[]).append(number(r,"score"))
            for (n,split),scores in groups.items():
                mid = mean(scores)
                spread = spec.get("spread",{})
                delta = pstdev(scores)*spread.get("multiplier",1) if spread is not False else None
                values.append((n,mid,split,mid-delta if delta is not None else None,mid+delta if delta is not None else None))
        elif mode=="summaries":
            values = [(number(r,"trainSize"),number(r,"score"),field(r,"split"),r.get("lower"),r.get("upper")) for r in rows]
        else:
            raise ValueError("learningCurve requires folds or summaries")
        values.sort(key=lambda p:p[0])
        return Plot(values,"groups",("训练样本数",spec["metric"]),legend=tuple(dict.fromkeys(p[2] for p in values)))
    if kind=="seasonalPlot":
        cycles,phases = spec["cycleOrder"],spec["phaseOrder"]
        vs = {(field(r,"cycle"),field(r,"phase")):number(r,"value") for r in rows}
        values = [(p,vs.get((c,p)),c,None,None) for c in cycles for p in phases]
        return Plot(values,"groups",("周期内位置","值"),True,legend=tuple(cycles))
    if kind == "timeSeriesPlot":
        if spec.get("input") not in ("observations","estimates"):
            raise ValueError("timeSeriesPlot requires observations or estimates")
        parsed = []
        for row in rows:
            dt = datetime.fromisoformat(field(row,"time").replace("Z","+00:00"))
            if dt.tzinfo is None or "lower" in row or "upper" in row:
                raise ValueError("timeSeriesPlot requires zoned times without interval bands")
            parsed.append((dt.timestamp()*1000,number(row,"value") if row["value"] is not None else None))
        parsed.sort(key=lambda p:p[0])
        if spec.get("input")=="observations" and spec.get("estimator") is not False:
            points = []
            for t,g in groupby(parsed,lambda p:p[0]):
                vs = [v for _,v in g if v is not None]
                if len(vs)>1 and spec.get("errorBar") is not False:
                    raise ValueError("timeSeriesPlot aggregated repeats require errorBar=false")
                points.append((t,(median(vs) if spec.get("estimator")=="median" else mean(vs)) if vs else None))
            parsed = points
        return Plot(parsed,"time",("时间（UTC）","值"))
    if kind == "autocorrelationPlot":
        values = [number(row,"value") for row in rows]
        n = len(values)
        lag = spec.get("maxLag",min(int(10*log10(n)),n-1,512))
        if not 1<=lag<n or type(lag) is not int:
            raise ValueError("Invalid autocorrelation maxLag")
        mid = mean(values)
        vs = [v-mid for v in values]
        variance = sum(v*v for v in vs)
        if not variance:
            raise ValueError("Autocorrelation requires varying observations")
        level = spec.get("confidence",{})
        z = NormalDist().inv_cdf((1+level.get("level",.95))/2) if level is not False else 0
        points,total = [],0
        for i in range(lag+1):
            corr = sum(a*b for a,b in zip(vs,vs[i:]))/variance
            band = z*sqrt((1+2*total)/n) if i else 0
            points.append((i,corr,band))
            if i:
                total += corr*corr
        return Plot(points,"acf",("滞后阶数","ACF"),reference="zero")
    if kind == "residualPlot":
        mode = spec.get("input")
        if mode == "observations":
            xy = [(number(r,"x"),number(r,"y")) for r in rows]
            xs,ys = zip(*xy)
            slope, intercept = linear_regression(xs,ys)
            points = [(x,y-(slope*x+intercept)) for x,y in xy]
            title = "x"
        elif mode in ("predictions","residuals"):
            title = "拟合值"
            points = [(number(r,"fittedValue"),number(r,"residual") if mode=="residuals"
                       else number(r,"actual")-number(r,"fittedValue")) for r in rows]
        else:
            raise ValueError("residualPlot requires a supported input")
        kind_label = {"raw":"原始残差","standardized":"标准化残差","studentized":"学生化残差"}
        return Plot(points,"scatter",(title,kind_label[spec.get("residualKind","raw")]),reference="zero")
    if kind == "kdePlot":
        density = density_curve(spec,rows,3)
        lo,hi = density[0][0],density[-1][0]
        return Plot(density,"line",("数值","概率密度"),xlim=(lo,hi))
    if kind == "pairedComparisonPlot":
        order = spec.get("categoryOrder")
        if not isinstance(order,list) or len(order)!=2 or order[0]==order[1]:
            raise ValueError("pairedComparisonPlot requires two ordered categories")
        values = [(field(r,"category"),number(r,"value"),field(r,"id")) for r in rows]
        return Plot(sorted(values,key=lambda p:order.index(p[0])),"paired",("","值"),True)
    if kind == "violinPlot":
        groups = {}
        for row in rows:
            groups.setdefault(field(row,"category"),[]).append(row)
        curves = {k:density_curve(spec,g,2) for k,g in groups.items()}
        peak = max(v for curve in curves.values() for _,v in curve)
        points = [(k,y,v/peak) for k,curve in curves.items() for y,v in curve]
        return Plot(points,"violin",("分组","数值"),True,ylim=(min(p[1] for p in points),max(p[1] for p in points)))
    if kind == "boxPlot":
        groups = {}
        for row in rows:
            groups.setdefault(field(row,"category"),[]).append(number(row,"value"))
        points = []
        factor = spec.get("whiskers",{}).get("iqrMultiplier",1.5)
        for category,vs in groups.items():
            vs.sort()
            def quantile(p):
                i = (len(vs)-1)*p
                return vs[int(i)] + (i-int(i))*(vs[ceil(i)]-vs[int(i)])
            q1,med,q3 = (quantile(p) for p in (.25,.5,.75))
            reach = factor*(q3-q1)
            inside = [v for v in vs if q1-reach<=v<=q3+reach]
            outside = [v for v in vs if v<q1-reach or v>q3+reach]
            points.append((category,med,[min([q1,*inside]),q1,med,q3,max([q3,*inside])],outside))
        return Plot(points,"box",("分组","数值"),True)
    if kind == "countPlot":
        counts = Counter(field(r,"category") for r in rows)
        proportion = spec.get("statistic","count") == "proportion"
        return Plot([(k,v/len(rows) if proportion else v) for k,v in counts.items()],
                    "bar",("类别","全表比例" if proportion else "计数"),True,ylim=(0,1) if proportion else ())
    if kind == "screePlot":
        return Plot([(str(field(r,"component")),number(r,"explainedVarianceRatio")) for r in rows],
                    "bar",("成分","解释方差比率"),True,ylim=(0,1))
    if kind in ("scatterPlot","embeddingPlot"):
        titles = ["x","y"]
        if kind == "embeddingPlot":
            if spec.get("method") not in ("pca","tsne","umap"):
                raise ValueError("embeddingPlot requires a supported method")
            for i,k in enumerate(titles.copy()):
                dim = spec.get("dimensions",{}).get(k,{})
                titles[i] = dim.get("name",f"{spec['method'].upper()} {i+1}")
                if "explainedVarianceRatio" in dim:
                    titles[i] += f" ({dim['explainedVarianceRatio']*100:.1f}%)"
        return Plot([(number(r,"x"),number(r,"y")) for r in rows],"scatter",titles)
    if kind == "stripPlot":
        return Plot([(field(r,"category"),number(r,"value")) for r in rows],"scatter",("类别","值"),True)
    if kind in ("ecdfPlot","qqPlot","histogram"):
        values = sorted(number(r,"value") for r in rows)
        lo, hi = values[0], values[-1]
        if kind == "qqPlot":
            config = spec.get("distribution",{})
            normal = NormalDist(config.get("mean",0),config.get("standardDeviation",1))
            return Plot([(normal.inv_cdf(i/(len(values)+1)),v) for i,v in enumerate(values,1)],
                        "scatter",("正态理论分位数","样本分位数"))
        if kind == "ecdfPlot":
            margin = (hi-lo)*.05 if hi>lo else max(.5,abs(lo)*.05)
            limits = (lo-margin,hi+margin)
            points = [(limits[0],0),*((v,bisect_right(values,v)/len(values)) for v in sorted(set(values))),(limits[1],1)]
            return Plot(points,"line",("数值","累计概率"),xlim=limits,ylim=(0,1),step="after")
        n = spec.get("binning",{}).get("binCount",min(200,ceil(log2(len(values))+1)))
        if type(n) is not int or not 1 <= n <= 1000:
            raise ValueError("Invalid histogram binCount")
        if hi == lo:
            half = max(1,abs(lo))/2
            lo,hi,n = lo-half,hi+half,1
        edges = [lo+(hi-lo)*i/n for i in range(n)]+[hi]
        counts = Counter(min(n-1,bisect_right(edges,v)-1) for v in values)
        statistic = spec.get("statistic","count")
        divisor = {"count":1,"proportion":len(values),"density":len(values)*(hi-lo)/n}[statistic]
        return Plot([(a,counts[i]/divisor,b) for i,(a,b) in enumerate(zip(edges,edges[1:]))],
                    "bins",("数值",{"count":"数量","proportion":"比例","density":"概率密度"}[statistic]),xlim=(lo,hi))
    if kind == "calibrationCurve":
        n = spec.get("binning",{}).get("binCount",5)
        if type(n) is not int or not 1 <= n <= 1000:
            raise ValueError("Invalid calibration binCount")
        edges = [i/n for i in range(1,n)]
        groups = [[] for _ in range(n)]
        for r in rows:
            p = number(r,"probability")
            if not 0 <= p <= 1 or type(r.get("actual")) is not bool:
                raise ValueError("calibration requires probabilities and boolean outcomes")
            groups[bisect_left(edges,p)].append((p,r["actual"]))
        points = [(mean(x),mean(y)) for g in groups if g for x,y in [zip(*g)]]
        return Plot(points,"curve",("平均预测概率","实际正例比例"),xlim=(0,1),ylim=(0,1),reference="diagonal")
    roc = kind == "rocCurve"
    scores = [(number(r,"score"),field(r,"actual")) for r in rows]
    if any(type(label) is not bool for _,label in scores):
        raise ValueError("classification requires boolean outcomes")
    positives = sum(label for _,label in scores)
    negatives = len(scores)-positives
    if not positives or not negatives:
        raise ValueError("classification requires both classes")
    points = [(0,0 if roc else 1)]
    tp = fp = 0
    for _, group in groupby(sorted(scores,reverse=True),lambda p:p[0]):
        for _,label in group:
            tp += label
            fp += not label
        points.append((fp/negatives,tp/positives) if roc else (tp/positives,tp/(tp+fp)))
    return Plot(points,"curve",("假阳性率 FPR","真阳性率 TPR") if roc else ("召回率","精确率"),
                xlim=(0,1),ylim=(0,1),reference="diagonal" if roc else "",step="" if roc else "before")


OPTIONS = {
    "learningCurve":{"input","metric","spread","interval"}, "seasonalPlot":{"phaseOrder","cycleOrder"},
    "timeSeriesPlot":{"input","estimator","errorBar"}, "autocorrelationPlot":{"confidence","maxLag"},
    "residualPlot":{"input","residualKind"}, "pairedComparisonPlot":{"categoryOrder"},
    "kdePlot":{"estimation","sampling"}, "violinPlot":{"estimation","sampling"}, "boxPlot":{"whiskers"},
    "countPlot":{"statistic"}, "screePlot":set(), "scatterPlot":set(), "embeddingPlot":{"method","dimensions"},
    "qqPlot":{"distribution"}, "stripPlot":set(), "ecdfPlot":set(), "histogram":{"binning","statistic"},
    "calibrationCurve":{"binning"}, "rocCurve":set(), "precisionRecallCurve":set()
}


def axis_for(side, values, category, limits, zero):
    if category:
        return Axis.make(side,"band",values,{},"statplot")
    if limits:
        return Axis.make(side,"linear",values,dict(zip(("min","max"),limits)),"statplot")
    lo,hi = min(values),max(values)
    if zero:
        lo,hi = min(lo,0),max(hi,0)
    if lo == hi:
        lo,hi = min(0,lo),max(1,hi)
    from .._deps.vscale import numeric_axis
    # Nice the data extent without forcing a zero baseline for scatter axes.
    domain,ticks = numeric_axis([lo,hi],{},path="statplot", include_zero=False)
    return Axis(side,"linear",domain,ticks,True)


STAT_COLORS = ("#0173b2","#de8f05","#029e73","#d55e00","#cc78bc","#ca9161","#fbafe4","#949494","#ece133","#56b4e9")


def draw_legend(surface,width,labels,shape,colors=STAT_COLORS,*,center_y=25.8):
    sizes = [surface.measure(label) for label in labels]
    # Ten-pixel swatch, six-pixel text gap and fourteen pixels between items.
    start = (width-sum(sizes)-30*len(labels)+14)/2
    for i,(label,size) in enumerate(zip(labels,sizes)):
        color = colors[i%len(colors)]
        if shape=="circle":
            surface.circle(start+5,center_y,10,color,None,0)
        else:
            half = 2.5 if shape=="rect" else 5
            surface.rect([start,center_y-half,start+10,center_y+half],color)
        ctx = surface.ctx
        ctx.save()
        ctx.fillStyle = "#606773"
        ctx.fontHinting = True
        ctx.textAlign = "left"
        ctx.textBaseline = "alphabetic"
        ctx.fillText(label,start+16,center_y+5)
        ctx.restore()
        start += 30+size


def statistical_frame(surface, width, height, plot):
    x = axis_for("bottom",[p[0] for p in plot.points],plot.category,plot.xlim,False)
    if plot.step == "after":
        inner = axis_for("bottom",[p[0] for p in plot.points[1:-1]],False,(),False)
        x.ticks = [t for t in inner.ticks if x.domain[0] <= t <= x.domain[1]]
    if plot.mark=="acf":
        xmax = plot.points[-1][0]+(.5 if plot.points[-1][2] else 0)
        x = axis_for("bottom",[0,xmax],False,(),True)
    ys = [p[1] for p in plot.points if p[1] is not None]
    if not ys:
        raise ValueError("Statistical plot requires measured values")
    if plot.mark=="groups":
        ys.extend(v for p in plot.points for v in p[3:] if v is not None)
    if plot.mark=="acf":
        ys.extend(v for _,_,c in plot.points for v in (-c,c))
    if plot.mark=="box":
        ys = [v for p in plot.points for v in p[2]+p[3]]
    y = axis_for("left",ys,False,plot.ylim,plot.mark in ("bar","bins") or plot.mark=="line" and not plot.ylim)
    left = round(56 + max(surface.measure(y.label(t)) for t in y.ticks))
    bottom = height-16-(48 if plot.category else 44)
    if not plot.titles[0]:
        bottom += 24
    right = 16
    time_axis = plot.mark == "time"
    if time_axis:
        bottom -= 4
        right += ceil(surface.measure("0000-00-00")/2)
    top = 52 if plot.legend else 16
    w,h = width-right-left,bottom-top
    if min(w,h)<=0:
        raise ValueError("Statistical canvas too small")
    frame = CartesianFrame((left,top,w,h),False,{"bottom":x,"left":y},
                           {"bottom":bands(x.domain,w)} if plot.category else {})
    surface.rect((0,0,width,height),"white")
    if plot.legend:
        draw_legend(surface,width,plot.legend,"square" if any(p[3] is not None for p in plot.points) else "circle")
    for tick in y.ticks:
        pos = frame.coordinate("left",tick)
        surface.line(left,pos,left+w,pos,GRID)
        base = "top" if tick==y.domain[1] else "bottom" if tick==y.domain[0] else "middle"
        surface.label(y.label(tick),left-12,pos,"right",base) if base=="middle" else surface.label(
            y.label(tick),left-12,pos,"right",base,line_height=12)
    if plot.category or time_axis:
        surface.line(left,bottom,left+w,bottom,AXIS)
    for tick in x.ticks:
        pos = frame.coordinate("bottom",tick)
        if plot.category or time_axis:
            surface.line(pos,bottom,pos,bottom+4,AXIS)
        align = "center"
        if not (plot.category or time_axis):
            align = "left" if tick==x.domain[0] else "right" if tick==x.domain[1] else "center"
        label = datetime.fromtimestamp(tick/1000,timezone.utc).date().isoformat() if time_axis else x.label(tick)
        surface.label(label,pos,bottom+(12 if plot.category or time_axis else 8),align,"top",line_height=12)
    ctx = surface.ctx
    ctx.save()
    ctx.fontHinting = True
    ctx.fillStyle = "#606773"
    ctx.textAlign = "left"
    ctx.textBaseline = "alphabetic"
    glyph_run(surface,plot.titles[0],left+w/2,bottom+(32 if plot.category or time_axis else 28)+12.8,12,"#606773","center")
    ctx.translate(left-12-max(surface.measure(y.label(t)) for t in y.ticks)-12,top+h/2)
    ctx.rotate(-1.5707963267948966)
    if plot.titles[1].isascii():
        ctx.fillText(plot.titles[1],-surface.measure(plot.titles[1])/2,-3.2)
    else:
        glyph_run(surface,plot.titles[1],0,-2.8,12,"#606773","center")
    ctx.restore()
    return frame


def render_stat(spec,surface,width,height):
    kind = spec["type"]
    check_keys(spec,{"type","data","width","height"}|OPTIONS[kind],kind)
    rows = spec.get("data")
    if not isinstance(rows,list) or not rows or not all(isinstance(r,dict) and "series" not in r for r in rows):
        raise ValueError(f"{kind} requires a nonempty single series of records")
    if "binning" in spec:
        check_keys(spec["binning"],{"binCount"},kind+".binning")
    plot = summary(spec,rows)
    frame = statistical_frame(surface,width,height,plot)
    color = "#0173b2"
    points = [frame.point(*p[:2]) for p in plot.points if p[1] is not None]
    marks = {}
    if plot.mark in ("bar","bins"):
        boxes = []
        for p,(x,y) in zip(plot.points,points):
            if plot.category:
                half = frame.positions[p[0]][1]/2
                a,b = x-half,x+half
            else:
                a,b = x,frame.coordinate("bottom",p[2])
            box = [a,min(y,frame.value_pixel(0)),b,max(y,frame.value_pixel(0))]
            if plot.mark == "bins":
                surface.ctx.globalAlpha = .6
            surface.rect(box,color)
            surface.ctx.globalAlpha = 1
            if plot.mark == "bins":
                surface.outline(box,"white")
            boxes.append(box)
        marks["0.bar"] = boxes
    if plot.mark in ("line","curve"):
        path = []
        for x,y in points:
            if path and plot.step:
                path.append([x,path[-1][1]] if plot.step=="after" else [path[-1][0],y])
            path.append([x,y])
        surface.polyline(path,color,2)
        marks["0.line"] = points
    if plot.mark == "groups":
        has_bands = any(p[3] is not None for p in plot.points)
        i = int(has_bands)
        if has_bands:
            marks["0.area"] = []
        marks[f"{i}.line"] = []
        marks[f"{i}.point"] = []
        for j,group in enumerate(plot.legend):
            color = STAT_COLORS[j%len(STAT_COLORS)]
            records = [p for p in plot.points if p[2]==group]
            if has_bands:
                area = [[*frame.point(x,lo),*frame.point(x,hi)] for x,_,_,lo,hi in records if lo is not None]
                surface.polygon([p[:2] for p in area]+[p[2:] for p in reversed(area)],color,.18)
                marks["0.area"].extend(area)
            for defined,run in groupby(records,lambda p:p[1] is not None):
                if not defined:
                    continue
                pts = [frame.point(*p[:2]) for p in run]
                surface.polyline(pts,color,2)
                for pt in pts:
                    surface.circle(*pt,5,color,"white",1)
                marks[f"{i}.line"].extend(pts)
                marks[f"{i}.point"].extend(pts)
        marks[f"{i}.point"] = points
    if plot.mark == "time":
        segment = []
        for t,v in plot.points:
            if v is not None:
                segment.append(frame.point(t,v))
            else:
                surface.polyline(segment,color,2)
                segment = []
        surface.polyline(segment,color,2)
        for pt in points:
            surface.circle(*pt,5,color,"white",1)
        marks = {"0.line":points,"0.point":points}
    if plot.mark == "acf":
        i = 0
        if plot.points[-1][2]:
            series = [(k,b) for k,_,b in plot.points[1:]]
            series = [(series[0][0]-.5,series[0][1]),*series,(series[-1][0]+.5,series[-1][1])]
            area = [[*frame.point(k,-b),*frame.point(k,b)] for k,b in series]
            surface.polygon([p[:2] for p in area]+[p[2:] for p in reversed(area)],color,.18)
            marks["0.area"] = area
            i += 1
        stems = []
        for (k,v,_),pt in zip(plot.points,points):
            segment = [frame.point(k,0),pt]
            surface.polyline(segment,color,1.5)
            stems.extend(segment)
        for pt in points:
            surface.circle(*pt,7,color,None,0,.8)
        marks[f"{i}.line"] = stems
        marks[f"{i+1}.point"] = points
    if plot.mark == "paired":
        ids = {}
        for p,pt in zip(plot.points,points):
            ids.setdefault(p[2],[]).append(pt)
        marks["0.line"] = []
        for segment in ids.values():
            surface.ctx.globalAlpha = .5
            surface.polyline(segment,"#606773",1)
            surface.ctx.globalAlpha = 1
            marks["0.line"].extend(segment)
        colors = ["#0173b2","#de8f05","#029e73","#d55e00","#cc78bc","#ca9161","#fbafe4","#949494","#ece133","#56b4e9"]
        for x,y in points:
            surface.circle(x,y,7,colors[len(ids)%len(colors)],None,0,.8)
        marks["1.point"] = points
    if plot.mark == "violin":
        marks["0.area"] = []
        for category,group in groupby(plot.points,lambda p:p[0]):
            path = []
            for _,value,density in group:
                x,y = frame.point(category,value)
                offset = frame.positions[category][1]*.42*density
                path.append([x-offset,y,x+offset,y])
            surface.polygon([p[:2] for p in path]+[p[2:] for p in reversed(path)],color,.75)
            marks["0.area"].extend(path)
    if plot.mark == "box":
        marks = {"0.boxPlot":[],"0.outlier":[]}
        for key,_,stats,outliers in plot.points:
            x = frame.coordinate("bottom",key)
            breadth = frame.positions[key][1]*.55
            low,q1,med,q3,high = [frame.value_pixel(v) for v in stats]
            marks["0.boxPlot"].append([x,breadth,low,q1,med,q3,high])
            surface.line(x,low,x,high,color)
            box = [x-breadth/2,q3,x+breadth/2,q1]
            surface.rect(box,"white")
            surface.outline(box,color)
            for y in (low,med,high):
                surface.line(box[0],y,box[2],y,color)
            for v in outliers:
                pt = frame.point(key,v)
                surface.circle(*pt,10,color,None,0)
                marks["0.outlier"].append(pt)
    if plot.mark in ("scatter","curve"):
        for x,y in points:
            if plot.mark=="scatter":
                surface.circle(x,y,7,color,"white",1,1) if kind=="stripPlot" else surface.circle(x,y,7,color,None,0,.8)
            else:
                surface.circle(x,y,5,color,"white",1)
        marks["0.point"] = points
    if plot.reference:
        surface.ctx.save()
        surface.ctx.setLineDash([4,4])
        if plot.reference == "zero":
            a,b = frame.axes["bottom"].domain
            surface.line(*frame.point(a,0),*frame.point(b,0),"#606773")
        else:
            surface.line(*frame.point(0,0),*frame.point(1,1),"#606773")
        surface.ctx.restore()
    return frame_scene(surface,frame) | {"marks":marks}
