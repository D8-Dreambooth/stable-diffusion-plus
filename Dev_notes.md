## Creating a Module

For starters, you should look at the existing modules. They're all pretty simple, and should give you a good idea of how to create your own.
Every module should inherit from BaseModule.

To register a websocket or API method, you can add the code to the respective _initialize functions, which are called on startup automatically for each module.
```python
    # Called on startup to register methods for the UI and API
    def initialize(self, app: FastAPI, handler: SocketHandler):
        self._initialize_api(app)
        self._initialize_websocket(handler)

    def _initialize_api(self, app: FastAPI):
        # Sample endpoint
        @app.get(f"/{self.name}/import")
        async def import_model(
                api_key: str = Query("", description="If an API key is set, this must be present.", )) -> \
                JSONResponse:
            """
            Check the current state of Dreambooth processes.
            foo
            @return:
            """
            return JSONResponse(content={"message": f"Job started."})

    # Registers a method with the websocket named "extract checkpoint" that calls the _import_model method.
    # Note, _import_model must be async def.
    def _initialize_websocket(self, handler: SocketHandler):
        super()._initialize_websocket(handler)
        handler.register("extract_checkpoint", _import_model)
```

Module.py files can be named anything you want, same with js and css files.

For the UI-side of things, index.html *must* be called index.html. IDK why I did this, and it can probably be changed, I just haven't done so.

index.html should only contain the module's code - not a full HTML page. Specifically, it should start with a div with a class of "module" and a unique ID - the ID will be used to register the module with the UI. Everything else inside the module div is totally up to you, but I recommend using bootstrap, as it's easy and pretty.

`<div class="module" id="moduleInfer">...</div>`

For JS, you should always have this in your main module's JSON:

```
document.addEventListener("DOMContentLoaded", function () {

    // Register the module with the UI. Icon is from boxicons by default. "True" indicates the module should be default, and 1 is the display order. Use -1 for auto.
    registerModule("Inference", "moduleInfer", "images", true, 1);
    
    // Register a listener for ctrl+ enter on any child of the element inferSettings, and call the method "startInference" if pressed.
    keyListener.register("ctrl+Enter", "#inferSettings", startInference);
}
```


## Handlers

There are a number of handlers created for, well, handling common functionality so you don't have to hijack code or re-invent the wheel. 

These include, but aren't limited to:

Reading and writing configuration values

Reading and writing files

Handling images

Queueing jobs

Updating the status in the UI

Sending and receiving messages over the websocket

Handling image captions

Loading and saving models


All handlers are singletons, and can be accessed from anywhere in the code. For example, to get the config handler, you can do:

```python
from core.handlers.config_handler import ConfigHandler
ch = ConfigHandler()
some_data = ch.get_item("some_key", "some_section", "default_value")
```

The config handler also contains methods to get and set full sections, as well as set individual items.
