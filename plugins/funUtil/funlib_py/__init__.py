"""Main funscript classes and utilities."""

from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING
import json
from .types import *
from .converter import (
    axisLikes, axisToChannelName, channelNameToAxis, formatJson, msToTimeSpan,
    orderByChannel, orderTrimJson, timeSpanToMs
)
from .misc import clamp, clone, isEmpty, makeNonEnumerable, mapObject

if TYPE_CHECKING:
    pass

__all__ = ['FunAction', 'FunChapter', 'FunBookmark', 'FunMetadata', 'FunscriptFile', 'Funscript', 'FunChannel']


class FunAction:
    """Represents a single action point in a funscript."""

    # --- Public Instance Properties ---
    at: 'ms' = 0
    pos: 'pos' = 0

    # --- Constructor ---
    def __init__(self, action: Optional[JsonAction] = None):
        if action:
            self.at = action.get('at', 0) if isinstance(action, dict) else action.at
            self.pos = action.get('pos', 0) if isinstance(action, dict) else action.pos

    # --- JSON & Clone Section ---
    jsonShape = {'at': None, 'pos': None}

    def toJSON(self) -> JsonAction:
        return orderTrimJson(self, {
            'at': round(self.at, 1),
            'pos': round(self.pos, 1),
        })

    def clone(self) -> 'FunAction':
        return clone(self)


class FunChapter:
    """Represents a chapter in a funscript."""

    name: 'chapterName' = ''
    startTime: 'timeSpan' = '00:00:00.000'
    endTime: 'timeSpan' = '00:00:00.000'

    def __init__(self, chapter: Optional[JsonChapter] = None):
        if chapter:
            # Object.assign equivalent
            self.name = chapter.get('name', '') if isinstance(chapter, dict) else getattr(chapter, 'name', '')
            self.startTime = chapter.get('startTime', '00:00:00.000') if isinstance(chapter, dict) else getattr(chapter, 'startTime', '00:00:00.000')
            self.endTime = chapter.get('endTime', '00:00:00.000') if isinstance(chapter, dict) else getattr(chapter, 'endTime', '00:00:00.000')

    @property
    def startAt(self) -> ms:
        return timeSpanToMs(self.startTime)

    @startAt.setter
    def startAt(self, v: ms) -> None:
        self.startTime = msToTimeSpan(v)

    @property
    def endAt(self) -> ms:
        return timeSpanToMs(self.endTime)

    @endAt.setter
    def endAt(self, v: ms) -> None:
        self.endTime = msToTimeSpan(v)

    jsonShape = {'startTime': None, 'endTime': None, 'name': ''}

    def toJSON(self) -> JsonChapter:
        return orderTrimJson(self)

    def clone(self) -> 'FunChapter':
        return clone(self)



class FunBookmark:
    """Represents a bookmark in a funscript."""

    name: str = ''
    time: 'timeSpan' = '00:00:00.000'

    def __init__(self, bookmark: Optional[Dict[str, Any]] = None):
        if bookmark:
            self.name = bookmark.get('name', '')
            self.time = bookmark.get('time', '00:00:00.000')

    @property
    def startAt(self) -> ms:
        return timeSpanToMs(self.time)

    @startAt.setter
    def startAt(self, v: ms) -> None:
        self.time = msToTimeSpan(v)

    jsonShape = {'time': None, 'name': ''}

    def toJSON(self) -> Dict[str, Any]:
        return orderTrimJson(self)



class FunMetadata:
    """Represents metadata for a funscript."""

    # --- Static Class References (for extensibility) ---
    Bookmark = FunBookmark
    Chapter = FunChapter

    # --- Public Instance Properties ---
    duration: 'seconds' = 0
    chapters: List[FunChapter] = []
    bookmarks: List[FunBookmark] = []

    # --- Constructor ---
    def __init__(self, metadata: Optional[JsonMetadata] = None, parent: Optional['Funscript'] = None):
        self.chapters = []
        self.bookmarks = []
        self.duration = 0

        if metadata:
            # Object.assign equivalent
            for key, value in metadata.items():
                if key not in ['bookmarks', 'chapters', 'duration']:
                    setattr(self, key, value)

        # Get base class for extensibility
        base = self.__class__

        if metadata and 'bookmarks' in metadata:
            self.bookmarks = [base.Bookmark(e) for e in metadata['bookmarks']]
        if metadata and 'chapters' in metadata:
            self.chapters = [base.Chapter(e) for e in metadata['chapters']]
        if metadata and 'duration' in metadata:
            self.duration = metadata['duration']

        # Duration conversion logic
        if self.duration > 3600:  # 1 hour
            actionsDuration = parent.actionsDuraction if parent else None
            if actionsDuration and actionsDuration < 500 * self.duration:
                self.duration /= 1000

    # --- JSON & Clone Section ---
    jsonShape = {
        'title': '',
        'creator': '',
        'description': '',
        'duration': None,
        'durationTime': None,
        'chapters': [],
        'bookmarks': [],
        'license': '',
        'notes': '',
        'performers': [],
        'topic_url': '',
        'script_url': '',
        'tags': [],
        'type': 'basic',
        'video_url': '',
    }

    def toJSON(self) -> JsonMetadata:
        return orderTrimJson(self, {
            'duration': round(self.duration, 3),
            'durationTime': msToTimeSpan(self.duration * 1000),
        })

    def clone(self) -> 'FunMetadata':
        # Create a deep clone to avoid modifying the original's chapters/bookmarks
        clonedData = json.loads(json.dumps(self.toJSON()))
        return clone(self, clonedData)



class FunscriptFile:
    """Represents a funscript file with parsed path information."""

    channel: Union['channel', str] = ''
    title: str = ''
    dir: str = ''
    mergedFiles: Optional[List['FunscriptFile']] = None

    def __init__(self, filePath: Union[str, 'FunscriptFile']):
        if isinstance(filePath, FunscriptFile):
            filePath = filePath.filePath

        parts = filePath.split('.')
        if parts[-1] == 'funscript':
            parts.pop()

        channel = parts[-1] if parts else ''
        if channel in axisLikes:
            self.channel = parts.pop()

        filePath = '.'.join(parts)
        parts = filePath.replace('\\', '/').split('/')
        self.title = parts.pop() if parts else ''
        self.dir = filePath[:len(filePath) - len(self.title)]

    @property
    def filePath(self) -> str:
        channelPart = f".{self.channel}" if self.channel else ""
        return f"{self.dir}{self.title}{channelPart}.funscript"

    def clone(self) -> 'FunscriptFile':
        return clone(self, self.filePath)


class Funscript:
    """Main funscript class representing a complete funscript file."""

    # --- Static Class References (for extensibility) ---
    Action = FunAction
    Chapter = FunChapter
    Bookmark = FunBookmark
    Metadata = FunMetadata
    File = FunscriptFile
    Channel = None  # Will be set after FunChannel declaration

    @staticmethod
    def mergeMultiAxis(scripts: List['Funscript'], options: Optional[Dict[str, Any]] = None) -> List['Funscript']:
        """merge multi-axis scripts into one"""
        allowMissingActions = options.get('allowMissingActions', False) if options else False
        combineSingleSecondaryChannel = options.get('combineSingleSecondaryChannel', False) if options else False

        multiScriptChannels = [e for e in scripts if e.listChannels]
        singleScriptChannels = [e for e in scripts if not e.listChannels]

        # Group by directory + title
        groups = {}
        for script in singleScriptChannels:
            key = f"{script.file.dir}{script.file.title}" if script.file else '[unnamed]'
            if key not in groups:
                groups[key] = []
            groups[key].append(script)

        mergedSingleScriptChannels = []
        for title, scriptsGroup in groups.items():
            if not scriptsGroup:
                continue

            # base case: no duplicate axes
            # scripts already checked to have no channels
            allScripts = sorted(scriptsGroup, key=lambda e: orderByChannel(e, e))
            usedChannels = list(set([e.channel for e in allScripts]))
            if len(usedChannels) != len(allScripts):
                channelsList = [e.channel for e in allScripts]
                raise ValueError(f"Funscript.mergeMultiAxis: some of the {json.dumps(title)} channels {json.dumps(channelsList)} are duplicate")

            if len(allScripts) == 1:
                if not allScripts[0].channel:
                    mergedSingleScriptChannels.extend(allScripts)
                    continue
                if not combineSingleSecondaryChannel:
                    mergedSingleScriptChannels.extend(allScripts)
                    continue
                mergedSingleScriptChannels.append(Funscript({
                    **allScripts[0].__dict__,
                    'actions': [],
                    'channels': {allScripts[0].channel: allScripts[0]},
                    'channel': None,
                }, {'isMerging': True}))
                continue

            mainScript = next((e for e in allScripts if not e.channel), None)
            secondaryScripts = [e for e in allScripts if e.channel]

            if not mainScript and not allowMissingActions:
                raise ValueError('Funscript.mergeMultiAxis: cannot merge scripts with no base script')

            mergedSingleScriptChannels.append(Funscript(mainScript, {'channels': secondaryScripts, 'isMerging': True}))

        return multiScriptChannels + mergedSingleScriptChannels

    # --- Public Instance Properties ---
    channel: Optional[channel] = None
    actions: List[FunAction] = []
    channels: Dict[channel, 'FunChannel'] = {}
    metadata: FunMetadata = None

    # --- Non-enumerable Properties ---
    parent: Optional['Funscript'] = None
    file: Optional[FunscriptFile] = None

    # --- Constructor ---
    def __init__(self, funscript: Optional[JsonFunscript] = None, extras: Optional[Dict[str, Any]] = None):
        self.actions = []
        self.channels = {}

        base = self.__class__
        self.metadata = base.Metadata()

        if extras and 'file' in extras:
            self.file = base.File(extras['file'])
        elif isinstance(funscript, Funscript) and funscript.file:
            self.file = funscript.file.clone()

        # prefer file > funscript > extras
        self.channel = (extras.get('channel') if extras else None) or \
                      (funscript.get('channel') if isinstance(funscript, dict) else getattr(funscript, 'channel', None)) or \
                      (self.file.channel if self.file else None)

        if funscript:
            # Object.assign equivalent for simple properties
            if isinstance(funscript, dict):
                for key in funscript:
                    if key not in ['actions', 'metadata', 'channels', 'axes']:
                        setattr(self, key, funscript[key])

        if funscript:
            if isinstance(funscript, dict) and 'actions' in funscript:
                self.actions = [base.Action(e) for e in funscript['actions']]
            elif isinstance(funscript, Funscript) and funscript.actions:
                self.actions = [base.Action(e) for e in funscript.actions]

        if funscript:
            if isinstance(funscript, dict) and 'metadata' in funscript:
                self.metadata = base.Metadata(funscript['metadata'], self)
            elif isinstance(funscript, Funscript):
                self.file = funscript.file.clone() if funscript.file else None

        if extras and 'channels' in extras and funscript:
            channelsFromFunscript = funscript.get('channels') if isinstance(funscript, dict) else getattr(funscript, 'channels', None)
            axesFromFunscript = funscript.get('axes') if isinstance(funscript, dict) else getattr(funscript, 'axes', None)
            if not isEmpty(channelsFromFunscript) or not isEmpty(axesFromFunscript):
                raise ValueError('FunFunscript: channels are defined on both script and extras')

        channelsOrAxes = (extras.get('channels') if extras else None) or \
                        (funscript.get('channels') if isinstance(funscript, dict) else getattr(funscript, 'channels', None)) or \
                        (funscript.get('axes') if isinstance(funscript, dict) else getattr(funscript, 'axes', None))

        if isinstance(channelsOrAxes, list):
            channelsDict = {}
            for e in channelsOrAxes:
                if isinstance(e, dict):
                    channelKey = e.get('channel') if 'channel' in e else axisToChannelName(e.get('id'))
                else:
                    # e is a Funscript object
                    channelKey = e.channel if e.channel else 'main'
                channelsDict[channelKey] = e
            channelsOrAxes = channelsDict

        if channelsOrAxes:
            self.channels = mapObject(channelsOrAxes or {}, lambda e, ch: base.Channel(e, {'parent': self, 'channel': ch}))

        if extras and extras.get('isMerging'):
            baseFile = self.file or next((e.file for e in self.listChannels if e.file), None)
            newFile = base.File(baseFile if baseFile else '[unnamed]')
            mergedFilesList = [self.file] + [e.file for e in self.listChannels]
            newFile.mergedFiles = [f for f in mergedFilesList if f is not None]
            if newFile.mergedFiles:
                self.file = newFile

        if extras and 'parent' in extras:
            self.parent = extras['parent']

        makeNonEnumerable(self, 'parent')
        makeNonEnumerable(self, 'file')

    # --- Getters/Setters ---

    @property
    def duration(self) -> seconds:
        if self.metadata.duration:
            return self.metadata.duration
        channel_times = [e.actions[-1].at if e.actions else 0 for e in self.listChannels]
        all_times = [self.actions[-1].at if self.actions else 0] + channel_times
        return max(all_times) / 1000 if all_times else 0

    @property
    def actionsDuraction(self) -> seconds:
        channel_times = [e.actions[-1].at if e.actions else 0 for e in self.listChannels]
        all_times = [self.actions[-1].at if self.actions else 0] + channel_times
        return max(all_times) / 1000 if all_times else 0

    @property
    def actualDuration(self) -> seconds:
        if not self.metadata.duration:
            return self.actionsDuraction
        actionsDuraction = self.actionsDuraction
        metadataDuration = self.metadata.duration
        if actionsDuraction > metadataDuration:
            return actionsDuraction
        if actionsDuraction * 3 < metadataDuration:
            return actionsDuraction
        return metadataDuration

    @property
    def listChannels(self) -> List['FunChannel']:
        return list(self.channels.values())

    @property
    def allChannels(self) -> List['Funscript']:
        return [self] + self.listChannels

    # --- Public Instance Methods ---

    def normalize(self) -> 'Funscript':
        for e in self.listChannels:
            e.normalize()

        for e in self.actions:
            e.at = round(e.at) or 0
            e.pos = clamp(round(e.pos) or 0, 0, 100)

        self.actions.sort(key=lambda a: a.at)
        self.actions = [e for i, e in enumerate(self.actions) if i == 0 or self.actions[i-1].at < e.at]

        negativeActions = [e for e in self.actions if e.at < 0]
        if negativeActions:
            self.actions = [e for e in self.actions if e.at >= 0]
            if self.actions and self.actions[0].at > 0:
                lastNegative = negativeActions[-1]
                lastNegative.at = 0
                self.actions.insert(0, lastNegative)

        duration = int(self.actualDuration + 0.5)  # ceil equivalent
        self.metadata.duration = duration
        for e in self.listChannels:
            e.metadata.duration = duration

        return self

    # --- JSON & Clone Section ---
    jsonShape = {
        'id': None,
        'channel': None,
        'metadata': {},
        'actions': None,
        'axes': None,
        'channels': {},
        'inverted': False,
        'range': 100,
        'version': '1.0',
    }

    def toJSON(self, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        v = options.get('version') if options else None
        if not v:
            v = '2.0' if self.channels else '1.0'

        if v == '1.0-list':
            return [e.toJSON({'version': '1.0'}) for e in [self] + self.listChannels]

        ops = {**(options or {}), 'root': False}
        return orderTrimJson(self, {
            'version': v,
            'id': channelNameToAxis(self.channel, self.channel) if v == '1.1' and self.parent else None,
            'axes': [axis.toJSON(ops) for axis in self.channels.values()] if v == '1.1' else None,
            'channel': self.channel or None if v == '1.0' else None,
            'channels': mapObject(self.channels, lambda e, k: e.toJSON(ops)) if v == '2.0' else None,
            'metadata': {
                **self.metadata.toJSON(),
                'duration': round(self.duration, 3),
                'durationTime': msToTimeSpan(self.duration * 1000),
            },
        })

    def toJsonText(self, options: Optional[Dict[str, Any]] = None) -> str:
        jsonData = self.toJSON(options)
        return formatJson(json.dumps(jsonData, indent=2), options or {})

    def __str__(self) -> str:
        return self.toJsonText()

    def clone(self) -> 'Funscript':
        cloned = clone(self)
        if self.file:
            cloned.file = self.file.clone()
        return cloned


class FunChannel(Funscript):
    """Represents a secondary channel in a multi-axis funscript."""

    # Type declarations (for clarity, though Python doesn't enforce)
    channel: 'channel'
    channels: Dict['channel', Any]  # Should be empty for FunChannel
    parent: Funscript

    def __init__(self, funscript: Optional[JsonFunscript] = None, extras: Optional[Dict[str, Any]] = None):
        super().__init__(funscript, extras)

        if not self.channel:
            raise ValueError('ScriptChannel: channel is not defined')
        if not self.parent:
            raise ValueError('ScriptChannel: parent is not defined')

    def clone(self) -> 'FunChannel':
        return self.parent.clone().channels[self.channel]

    def toJSON(self, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        jsonData = super().toJSON(options)

        if options and options.get('version') == '1.0-list':
            return jsonData

        if options and options.get('root') is False:
            parentMetadata = json.dumps(self.parent.metadata.toJSON()) if self.parent else '{}'
            if all(
                key in ['duration', 'durationTime'] or
                json.dumps(jsonData.get('metadata', {}).get(key)) == json.dumps(json.loads(parentMetadata).get(key))
                for key in jsonData.get('metadata', {}).keys()
            ):
                if 'metadata' in jsonData:
                    del jsonData['metadata']

            if 'axes' in jsonData:
                del jsonData['axes']
            if 'channels' in jsonData:
                del jsonData['channels']
            if 'version' in jsonData:
                del jsonData['version']
            if 'parent' in jsonData:
                del jsonData['parent']
            if options.get('version') != '1.0' and 'channel' in jsonData:
                del jsonData['channel']

        return jsonData


# Set the ScriptChannel reference after it's declared
Funscript.Channel = FunChannel

