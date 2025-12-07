from typing import Dict, Any, List, Tuple, Optional, Union, TYPE_CHECKING
import re
import math
import json as json_module

if TYPE_CHECKING:
    from .types import timeSpan, ms, seconds, axis, channel, axisLike, speed
    from . import Funscript

from .misc import clamplerp, compareWithOrder

# Import oklch2hex from colorizr equivalent
try:
    from colour.models import Oklab_to_XYZ, XYZ_to_sRGB
    import numpy as np

    def oklch2hex(color: Dict[str, float]) -> str:
        l, c, h = color['l'], color['c'], color['h']
        h_rad = math.radians(h)
        a = c * math.cos(h_rad)
        b = c * math.sin(h_rad)

        oklab = np.array([l, a, b])
        xyz = Oklab_to_XYZ(oklab)
        rgb = XYZ_to_sRGB(xyz)

        r, g, b_val = [max(0, min(255, int(round(x * 255)))) for x in rgb]
        return f"#{r:02x}{g:02x}{b_val:02x}"
except ImportError:
    def oklch_to_rgb(lightness: float, c: float, h: float) -> Tuple[int, int, int]:
        """
        Convert OKLCH to sRGB based on Björn Ottosson's OKLab specification
        https://bottosson.github.io/posts/oklab/
        """
        # Convert LCH to Lab
        h_rad = h * math.pi / 180.0
        a = c * math.cos(h_rad)
        b = c * math.sin(h_rad)
        
        # OKLab to linear RGB (via LMS cone space)
        l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
        m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
        s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
        
        # Cube the LMS values
        l_cubed = l_ * l_ * l_
        m_cubed = m_ * m_ * m_
        s_cubed = s_ * s_ * s_
        
        # LMS to linear RGB
        r_linear = +4.0767416621 * l_cubed - 3.3077115913 * m_cubed + 0.2309699292 * s_cubed
        g_linear = -1.2684380046 * l_cubed + 2.6097574011 * m_cubed - 0.3413193965 * s_cubed
        b_linear = -0.0041960863 * l_cubed - 0.7034186147 * m_cubed + 1.7076147010 * s_cubed
        
        # Linear RGB to sRGB gamma correction
        def linear_to_srgb(c: float) -> int:
            if c <= 0.0031308:
                srgb = 12.92 * c
            else:
                srgb = 1.055 * (c ** (1/2.4)) - 0.055
            return max(0, min(255, int(round(srgb * 255))))
        
        return (linear_to_srgb(r_linear), linear_to_srgb(g_linear), linear_to_srgb(b_linear))

    def oklch2hex(color: Dict[str, float]) -> str:
        r, g, b = oklch_to_rgb(color['l'], color['c'], color['h'])
        return f"#{r:02x}{g:02x}{b:02x}"


def timeSpanToMs(timeSpan: 'timeSpan') -> 'ms':
    from .types import ms as MsType

    if not isinstance(timeSpan, str):
        raise TypeError('timeSpanToMs: timeSpan must be a string')

    sign = -1 if timeSpan.startswith('-') else 1
    if sign < 0:
        timeSpan = timeSpan[1:]

    split = [float(e) for e in timeSpan.split(':')]
    while len(split) < 3:
        split.insert(0, 0)

    hours, minutes, seconds = split
    return MsType(round(sign * (hours * 60 * 60 + minutes * 60 + seconds) * 1000))


def msToTimeSpan(ms: 'ms') -> 'timeSpan':
    from .types import timeSpan as TimeSpanType

    sign = -1 if ms < 0 else 1
    ms = abs(ms)

    seconds = int(ms / 1000) % 60
    minutes = int(ms / 1000 / 60) % 60
    hours = int(ms / 1000 / 60 / 60)
    ms_part = int(ms % 1000)

    sign_str = '-' if sign < 0 else ''
    return TimeSpanType(
        f"{sign_str}{str(hours).zfill(2)}:{str(minutes).zfill(2)}:{str(seconds).zfill(2)}.{str(ms_part).zfill(3)}"
    )


def secondsToDuration(seconds: 'seconds') -> str:
    seconds = round(seconds)
    if seconds < 3600:
        return f"{int(seconds / 60)}:{str(int(seconds % 60)).zfill(2)}"
    return f"{int(seconds / 60 / 60)}:{str(int(seconds / 60 % 60)).zfill(2)}:{str(int(seconds % 60)).zfill(2)}"


def orderTrimJson(that: Any, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    shape = getattr(type(that), 'jsonShape', None) if hasattr(that, '__class__') else None
    if not shape or not isinstance(shape, dict):
        raise ValueError('orderTrimJson: missing static jsonShape on constructor')

    # Convert object to dict if needed
    that_dict = that.__dict__ if hasattr(that, '__dict__') else that
    copy = {**shape, **that_dict}
    if overrides:
        copy.update(overrides)

    # Serialize actions list items (FunAction objects)
    if 'actions' in copy and isinstance(copy['actions'], list):
        copy['actions'] = [item.toJSON() if hasattr(item, 'toJSON') else item for item in copy['actions']]
    
    # Serialize chapters list items (FunChapter objects)
    if 'chapters' in copy and isinstance(copy['chapters'], list):
        copy['chapters'] = [item.toJSON() if hasattr(item, 'toJSON') else item for item in copy['chapters']]
    
    # Serialize bookmarks list items (FunBookmark objects)
    if 'bookmarks' in copy and isinstance(copy['bookmarks'], list):
        copy['bookmarks'] = [item.toJSON() if hasattr(item, 'toJSON') else item for item in copy['bookmarks']]
    
    # Serialize channels dict if it contains Funscript objects (shouldn't happen but safety check)
    if 'channels' in copy and isinstance(copy['channels'], dict):
        channels_dict = copy['channels']
        # Check if any value is a Funscript object (not serialized)
        from funlib_py import Funscript
        for key, value in list(channels_dict.items()):
            if isinstance(value, Funscript):
                # This shouldn't happen - channels should already be serialized
                # But handle it anyway
                channels_dict[key] = value.toJSON()

    keys_to_delete = []
    for k, v in shape.items():
        if k not in copy:
            continue
        copy_value = copy[k]
        # If shape says None is OK and copy value is None, delete it
        if v is None and copy_value is None:
            keys_to_delete.append(k)
        # If values match exactly, delete (e.g., empty list/dict matching default)
        elif copy_value == v:
            keys_to_delete.append(k)
        elif isinstance(v, list) and isinstance(copy_value, list) and len(copy_value) == 0 and len(v) == 0:
            keys_to_delete.append(k)
        elif (isinstance(v, dict) and v is not None and len(v) == 0 and
              isinstance(copy_value, dict) and copy_value is not None and len(copy_value) == 0):
            keys_to_delete.append(k)

    for k in keys_to_delete:
        if k in copy:
            del copy[k]

    return copy


axisPairs: List[Tuple['axis', 'channel']] = [
    ('L0', 'stroke'),
    ('L1', 'surge'),
    ('L2', 'sway'),
    ('R0', 'twist'),
    ('R1', 'roll'),
    ('R2', 'pitch'),
    ('A1', 'suck'),
]

# Legacy numeric axis IDs (used in older v1.1 funscripts)
numericAxisMap: Dict[int, 'axis'] = {
    0: 'L0',  # stroke/up-down
    1: 'L1',  # surge/forward-backward
    2: 'L2',  # sway/left-right
    3: 'R0',  # twist/yaw
    4: 'R1',  # roll
    5: 'R2',  # pitch
    6: 'A1',  # suck/valve
}

axisToNameMap: Dict['axis', 'channel'] = dict(axisPairs)
channelNameToAxisMap: Dict['channel', 'axis'] = {b: a for a, b in axisPairs}
axisIds: List['axis'] = [a for a, b in axisPairs]
channelNames: List['channel'] = [b for a, b in axisPairs]
axisLikes: List['axisLike'] = [item for pair in axisPairs for item in pair]


def channelNameToAxis(name: Optional['channel'], fallback: Any = None) -> 'axis':
    from .types import axis as AxisType

    if name and name in channelNameToAxisMap:
        return AxisType(channelNameToAxisMap[name])
    if fallback is not None:
        return fallback
    raise ValueError(f"axisNameToAxis: {name} is not supported")


def axisToChannelName(axis: Optional['axis']) -> 'channel':
    # Handle legacy numeric axis IDs
    if isinstance(axis, int) and axis in numericAxisMap:
        axis = numericAxisMap[axis]
    
    if axis and axis in axisToNameMap:
        return axisToNameMap[axis]
    raise ValueError(f"axisToName: {axis} is not supported")


def axisLikeToAxis(axisLike: Optional[Union['axisLike', str]]) -> 'axis':
    from .types import axis as AxisType

    if not axisLike:
        return AxisType('L0')
    if axisLike in axisIds:
        return AxisType(axisLike)
    if axisLike in channelNames:
        return AxisType(channelNameToAxisMap[axisLike])
    if axisLike == 'singleaxis':
        return AxisType('L0')
    raise ValueError(f"axisLikeToAxis: {axisLike} is not supported")


def orderByChannel(a: 'Funscript', b: 'Funscript') -> int:
    return compareWithOrder(a.channel, b.channel, channelNames)


def fileNameToInfo(filePath: Optional[str] = None) -> Dict[str, Any]:
    parts = filePath.split('.') if filePath else []
    if parts and parts[-1] == 'funscript':
        parts.pop()

    axisLike = parts[-1] if parts else None
    if axisLike in axisLikes:
        parts.pop()
    elif axisLike == 'singleaxis':
        parts.pop()
    else:
        axisLike = None

    fileName = '.'.join(parts)
    title = fileName.split('/')[-1].split('\\')[-1] if fileName else ''

    return {
        'filePath': filePath,
        'fileName': fileName,
        'primary': not axisLike or axisLike == 'singleaxis',
        'title': title,
        'id': axisLikeToAxis(axisLike) if axisLike else None,
    }


def formatJson(
    json: str,
    lineLength: int = 100,
    maxPrecision: int = 0,
    compress: bool = True
) -> str:
    def removeNewlines(s: str) -> str:
        return re.sub(r' *\n\s*', ' ', s)

    inArrayRegex = re.compile(r'(?<=\[)([^[\]]+)(?=\])')

    json = re.sub(r'\{\s*"(at|time|startTime)":[^{}]+\}', lambda m: removeNewlines(m.group(0)), json)

    def processArray(match):
        s = match.group(0)

        # Round numbers to maxPrecision
        def round_num(m):
            num = float(m.group(0))
            rounded = f"{num:.{maxPrecision}f}"
            return re.sub(r'\.0+$', '', rounded)

        s = re.sub(r'(?<="(at|pos)":\s*)(-?\d+\.?\d*)', round_num, s)

        # "at": -123.456,
        at_values = re.findall(r'(?<="at":\s*)(-?\d+\.?\d*)', s)
        if not at_values:
            return s

        max_at_length = max(len(e) for e in at_values)
        s = re.sub(r'(?<="at":\s*)(-?\d+\.?\d*)', lambda m: m.group(0).rjust(max_at_length), s)

        pos_values = re.findall(r'(?<="pos":\s*)(-?\d+\.?\d*)', s)
        pos_dot = max(
            (len(e.split('.')[1]) + 1 for e in pos_values if '.' in e),
            default=0
        )

        def pad_pos(m):
            val = m.group(0)
            if '.' not in val:
                return val.rjust(3) + ' ' * pos_dot
            a, b = val.split('.')
            return f"{a.rjust(3)}.{b.ljust(pos_dot - 1)}"

        s = re.sub(r'(?<="pos":\s*)(-?\d+\.?\d*)', pad_pos, s)

        action_length = len('{ "at": , "pos": 100 },') + max_at_length + pos_dot

        actions_per_line1 = 10
        while 6 + (action_length + 1) * actions_per_line1 - 1 > lineLength:
            actions_per_line1 -= 1

        counter = [0]
        def replace_newline(m):
            result = m.group(0) if counter[0] % actions_per_line1 == 0 else ' '
            counter[0] += 1
            return result

        s = re.sub(r'\n(?!\s*$)\s*', replace_newline, s)

        if compress:
            match_result = re.match(r'^(\s*(?=$|\S))([\s\S]+)((?<=^|\S)\s*)$', s)
            if match_result:
                start, middle, end = match_result.group(1), match_result.group(2), match_result.group(3)
                compressed = json_module.dumps(json_module.loads(f"[{middle}]"))[1:-1]
                s = start + compressed + end

        return s

    json = inArrayRegex.sub(processArray, json)

    return json


speedToOklchParams = {
    'l': {'left': 500, 'right': 600, 'from': 0.8, 'to': 0.4},
    'c': {'left': 800, 'right': 900, 'from': 0.4, 'to': 0.1},
    'h': {'speed': -2.4, 'offset': 210},
    'a': {'left': 0, 'right': 100, 'from': 0, 'to': 1},
}


def speedToOklch(speed: 'speed', useAlpha: bool = False) -> Tuple[float, float, float, float]:
    def roll(value: float, cap: float) -> float:
        return (value % cap + cap) % cap

    lightness = clamplerp(speed, speedToOklchParams['l']['left'], speedToOklchParams['l']['right'],
                  speedToOklchParams['l']['from'], speedToOklchParams['l']['to'])
    c = clamplerp(speed, speedToOklchParams['c']['left'], speedToOklchParams['c']['right'],
                  speedToOklchParams['c']['from'], speedToOklchParams['c']['to'])
    h = roll(speedToOklchParams['h']['offset'] + speed / speedToOklchParams['h']['speed'], 360)
    a = clamplerp(speed, speedToOklchParams['a']['left'], speedToOklchParams['a']['right'],
                  speedToOklchParams['a']['from'], speedToOklchParams['a']['to'])

    return (lightness, c, h, a)


def speedToOklchText(speed: 'speed', useAlpha: bool = False) -> str:
    """
    in css:
    oklch(
       max(40%, min(80%, calc(80% + (var(--speed) - 500) / 250 * -40%)))
       max(10%, min(40%, calc(40% + (var(--speed) - 500) / 300 * -30%)))
       calc(210 - var(--speed) / 2.4))
    """
    l, c, h, a = speedToOklch(speed, useAlpha)

    def toFixed(value: float, precision: int) -> str:
        return re.sub(r'\.?0+$', '', f"{value:.{precision}f}")

    alpha_str = f" / {toFixed(a, 3)}" if useAlpha else ""
    return f"oklch({toFixed(l * 100, 3)}% {toFixed(c, 3)} {toFixed(h, 1)}{alpha_str})"


def speedToHex(speed: 'speed') -> str:
    l, c, h, _ = speedToOklch(speed)
    return oklch2hex({'l': l, 'c': c, 'h': h})


_hexCache: Dict['speed', str] = {}

def speedToHexCached(speed: 'speed') -> str:
    if speed in _hexCache:
        return _hexCache[speed]
    hex_val = speedToHex(abs(speed))
    _hexCache[speed] = hex_val
    return hex_val


def formatTCode(tcode: str, format: bool = True) -> str:
    if not format:
        return tcode
    return re.sub(
        r'\b([LR])(\d)(\d+)(?:([IS])(\d+))?',
        lambda m: f"{m.group(1)}{m.group(2)}{m.group(3).rjust(4, '_')}"
                  f"{'_' + m.group(4) if m.group(4) else ''}"
                  f"{m.group(5).rjust(4, '_') if m.group(5) else ''}",
        tcode
    )
