let gallery;
let inferProgress;
let scaleTest, stepTest, numImages, batchSize, widthSlider, heightSlider, loraWeight;
let userConfig;
let controlnetImageEditor;
let controlnetFileBrowser;
let inferModelSelect;
let vaeModelSelect;
let loraModelSelect;
let pipelineData = {};


const ratioContainer = $("#infer_ratios");
const inferWidth = $("#infer_width");
const inferHeight = $("#infer_height");
const advancedElements = $(".advancedInfer");
const inpaintContainer = $("#inpaintContainer");

let inpaintImageEditor;
let inferSettings = {
    batch_size: 1,
    controlnet_batch: false,
    controlnet_batch_dir: "",
    controlnet_batch_find: "",
    controlnet_batch_replace: "",
    controlnet_batch_use_prompt: "",
    controlnet_image: null,
    controlnet_mask: null,
    controlnet_preprocess: true,
    controlnet_scale_mode: "scale",
    controlnet_type: null,
    height: 512,
    infer_image: null,
    infer_mask: null,
    infer_scale_mode: "scale",
    invert_mask: true,
    lora_weight: 0.9,
    loras: null,  // Assuming ModelData will be an array
    model: "None",  // Assuming ModelData will be a string
    negative_prompt: "",
    num_images: 1,
    pipeline: "auto",
    pipeline_settings: {},
    prompt: "",
    prompts: [],
    scale: 7.5,
    seed: -1,
    steps: 30,
    use_control_resolution: true,
    use_input_resolution: true,
    vae: null,  // Assuming this will be an object
    width: 512
}

advancedElements.hide();
ratioContainer.hide();
inferWidth.hide();
inferHeight.hide();

const inferModule = new Module(
    "Inference",
    "moduleInfer",
    "images",
    true,
    1,
    inferInit,
    inferRefresh
);

function inferResponse(data) {
    //console.log("Inference response received: ", data);
}

function inferInit() {
    registerSocketMethod("infer", "infer", inferResponse);
    keyListener.register("ctrl+Enter", "#inferSettings", startInference);
    keyListener.register("ctrl+ArrowUp", "#infer_prompt", increaseWeight);
    keyListener.register("ctrl+ArrowDown", "#infer_prompt", decreaseWeight);
    keyListener.register("ctrl+ArrowUp", "#infer_negative_prompt", increaseWeight);
    keyListener.register("ctrl+ArrowDown", "#infer_negative_prompt", decreaseWeight);
    inferModelSelect = $("#inferModel").modelSelect();
    vaeModelSelect = $("#inferVae").modelSelect();
    loraModelSelect = $("#inferLoraModels").modelSelect();
    let promptEl = document.getElementById("infer_prompt");
    let negEl = document.getElementById("infer_negative_prompt");
    historyTracker.registerHistory(promptEl);
    historyTracker.registerHistory(negEl);

    // Progress group example. Options can also be passed to inferProgress.update() in the same format.
    inferProgress = new ProgressGroup(document.getElementById("inferProgress"), {
        "primary_status": "Status 1", // Status 1 text
        "secondary_status": "Status 2", // Status 2...
        "bar1_progress": 0, // Progressbar 1 position
        "bar2_progress": 0,
        "id": "inference"// etc
    });

    // Gallery creation. Options can also be passed to .update()
    gallery = new InlineGallery(document.getElementById('inferGallery'), {
        "thumbnail": true,
        "closeable": false,
        "show_maximize": true,
        "start_open": true,
        "id": "inference"
    });

    scaleTest = $("#infer_scale").BootstrapSlider({
        elem_id: "scaleSlid",
        min: 1,
        max: 20,
        step: 0.1,
        value: 7.5,
        label: "Scale"
    });

    widthSlider = inferWidth.BootstrapSlider({
        elem_id: "widthSlid",
        min: 256,
        max: 4096,
        value: 512,
        step: 64,
        label: "Width"
    });

    heightSlider = inferHeight.BootstrapSlider({
        elem_id: "heightSlid",
        min: 256,
        max: 4096,
        value: 512,
        step: 64,
        label: "Height"
    });

    stepTest = $("#infer_steps").BootstrapSlider({
        elem_id: "stepSlid",
        min: 5,
        max: 100,
        value: 20,
        step: 1,
        label: "Steps"
    });

    numImages = $("#infer_num_images").BootstrapSlider({
        elem_id: "numImages",
        min: 1,
        max: 100,
        value: 1,
        step: 1,
        label: "Number of Images"
    });

    batchSize = $("#infer_batch_size").BootstrapSlider({
        elem_id: "batchSize",
        min: 1,
        max: 100,
        value: 1,
        step: 1,
        label: "Batch Size"
    });

    loraWeight = $("#infer_lora_weight").BootstrapSlider({
        elem_id: "lora_weight",
        min: 0.01,
        max: 1,
        value: 0.9,
        step: 0.01,
    });

    controlnetFileBrowser = $("#controlnet_batch_dir").fileBrowser({
        "file_type": "image",
        "showSelectButton": true,
        "listFiles": false,
        "showTitle": false,
        "showInfo": false,
        "multiselect": false,
        "dropdown": true,
        "label": "Controlnet Batch Directory"
    });

    controlnetImageEditor = new ImageEditor("controlnetEditor", "auto", "", false);
    inpaintImageEditor = new ImageEditor("inpaintEditor", "auto", "", false);

    let submit = document.getElementById("startInfer");

    submit.addEventListener("click", function () {
        startInference().then(function (result) {
        })
    });

    $(".inferDrop").each(function () {
        this.addEventListener("dragover", function (event) {
            event.preventDefault();
        });

        this.addEventListener("drop", function (event) {
            event.preventDefault();
            let file = event.dataTransfer.files[0];
            // If the file is a png, try to read the pnginfo
            if (file.name.endsWith(".png")) {
                let reader = new FileReader();
                reader.onload = function (e) {
                    let dataURL = e.target.result;
                    let base64Data = dataURL.split(",")[1];
                    sendMessage("read_image_info", {"image": base64Data}).then((data) => {
                        if (data.hasOwnProperty("image_data")) {
                            console.log("Image info: ", data);
                            applyInferSettingsNew(data["image_data"]);
                        }
                    });
                };
                reader.readAsDataURL(file);
            }
        });
    });

    $("#controlnet_batch").change(function () {
        if (this.checked) {
            $(".controlnetSingle").hide();
            $(".controlnetBatch").show();
        } else {
            $(".controlnetSingle").show();
            $(".controlnetBatch").hide();
        }
    });

    let moduleSettings = inferModule.systemConfig;
    console.log("Loading inference settings(1) from: ", moduleSettings);
    loadInferSettings(moduleSettings);
    sendMessage("get_controlnets", {}, true).then((data) => {
        console.log("Controlnets: ", data);
        let controlnetSelect = document.getElementById("controlnet_type");
        let option = document.createElement("option");
        option.value = "None";
        option.text = "";
        controlnetSelect.add(option);
        data = data["nets"];
        for (let i = 0; i < data.length; i++) {
            let option = document.createElement("option");
            option.value = data[i]["name"];
            option.text = data[i]["name"];
            controlnetSelect.add(option);
        }
    });
    sendMessage("get_pipelines", {}, true).then((data) => {
        console.log("Pipelines: ", data);
        let pipelineSelect = document.getElementById("infer_pipeline");
        let pipe_data = data["pipelines"];
        pipelineData = pipe_data;
        // Enumerate keyvalues in pipe_data
        let options = [];
        for (let key in pipe_data) {
            if (key === "StableDiffusionPipeline") {
                continue;
            }
            let option = document.createElement("option");
            option.value = key;
            option.text = key.replace("StableDiffusion", "").replace("Pipeline", "");
            options.push(option);
        }
        options.sort(function (a, b) {
            return a.text.localeCompare(b.text);
        });
        console.log("Sorted options:", options);
        for (let i = 0; i < options.length; i++) {
            pipelineSelect.add(options[i]);
        }
    });

    $("#infer_prompt2prompt").hide();
    $("#controlnetSettings").hide();
    $("#infer_pipeline").change(function () {
        console.log("Pipeline changed: ", this.value);
        updatePipelineSettings(this.value);
    });

    $("#controlnet_type").change(function () {
        console.log("Controlnet type changed: ", this.value);
        if (this.value === "ControlNet Reference") {
            console.log("SHOW.");
            $(".refParam").show();
        } else {
            console.log("HIDE.");
            $(".refParam").hide();
        }
    });

    $("#pipeHelpButton").click(function () {
        $(".hintBox").toggle();
        $("#pipeHelpButton").toggleClass("active");
    });

    console.log("Infer settings: ", inferSettings);
}

function updatePipelineSettings(pipelineName) {
    let pipelineParams = $("#pipelineParams");
    pipelineParams.empty();
    if (pipelineName !== "auto") {
        let pipeline = pipelineData[pipelineName];
        console.log("Pipeline: ", pipeline);
        // Enumerate keyvalues in pipeline
        let keysToIgnore = ["height", "width", "image", "latents", "source_enbeds", "target_embeds", "DOCSTRING",
            "cross_attention_kwargs", "prompt", "negative_prompt", "prompt_embeds", "negative_prompt_embeds"];
        if (pipeline.hasOwnProperty("image")) {
            $("#inpaintContainer").show();
        } else {
            $("#inpaintContainer").hide();
        }
        if (pipelineName === "StableDiffusionControlNetPipeline" || pipelineName === "StableDiffusionControlNetSAGPipeline") {
            $("#inpaintContainer").hide();
        }
        for (let key in pipeline) {
            if (keysToIgnore.includes(key)) continue;

            let inputContainer = document.createElement("div");
            inputContainer.className = "form-group mb-3";
            let inputElement;
            inputContainer.id = "pipeline_" + key;
            pipelineParams.append(inputContainer);
            if (key === "width" || key === "height" || key === "image" || key === "latents") continue;
            let value = pipeline[key];
            console.log("Key: ", key, " Value: ", value);
            // Split the key by underscores and title case it
            let keySplit = key.split("_");
            let keyTitle = "";
            for (let i = 0; i < keySplit.length; i++) {
                keyTitle += " " + keySplit[i].charAt(0).toUpperCase() + keySplit[i].slice(1);
            }
            // If the value is a float, create a BootstrapSlider
            if (typeof value === "number") {
                inputElement = document.createElement("div");

                let slider = $("#pipeline_" + key).BootstrapSlider({
                    min: 0,
                    max: 1,
                    value: value,
                    step: 0.01,
                    label: keyTitle
                });

            }
            // if the value is a boolean, create a bootstrap switch
            if (typeof value === "boolean") {
                inputElement = document.createElement("div");
                inputElement.className = "form-check form-switch";
                let input = document.createElement("input");
                input.className = "form-check-input";
                input.type = "checkbox";
                input.id = "pipeline_" + key;
                input.checked = value;
                let label = document.createElement("label");
                label.className = "form-check-label";
                label.htmlFor = "pipeline_" + key;
                label.innerText = keyTitle;
                inputElement.appendChild(input);
                inputElement.appendChild(label);
            }
            // If the value is a string, set inputElement to be a text input and create a label
            if (typeof value === "string" || key.indexOf("prompt") !== -1) {
                let label = document.createElement("label");
                label.innerText = keyTitle;
                label.htmlFor = "pipeline_" + key;
                inputElement = document.createElement("input");
                inputElement.className = "form-control";
                inputElement.id = "pipeline_" + key;
                inputElement.type = "text";
                inputElement.value = value;
                inputContainer.appendChild(label);
            }
            if (inputElement !== undefined) inputContainer.appendChild(inputElement);
        }
        if (pipeline.hasOwnProperty("DOCSTRING")) {
            let docstring = document.createElement("div");
            docstring.className = "form-text hintBox";
            docstring.innerText = pipeline["DOCSTRING"];
            pipelineParams.prepend(docstring);
            if (!$("#pipeHelpButton").hasClass("active")) $(".hintBox").hide();
        }
    } else {
        $("#inpaintContainer").hide();
        $("#infer_prompt2prompt").hide();
        $("#controlnetSettings").hide();
    }
    if (pipelineName === "StableDiffusionPrompt2PromptPipeline") {
        $("#infer_prompt2prompt").show();
    } else {
        $("#infer_prompt2prompt").hide();
    }
    if (pipelineName.indexOf("ControlNet") !== -1) {
        $("#controlnetSettings").show();
    } else {
        $("#controlnetSettings").hide();
    }
}

function inferRefresh() {
    loadInferSettings(inferModule.systemConfig);
    sendMessage("get_controlnets", {}, true).then((data) => {
        console.log("Controlnets: ", data);
        let controlnetSelect = document.getElementById("controlnet_type");
        let option = document.createElement("option");
        option.value = "None";
        option.text = "";
        controlnetSelect.add(option);
        data = data["nets"];
        for (let i = 0; i < data.length; i++) {
            let option = document.createElement("option");
            option.value = data[i]["name"];
            option.text = data[i]["name"];
            controlnetSelect.add(option);
        }
    });
    getInferSettings();
    console.log("Infer settings(refresh): ", inferSettings);
}

function getSelectedText(input) {
    return input.value.substring(input.selectionStart, input.selectionEnd);
}

function increaseWeight() {
    const input = document.activeElement;
    const value = input.value;
    let selectionStart = input.selectionStart;
    let selectionEnd = input.selectionEnd;
    const selectedText = value.substring(selectionStart, selectionEnd);
    if (!selectedText) {
        return;
    }
    let selectionOffset = 0
    // Check if the characters immediately before and after selection are square brackets
    if (value[selectionStart - 1] === "[" && value[selectionEnd] === "]") {
        // If so, remove them and return
        input.value = value.substring(0, selectionStart - 1) + selectedText + value.substring(selectionEnd + 1);
        selectionOffset = -1;
    } else {
        // Otherwise, surround the selected text with parenthesis and apply it to the input
        input.value = value.replace(selectedText, "(" + selectedText + ")");
        selectionOffset = 1;
    }
    selectionStart += selectionOffset;
    selectionEnd += selectionOffset;
    input.setSelectionRange(selectionStart, selectionEnd);
}

function decreaseWeight() {
    const input = document.activeElement;
    const value = input.value;
    let selectionStart = input.selectionStart;
    let selectionEnd = input.selectionEnd;
    const selectedText = value.substring(selectionStart, selectionEnd);
    if (!selectedText) {
        return;
    }
    let selectionOffset = 0
    // Check if the characters immediately before and after selection are square brackets
    if (value[selectionStart - 1] === "(" && value[selectionEnd] === ")") {
        // If so, remove them and return
        input.value = value.substring(0, selectionStart - 1) + selectedText + value.substring(selectionEnd + 1);
        selectionOffset = -1;
    } else {
        // Otherwise, surround the selected text with parenthesis and apply it to the input
        input.value = value.replace(selectedText, "[" + selectedText + "]");
        selectionOffset = 1;
    }
    selectionStart += selectionOffset;
    selectionEnd += selectionOffset;
    input.setSelectionRange(selectionStart, selectionEnd);
}

function loadInferSettings(data) {
    console.log("Loading inference settings: ", data);
    userConfig = data;
    if (data.hasOwnProperty("basic_infer")) {
        if (data.basic_infer) {
            advancedElements.hide();
        } else {
            advancedElements.show();
            inpaintContainer.hide();
        }
    }

    if (data["show_aspect_ratios"]) {
        console.log("Show aspect ratios");
        addRatioCards();
        ratioContainer.show();
        inferWidth.hide();
        inferHeight.hide();
    } else {
        console.log("Hide aspect ratios");
        ratioContainer.hide();
        inferWidth.show();
        inferHeight.show();
    }

    if (data["show_vae_select"]) {
        inpaintContainer.show();
    } else {
        inpaintContainer.hide();
    }
}

function addRatioCards() {
    const ratioContainer = document.querySelector("#infer_ratios");
    ratioContainer.innerHTML = "";
    const aspectRatios = ["16:9", "5:4", "4:3", "1:1", "3:4", "4:5", "9:16"];
    const buttonGroup = document.createElement("div");
    buttonGroup.classList.add("btn-group");
    buttonGroup.id = "aspectButtons";
    for (let i = 0; i < aspectRatios.length; i++) {
        const button = document.createElement("button");
        button.classList.add("btn", "aspectButton", "btn-secondary");
        if (aspectRatios[i] === "1:1") button.classList.add("btn-selected");
        button.setAttribute("data-ratio", aspectRatios[i]);
        button.textContent = aspectRatios[i];
        buttonGroup.appendChild(button);
    }
    const label = document.createElement("label");
    label.setAttribute("for", "aspectButtons");
    label.innerHTML = "Aspect Ratio";
    ratioContainer.appendChild(label);
    ratioContainer.appendChild(buttonGroup);
    document.querySelectorAll('.aspectButton').forEach(function (button) {
        button.addEventListener('click', function () {
            console.log('CLICK.');
            document.querySelector('.aspectButton.btn-selected').classList.remove('btn-selected');
            this.classList.add('btn-selected');
            setResolution(this.dataset.ratio);
        });
    });
}

function setResolution(ratio) {
    const maxRes = userConfig["max_resolution"];
    const [widthRatio, heightRatio] = ratio.split(":");
    const ratioValue = parseInt(widthRatio) / parseInt(heightRatio);

    let width = Math.round(Math.min(maxRes, ratioValue * maxRes));
    let height = Math.round(Math.min(maxRes, maxRes / ratioValue));

    width = Math.floor(width / 8) * 8;
    height = Math.floor(height / 8) * 8;
    inferSettings.width = width;
    inferSettings.height = height;
    console.log("Updated infer settings: ", inferSettings);
    return {width, height};
}

async function startInference() {
    gallery.clear();
    inferProgress.clear();
    console.log("MS: ", inferModelSelect);
    const model = inferModelSelect.getModel();

    if (model === undefined) {
        return alert("Please select a model.");
    } else {
        let promptEl = document.getElementById("infer_prompt");
        let negEl = document.getElementById("infer_negative_prompt");
        getInferSettings();

        historyTracker.storeHistory(promptEl);
        historyTracker.storeHistory(negEl);

        return sendMessage("start_inference", inferSettings, true, "inference");
    }
}

function applyInferSettingsNew(decodedSettings) {
    console.log("Applying infer settings: ", decodedSettings);
    if ("pipeline" in decodedSettings && "pipeline_settings" in decodedSettings) {
        let pipeLine = decodedSettings["pipeline"];
        let pipeSettings = decodedSettings["pipeline_settings"];
        delete decodedSettings["pipeline"];
        delete decodedSettings["pipeline_settings"];
        $("#infer_pipeline").val(pipeLine); // Removed jQuery code
        updatePipelineSettings(pipeLine);
        for (let key in pipeSettings) {
            let value = pipeSettings[key];
            if (value === "true") {
                value = true;
            } else if (value === "false") {
                value = false;
            }
            key = "pipeline_" + key;
            setElementValue(key, value);
        }
    }
    // Manually get the images
    if (decodedSettings.hasOwnProperty("infer_image") && decodedSettings.hasOwnProperty("infer_mask")) {
        let image = decodedSettings["infer_image"];
        let mask = decodedSettings["infer_mask"];
        inpaintImageEditor.setMask(mask);
        inpaintImageEditor.setDropped(image);
        delete decodedSettings["infer_image"];
        delete decodedSettings["infer_mask"];
    }
    if (decodedSettings.hasOwnProperty("controlnet_image") && decodedSettings.hasOwnProperty("controlnet_mask")) {
        let image = decodedSettings["controlnet_image"];
        let mask = decodedSettings["controlnet_mask"];
        controlnetImageEditor.setMask(mask);
        controlnetImageEditor.setDropped(image);
        delete decodedSettings["controlnet_image"];
        delete decodedSettings["controlnet_mask"];
    }
    let modelKeys = ["loras", "vae", "model"];

    for (let key in decodedSettings) {
        let value = decodedSettings[key];
        console.log("Checking key: ", key, " Value: ", value);

        if (key === "prompts" && value.length > 0) {
            key = "prompt";
            // Concatenate all prompts by newline
            value = decodedSettings[key].join("\n");
        }

        if (value === "true") {
            value = true;
        } else if (value === "false") {
            value = false;
        }
        if (modelKeys.includes(key)) {
            console.log("Key: ", key, " Value: ", value);
            if (key === "model") {
                inferModelSelect.setValue(value);
            } else if (key === "loras") {
                loraModelSelect.setValue(value);
            } else {
                vaeModelSelect.setValue(value);
            }
        } else {
            if (key.indexOf("controlnet_") === -1) {
                key = "infer_" + key;
            }
            setElementValue(key, value);
        }
    }
    updateRatioButtons();
}

function setElementValue(id, value) {
    let inputElement = document.getElementById(id);
    if (inputElement === null) {
        console.log("Could not find element with id: ", id);
        return;
    }

    console.log("Setting element value: ", id, " to ", value);
    if (inputElement.classList.contains("bootstrapSlider")) {
        let bs = $(inputElement).BootstrapSlider();
        bs.setValue(value);
    } else if (inputElement.classList.contains("fileBrowser")) {
        let fileBrowser = $(inputElement).fileBrowser();
        fileBrowser.setValue(value);
    } else if (inputElement.type === "checkbox") {
        inputElement.checked = value;
    } else if (inputElement.classList.contains("model-select")) {
        let modelSelect = $(inputElement).modelSelect();
        modelSelect.setValue(value);
    } else if (inputElement.classList.contains("image-editor")) {
        let imageEditor = $(inputElement).imageEditor();
        imageEditor.setDropped(value["image"]);
        imageEditor.setMask(value["mask"]);
    } else {
        inputElement.value = value;
    }
    // If the element is a bootstrap slider, set the value using the slider's setValue method

}

function aspectRatioValue(ratio) {
    const [width, height] = ratio.split(":");
    return parseInt(width) / parseInt(height);
}


function updateRatioButtons() {
    let currentWidth = widthSlider.getValue();
    let currentHeight = heightSlider.getValue();

    const aspectRatios = ["16:9", "5:4", "4:3", "1:1", "3:4", "4:5", "9:16"];
    const targetAspectRatio = currentWidth / currentHeight;

    // Find the closest aspect ratio
    let closestRatio = aspectRatios[0];
    let closestDifference = Math.abs(targetAspectRatio - aspectRatioValue(aspectRatios[0]));

    for (let i = 1; i < aspectRatios.length; i++) {
        const currentDifference = Math.abs(targetAspectRatio - aspectRatioValue(aspectRatios[i]));
        if (currentDifference < closestDifference) {
            closestDifference = currentDifference;
            closestRatio = aspectRatios[i];
        }
    }


    // Get the index of the closest aspect ratio in the array
    const closestIndex = aspectRatios.indexOf(closestRatio);
    console.log("Closest index: ", closestIndex);
    // Iterate through the buttons and set the closest aspect ratio as selected
    const buttons = document.querySelectorAll('.aspectButton');
    buttons.forEach((button, index) => {
        if (index === closestIndex) {
            button.classList.add('btn-selected');
            setResolution(button.dataset.ratio);
        } else {
            button.classList.remove('btn-selected');
        }
    });

}

function getInferSettings() {
    let promptEl = document.getElementById("infer_prompt");
    let negEl = document.getElementById("infer_negative_prompt");
    let seedEl = document.getElementById("infer_seed");
    let controlnetType = document.getElementById("controlnet_type");
    const loras = loraModelSelect.getModel();
    inferSettings.loras = loras ? loras : [];
    inferSettings.model = inferModelSelect.getModel();
    inferSettings.vae = vaeModelSelect.getModel();
    inferSettings.prompt = promptEl.value;
    inferSettings.pipeline = $("#infer_pipeline").val();
    inferSettings.negative_prompt = negEl.value;
    inferSettings.seed = parseInt(seedEl.value);
    inferSettings.scale = scaleTest.value;
    inferSettings.steps = parseInt(stepTest.value);
    inferSettings.num_images = parseInt(numImages.value);
    inferSettings.batch_size = parseInt(batchSize.value);
    inferSettings.lora_weight = loraWeight.value;
    inferSettings.controlnet_mask = controlnetImageEditor.getMask();
    inferSettings.controlnet_image = controlnetImageEditor.getDropped();
    inferSettings.infer_mask = inpaintImageEditor.getMask();
    inferSettings.infer_image = inpaintImageEditor.getDropped();
    inferSettings.infer_scale_mode = $("#infer_scale_mode").val();
    inferSettings.controlnet_scale_mode = $("#controlnet_scale_mode").val();
    inferSettings.controlnet_type = controlnetType.value;
    inferSettings.controlnet_preprocess = document.getElementById("controlnet_preprocess").checked;
    inferSettings.controlnet_batch = document.getElementById("controlnet_batch").checked;
    inferSettings.controlnet_batch_dir = controlnetFileBrowser.value;
    inferSettings.controlnet_batch_find = document.getElementById("controlnet_batch_find").value;
    inferSettings.controlnet_batch_replace = document.getElementById("controlnet_batch_replace").value;
    inferSettings.controlnet_batch_use_prompt = document.getElementById("controlnet_batch_use_prompt").checked;
    inferSettings.use_control_resolution = $("#infer_use_control_resolution").is(":checked");
    inferSettings.use_input_resolution = $("#infer_use_input_resolution").is(":checked");

    const pipelineElements = document.querySelectorAll('[id^="pipeline_"]');
    inferSettings.pipeline_settings = {};
    pipelineElements.forEach((element) => {
        let elementId = element.id;
        // If the element's ID has "_container" or "_range" in it, continue
        if (element.id.includes("_container") || element.id.includes("_range")) {
            return;
        }
        if (elementId === "pipeline_controller" && inferSettings.pipeline !== "StableDiffusionPrompt2PromptPipeline") {
            return;
        }
        let eleValue = element.value;

        // If the element's ID has "_number" in it, remove _number from the "key" and parse the value as a float
        if (element.id.includes("_number")) {
            elementId = element.id.replace("_number", "");
            eleValue = parseFloat(element.value);
        }

        // Make sure we parse check values
        if (element.type === "checkbox") {
            eleValue = element.checked;
        }
        elementId = elementId.replace("pipeline_", "");
        inferSettings.pipeline_settings[elementId] = eleValue;
    });
    if (inferSettings.pipeline.indexOf("ControlNet") > -1 && inferSettings.image !== undefined) {
        inferSettings.image = controlnetImageEditor.imageSource;
    }
    if (userConfig["show_aspect_ratios"]) {
        const selectedRatio = document.querySelector(".aspectButton.btn-selected");
        setResolution(selectedRatio.dataset.ratio);
    } else {
        inferSettings.width = parseInt(widthSlider.value);
        inferSettings.height = parseInt(heightSlider.value);
    }
    console.log("Infer settings: ", inferSettings);
}