## Terminology and Concepts

The overarching theme for this project is modularity and security. The goal is to create a framework that allows for easy creation of new functionality without having to write a ton of code from scratch, or go digging through the code to find where things are and what they do.

The most basic concepts here are "Modules", "Extensions" and "Handlers".

### Modules
A module is a self-contained piece of functionality. It can be anything from a simple image captioning model, to a full-blown image editor. Modules are loaded on startup, and can be enabled or disabled at any time. These provide what would be considered "core" application functionality, and as such, have full access to all methods in the code.

### Extensions
An extension is very similar to a module, with the exception that it is restricted in what it can do with data and methods within the appliction.

Specifically, extensions can only access data and methods that are explicitly exposed to them. Extensions are intended to be created and maintaned by other users, and as such, are not allowed to override core functionality or packages.  

A lot of the security functionality here is still theoretical, and while I've tried to design things with this in the back of my mind, not everything is probably built right to really maintain this idea of a standard.

### Handlers

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



## Project Structure
/app - Contains the main application code, with main.py being the entry point.

This is where the FastAPI app is created, and handlers are initialized. It's also the location for module discovery and initialization.

/conf_src - Contains default configuration files for core application functionality. Individual module/extension configs are NOT stored here.

/core - Contains the core application code. This is where the bulk of the application logic is.

/core/dataclasses - Contains the various dataclasses used throughout the application.

/core/handlers - Contains the various handlers for common functionality. These are singletons, and can be accessed from anywhere in the code.

/core/modules - Contains the core modules. These are the modules that are loaded by default, and are required for the application to function.

/core/pipelines - A concept for stacking functionality, but I haven't found a use for it yet.

/core/shared - Designed to contain functionality accessible to extensions...but haven't gotten around to fleshing out that idea yet.

/data_protected and /data_shared - These are the "default" locations for data. The protected folder is for data that should be protected from non-admin users, and the shared folder is for data that should be accessible to everyone. These can be changed in the launch_settings.config file.

/static - Contains files for the UI. This includes images, css, js, and html.

/templates - Contains the base html templates for the UI. "base.html" is the primary page.

/tests - We should use this...extensively. But, I suck, and haven't done anything with it yet.

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


### Module Structure

Modules should be structured as follows, with all files and directories below being stored /core/modules/module_name:

/config - Contains default config files for the module. These are imported automatically if not found in the main configuration store.

/css - Contains css files for the module. These are loaded automatically by the UI, and can have any name.

/custom - Contains any custom files for the UI. These are loaded automatically by the UI, and can have any name.

/js - Contains js files for the module. These are loaded automatically by the UI, and can have any name.

/src - Contains additional python files for the module outisde of the main module interface for the application.

/index.html - The main UI file for the module. This should only contain the module's code, not a full HTML page.

/module_yourmodule.py - The main module file for the application. This should inherit from BaseModule, and implement any methods that interface with the application.


## Javascript Fun!

Within /static/js/custom-elements there are a number of custom elements that can be used to implement complex functionality in the UI with minimal effort.

Currently, these include:

### BootstrapSlider Constructor
The `BootstrapSlider` class is used to create a slider control with Bootstrap styling. It takes two arguments: the `parentElement` where the slider will be added, and an `options` object that can be used to customize the slider's behavior and appearance.

The following options can be passed to the `options` object:
- `min`: the minimum value of the slider (default is `1`)
- `max`: the maximum value of the slider (default is `150`)
- `step`: the step value of the slider (default is `1`)
- `value`: the initial value of the slider (default is `min`)
- `visible`: whether the slider should be visible or hidden (default is `true`)
- `interactive`: whether the slider should be interactive or disabled (default is `true`)
- `label`: the label of the slider (default is `"Sampling steps"`)
- `elem_id`: the HTML element ID of the slider (default is `"item-"` plus a randomly generated string of 8 characters)

The `BootstrapSlider` constructor creates HTML elements to represent the slider control and adds them to the `parentElement`.

#### updateValue Method
The `updateValue` method is used to update the value of the slider. It takes a `newValue` argument and sets the slider's `value`, `numberInput`, and `rangeInput` to the new value. If a `onChangeCallback` is set, it is called with the new value.

#### setOnChange Method
The `setOnChange` method is used to set a callback function that is called whenever the slider value is changed. It takes a `callback` argument that is called with the new value of the slider whenever it is changed. The `onChangeCallback` property of the slider object is set to the `callback` argument.

#### show and hide Methods
The `show` method is used to show the slider control by setting its `display` property to `""`. The `hide` method is used to hide the slider control by setting its `display` property to `"none"`.

#### value Method
The `value` method is used to get the current value of the slider control. It returns the `value` property of the slider object.



### cancelButton Constructor
The `cancelButton` class is used to create a button element that cancels a task or process. It takes an `element` argument, which is the HTML element that represents the button, and attaches a click event listener to it.

When the button is clicked, the `onClick` method is called asynchronously. It sends a message to cancel the task or process using the `sendMessage` function, passing an empty object as the payload and `true` as the `expectResponse` parameter. The result of the message is logged to the console.

#### onClick Method
The `onClick` method is called when the `cancelButton` is clicked. It sends a message to cancel the task or process using the `sendMessage` function, passing an empty object as the payload and `true` as the `expectResponse` parameter. The result of the message is logged to the console.

#### init Static Method
The `init` static method is used to initialize `cancelButton` elements on the page. It gets all elements with the `cancelButton` class using jQuery's `$` function and creates an instance of `cancelButton` for each element. If no elements are found, it creates a new `button` element with the `cancelButton` class and creates an instance of `cancelButton` for it.

#### cancelButton jQuery Plugin
The `cancelButton` jQuery plugin is used to initialize `cancelButton` elements on the page. It calls the `cancelButton.init` static method to create and return an array of `cancelButton` instances for each `cancelButton` element found on the page. If only one `cancelButton` element is found, it returns a jQuery object that wraps the `element` property of the corresponding `cancelButton` instance. If multiple `cancelButton` elements are found, it returns a jQuery object that wraps an array of `element` properties from all corresponding `cancelButton` instances.


### fileBrowser Constructor
The `fileBrowser` class is used to create a file browser that allows users to select files and directories. It takes a `parentElement` argument, which is the HTML element that the file browser will be appended to, and an optional `options` object.

The file browser is composed of a tree view that displays the directory structure and a list of files and directories. The `options` object can be used to customize the appearance and behavior of the file browser.

The `fileBrowser` constructor takes an optional `options` object that can be used to customize the behavior and appearance of the file browser. Here is a list of the available options:

- `placeholder`: The placeholder text to display in the input field.
- `showSelectButton`: A boolean value that indicates whether to show the select button. If true, a select button will be displayed next to the input field.
- `listFiles`: A boolean value that indicates whether to display files in the file browser. If false, only directories will be displayed.
- `expand`: A boolean value that indicates whether to expand the directory tree by default.
- `multiselect`: A boolean value that indicates whether to allow multiple file or directory selection.
- `dropdown`: A boolean value that indicates whether to display the file browser as a dropdown.
- `showTitle`: A boolean value that indicates whether to display the title of each file or directory.
- `showInfo`: A boolean value that indicates whether to display the info panel.
- `style`: A string value that can be used to add custom CSS styles to the file browser.


The file browser supports multiple event handlers, which can be added using the `addOnDoubleClick`, `addOnClick`, `addOnSelect`, and `addOnCancel` methods.

#### refresh Method
The `refresh` method is used to refresh the file browser. It rebuilds the directory tree and updates the file and directory list.

#### setCurrentPath Method
The `setCurrentPath` method is used to set the current path of the file browser. It takes a `path` argument, which is the path of the current directory.

#### addOnDoubleClick Method
The `addOnDoubleClick` method is used to add an event handler for double-click events. It takes a `callback` argument, which is the function that will be called when a file or directory is double-clicked.

#### addOnClick Method
The `addOnClick` method is used to add an event handler for click events. It takes a `callback` argument, which is the function that will be called when a file or directory is clicked.

#### addOnSelect Method
The `addOnSelect` method is used to add an event handler for file or directory selection events. It takes a `callback` argument, which is the function that will be called when a file or directory is selected.

#### addOnCancel Method
The `addOnCancel` method is used to add an event handler for cancel events. It takes a `callback` argument, which is the function that will be called when the file browser is cancelled.

#### buildTree Method
The `buildTree` method is used to build the directory tree. It is called when the file browser is initialized and when it is refreshed.

#### buildInput Method
The `buildInput` method is used to build the input field for the file browser. It is called when the file browser is initialized.

#### toggleTree Method
The `toggleTree` method is used to toggle the visibility of the file browser. It is called when the user clicks the input field.

#### showFileInfo Method
The `showFileInfo` method is used to display information about a file or directory in the info panel. It is called when a file or directory is clicked.

#### buildFileButtons Method
The `buildFileButtons` method is used to build the file buttons for the file browser. It is called when the file browser is initialized.

#### attachEventHandlers Method
The `attachEventHandlers` method is used to attach event handlers to the file browser elements. It is called when the file browser is initialized.



### ImageEditor

This one is still a WIP, and missing various methods.

#### ImageEditor Class and Constructor

The `ImageEditor` class represents an HTML canvas that can be used to draw and edit images. The constructor takes a single argument, `containerId`, which is the ID of the HTML element that will contain the canvas.

#### Options

The `ImageEditor` constructor does not take any options. However, it provides methods for customizing the behavior and appearance of the editor, including:

- `clear()`: Clears the canvas.
- `undo()`: Undoes the last drawing action.
- `showBrushSizeDialog()`: Displays a dialog for choosing the brush size.
- `showColorPicker()`: Displays a color picker for choosing the brush color.

These methods can be called on an `ImageEditor` instance after it has been created.


### InlineGallery Class Documentation

This class creates an inline gallery that can be used to display a collection of images. It uses the Fotorama library to provide a customizable gallery experience. 

### Constructor

##### `InlineGallery(parentElement, options = {})`

This constructor creates a new instance of the InlineGallery class.

**Parameters:**

- `parentElement`: The parent element that the gallery will be added to.
- `options`: (Optional) An object containing the configuration options for the gallery. See https://fotorama.io/docs/4/options/ for the full list of options.

#### Public Methods

##### `clear()`

This method clears the gallery and removes all images.

##### `update(newItems, append = false)`

This method updates the gallery with a new set of images.

**Parameters:**

- `newItems`: An array of objects containing the image data.
- `append`: (Optional) A boolean indicating whether the new images should be appended to the existing ones or replace them. Default is `false`.

##### `socketUpdate(data)`

This method updates the gallery with new images received from a WebSocket.

**Parameters:**

- `data`: An object containing the new image data.

##### `extractImageData(data)`

This method extracts image data from the WebSocket data.

**Parameters:**

- `data`: An object containing the WebSocket data.

##### `mapElements()`

This method maps the image data to the format required by Fotorama.

##### `createFotorama()`

This method creates a new Fotorama instance.

##### `addDownloadButton()`

This method adds a download button to the active image.

##### `onDownloadButtonClick()`

This method downloads the active image when the download button is clicked.



### KeyListener

A class for registering and unregistering event listeners for keyboard key presses, with support for specifying a selector for the element(s) the event listener should apply to, and a specific key command to listen for.

#### Constructor

##### `constructor()`

Creates a new `KeyListener` instance and attaches a `keydown` event listener to the `document`.

#### Methods

##### `register(keyCommand: string, selector: string, callback: function)`

Registers a new event listener for the specified `keyCommand` (e.g. "Shift+Enter") and `selector` (e.g. ".my-selector") with the specified `callback` function. When the specified key combination is pressed within an element that matches the given selector, the callback will be executed.

##### `unregister(keyCommand: string, selector: string, callback: function)`

Unregisters the specified `callback` function for the given `keyCommand` and `selector`. If no callback is specified, all callbacks for the given key and selector will be removed.

#### Example Usage

```javascript
const keyListener = new KeyListener();

keyListener.register("Enter", ".my-selector", () => {
  console.log("Enter key pressed within element matching .my-selector");
});

keyListener.register("Shift+Enter", ".my-selector", () => {
  console.log("Shift+Enter key pressed within element matching .my-selector");
});

keyListener.unregister("Enter", ".my-selector");
```

### Class: ProgressGroup

#### `constructor(parentElement, options)`

Creates a new `ProgressGroup` instance and appends it to the given `parentElement`.

**Parameters:**

- `parentElement` {HTMLElement} - The parent element to append the `ProgressGroup` to.
- `options` {Object} - An object of options to initialize the `ProgressGroup` with.

  - `progress_1_current` {number} - The current value of the first progress bar. Default is `0`.
  - `progress_2_current` {number} - The current value of the second progress bar. Default is `0`.
  - `progress_1_total` {number} - The total value of the first progress bar. Default is `0`.
  - `progress_2_total` {number} - The total value of the second progress bar. Default is `0`.
  - `progress_1_css` {string} - The CSS class for the first progress bar. Default is `" bg-success"`.
  - `progress_2_css` {string} - The CSS class for the second progress bar. Default is `" bg-warning"`.
  - `status` {string} - The primary status text to display. Default is `""`.
  - `status2` {string} - The secondary status text to display. Default is `""`.
  - `show_bar1` {boolean} - Whether to show the first progress bar. Default is `true`.
  - `show_bar2` {boolean} - Whether to show the second progress bar. Default is `true`.
  - `show_primary_status` {boolean} - Whether to show the primary status text. Default is `true`.
  - `show_secondary_status` {boolean} - Whether to show the secondary status text. Default is `true`.
  - `show_percent` {boolean} - Whether to show the progress percentage. Default is `true`.

#### `clear()`

Clears the progress bars and status text.

#### `update(options)`

Updates the `ProgressGroup` with the given options.

**Parameters:**

- `options` {Object} - An object of options to update the `ProgressGroup` with.

  - `progress_1_current` {number} - The current value of the first progress bar.
  - `progress_2_current` {number} - The current value of the second progress bar.
  - `progress_1_total` {number} - The total value of the first progress bar.
  - `progress_2_total` {number} - The total value of the second progress bar.
  - `progress_1_css` {string} - The CSS class for the first progress bar.
  - `progress_2_css` {string} - The CSS class for the second progress bar.
  - `status` {string} - The primary status text to display.
  - `status2` {string} - The secondary status text to display.
  - `show_bar1` {boolean} - Whether to show the first progress bar.
  - `show_bar2` {boolean} - Whether to show the second progress bar.
  - `show_primary_status` {boolean} - Whether to show the primary status text.
  - `show_secondary_status` {boolean} - Whether to show the secondary status text.
  - `show_percent` {boolean} - Whether to show the progress percentage.
