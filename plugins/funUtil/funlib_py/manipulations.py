from typing import List, Tuple, Dict, Any, TYPE_CHECKING
import math

if TYPE_CHECKING:
    from . import FunAction
    from .types import ms, pos, speed

from .converter import secondsToDuration
from .misc import absSpeedBetween, clamplerp, lerp, listToSum, minBy, speedBetween, unlerp


def binaryFindLeftBorder(actions: List['FunAction'], at: 'ms') -> int:
    """
    Finds the index of the action at or immediately before the specified time.
    Returns `0` if the time is before the first action.
    Returns rightmost of actions with same `at`
    """
    if len(actions) <= 1:
        return 0
    if at < actions[0].at:
        return 0
    if at > actions[-1].at:
        return len(actions) - 1

    left = 0
    right = len(actions) - 1

    while left < right:
        mid = (left + right) // 2
        if actions[mid].at < at:
            left = mid + 1
        else:
            right = mid

    # Always return the left border (the action at or before the time)
    if left > 0 and actions[left].at > at:
        return left - 1
    return left


def clerpAt(actions: List['FunAction'], at: 'ms') -> 'pos':
    from .types import pos as PosType

    if len(actions) == 0:
        return PosType(50)
    if len(actions) == 1:
        return actions[0].pos
    if at <= actions[0].at:
        return actions[0].pos
    if at >= actions[-1].at:
        return actions[-1].pos

    leftIndex = binaryFindLeftBorder(actions, at)
    leftAction = actions[leftIndex]
    rightAction = actions[leftIndex + 1] if leftIndex + 1 < len(actions) else None

    if at == leftAction.at:
        return leftAction.pos
    if not rightAction:
        return leftAction.pos

    return PosType(clamplerp(at, leftAction.at, rightAction.at, leftAction.pos, rightAction.pos))


def isPeak(actions: List['FunAction'], index: int) -> int:
    """
    Determines if an action at given index is a peak
    @returns -1 for valley, 0 for neither, 1 for peak
    """
    action = actions[index]
    prevAction = actions[index - 1] if index > 0 else None
    nextAction = actions[index + 1] if index < len(actions) - 1 else None

    # if there is no prev or next action, it's a peak because we need peaks at corners
    if not prevAction and not nextAction:
        return 1
    if not prevAction:
        speedFrom = speedBetween(action, nextAction)
        return 1 if speedFrom < 0 else 1
    if not nextAction:
        speedTo = speedBetween(prevAction, action)
        return -1 if speedTo > 0 else -1

    speedTo = speedBetween(prevAction, action)
    speedFrom = speedBetween(action, nextAction)

    # Use sign comparison like TypeScript's Math.sign() which returns 0 for zero
    # Python's math.copysign treats 0 as positive, but Math.sign(0) === 0
    signTo = 0 if speedTo == 0 else (1 if speedTo > 0 else -1)
    signFrom = 0 if speedFrom == 0 else (1 if speedFrom > 0 else -1)
    
    if signTo == signFrom:
        return 0

    if speedTo > speedFrom:
        return 1
    if speedTo < speedFrom:
        return -1
    return 0


class ActionLine(list):
    """Line segment between two actions with speed calculations"""
    def __init__(self, p: 'FunAction', e: 'FunAction', absSpeed: float):
        super().__init__([p, e, absSpeed])
        self.speed: float = 0
        self.absSpeed: float = absSpeed
        self.speedSign: int = 0
        self.dat: float = 0
        self.atStart: float = 0
        self.atEnd: float = 0


def actionsToLines(actions: List['FunAction']) -> List[ActionLine]:
    """
    Converts an array of actions into an array of lines with speed calculations
    """
    lines = []
    for i in range(1, len(actions)):
        p = actions[i - 1]
        e = actions[i]
        speed = speedBetween(p, e)
        line = ActionLine(p, e, abs(speed))
        line.speed = speed
        line.absSpeed = abs(speed)
        line.speedSign = math.copysign(1, speed) if speed != 0 else 0
        line.dat = e.at - p.at
        line.atStart = p.at
        line.atEnd = e.at
        lines.append(line)

    return [e for e in lines if e[0].at < e[1].at]


def actionsToZigzag(actions: List['FunAction']) -> List['FunAction']:
    """
    Filters actions to create a zigzag pattern by removing actions with same direction changes
    """
    return [e.clone() for i, e in enumerate(actions) if isPeak(actions, i)]


def mergeLinesSpeed(lines: List[ActionLine], mergeLimit: float) -> List[ActionLine]:
    """
    Merges line segments with similar speeds within a time limit
    """
    if not mergeLimit:
        return lines

    j = 0
    i = 0
    while i < len(lines) - 1:
        j = i
        while j < len(lines) - 1:
            if lines[i].speedSign != lines[j + 1].speedSign:
                break
            j += 1

        f = lines[i:j + 1]
        if i == j:
            i = j + 1
            continue
        if listToSum([e.dat for e in f]) > mergeLimit:
            i = j + 1
            continue

        avgSpeed = listToSum([e.absSpeed * e.dat for e in f]) / listToSum([e.dat for e in f])
        for e in f:
            e[2] = avgSpeed

        i = j + 1

    return lines


def calculateWeightedSpeed(lines: List[ActionLine]) -> float:
    """
    Calculates weighted average speed from a set of lines
    """
    if len(lines) == 0:
        return 0
    return listToSum([e.absSpeed * e.dat for e in lines]) / listToSum([e.dat for e in lines])


def smoothActions(actions: List['FunAction'], windowSize: int = 3) -> List['FunAction']:
    """
    Smooths out action positions using a moving average
    """
    from . import FunAction

    if windowSize < 2:
        return actions

    result = []
    for i, action in enumerate(actions):
        start = max(0, i - windowSize // 2)
        end = min(len(actions), start + windowSize)
        window = actions[start:end]
        avgPos = sum(a.pos for a in window) / len(window)
        result.append(FunAction(at=action.at, pos=avgPos))

    return result


def actionsAverageSpeed(actions: List['FunAction']) -> float:
    zigzag = actionsToZigzag(actions)
    fast = []
    for i, e in enumerate(zigzag):
        prev = zigzag[i - 1] if i > 0 else None
        if prev and abs(speedBetween(prev, e)) > 30:
            fast.append(e)

    numerator = 0
    for i, e in enumerate(fast):
        prev = fast[i - 1] if i > 0 else None
        next_action = fast[i + 1] if i < len(fast) - 1 else None
        speedTo = abs(speedBetween(prev, e)) if prev else 0
        datNext = next_action.at - e.at if next_action else 0
        numerator += speedTo * datNext

    denominator = sum(fast[i + 1].at - e.at for i, e in enumerate(fast) if i < len(fast) - 1)

    return numerator / (denominator or 1)


def actionsRequiredMaxSpeed(actions: List['FunAction']) -> 'speed':
    """
    while the device speed may be lower then the script's max speed
    the device doesn't have to actually reach it - it needs just enough so to reach the next peak fast enough
    """
    from .types import speed as SpeedType

    if len(actions) < 2:
        return SpeedType(0)

    requiredSpeeds: List[Tuple['speed', 'ms']] = []

    nextPeakIndex = 0
    for i in range(len(actions)):
        a = actions[i]
        if nextPeakIndex == i:
            # Find next peak
            nextPeakIndex = -1
            for idx in range(i + 1, len(actions)):
                if isPeak(actions, idx) != 0:
                    nextPeakIndex = idx
                    break
            if nextPeakIndex == -1:
                break
        nextPeak = actions[nextPeakIndex]
        if not nextPeak:
            break
        requiredSpeeds.append((abs(speedBetween(a, nextPeak)), nextPeak.at - a.at))

    # sort by speed descending
    sorted_speeds = sorted(requiredSpeeds, key=lambda x: x[0], reverse=True)

    # return speed that is active for at least 50ms
    for required_speed, duration in sorted_speeds:
        if duration >= 50:
            return SpeedType(required_speed)

    return SpeedType(0)


def smoothCurve(
    curve: List['FunAction'],
    timeRadius: 'ms' = 50,
    iterations: int = 1,
    preserveEnds: bool = False,
) -> List['FunAction']:
    """
    Smooths a 1D animation curve using a weighted moving average
    @param curve - The original curve data points with time and position
    @param timeRadius - Number of neighboring points to consider (odd number recommended)
    @param iterations - Number of smoothing passes to apply
    @param preserveEnds - Whether to keep the start/end points unchanged
    @returns The smoothed curve (modified in place)
    """
    radius = 5

    positions = [e.pos for e in curve]

    for iter in range(iterations):
        for i in range(len(curve)):
            if preserveEnds and (i == 0 or i == len(curve) - 1):
                continue

            sum_val = 0
            weight_sum = 0

            for j in range(-radius, radius + 1):
                index = i + j
                if 0 <= index < len(curve):
                    # triangular weight distribution
                    weight = max(0, timeRadius - abs(curve[index].at - curve[i].at))
                    sum_val += positions[index] * weight
                    weight_sum += weight

            curve[i].pos = positions[i] = sum_val / weight_sum

    return curve


def splitToSegments(actions: List['FunAction']) -> List[List['FunAction']]:
    """
    Splits a curve into segments between peaks
    """
    segments: List[List['FunAction']] = []
    prevPeakIndex = -1

    # Find segments between peaks
    for i in range(len(actions)):
        if isPeak(actions, i) != 0:
            if prevPeakIndex != -1:
                segments.append(actions[prevPeakIndex:i + 1])
            prevPeakIndex = i

    return segments


def connectSegments(segments: List[List['FunAction']]) -> List['FunAction']:
    """
    Connects segments back into a single array of actions
    """
    flat = []
    for segment in segments:
        flat.extend(segment)

    result = []
    for i, e in enumerate(flat):
        if i == 0 or e != flat[i - 1]:
            result.append(e)

    return result


def simplifyLinearCurve(
    curve: List['FunAction'],
    threshold: float,
) -> List['FunAction']:
    """
    Removes redundant points from a curve where points lie on nearly straight lines
    """
    if len(curve) <= 2:
        return curve  # Nothing to simplify

    segments = splitToSegments(curve)
    simplifiedSegments = []

    for segment in segments:
        # First check if the entire segment can be simplified to just endpoints
        if lineDeviation(segment) <= threshold:
            simplifiedSegments.append([segment[0], segment[-1]])
            continue

        result = [segment[0]]
        startIdx = 0

        # Examine each potential line segment
        while startIdx < len(segment) - 1:
            endIdx = startIdx + 2  # At least consider the next point

            # Try to extend the current line segment as far as possible
            while endIdx <= len(segment) - 1:
                # Check if the current segment is straight enough
                if lineDeviation(segment[startIdx:endIdx + 1]) > threshold:
                    break
                endIdx += 1

            # We've found the longest valid line segment
            endIdx = max(startIdx + 1, endIdx - 1)

            # Add the endpoint of this segment to our result
            result.append(segment[endIdx])

            # Move to the next segment
            startIdx = endIdx

        simplifiedSegments.append(result)

    return connectSegments(simplifiedSegments)


HANDY_MAX_SPEED = 550
HANDY_MIN_INTERVAL = 60
HANDY_MAX_STRAIGHT_THRESHOLD = 3


def handySmooth(actions: List['FunAction']) -> List['FunAction']:
    """
    Handy has a max speed and a min interval between actions
    This function will smooth the actions to fit those constraints
    """
    from . import FunAction

    actions = [e.clone() for e in actions]
    # pass 0: round at values
    for e in actions:
        e.pos = round(e.pos)

    # pass 1: split into segments of [peak, ...nonpeaks, peak]
    segments = splitToSegments(actions)

    def straigten(segment: List['FunAction']) -> List['FunAction']:
        if len(segment) <= 2:
            return segment
        if lineDeviation(segment) <= HANDY_MAX_STRAIGHT_THRESHOLD:
            return [segment[0], segment[-1]]
        return segment

    # pass 2: remove non-peak actions that are too close to peaks
    def simplifySegment(segment: List['FunAction']) -> List['FunAction']:
        if len(segment) <= 2:
            return segment
        first = segment[0]
        last = segment[-1]
        middle = segment[1:-1]

        if lineDeviation(segment) <= HANDY_MAX_STRAIGHT_THRESHOLD:
            return [first, last]
        if absSpeedBetween(first, last) > HANDY_MAX_SPEED:
            return [first, last]

        # split to 2 parts cannot create too high speed
        middle = [e for e in middle
                  if absSpeedBetween(first, e) < HANDY_MAX_SPEED
                  and absSpeedBetween(e, last) < HANDY_MAX_SPEED]

        # middle cannot contain points too close to first or last
        middle = [e for e in middle
                  if e.at - first.at >= HANDY_MIN_INTERVAL
                  and last.at - e.at >= HANDY_MIN_INTERVAL]

        if not middle:
            return [first, last]
        if len(middle) == 1:
            return straigten([first, middle[0], last])

        middleDuration = middle[-1].at - middle[0].at
        if middleDuration < HANDY_MIN_INTERVAL:
            # can place only a single point in the middle
            # find the point that is closest to the middle of the segment
            middlePoint = minBy(middle, lambda e: abs(e.at - middleDuration / 2))
            return straigten([first, middlePoint, last])

        return [first] + simplifySegment(middle) + [last]

    filteredSegments = [simplifySegment(segment) for segment in segments]
    filteredActions = connectSegments(filteredSegments)

    # pass 3: merge points that are too close to each other
    i = 1
    while i < len(filteredActions):
        # merge only poins that have <30 speed
        current = filteredActions[i]
        prev = filteredActions[i - 1]
        if isPeak(filteredActions, i) == 0 and isPeak(filteredActions, i - 1) == 0:
            i += 1
            continue
        speed = absSpeedBetween(prev, current)
        if speed > 10:
            i += 1
            continue

        prev.pos = lerp(prev.pos, current.pos, 0.5)
        prev.at = lerp(prev.at, current.at, 0.5)
        # remove current point
        filteredActions.pop(i)
        i -= 1
        i += 1

    # filteredActions = filteredActions # linkList is noop

    # pass 4: if the speed between two points is too high, move them closer together
    filteredActions = limitPeakSpeed(filteredActions, HANDY_MAX_SPEED)

    # pass 5: simplify the curve
    filteredActions = simplifyLinearCurve(filteredActions, HANDY_MAX_STRAIGHT_THRESHOLD)

    # pass 6: round at and pos values
    for e in filteredActions:
        e.at = round(e.at)
        e.pos = round(e.pos)

    return filteredActions


def lineDeviation(actions: List['FunAction']) -> float:
    """
    Calculates maximum deviation of points from a straight line between endpoints
    """
    if len(actions) <= 2:
        return 0

    first = actions[0]
    last = actions[-1]

    maxDeviation = 0
    # Check each point's distance from the line between first and last
    for i in range(1, len(actions) - 1):
        t = (actions[i].at - first.at) / (last.at - first.at)
        expectedPos = first.pos + (last.pos - first.pos) * t
        deviation = abs(actions[i].pos - expectedPos)

        if deviation > maxDeviation:
            maxDeviation = deviation

    return maxDeviation


def limitPeakSpeed(actions: List['FunAction'], maxSpeed: float) -> List['FunAction']:
    peaks = actionsToZigzag(actions)

    poss = [e.pos for e in peaks]
    for iteration in range(10):
        retry = False
        # First calculate all changes
        lchanges = [0.0] * len(poss)
        rchanges = [0.0] * len(poss)
        for left_idx in range(len(poss) - 1):
            r = left_idx + 1
            left = peaks[left_idx]
            right = peaks[r]
            absSpeed = abs(speedBetween(left, right))
            if absSpeed <= maxSpeed:
                continue
            height = right.pos - left.pos
            changePercent = (absSpeed - maxSpeed) / absSpeed
            totalChange = height * changePercent
            # Split into left and right changes
            lchanges[left_idx] += totalChange / 2
            rchanges[r] -= totalChange / 2

        # Merge changes first
        changes = []
        for i in range(len(poss)):
            lchange = lchanges[i]
            rchange = rchanges[i]
            # If signs are different, use the max absolute value with original sign
            # If signs are same, sum them
            if math.copysign(1, lchange) == math.copysign(1, rchange):
                changes.append(lchange if abs(lchange) > abs(rchange) else rchange)
            else:
                changes.append(lchange + rchange)

        # Apply all changes at once
        for i in range(len(poss)):
            poss[i] += changes[i]
            peaks[i].pos = poss[i]

        speed = max(
            abs(speedBetween(peaks[idx], peaks[idx + 1])) if idx + 1 < len(peaks) else 0
            for idx in range(len(peaks))
        )
        if speed > maxSpeed:
            retry = True

        if not retry:
            break

    segments = splitToSegments(actions)
    for i in range(len(segments)):
        newLeftPos = peaks[i].pos
        newRightPos = peaks[i + 1].pos
        segment = segments[i]
        leftAt = segment[0].at
        rightAt = segment[-1].at
        for j in range(len(segment)):
            segment[j].pos = lerp(newLeftPos, newRightPos, unlerp(leftAt, rightAt, segment[j].at))

    return connectSegments(segments)


def toStats(actions: List['FunAction'], options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates statistics for a funscript's actions
    """
    durationSeconds = options['durationSeconds']

    MaxSpeed = actionsRequiredMaxSpeed(actions)
    AvgSpeed = actionsAverageSpeed(actions)

    return {
        'Duration': secondsToDuration(durationSeconds),
        'Actions': len([e for i, e in enumerate(actions) if isPeak(actions, i) != 0]),
        'MaxSpeed': round(MaxSpeed),
        'AvgSpeed': round(AvgSpeed),
    }
    lines = []
    from .misc import speedBetween

    for i in range(1, len(actions)):
        p = actions[i - 1]
        e = actions[i]
        line_speed = speedBetween(p, e)
        line = ActionLine(p, e, abs(line_speed))
        line.speed = line_speed
        line.absSpeed = abs(line_speed)
        line.speedSign = 1 if line_speed > 0 else -1 if line_speed < 0 else 0
        line.dat = e.at - p.at
        line.atStart = p.at
        line.atEnd = e.at
        lines.append(line)

    return [e for e in lines if e[0].at < e[1].at]
