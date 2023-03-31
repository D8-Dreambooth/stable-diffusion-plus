document.addEventListener("DOMContentLoaded", function (event) {
    sendMessage("get_config",{"section_key": "import_export"}).then((data)=>{
        console.log("IODATA: ", data);
        if (data["enable"]) {
            loadModule();
        }
    });
});

function loadModule() {
    registerModule("Input/Output", "moduleImportExport", "import", false, -1);
    const modelSelect = document.getElementById("modelSelect");
    const modelExportSelect = document.getElementById("modelExportSelect");

    const selector = new ModelSelect(modelSelect, {
        "model_type": "stable-diffusion",
        "ext_include": [".safetensors", ".ckpt"],
        "load_on_select": false
    });

    const selectorEx = new ModelSelect(modelExportSelect,{
        "model_type": "diffusers",
        "load_on_select": false
    });

    const startExtract = document.getElementById("startExtract");
    const startCompile = document.getElementById("startCompile");
    startExtract.addEventListener("click", () => {
        console.log("startExtract button was clicked");
        let modelInfo = selector.getModel();
        let is_512 = document.getElementById("convUse512").checked;
        modelInfo["is_512"] = is_512;
        sendMessage("extract_checkpoint", modelInfo,true).then((res)=>{
            console.log("All done!", res);
        });

        console.log("Current model info: ", modelInfo);
    });

    startCompile.addEventListener("click", () => {
        // Code to be executed when the "startCompile" button is clicked
        console.log("startCompile button was clicked");
        let modelInfo = selectorEx.getModel();
        console.log("Current export model: ", modelInfo);
    });
}