// A set of JS methods that are loaded *after* extensions, so they are only available to native modules
let moduleIds = {};
let modules = [];
let loadDiv = $(".loading");
let localData = {};
// region ModuleHandling

document.addEventListener("DOMContentLoaded", function () {
    initializeCore();
    console.log("Getting module data...");
    sendMessage("get_modules", {}).then(function (response) {
        let module_data = response["module_data"];
        console.log("Got module data: ", module_data);
        loadDiv.addClass("loaded");
        let enabled_modules = [];
        // Parse module data, which is a dict of lists where the key is the module ID, and the value is a list with two
        // elements, the first being the module settings, and the second being the module defaults.
        const localeDataElement = document.getElementById("locale-data");
        let localeInner = localeDataElement.textContent;
        const localeData = JSON.parse(localeInner);
        let newDefaults = {};
        for (let module_id in module_data) {
            let module_settings = module_data[module_id]["config"];
            let module_defaults = module_data[module_id]["defaults"];
            let module_locales = localeData[module_id];
            let enableModule = false;
            if (module_settings.hasOwnProperty("enable")) {
                enableModule = module_settings["enable"];
            }
            if (module_id === "module_settings") {
                enableModule = true;
            }
            // Check if the module is enabled
            if (enableModule) {
                enabled_modules.push(module_id);
                for (let module of modules) {
                    const camelCaseId = module_id.replace(/_([a-z])/g, (match, letter) => letter.toUpperCase());
                    console.log("Comparing ", module.id, " to ", camelCaseId);
                    if (module.id === camelCaseId) {
                        module.enabled = true;
                        module.init(module_settings, module_defaults, module_locales);
                        newDefaults[module_id] = module.enumerateInputs();
                        console.log("MATCHED: ", module.id, " to ", camelCaseId);
                        break;
                    }
                }
            }
        }
        // Uncomment this to grab default configs after adding/changing stuff.
        // console.log("New defaults: ", newDefaults);
        fitty(".fit",
            {
                minSize: 10,
                maxSize: 16,
                multiLine: false,
            });
    });
});



// Register a UI Module in the menu
function registerModule(module) {
    if (modules.indexOf(module) !== -1) {
        console.log ("Module already registered: ", module);
        return;
    }
    modules.push(module);
}

// Deregister a UI Module from the menu
function deregisterModule(module_id) {
    if (modules.indexOf(module_id) === -1) {
        console.log("Module not registered: ", module_id);
        return;
    }
    modules.splice(modules.indexOf(module_id), 1);
}


// endregion
