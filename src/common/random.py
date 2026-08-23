import random
from collections.abc import Sequence
from typing import TypeVar


T = TypeVar("T")


def rng_from_seed(seed: int | None = None) -> random.Random:
    return random.Random(seed)


def sample_range(rng: random.Random, bounds: Sequence[float]) -> float:
    low, high = bounds
    return rng.uniform(float(low), float(high))


def choose(rng: random.Random, values: Sequence[T]) -> T:
    if not values:
        raise ValueError("Cannot choose from an empty sequence.")
    return values[rng.randrange(len(values))]

