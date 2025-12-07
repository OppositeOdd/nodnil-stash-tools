from typing import List, Optional, Callable, TypeVar, Any, Tuple, Dict, TYPE_CHECKING
import math

if TYPE_CHECKING:
    from . import FunAction
    from .types import mantissaText, pos, speed

try:
    from colour.models import Oklab_to_XYZ, XYZ_to_sRGB
    import numpy as np

    def oklch2rgb(lightness: float, c: float, h: float) -> Tuple[int, int, int]:
        h_rad = math.radians(h)
        a = c * math.cos(h_rad)
        b = c * math.sin(h_rad)

        oklab = np.array([lightness, a, b])
        xyz = Oklab_to_XYZ(oklab)
        rgb = XYZ_to_sRGB(xyz)

        r, g, b_val = [max(0, min(255, int(round(x * 255)))) for x in rgb]
        return (r, g, b_val)
except ImportError:
    def oklch2rgb(lightness: float, c: float, h: float) -> Tuple[int, int, int]:
        h_rad = h * math.pi / 180
        a = c * math.cos(h_rad)
        b = c * math.sin(h_rad)

        y = (lightness + 0.3963377774 * a + 0.2158037573 * b)
        x = (lightness - 0.1055613458 * a - 0.0638541728 * b)
        z = (lightness - 0.0894841775 * a - 1.2914855480 * b)

        r = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
        g = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
        b_val = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z

        def gamma_correct(c: float) -> int:
            if c <= 0.0031308:
                c = 12.92 * c
            else:
                c = 1.055 * (c ** (1/2.4)) - 0.055
            return max(0, min(255, int(round(c * 255))))

        return (gamma_correct(r), gamma_correct(g), gamma_correct(b_val))


def clamp(value: float, left: float, right: float) -> float:
    return max(left, min(right, value))


def lerp(left: float, right: float, t: float) -> float:
    return left * (1 - t) + right * t


def unlerp(left: float, right: float, value: float) -> float:
    if left == right:
        return 0.5
    return (value - left) / (right - left)


def clamplerp(
    value: float,
    inMin: float,
    inMax: float,
    outMin: float,
    outMax: float,
) -> float:
    return lerp(outMin, outMax, clamp(unlerp(inMin, inMax, value), 0, 1))


def listToSum(list: List[float]) -> float:
    return sum(list)


def speedBetween(a: Optional['FunAction'], b: Optional['FunAction']) -> 'speed':
    from .types import speed as SpeedType

    if not a or not b:
        return SpeedType(0)
    if a.at == b.at:
        return SpeedType(0)
    # Convert to u/s by multiplying by 1000 (ms to s)
    return SpeedType((b.pos - a.pos) / (b.at - a.at) * 1000)


def absSpeedBetween(a: Optional['FunAction'], b: Optional['FunAction']) -> 'speed':
    return abs(speedBetween(a, b))


def segmentSpeed(segment: List['FunAction']) -> 'speed':
    return speedBetween(segment[0], segment[-1] if segment else None)


def segmentAbsSpeed(segment: List['FunAction']) -> 'speed':
    return abs(segmentSpeed(segment))


T = TypeVar('T')


def minBy(list: List[T], fn: Callable[[T], float]) -> T:
    values = [fn(item) for item in list]
    min_index = min(range(len(values)), key=lambda i: values[i])
    return list[min_index]


def compareWithOrder(a: Optional[str], b: Optional[str], order: List[Optional[str]]) -> int:
    """
    Compare two values with an order array
    - If both are in the order array, return the indexOf difference
    - Missing strings are compared lexicographically
    - `undefined`s are placed in the very end
    """
    N = len(order)
    try:
        aIndex = order.index(a)
    except ValueError:
        aIndex = N if a else (N + 1 if a == '' else N + 2)

    try:
        bIndex = order.index(b)
    except ValueError:
        bIndex = N if b else (N + 1 if b == '' else N + 2)

    if aIndex != bIndex:
        return aIndex - bIndex

    # both are strings
    if aIndex == N:
        return 0 if a == b else (-1 if a < b else 1)

    return 0


def toMantissa(value: 'pos', trim: bool = False) -> 'mantissaText':
    from .types import mantissaText as MantissaTextType

    text = f"{clamp(value / 100, 0, 0.9999):.4f}"[2:]
    if trim:
        import re
        text = re.sub(r'(?<=.)0+$', '', text)
    return MantissaTextType(text)


def makeNonEnumerable(target: Any, key: str, value: Any = None) -> Any:
    """
    Make a property non-enumerable (Python doesn't have true non-enumerable properties,
    so this is a no-op that returns the target for compatibility)
    """
    if value is not None:
        setattr(target, key, value)
    return target


def clone(obj: T, *args: Any) -> T:
    """
    Generic clone utility that preserves the constructor type
    """
    return type(obj)(obj, *args)


K = TypeVar('K', bound=str)
V = TypeVar('V')
R = TypeVar('R')


def mapObject(obj: Dict[K, V], fn: Callable[[V, K], R]) -> Dict[K, R]:
    return {key: fn(value, key) for key, value in obj.items()}


def isEmpty(o: Optional[Any] = None) -> bool:
    if not o:
        return True
    if isinstance(o, list):
        return len(o) == 0
    if isinstance(o, dict):
        return len(o) == 0
    return False


def toValues(o: Optional[Any] = None) -> List[Any]:
    if not o:
        return []
    if isinstance(o, list):
        return list(o)
    if isinstance(o, dict):
        return list(o.values())
    return []
