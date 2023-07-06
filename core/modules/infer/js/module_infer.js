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
let controlnetData, preprocessorData;
let inferParams;


const ratioContainer = $("#infer_ratios");
const inferWidth = $("#infer_width");
const inferHeight = $("#infer_height");
const advancedElements = $(".infer_advanced");
const inpaintContainer = $("#inferInpaintCollapse");

let inpaintImageEditor;

advancedElements.hide();
ratioContainer.hide();
inferWidth.hide();
inferHeight.hide();

const inferModule = new Module(
    "Generate",
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
    inferModelSelect = $("#infer_model").modelSelect();
    vaeModelSelect = $("#infer_vae").modelSelect();
    loraModelSelect = $("#infer_loras").modelSelect();
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

    widthSlider = inferWidth.BootstrapSlider({
        min: 256,
        max: 4096,
        value: 512,
        step: 64,
        label: "Width"
    });

    heightSlider = inferHeight.BootstrapSlider({
        min: 256,
        max: 4096,
        value: 512,
        step: 64,
        label: "Height"
    });

    widthSlider.setOnChange(function (value) {
        inpaintImageEditor.updateCanvasWidth(value);
        controlnetImageEditor.updateCanvasWidth(value);
    });

    heightSlider.setOnChange(function (value) {
        inpaintImageEditor.updateCanvasHeight(value);
        controlnetImageEditor.updateCanvasHeight(value);
    });

    loraWeight = $("#infer_lora_weight").BootstrapSlider({
        elem_id: "lora_weight",
        min: 0.01,
        max: 1,
        value: 0.9,
        step: 0.01,
    });

    controlnetFileBrowser = $("#infer_controlnet_batch_dir").fileBrowser({
        "file_type": "image",
        "showSelectButton": true,
        "listFiles": false,
        "showTitle": false,
        "showInfo": false,
        "multiselect": false,
        "dropdown": true,
        "label": "Controlnet Batch Directory"
    });
    controlnetImageEditor = $("#infer_controlnet_image").imageEditor({
        "width": 512,
        "height": 512,
        "canvas_width": 512,
        "canvas_height": 512,
    });

    inpaintImageEditor = $("#infer_image").imageEditor({
        "width": 512,
        "height": 512,
        "canvas_width": 512,
        "canvas_height": 512,
    });

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
    sendMessage("get_params", {}, true).then((data) => {
        console.log("Params: ", data["params"]);
        data = data["params"];
        // Pop pipelines and keys from data
        pipelineData = data["pipelines"];
        let keys = data["keys"];
        delete data["pipelines"];
        delete data["keys"];
        console.log("Keys: ", keys);
        inferParams = data;
        let newParams = {};
        let autoContainer = $("#inferSettingsContainer");
        let groupElements = {};
        for (let key in data) {
            if (key === "mask" || key === "controlnet_mask") continue;
            let elemData = data[key];
            elemData["key"] = key;

            let group = "General";
            if (elemData.hasOwnProperty("group")) {
                group = elemData["group"];
            }

            let target = autoContainer;
            let groupTarget = $("#infer" + elemData["group"] + "Group");
            let lastElement = null;
            if (group in groupElements) {
                lastElement = groupElements[group];
            }
            if (groupTarget.length > 0) {
                target = groupTarget;
            }

            if (key === "processors" || key === "pipelines") {
                continue;
            }
            let uiKey = "infer_" + key;
            let elem = $("#" + uiKey);
            if (elem.length > 0) {
                // Get the form-group surrounding the element
                let formGroup = elem.closest(".form-group");
                groupElements[group] = formGroup[0];
            } else {
                let element = createElement(elemData, "infer", ["inferParam", "inferDrop"]);
                if (element !== null) {
                    element.classList.add("col-12", "col-md-6");
                    // If last element is null, append to auto container, otherwise insert after last element
                    if (lastElement === null) {
                        console.log("Inserting "+uiKey+ " into: ", groupTarget);
                        groupTarget.prepend(element);
                    } else {
                        console.log("Inserting "+uiKey+ " after: ", lastElement);
                        lastElement.after(element);
                    }
                    groupElements[group] = element;
                } else {
                    console.error("Failed to create element for: ", uiKey);
                }
            }
        }
        setListeners();
        loadInferSettings(moduleSettings);
        refreshControlNets();
    });


}

function setListeners() {
    $("#inpaint_origin").change(function () {
        inpaintImageEditor.updateImageOrigin(this.value);
    });

    $("#controlnet_origin").change(function () {
        controlnetImageEditor.updateImageOrigin(this.value);
    });

    $("#controlnetSettings").hide();
    $("#infer_pipeline").change(function () {
        console.log("Pipeline changed: ", this.value);
        updatePipelineSettings(this.value);
    });

    const inferUseControlResolution = $("#infer_use_control_resolution");
    const controlnetScaleModeContainer = $(".controlnet_scale_mode_container");
    const controlnetScaleMode = $("#controlnet_scale_mode");

    inferUseControlResolution.change(function () {
        const isChecked = inferUseControlResolution.is(":checked");
        controlnetImageEditor.updateUseImageScale(isChecked);
        if (!isChecked) {
            controlnetScaleModeContainer.show();
        } else {
            controlnetScaleModeContainer.hide();
        }
    });

    controlnetScaleMode.change(function () {
        if (!inferUseControlResolution.is(":checked")) {
            controlnetImageEditor.updateScaleMode(controlnetScaleMode.val());
        }
    });



    const inferUseInputResolution = $("#infer_use_input_resolution");
    const inferScaleMode = $("#infer_scale_mode");
    const scaleModeContainer = $(".scale_mode_container");

    inferUseInputResolution.change(function () {
        const isChecked = inferUseInputResolution.is(":checked");
        inpaintImageEditor.updateUseImageScale(isChecked);
        if (!isChecked) {
            scaleModeContainer.show();
        } else {
            scaleModeContainer.hide();
        }
    });
    scaleModeContainer.hide();
    inferScaleMode.change(function () {
        if (!inferUseInputResolution.is(":checked")) {
            inpaintImageEditor.updateScaleMode(inferScaleMode.val());
        }
    });


    $("#controlnet_type").change(function () {
        console.log("Controlnet type changed: ", this.value);
        // Get controlnet data from controlnetData if the value is in controlnetData
        if (controlnetData.hasOwnProperty(this.value)) {
            let controlnet = controlnetData[this.value];
            console.log("Controlnet: ", controlnet);
        }
    });
}


function refreshControlNets() {
    sendMessage("get_controlnets", {}, true).then((data) => {
        let controlnetSelect = document.getElementById("infer_controlnet_type");
        controlnetSelect.innerHTML = "";
        let option = document.createElement("option");
        option.value = "None";
        option.text = "";
        controlnetSelect.add(option);
        preprocessorData = data["detectors"];
        controlnetData = data["nets"];
        // Enumerate data, which is now a dict
        for (let key in controlnetData) {
            let element = controlnetData[key];
            let option = document.createElement("option");
            option.value = key;
            option.text = element["name"];
            controlnetSelect.add(option);
        }
    });
}


function updatePipelineSettings(pipelineName) {
    let pipelineParams = $("#pipelineParams");
    pipelineParams.empty();
    if (pipelineName === "auto") pipelineName = "Default";
    if (!pipelineData.hasOwnProperty(pipelineName)) {
        console.log("Pipeline not found: ", pipelineName);
        return;
    }
    let pipeline = pipelineData[pipelineName];

    let keysToIgnore = ["height", "width", "image", "latents", "source_enbeds", "target_embeds", "DOCSTRING",
            "cross_attention_kwargs", "prompt", "negative_prompt", "prompt_embeds", "negative_prompt_embeds", "mask_image", "controlnet_mask"];
        let keys = Object.keys(pipeline).filter(key => !keysToIgnore.includes(key));

    if (pipelineName !== "Default") {
        console.log("Pipeline: ", pipeline, pipelineData, keys);
        // Enumerate keyvalues in pipeline
        if (pipeline.hasOwnProperty("control_image")) {
            $("#controlnetSettings").show();
        } else {
            $("#controlnetSettings").hide();
        }

        if (pipeline.hasOwnProperty("image")) {
            inpaintContainer.show();
        } else {
            inpaintContainer.hide();
        }
        if (pipelineName === "StableDiffusionControlNetPipeline" || pipelineName === "StableDiffusionControlNetSAGPipeline") {
            inpaintContainer.hide();
        }
        // Sort pipeline by type, filtering keys to ignore
        keys.sort((a, b) => {
            if (pipeline[a].type < pipeline[b].type) {
                return 1;
            } else if (pipeline[a].type > pipeline[b].type) {
                return -1;
            } else {
                return 0;
            }
        });
        for (let idx in keys) {
            let key = keys[idx];
            if (key === "cls") continue;
            console.log("Key: ", key, " Value: ", pipeline[key]);
            let val = pipeline[key];
            // Add empty description to val if it doesn't exist
            if (!val.hasOwnProperty("description")) {
                val["description"] = "";
            }
            let element = createElement(val, "inferPipe", ["inferParam"]);
            if (element !== null) {
                element.classList.add("col-12");
                if (keys.length > 1) {
                    element.classList.add("col-lg-6");
                }
                pipelineParams.append(element);
            }
        }

    } else {
        inpaintContainer.hide();
        $("#infer_prompt2prompt").hide();
        $("#controlnetSettings").hide();
    }
}

function inferRefresh() {
    loadInferSettings(inferModule.systemConfig);
    refreshControlNets();
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
            console.log("Basic infer");
            $(".infer_advanced").hide();
        } else {
            console.log("Advanced infer");
            $(".infer_advanced").show();
            updatePipelineSettings($("#infer_pipeline").val());
        }
    } else {
        console.log("No basic_infer key in data: ", data);
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
        let inferSettings = getInferSettings();

        historyTracker.storeHistory(promptEl);
        historyTracker.storeHistory(negEl);

        return sendMessage("start_inference", inferSettings, true, "inference");
    }
}

function applyInferSettingsNew(decodedSettings) {
    console.log("Applying infer settings: ", decodedSettings);
    if ("pipeline" in decodedSettings && "pipeline_settings" in decodedSettings) {
        let pipeLine = decodedSettings["pipeline"];
        if (pipeLine === "auto") pipeLine = "Default";
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
    let params = {};
    console.log("Getting infer params: ", inferParams);
    for (let key in inferParams) {
        if (key === "pipelines" || key === "controlnets") continue;
        let lookKey = key;

        if (key === "mask" || key === "controlnet_mask") {
            console.log("Replacing mask with image", key);
            lookKey = key.replace("mask", "image");
        }
        let element = $("#infer_" + lookKey);
        if (element.length === 0) {
            console.log("Could not find element(0) with id: ", "infer_" + lookKey);
        } else {
            let elementValue;
            if (key === "mask" || key === "controlnet_mask" || key === "image" || key === "controlnet_image") {
                if (key === "mask") elementValue = inpaintImageEditor.getMask();
                if (key === "controlnet_mask") elementValue = controlnetImageEditor.getMask();
                if (key === "image") elementValue = inpaintImageEditor.getDropped();
                if (key === "controlnet_image") elementValue = controlnetImageEditor.getDropped();
                console.log("Setting image value: ", elementValue);
            } else {
                elementValue = getElementValue("infer_" + lookKey);
            }
            if (elementValue !== null) {
                params[key] = elementValue;
            }
        }
    }
    // Find all elements who's IDs start with inferPipe_
    let pipeElements = $("[id^=inferPipe_]");
    let pipeParams = {};
    for (let i = 0; i < pipeElements.length; i++) {
        let element = pipeElements[i];
        let id = element.id;
        let key = id.replace("inferPipe_", "");
        pipeParams[key] = getElementValue(id);
    }
    params["pipeline_settings"] = pipeParams;
    console.log("Infer settings: ", params);
    return params;
}


