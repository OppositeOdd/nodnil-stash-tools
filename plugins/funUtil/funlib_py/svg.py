from typing import List, Optional, Dict, Any, Callable, Union, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from . import FunAction, Funscript
    from .types import ms

from . import FunAction
from .converter import channelNameToAxis, speedToHexCached
from .manipulations import actionsToLines, actionsToZigzag, mergeLinesSpeed, toStats
from .misc import lerp


class SvgOptions:
    """Configuration options for SVG rendering"""
    def __init__(self, **kwargs):
        # rendering
        self.lineWidth: float = kwargs.get('lineWidth', 0.5)
        self.title: Optional[Union[Callable[['Funscript', str], str], str, None]] = kwargs.get('title', None)
        self.icon: Optional[Union[Callable[['Funscript', str], str], str, None]] = kwargs.get('icon', None)
        self.font: str = kwargs.get('font', 'Arial, sans-serif')
        self.iconFont: str = kwargs.get('iconFont', 'Consolas, monospace')
        self.halo: bool = kwargs.get('halo', True)
        self.solidTitleBackground: bool = kwargs.get('solidTitleBackground', False)
        self.graphOpacity: float = kwargs.get('graphOpacity', 0.2)
        self.titleOpacity: float = kwargs.get('titleOpacity', 0.7)
        self.mergeLimit: float = kwargs.get('mergeLimit', 500)
        self.normalize: bool = kwargs.get('normalize', True)
        self.titleEllipsis: bool = kwargs.get('titleEllipsis', True)
        self.titleSeparateLine: Union[bool, str] = kwargs.get('titleSeparateLine', 'auto')

        # sizing
        self.width: float = kwargs.get('width', 690)
        self.height: float = kwargs.get('height', 52)
        self.titleHeight: float = kwargs.get('titleHeight', 20)
        self.titleSpacing: float = kwargs.get('titleSpacing', 0)
        self.iconWidth: float = kwargs.get('iconWidth', 46)
        self.iconSpacing: float = kwargs.get('iconSpacing', 0)
        self.durationMs: 'ms' = kwargs.get('durationMs', 0)
        self.showChapters: bool = kwargs.get('showChapters', False)
        self.chapterHeight: float = kwargs.get('chapterHeight', 10)


# y between one axis G and the next
SPACING_BETWEEN_AXES = 0
# y between one funscript and the next
SPACING_BETWEEN_FUNSCRIPTS = 4
# padding around the svg, reduces width and adds to y
SVG_PADDING = 0

HANDY_ICON = '☞'

svgDefaultOptions = SvgOptions(
    title=None,
    icon=None,
    lineWidth=0.5,
    font='Arial, sans-serif',
    iconFont='Consolas, monospace',
    halo=True,
    solidTitleBackground=False,
    graphOpacity=0.2,
    titleOpacity=0.7,
    mergeLimit=500,
    normalize=True,
    titleEllipsis=True,
    titleSeparateLine='auto',
    width=690,
    height=52,
    titleHeight=20,
    titleSpacing=0,
    iconWidth=46,
    iconSpacing=0,
    durationMs=0,
    showChapters=False,
    chapterHeight=10,
)

isBrowser = False


def textToSvgLength(text: str, font: str) -> float:
    if not isBrowser:
        return 0
    # In browser environment, would use canvas measureText
    return 0


def textToSvgText(text: str) -> str:
    """
    Escapes text for safe usage in SVG by converting special characters to HTML entities.
    Works in both browser and non-browser environments without DOM manipulation.
    """
    if not text:
        return text

    # Define HTML entity mappings for characters that need escaping in SVG
    entityMap = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
        '/': '&#x2F;',
    }

    result = ''
    for char in text:
        result += entityMap.get(char, char)
    return result


def truncateTextWithEllipsis(text: str, maxWidth: float, font: str) -> str:
    """
    Truncates text with ellipsis to fit within the specified width.
    Uses a simple while loop to iteratively remove characters until the text fits.
    """
    if not text:
        return text
    if textToSvgLength(text, font) <= maxWidth:
        return text

    while text and textToSvgLength(text + '…', font) > maxWidth:
        text = text[:-1]
    return text + '…'


def toSvgLines(
    script: 'Funscript',
    ops: SvgOptions,
    ctx: Dict[str, float],
) -> List[str]:
    """
    Converts a Funscript to SVG path elements representing the motion lines.
    Each line is colored based on speed and positioned within the specified dimensions.
    """
    lineWidth = ops.lineWidth
    mergeLimit = ops.mergeLimit
    durationMs = ops.durationMs
    width = ctx['width']
    height = ctx['height']

    def round_val(x: float) -> float:
        return round(x, 2)

    def lineToStroke(a: 'FunAction', b: 'FunAction') -> str:
        def at(action: 'FunAction') -> float:
            return round_val((action.at / durationMs * (width - 2 * lineWidth)) + lineWidth)

        def pos(action: 'FunAction') -> float:
            return round_val((100 - action.pos) * (height - 2 * lineWidth) / 100 + lineWidth)

        return f"M {at(a)} {pos(a)} L {at(b)} {pos(b)}"

    lines = actionsToLines(script.actions)
    mergeLinesSpeed(lines, mergeLimit)

    lines.sort(key=lambda x: x[2])
    # global styles: stroke-width="${w}" fill="none" stroke-linecap="round"
    return [f'<path d="{lineToStroke(a, b)}" stroke="{speedToHexCached(speed)}"></path>'
            for a, b, speed in lines]


def toSvgBackgroundGradient(
    script: 'Funscript',
    ops: SvgOptions,
    linearGradientId: str,
) -> str:
    """
    Creates an SVG linear gradient definition based on a Funscript's speed variations over time.
    The gradient represents speed changes throughout the script duration with color transitions.
    """
    durationMs = ops.durationMs

    def round_val(x: float) -> float:
        return round(x, 2)

    lines = []
    for e in actionsToLines(actionsToZigzag(script.actions)):
        a, b, s = e[0], e[1], e[2]
        length = b.at - a.at
        if length <= 0:
            continue
        if length < 2000:
            lines.append(e)
            continue
        # split into len/1000-1 periods
        N = int((length - 500) / 1000)
        for i in range(N):
            new_a = FunAction({'at': lerp(a.at, b.at, i / N), 'pos': lerp(a.pos, b.pos, i / N)})
            new_b = FunAction({'at': lerp(a.at, b.at, (i + 1) / N), 'pos': lerp(a.pos, b.pos, (i + 1) / N)})
            lines.append([new_a, new_b, s])

        # merge lines so they are at least 500 long
    i = 0
    while i < len(lines) - 1:
        a, b, ab = lines[i][0], lines[i][1], lines[i][2]
        c, d, cd = lines[i + 1][0], lines[i + 1][1], lines[i + 1][2]
        if d.at - a.at < 1000:
            speed = (ab * (b.at - a.at) + cd * (d.at - c.at)) / ((b.at - a.at) + (d.at - c.at))
            lines[i:i + 2] = [[a, d, speed]]
            i -= 1
        i += 1

    stops = []
    for i, e in enumerate(lines):
        p = lines[i - 1] if i > 0 else None
        n = lines[i + 1] if i < len(lines) - 1 else None
        if not p or not n:
            stops.append(e)
            continue
        if p[2] == e[2] == n[2]:
            continue
        stops.append(e)

    stops = [{'at': (e[0].at + e[1].at) / 2, 'speed': e[2]} for e in stops]

    # add start, first, last, end stops
    if lines:
        first = lines[0]
        last = lines[-1]
        stops.insert(0, {'at': first[0].at, 'speed': first[2]})
        if first[0].at > 100:
            stops.insert(0, {'at': first[0].at - 100, 'speed': 0})
        stops.append({'at': last[1].at, 'speed': last[2]})
        if last[1].at < durationMs - 100:
            stops.append({'at': last[1].at + 100, 'speed': 0})

    # remove duplicates
    filtered_stops = []
    for i, e in enumerate(stops):
        p = stops[i - 1] if i > 0 else None
        n = stops[i + 1] if i < len(stops) - 1 else None
        if not p or not n:
            filtered_stops.append(e)
            continue
        if p['speed'] == e['speed'] == n['speed']:
            continue
        filtered_stops.append(e)
    stops = filtered_stops

    stop_elements = []
    for s in stops:
        offset = round_val(max(0, min(1, s['at'] / durationMs)))
        opacity_attr = '' if s['speed'] >= 100 else f' stop-opacity="{round_val(s["speed"] / 100)}"'
        stop_elements.append(
            f'<stop offset="{offset}" stop-color="{speedToHexCached(s["speed"])}"{opacity_attr}></stop>'
        )

    return f'''
      <linearGradient id="{linearGradientId}">
        {chr(10).join(f"          {s}" for s in stop_elements)}
      </linearGradient>'''


def toSvgBackground(
    script: 'Funscript',
    ops: SvgOptions,
    ctx: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Creates a complete SVG background with gradient fill based on a Funscript's speed patterns.
    Includes both the gradient definition and the rectangle that uses it.
    """
    width = ops.width
    height = ops.height
    ctx = ctx or {}
    bgOpacity = ctx.get('bgOpacity', svgDefaultOptions.graphOpacity)
    rectId = ctx.get('rectId')

    id_val = f"grad_{random.random():.16f}".replace('0.', '').replace('.', '')[:10]

    return f'''
    <defs>{toSvgBackgroundGradient(script, ops, id_val)}</defs>
    <rect{f' id="{rectId}"' if rectId else ''} width="{width}" height="{height}" fill="url(#{id_val})" opacity="{bgOpacity}"></rect>'''


def toSvgElement(scripts: Union['Funscript', List['Funscript']], ops: SvgOptions) -> str:
    """
    Creates a complete SVG document containing multiple Funscripts arranged vertically.
    Each script and its axes are rendered as separate visual blocks with proper spacing.
    """
    scripts = [scripts] if not isinstance(scripts, list) else scripts
    fullOps = SvgOptions(**{**vars(svgDefaultOptions), **{k: v for k, v in vars(ops).items() if v is not None}})
    fullOps.width -= SVG_PADDING * 2

    def round_val(x: float) -> float:
        return round(x, 2)

    # Check if any script has chapters and showChapters is enabled
    firstScript = scripts[0]
    hasChapters = (fullOps.showChapters and
                   hasattr(firstScript, 'metadata') and
                   firstScript.metadata and
                   hasattr(firstScript.metadata, 'chapters') and
                   firstScript.metadata.chapters and
                   len(firstScript.metadata.chapters) > 0)
    chapterOffset = fullOps.chapterHeight if hasChapters else 0
    
    # Chapters at top for full heatmaps (with title), at bottom for overlays (no title)
    chaptersAtTop = fullOps.titleHeight > 0

    pieces = []
    y = SVG_PADDING + (chapterOffset if chaptersAtTop else 0)

    title_extra_height = [0]  # Use list to allow modification in closure

    def onDoubleTitle():
        title_extra_height[0] += fullOps.titleHeight

    for s in scripts:
        if fullOps.normalize:
            s = s.clone().normalize()
        durationMs = fullOps.durationMs or s.actualDuration * 1000
        fullOps.durationMs = durationMs
        # Only show title for the first script
        pieces.append(toSvgG(s, fullOps, {
            'transform': f"translate({SVG_PADDING}, {y})",
            'onDoubleTitle': onDoubleTitle,
        }))
        y += fullOps.height + title_extra_height[0] + SPACING_BETWEEN_AXES
        title_extra_height[0] = 0
        
        # Only render secondary axes for full heatmaps (overlays should only show L0)
        if fullOps.titleHeight > 0:
            for a in s.listChannels:
                # Axes never show title
                fullOps.title = fullOps.title if fullOps.title is not None else ''
                pieces.append(toSvgG(a, fullOps, {
                    'transform': f"translate({SVG_PADDING}, {y})",
                    'isSecondaryAxis': True,
                    'onDoubleTitle': onDoubleTitle,
                }))
                y += fullOps.height + title_extra_height[0] + SPACING_BETWEEN_AXES
                title_extra_height[0] = 0
        y += SPACING_BETWEEN_FUNSCRIPTS - SPACING_BETWEEN_AXES
    y -= SPACING_BETWEEN_FUNSCRIPTS
    y += SVG_PADDING

    # Store chapter Y position
    if chaptersAtTop:
        chapterYPosition = SVG_PADDING  # Chapters at top for full heatmaps
    else:
        # For overlays, place chapters below the heatmap content
        chapterYPosition = y    # Generate chapter bar if enabled
    chapterSvg = ''
    if hasChapters:
        # Randomly chosen colors, could probably be changed to reflect average speeds or something similar
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2']
        durationMs = fullOps.durationMs or firstScript.actualDuration * 1000
        chapterY = chapterYPosition
        graphWidth = fullOps.width - fullOps.iconWidth - (fullOps.iconSpacing if fullOps.iconWidth > 0 else 0)
        xOffset = SVG_PADDING + fullOps.iconWidth + (fullOps.iconSpacing if fullOps.iconWidth > 0 else 0)

        chapterRects = []
        textHalos = []
        textElements = []

        # Helper function to convert time string to milliseconds
        def timeToMs(timeStr: str) -> float:
            parts = timeStr.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return (hours * 3600 + minutes * 60 + seconds) * 1000

        # Build chapter elements
        for idx, chapter in enumerate(firstScript.metadata.chapters):
            startMs = getattr(chapter, 'startAt', None) or timeToMs(getattr(chapter, 'startTime', '0:0:0'))
            endMs = getattr(chapter, 'endAt', None) or timeToMs(getattr(chapter, 'endTime', '0:0:0'))

            startX = (startMs / durationMs) * graphWidth + xOffset
            endX = (endMs / durationMs) * graphWidth + xOffset
            chapterWidth = endX - startX
            color = colors[idx % len(colors)]

            chapterRects.append(
                f'    <rect x="{round_val(startX)}" y="{chapterY}" width="{round_val(chapterWidth)}" height="{fullOps.chapterHeight}" fill="{color}" opacity="0.8" rx="2" ry="2"/>'
            )

            # Only render chapter name text if the chapter is wide enough
            if chapterWidth > 30:
                textX = round_val(startX + chapterWidth / 2)
                textY = round_val(chapterY + fullOps.chapterHeight / 2 + 3)
                fontSize = round_val(fullOps.chapterHeight * 0.7)

                textHalos.append(
                    f'      <text x="{textX}" y="{textY}" font-size="{fontSize}px" font-family="{fullOps.font}" text-anchor="middle" font-weight="bold">{textToSvgText(chapter.name)}</text>'
                )
                textElements.append(
                    f'    <text x="{textX}" y="{textY}" font-size="{fontSize}px" font-family="{fullOps.font}" text-anchor="middle" font-weight="bold">{textToSvgText(chapter.name)}</text>'
                )

        halo_group = ''
        if textHalos:
            halo_group = f'''    <g stroke="white" opacity="0.5" paint-order="stroke fill markers" stroke-width="3" stroke-dasharray="none" stroke-linejoin="round" fill="transparent">
{chr(10).join(textHalos)}
    </g>
'''

        chapterSvg = f'''  <g id="chapters">
{chr(10).join(chapterRects)}
{halo_group}{chr(10).join(textElements)}
  </g>
'''
        
        # Add chapter height to total SVG height only if chapters are at bottom
        if not chaptersAtTop:
            y += chapterOffset

    return f'''<svg class="funsvg" width="{round_val(fullOps.width)}" height="{round_val(y)}" xmlns="http://www.w3.org/2000/svg"
    font-size="{round_val(fullOps.titleHeight * 0.8)}px" font-family="{fullOps.font}"
>
{chapterSvg}{chr(10).join(pieces)}
</svg>'''


def toSvgG(
    script: 'Funscript',
    ops: SvgOptions,
    ctx: Dict[str, Any],
) -> str:
    """
    Creates an SVG group (g) element for a single Funscript with complete visualization.
    Includes background, graph lines, titles, statistics, axis labels, and borders.
    This is the core rendering function for individual script visualization.
    """
    title = ops.title
    icon = ops.icon
    w = ops.lineWidth
    graphOpacity = ops.graphOpacity
    titleOpacity = ops.titleOpacity
    titleHeight = ops.titleHeight
    titleSpacing = ops.titleSpacing
    height = ops.height
    iconFont = ops.iconFont
    width = ops.width
    solidTitleBackground = ops.solidTitleBackground
    titleEllipsis = ops.titleEllipsis
    titleSeparateLine = ops.titleSeparateLine
    font = ops.font
    durationMs = ops.durationMs
    iconWidth = ops.iconWidth

    isSecondaryAxis = ctx.get('isSecondaryAxis', False)
    isForHandy = ctx.get('isForHandy', False)
    iconSpacing = 0 if iconWidth == 0 else ops.iconSpacing

    titleText = ''
    if hasattr(script, 'file') and script.file and hasattr(script.file, 'filePath'):
        titleText = script.file.filePath
    elif hasattr(script, 'parent') and script.parent and hasattr(script.parent, 'file'):
        titleText = ''

    if callable(title):
        titleText = title(script, titleText)
    elif isinstance(title, str):
        titleText = title

    iconText = HANDY_ICON if isForHandy and not isSecondaryAxis else (
        channelNameToAxis(script.channel, script.channel) if script.channel else 'L0'
    )
    if callable(icon):
        iconText = icon(script, iconText)
    elif isinstance(icon, str):
        iconText = icon

    stats = toStats(script.actions, {'durationSeconds': durationMs / 1000})
    if isSecondaryAxis:
        stats.pop('Duration', None)

    statCount = len(stats)

    def round_val(x: float) -> float:
        return round(x, 2)

    proportionalFontSize = round_val(titleHeight * 0.8)
    statLabelFontSize = round_val(titleHeight * 0.4)
    statValueFontSize = round_val(titleHeight * 0.72)

    useSeparateLine = [False]  # Use list to allow modification

    # Define x positions for key SVG elements
    class XX:
        iconStart = 0  # Start of axis area
        iconEnd = iconWidth  # End of axis area
        titleStart = iconWidth + iconSpacing  # Start of title/graph area
        svgEnd = width  # End of SVG
        graphWidth = width - iconWidth - iconSpacing  # Width of graph area

        @staticmethod
        def statText(i: int) -> float:
            return round_val(width - (7 + i * 46) * (titleHeight / 20))

        @staticmethod
        def iconText() -> float:
            return round_val(XX.iconEnd / 2)

        @staticmethod
        def titleText() -> float:
            return round_val(XX.titleStart + titleHeight * 0.2)

        @staticmethod
        def textWidth() -> float:
            return XX.statText(0 if useSeparateLine[0] else statCount) - XX.titleText()

    xx = XX()

    if (titleText and titleSeparateLine is not False and
        textToSvgLength(titleText, f"{proportionalFontSize}px {font}") > xx.textWidth()):
        useSeparateLine[0] = True

    if (titleText and titleEllipsis and
        textToSvgLength(titleText, f"{proportionalFontSize}px {font}") > xx.textWidth()):
        titleText = truncateTextWithEllipsis(titleText, xx.textWidth(), f"{proportionalFontSize}px {font}")

    if useSeparateLine[0]:
        ctx['onDoubleTitle']()

    # Calculate the actual graph height from total height
    graphHeight = height - titleHeight - titleSpacing

    # Warn if encountered NaN actions
    badActions = [e for e in script.actions if not (isinstance(e.pos, (int, float)) and -float('inf') < e.pos < float('inf'))]
    if badActions:
        print('badActions', badActions)
        for e in badActions:
            e.pos = 120
        titleText += '::bad'
        iconText = '!!!'

    # Define y positions for key SVG elements
    class YY:
        top = 0  # Top of SVG

        @staticmethod
        def titleExtra() -> float:
            return titleHeight if useSeparateLine[0] else 0

        @staticmethod
        def titleBottom() -> float:
            return round_val(titleHeight + YY.titleExtra())

        @staticmethod
        def graphTop() -> float:
            return round_val(YY.titleBottom() + titleSpacing)

        @staticmethod
        def svgBottom() -> float:
            return round_val(height + YY.titleExtra())

        @staticmethod
        def iconText() -> float:
            return round_val((YY.top + YY.svgBottom()) / 2 + 4 + YY.titleExtra() / 2)

        titleText = round_val(titleHeight * 0.75)

        @staticmethod
        def statLabelText() -> float:
            return round_val(titleHeight * 0.35 + YY.titleExtra())

        @staticmethod
        def statValueText() -> float:
            return round_val(titleHeight * 0.92 + YY.titleExtra())

    yy = YY()

    bgGradientId = f"funsvg-grad-{script.channel or ''}-{len(script.actions)}-{script.actions[0].at if script.actions else 0}"

    iconColor = speedToHexCached(stats.get('AvgSpeed', 0))
    iconOpacity = round_val(titleOpacity * max(0.5, min(1, stats.get('AvgSpeed', 0) / 100)))

    lines_list = [
        f'<g transform="{ctx["transform"]}">',
        '  <g class="funsvg-bgs">',
        f'    <defs>{toSvgBackgroundGradient(script, ops, bgGradientId)}</defs>',
    ]

    if iconWidth > 0:
        lines_list.append(f'    <rect class="funsvg-bg-axis-drop" x="0" y="{yy.top}" width="{xx.iconEnd}" height="{yy.svgBottom() - yy.top}" fill="#ccc" opacity="{round_val(graphOpacity * 1.5)}"></rect>')

    lines_list.extend([
        f'    <rect class="funsvg-bg-title-drop" x="{xx.titleStart}" width="{xx.graphWidth}" height="{yy.titleBottom()}" fill="#ccc" opacity="{round_val(graphOpacity * 1.5)}"></rect>',
    ])

    if iconWidth > 0:
        lines_list.append(f'    <rect class="funsvg-bg-axis" x="0" y="{yy.top}" width="{xx.iconEnd}" height="{yy.svgBottom() - yy.top}" fill="{iconColor}" opacity="{iconOpacity}"></rect>')

    titleFill = iconColor if solidTitleBackground else f'url(#{bgGradientId})'
    titleOp = round_val(iconOpacity if solidTitleBackground else titleOpacity)

    lines_list.extend([
        f'    <rect class="funsvg-bg-title" x="{xx.titleStart}" width="{xx.graphWidth}" height="{yy.titleBottom()}" fill="{titleFill}" opacity="{titleOp}"></rect>',
        f'    <rect class="funsvg-bg-graph" x="{xx.titleStart}" width="{xx.graphWidth}" y="{yy.graphTop()}" height="{graphHeight}" fill="url(#{bgGradientId})" opacity="{round_val(graphOpacity)}"></rect>',
        '  </g>',
        '',
        f'  <g class="funsvg-lines" transform="translate({xx.titleStart}, {yy.graphTop()})" stroke-width="{w}" fill="none" stroke-linecap="round">',
    ])

    for line in toSvgLines(script, ops, {'width': xx.graphWidth, 'height': graphHeight}):
        lines_list.append(f'    {line}')

    lines_list.extend([
        '  </g>',
        '',
        '  <g class="funsvg-titles">',
    ])

    if ops.halo:
        lines_list.append('    <g class="funsvg-titles-halo" stroke="white" opacity="0.5" paint-order="stroke fill markers" stroke-width="3" stroke-dasharray="none" stroke-linejoin="round" fill="transparent">')
        lines_list.append(f'      <text class="funsvg-title-halo" x="{xx.titleText()}" y="{yy.titleText}"> {textToSvgText(titleText)} </text>')

        for i, (k, v) in enumerate(reversed(list(stats.items()))):
            lines_list.append(f'      <text class="funsvg-stat-label-halo" x="{xx.statText(i)}" y="{yy.statLabelText()}" font-weight="bold" font-size="{statLabelFontSize}px" text-anchor="end"> {k} </text>')
            lines_list.append(f'      <text class="funsvg-stat-value-halo" x="{xx.statText(i)}" y="{yy.statValueText()}" font-weight="bold" font-size="{statValueFontSize}px" text-anchor="end"> {v} </text>')

        lines_list.append('    </g>')

    if iconWidth > 0:
        lines_list.append(f'    <text class="funsvg-axis" x="{xx.iconText()}" y="{yy.iconText()}" font-size="{round_val(max(12, iconWidth * 0.75))}px" font-family="{iconFont}" text-anchor="middle" dominant-baseline="middle"> {textToSvgText(iconText)} </text>')

    lines_list.append(f'    <text class="funsvg-title" x="{xx.titleText()}" y="{yy.titleText}"> {textToSvgText(titleText)} </text>')

    for i, (k, v) in enumerate(reversed(list(stats.items()))):
        lines_list.append(f'    <text class="funsvg-stat-label" x="{xx.statText(i)}" y="{yy.statLabelText()}" font-weight="bold" font-size="{statLabelFontSize}px" text-anchor="end"> {k} </text>')
        lines_list.append(f'    <text class="funsvg-stat-value" x="{xx.statText(i)}" y="{yy.statValueText()}" font-weight="bold" font-size="{statValueFontSize}px" text-anchor="end"> {v} </text>')

    lines_list.extend([
        '  </g>',
        '</g>',
    ])

    return '\n'.join(lines_list)


def toSvgBlobUrl(script: Union['Funscript', List['Funscript']], ops: SvgOptions) -> str:
    """
    Creates a blob URL for downloading or displaying Funscript(s) as an SVG file.
    Useful for generating downloadable SVG files or creating object URLs for display.
    """
    # This function would work in browser environment with Blob and URL.createObjectURL
    # In Python, we just return the SVG string
    return toSvgElement(script, ops)
