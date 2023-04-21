from dataclasses import dataclass
from typing import List, Tuple, Union


@dataclass
class ConfigSettings:
    key: str
    type: type
    input_type: str
    label: str = ''
    description: str = ''
    options: List[Union[str, Tuple[str, str]]] = None
    default: Union[str, int, float] = None
    step: Union[int, float] = None
    min_val: Union[int, float] = None
    max_val: Union[int, float] = None
    max_chars: int = None
