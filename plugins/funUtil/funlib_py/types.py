"""Type definitions for funscript library."""

from typing import TypedDict, Literal, Union, List, Dict, Tuple, NewType

axisPairs = [
    ('L0', 'stroke'),
    ('L1', 'surge'),
    ('L2', 'sway'),
    ('R0', 'twist'),
    ('R1', 'roll'),
    ('R2', 'pitch'),
    ('A1', 'suck'),
]

mantissa = NewType('mantissa', float)
mantissaText = NewType('mantissaText', str)

# time variants
ms = NewType('ms', float)
seconds = NewType('seconds', float)
timeSpan = NewType('timeSpan', str)

speed = NewType('speed', float)

# axis value variants
# 0-100
pos = NewType('pos', float)

# axes
axis = NewType('axis', str)
channel = NewType('channel', str)
channelName = Literal['stroke', 'surge', 'sway', 'twist', 'roll', 'pitch',
                      'suck']
axisLike = Union[axis, channel]

AxisToName = {
    'L0': 'stroke', 'stroke': 'L0',
    'L1': 'surge', 'surge': 'L1',
    'L2': 'sway', 'sway': 'L2',
    'R0': 'twist', 'twist': 'R0',
    'R1': 'roll', 'roll': 'R1',
    'R2': 'pitch', 'pitch': 'R2',
    'A1': 'suck', 'suck': 'A1',
}

chapterName = NewType('chapterName', str)

TCodeTuple = Union[
    Tuple[axis, pos],
    Tuple[axis, pos, Literal['I'], ms],
    Tuple[axis, pos, Literal['S'], speed],
]


class JsonAction(TypedDict):
    at: ms
    pos: pos


class JsonChapter(TypedDict):
    name: chapterName
    startTime: timeSpan
    endTime: timeSpan


class JsonMetadata(TypedDict, total=False):
    bookmarks: List[Dict[str, Union[str, timeSpan]]]
    chapters: List[JsonChapter]
    duration: seconds
    durationTime: timeSpan
    title: str
    topic_url: str
    tags: List[str]


class JsonFunscript(TypedDict, total=False):
    # @deprecated Use channel instead
    id: axis
    # @deprecated Use channels instead
    axes: List[Dict[str, Union[axis, List[JsonAction], channel]]]

    metadata: JsonMetadata
    actions: List[JsonAction]
    channel: channel
    channels: Dict[channel, Dict[str, List[JsonAction]]]
