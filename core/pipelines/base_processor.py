from typing import Any, Dict


class Processor:
    def __init__(self):
        pass

    def load(self, params: Dict):
        pass

    def unload(self):
        pass

    def process(self, inputs: Any, params: Dict = None) -> Any:
        pass


class PreProcessor(Processor):
    pass


class PostProcessor(Processor):
    pass