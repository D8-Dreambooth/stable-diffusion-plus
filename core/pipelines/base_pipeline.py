from typing import Any, Dict


class BasePipeline:
    def __init__(self):
        self.pipe = None
        self.preprocessors = []
        self.postprocessors = []

    def load(self, src_pipe: Any, params: Dict):
        raise NotImplementedError("load() method must be implemented by child classes")

    def to(self, dest: str):
        if self.pipe is not None:
            try:
                self.pipe = self.pipe.to(dest)
            except:
                pass

    def unload(self):
        raise NotImplementedError("unload() method must be implemented by child classes")

    def process(self, params: Dict = None) -> Dict:
        raise NotImplementedError("process() method must be implemented by child classes")

    def add_preprocessor(self, preprocessor):
        self.preprocessors.append(preprocessor)

    def add_postprocessor(self, postprocessor):
        self.postprocessors.append(postprocessor)

    def get_preprocessors(self):
        return self.preprocessors

    def get_postprocessors(self):
        return self.postprocessors

    def start_process(self, params: Dict = None) -> Any:
        inputs = []
        if "inputs" in params:
            inputs = params["inputs"]
        for preprocessor in self.preprocessors:
            inputs = preprocessor.process(inputs, params)
        inputs = self.process(params)
        for postprocessor in self.postprocessors:
            inputs = postprocessor.process(inputs, params)
        return inputs
