// registerModule("Input/Output", "moduleImportExport", "import", false, -1);
const ioModule = new Module("Input/Output", "moduleImportExport", "import", false, -1, initImportExport);

function initImportExport() {
    const modelExportSelect = document.getElementById("modelExportSelect");
    const selector = $("#modelSelect").modelSelect({
        "model_type": "stable-diffusion",
        "ext_include": [".safetensors", ".ckpt"],
        "load_on_select": false,
        "label": "Source Checkpoint"
    });
    const selectorEx = $("#modelExportSelect").modelSelect({
        "model_type": "diffusers",
        "load_on_select": false,
        "label": "Source Checkpoint"
    });

    const modelMergePrimary = $("#modelMergePrimary").modelSelect({"model_type": "diffusers"});
    const modelMergeSecondary = $("#modelMergeSecondary").modelSelect({"model_type": "diffusers"});
    const modelMergeTertiary = $("#modelMergeTertiary").modelSelect({"model_type": "diffusers"});
    const loraModelSource = $("#io_lora_src").modelSelect({});
    const loraModelBase = $("#io_lora_base").modelSelect({});
    const startExtract = document.getElementById("startExtract");
    const startCompile = document.getElementById("startCompile");
    const extractLora = document.getElementById("startExtractLora");
    const startMerge = document.getElementById("startMerge");
    $("#merge_multiplier").BootstrapSlider({});
    startExtract.addEventListener("click", (event) => {
        event.preventDefault();
        console.log("startExtract button was clicked");
        let modelInfo = selector.getModel();
        modelInfo["save_shared"] = document.getElementById("extract_save_shared").checked;
        modelInfo["is_512"] = document.getElementById("convUse512").checked;
        sendMessage("extract_checkpoint", modelInfo, true, "io").then((res) => {
            console.log("All done!", res);
        });

        console.log("Current model info: ", modelInfo);
    });

    startCompile.addEventListener("click", (event) => {
        event.preventDefault();
        // Code to be executed when the "startCompile" button is clicked
        console.log("startCompile button was clicked");
        let modelInfo = selectorEx.getModel();
        sendMessage("compile_checkpoint", modelInfo, true, "io").then((res) => {
            console.log("All done!", res);
        });
        console.log("Current export model: ", modelInfo);
    })

    extractLora.addEventListener("click", (event) => {
        event.preventDefault();
        // Get references to the elements using their IDs
        const loraPrecisionSelect = document.querySelector('#io_lora_precision');
        const loraNetworkDimensionRange = document.querySelector('#io_lora_network_dimension input[type="range"]');
        const loraConvDimensionRange = document.querySelector('#io_lora_conv_dimension input[type="range"]');

        // Define an empty object
        const values = {};
        // Get the selected value from each of the select elements and add it to the object
        values.tuned = loraModelSource.getModel();
        values.src = loraModelBase.getModel();
        values.precision = loraPrecisionSelect.value;
        console.log("Dims: ", loraNetworkDimensionRange, loraConvDimensionRange);
        // Get the current value from each of the range input elements and add it to the object
        values.network_dim = parseInt(loraNetworkDimensionRange.value);
        values.conv_dim = parseInt(loraConvDimensionRange.value);
        sendMessage("extract_lora", values, true, "io").then((res) => {
           console.log("Loras extracted!", res);
        });
    });

    startMerge.addEventListener("click", (event) => {
        event.preventDefault();
        let modelInfo = {};
        modelInfo["primary_model"] = modelMergePrimary.getModel();
        modelInfo["secondary_model"] = modelMergeSecondary.getModel();
        modelInfo["tertiary_model"] = modelMergeTertiary.getModel();
        modelInfo["save_as_half"] = document.getElementById("merge_save_half").checked;
        modelInfo["merge_type"] = document.getElementById("merge_type").value;
        modelInfo["merge_new_name"] = document.getElementById("merge_new_name").value;
        modelInfo["merge_multiplier"] = $("#merge_multiplier").BootstrapSlider().value;
        console.log("Merge message: ", modelInfo);
        sendMessage("merge_checkpoints", modelInfo, true, "io").then((res) => {
            console.log("All done!", res);
        });
    });
    let pg = new ProgressGroup(document.getElementById("importProgressGroup"), {"id": "io"});

    $("#startModelDownload").click((event) => {
        event.preventDefault();
        let downloadModelUrl = $("#downloadModelUrl").val();
        let downloadModelType = $("#downloadModelType").val();
        let downloadModelName = $("#downloadModelName").val();
        if (downloadModelUrl !== "" && downloadModelType !== "") {
            sendMessage("download_model", {
                "url": downloadModelUrl,
                "model_type": downloadModelType,
                "model_name": downloadModelName
            }, false, "io").then((res) => {
                console.log("All done!", res);
            });
        } else {
            alert("Please provide a URL and model type.");
        }
    });
}