from time import time as now

from scal2.graph_utils import *
from scal2.event_search_tree import EventSearchTree
from scal2.locale_man import tr as _
from scal2.core import debugMode
from scal2.event_lib import epsTm
from scal2 import ui


movableEventTypes = (
    'task',
    'lifeTime',
)

#########################################

boxLineWidth = 2
boxInnerAlpha = 0.1

boxMoveBorder = 10
boxMoveLineW = 0.5

editingBoxHelperLineWidth = 0.3 ## px


#boxColorSaturation = 1.0
#boxColorLightness = 0.3 ## for random colors


boxReverseGravity = False

boxSkipPixelLimit = 0.1 ## pixels

rotateBoxLabel = -1

#########################################

class Box:
    def __init__(
        self,
        t0,
        t1,
        odt,
        u0,
        du,
        text='',
        color=None,
        ids=None,
        lineW=2,
    ):
        self.t0 = t0
        self.t1 = t1
        self.odt = odt ## original delta t
        #self.mt = (t0+t1)/2.0 ## - timeMiddle ## FIXME
        #self.dt = (t1-t0)/2.0
        #if t1-t0 != odt:
        #    print 'Box, dt=%s, odt=%s'%(t1-t0, odt)
        self.u0 = u0
        self.du = du
        ####
        self.x = None
        self.w = None
        self.y = None
        self.h = None
        ####
        self.text = text
        if color is None:
            color = ui.textColor ## FIXME
        self.color = color
        self.ids = ids ## (groupId, eventId)
        self.lineW = lineW
        ####
        self.hasBorder = False
        self.tConflictBefore = []
    mt_cmp = lambda self, other: cmp(self.mt, other.mt)
    dt_cmp = lambda self, other: -cmp(self.dt, other.dt)
    #########
    def setPixelValues(self, timeStart, pixelPerSec, beforeBoxH, maxBoxH):
        self.x = (self.t0 - timeStart) * pixelPerSec
        self.w = (self.t1 - self.t0) * pixelPerSec
        self.y = beforeBoxH + maxBoxH * self.u0
        self.h = maxBoxH * self.du
    contains = lambda self, px, py: 0 <= px-self.x < self.w and 0 <= py-self.y < self.h

def makeIntervalGraph(boxes):
    g = Graph()
    n = len(boxes)
    g.add_vertices(n - g.vcount())
    g.vs['name'] = list(range(n))
    ####
    points = [] ## (time, isStart, boxIndex)
    for boxI, box in enumerate(boxes):
        points += [
            (box.t0, True, boxI),
            (box.t1, False, boxI),
        ]
    points.sort()
    openBoxes = set()
    for t, isStart, boxI in points:
        if isStart:
            g.add_edges([
                (boxI, oboxI) for oboxI in openBoxes
            ])
            openBoxes.add(boxI)
        else:
            openBoxes.remove(boxI)
    return g




def renderBoxesByGraph(boxes, graph, minColor, minU):
    colorCount = max(graph.vs['color']) - minColor + 1
    if colorCount < 1:
        return
    du = (1.0-minU) / colorCount
    min_vertices = graph.vs.select(color_eq=minColor) ## a VertexSeq
    for v in min_vertices:
        box = boxes[v['name']]
        box.u0 = minU if boxReverseGravity else 1 - minU - du
        box.du = du
    graph.delete_vertices(min_vertices)
    for sgraph in graph.decompose():
        renderBoxesByGraph(
            boxes,
            sgraph,
            minColor + 1,
            minU + du,
        )


def calcEventBoxes(
    timeStart,
    timeEnd,
    pixelPerSec,
    borderTm,
):
    boxesDict = {}
    #timeMiddle = (timeStart + timeEnd) / 2.0
    for groupIndex in range(len(ui.eventGroups)):
        group = ui.eventGroups.byIndex(groupIndex)
        if not group.enable:
            continue
        if not group.showInTimeLine:
            continue
        for t0, t1, eid, odt in group.occur.search(timeStart-borderTm, timeEnd+borderTm):
            pixBoxW = (t1-t0) * pixelPerSec
            if pixBoxW < boxSkipPixelLimit:
                continue
            #if not isinstance(eid, int):
            #    print '----- bad eid from search: %r'%eid
            #    continue
            event = group[eid]
            eventIndex = group.index(eid)
            if t0 <= timeStart and timeEnd <= t1:## Fills Range ## FIXME
                continue
            lineW = boxLineWidth
            if lineW >= 0.5*pixBoxW:
                lineW = 0
            box = Box(
                t0,
                t1,
                odt,
                0,
                1,
                text = event.getSummary(),
                color = group.color,## or event.color FIXME
                ids = (group.id, event.id) if pixBoxW > 0.5 else None,
                lineW = lineW,
            )
            box.hasBorder = (borderTm > 0 and event.name in movableEventTypes)
            boxValue = (group.id, t0, t1)
            try:
                boxesDict[boxValue].append(box)
            except KeyError:
                boxesDict[boxValue] = [box]
    ###
    if debugMode:
        t0 = now()
    boxes = []
    for bvalue, blist in boxesDict.iteritems():
        if len(blist) < 4:
            boxes += blist
        else:
            box = blist[0]
            box.text = _('%s events')%_(len(blist))
            box.ids = None
            #print 'len(blist)', len(blist)
            #print (box.t1 - box.t0), 'secs'
            boxes.append(box)
    del boxesDict
    #####
    if not boxes:
        return []
    #####
    if debugMode:
        t1 = now()
    ###
    graph = makeIntervalGraph(boxes)
    if debugMode:
        print('makeIntervalGraph: %e'%(now()-t1))
    ###
    #####
    colorGraph(graph)
    renderBoxesByGraph(boxes, graph, 0, 0)
    if debugMode:
        print('box placing time:  %e'%(now()-t0))
        print()
    return boxes





