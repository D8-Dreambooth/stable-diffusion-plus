// registerModule("Input/Output", "moduleImportExport", "import", false, -1);
const ioModule = new Module("Input/Output", "moduleImportExport", "import", false, -1, initImportExport);

function initImportExport() {
    const modelSelect = document.getElementById("modelSelect");
    const modelExportSelect = document.getElementById("modelExportSelect");

    const selector = new ModelSelect(modelSelect, {
        "model_type": "stable-diffusion",
        "ext_include": [".safetensors", ".ckpt"],
        "load_on_select": false,
        "label": "Source Checkpoint"
    });

    const selectorEx = new ModelSelect(modelExportSelect, {
        "model_type": "diffusers",
        "load_on_select": false,
        "label": "Source Checkpoint"
    });

    const startExtract = document.getElementById("startExtract");
    const startCompile = document.getElementById("startCompile");
    const extractLora = document.getElementById("startExtractLora");

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
        console.log("Current export model: ", modelInfo);
    })

    extractLora.addEventListener("click", (event) => {
        event.preventDefault();
        // Get references to the elements using their IDs
        const loraSrcSelect = document.querySelector('#io_lora_src_select');
        const loraBaseSelect = document.querySelector('#io_lora_base_select');
        const loraPrecisionSelect = document.querySelector('#io_lora_precision');

        const loraNetworkDimensionRange = document.querySelector('#io_lora_network_dimension input[type="range"]');
        const loraConvDimensionRange = document.querySelector('#io_lora_conv_dimension input[type="range"]');


        // Define an empty object
        const values = {};
        let srcFS = new ModelSelect(document.getElementById("io_lora_src"), {});
        let baseFS = new ModelSelect(document.getElementById("io_lora_base"), {});
        // Get the selected value from each of the select elements and add it to the object
        values.tuned = srcFS.getModel();
        values.src = baseFS.getModel();
        values.precision = loraPrecisionSelect.value;
        console.log("Dims: ", loraNetworkDimensionRange, loraConvDimensionRange);
        // Get the current value from each of the range input elements and add it to the object
        values.network_dim = parseInt(loraNetworkDimensionRange.value);
        values.conv_dim = parseInt(loraConvDimensionRange.value);
        sendMessage("extract_lora", values, true, "io").then((res) => {
           console.log("Loras extracted!", res);
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