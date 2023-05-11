let gallery;
let inferProgress;
let scaleTest, stepTest, numImages, batchSize, widthSlider, heightSlider;
let userConfig;
let controlnetImageEditor;
let controlnetFileBrowser;
const moduleSelect = $("#inferModel").modelSelect();
const lorasSelect = $("#inferLoraModels").modelSelect();
const ratioContainer = $("#infer_ratios");
const inferWidth = $("#infer_width");
const inferHeight = $("#infer_height");
const advancedElements = $(".advancedInfer");
const inpaintContainer = $("#inpaintContainer");

let inpaintImageEditor;
let inferSettings = {
    "prompt": "",
    "mode": "infer",
    "negative_prompt": "",
    "steps": 20,
    "scale": 7.5,
    "use_sag": true,
    "num_images": 1,
    "batch_size": 1,
    "width": 512,
    "height": 512,
    "model": undefined,
    "loras": undefined,
    "infer_mask": undefined,
    "infer_image": undefined,
    "controlnet_mask": undefined,
    "controlnet_image": undefined,
    "controlnet": false,
    "controlnet_type": undefined,
    "controlnet_preprocess": true,
    "controlnet_batch": false,
    "controlnet_batch_dir": "",
    "controlnet_batch_find": "",
    "controlnet_batch_replace": "",
    "controlnet_batch_use_prompt": false
}

advancedElements.hide();
ratioContainer.hide();
inferWidth.hide();
inferHeight.hide();

const inferModule = new Module("Inference", "moduleInfer", "images", true, 1, inferInit);

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

    widthSlider = $("#infer_width").BootstrapSlider({
        elem_id: "widthSlid",
        min: 256,
        max: 4096,
        value: 512,
        step: 64,
        label: "Width"
    });

    heightSlider = $("#infer_height").BootstrapSlider({
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


    controlnetFileBrowser = new FileBrowser(document.getElementById("controlnetBatchFileSelect"), {
        "file_type": "image",
        "showSelectButton": true,
        "listFiles": false,
        "showTitle": false,
        "showInfo": false,
        "multiselect": false,
        "dropdown": true
    });
    controlnetImageEditor = new ImageEditor("controlnetEditor", 512, 512);
    inpaintImageEditor = new ImageEditor("inpaintEditor", 512, 512);

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
                            applyInferSettings(data["image_data"]);
                        }
                    });
                };
                reader.readAsDataURL(file);
            }
        });
    });

    $("#controlnet_batch").change(function () {
        console.log("Controlnet changed", this.checked);
        if (this.checked) {
            $(".controlnetSingle").hide();
            $(".controlnetBatch").show();
        } else {
            $(".controlnetSingle").show();
            $(".controlnetBatch").hide();
        }
    });

    const radioButtons = document.getElementsByName('inferMode');
    for (let i = 0; i < radioButtons.length; i++) {
        radioButtons[i].addEventListener('change', function () {
            if (this.value === "txt2img") {
                inpaintContainer.hide();
            } else {
                inpaintContainer.show();
            }
        });
    }
    let moduleSettings = inferModule.systemConfig;
    loadSettings(moduleSettings);
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
    console.log("Infer settings: ", inferSettings);
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

function loadSettings(data) {
    console.log("Data: ", data);
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
        addRatioCards();
        ratioContainer.show();
    } else {
        inferWidth.show();
        inferHeight.show();
    }
}

function addRatioCards() {
    const ratioContainer = document.querySelector("#infer_ratios");
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

    width = Math.floor(width / 64) * 64;
    height = Math.floor(height / 64) * 64;
    inferSettings.width = width;
    inferSettings.height = height;
    controlnetImageEditor.scaleCanvas(width, height);

    console.log("Updated infer settings: ", inferSettings);
    return {width, height};
}

async function startInference() {
    gallery.clear();
    inferProgress.clear();
    console.log("MS: ", moduleSelect);
    const model = moduleSelect[0].val();

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

function applyInferSettings(decodedSettings) {
    let promptEl = document.getElementById("infer_prompt");
    let negEl = document.getElementById("infer_negative_prompt");
    let seedEl = document.getElementById("infer_seed");
    let enableControlNet = document.getElementById("enable_controlnet");
    let controlnetType = document.getElementById("controlnet_type");
    let autoLoadResolution = document.getElementById("autoLoadResolutionOn");
    let enableSag = document.getElementById("infer_sag");
    let controlnet_mask = controlnetImageEditor.getMask();
    let controlnet_image = controlnetImageEditor.getDropped();
    let infer_mask = inpaintImageEditor.getMask();
    let infer_image = inpaintImageEditor.getDropped();

    promptEl.value = decodedSettings.prompt;
    negEl.value = decodedSettings.negative_prompt;
    seedEl.value = decodedSettings.seed.toString();
    enableControlNet.checked = decodedSettings.enable_controlnet;
    controlnetType.value = decodedSettings.controlnet_type;
    autoLoadResolution.checked = false;  // Set to true if image is set below
    enableSag.checked = decodedSettings.use_sag;
    // controlnetImageEditor.setMask(decodedSettings.controlnet_mask);
    // controlnetImageEditor.setDropped(decodedSettings.controlnet_image);
    // inpaintImageEditor.setMask(decodedSettings.infer_mask);
    // inpaintImageEditor.setDropped(decodedSettings.infer_image);

    const radioButtons = document.getElementsByName('inferMode');
    let inferMode = decodedSettings.mode;

    for (let i = 0; i < radioButtons.length; i++) {
        if (radioButtons[i].value === inferMode) {
            radioButtons[i].checked = true;
            break;
        }
    }

    if (decodedSettings.enable_controlnet && decodedSettings.image !== undefined) {
        autoLoadResolution.checked = true;
        controlnetImageEditor.setResolution(decodedSettings.width, decodedSettings.height);
        controlnetImageEditor.setImage(decodedSettings.image);
    } else {
        widthSlider.setValue(decodedSettings.width);
        heightSlider.setValue(decodedSettings.height);

        const aspectRatios = ["16:9", "5:4", "4:3", "1:1", "3:4", "4:5", "9:16"];
        const targetAspectRatio = decodedSettings.width / decodedSettings.height;

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

        function aspectRatioValue(ratio) {
            const [width, height] = ratio.split(":");
            return parseInt(width) / parseInt(height);
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


    scaleTest.setValue(decodedSettings.scale);
    stepTest.setValue(decodedSettings.steps);
    numImages.setValue(decodedSettings.num_images);
    batchSize.setValue(decodedSettings.batch_size);
    document.getElementById("controlnet_preprocess").checked = decodedSettings.controlnet_preprocess;
    document.getElementById("controlnet_batch").checked = decodedSettings.controlnet_batch;
    controlnetFileBrowser.value = decodedSettings.controlnet_batch_dir;
    document.getElementById("controlnet_batch_find").value = decodedSettings.controlnet_batch_find;
    document.getElementById("controlnet_batch_replace").value = decodedSettings.controlnet_batch_replace;
    document.getElementById("controlnet_batch_use_prompt").checked = decodedSettings.controlnet_batch_use_prompt;
}

function getInferSettings() {
    let promptEl = document.getElementById("infer_prompt");
    let negEl = document.getElementById("infer_negative_prompt");
    let seedEl = document.getElementById("infer_seed");
    let enableControlNet = document.getElementById("enable_controlnet");
    let controlnetType = document.getElementById("controlnet_type");
    let autoLoadResolution = document.getElementById("autoLoadResolutionOn");
    let enableSag = document.getElementById("infer_sag");
    let controlnet_mask = controlnetImageEditor.getMask();
    let controlnet_image = controlnetImageEditor.getDropped();
    let infer_mask = inpaintImageEditor.getMask();
    let infer_image = inpaintImageEditor.getDropped();
    const loras = lorasSelect[0].val();
    const radioButtons = document.getElementsByName('inferMode');
    let inferMode = 'txt2img';

    for (let i = 0; i < radioButtons.length; i++) {
        if (radioButtons[i].checked) {
            inferMode = radioButtons[i].value;
            break;
        }
    }
    const model = moduleSelect[0].val();

    inferSettings.mode = inferMode;
    inferSettings.model = model;
    inferSettings.loras = loras;
    inferSettings.prompt = promptEl.value;
    inferSettings.negative_prompt = negEl.value;
    inferSettings.seed = parseInt(seedEl.value);
    inferSettings.scale = scaleTest.value;
    inferSettings.use_sag = enableSag.checked;
    inferSettings.steps = parseInt(stepTest.value);
    inferSettings.num_images = parseInt(numImages.value);
    inferSettings.batch_size = parseInt(batchSize.value);
    inferSettings.controlnet_mask = controlnet_mask;
    inferSettings.controlnet_image = controlnet_image;
    inferSettings.infer_mask = infer_mask;
    inferSettings.infer_image = infer_image;
    inferSettings.enable_controlnet = enableControlNet.checked;
    inferSettings.controlnet_type = controlnetType.value;
    inferSettings.controlnet_preprocess = document.getElementById("controlnet_preprocess").checked;
    inferSettings.controlnet_batch = document.getElementById("controlnet_batch").checked;
    inferSettings.controlnet_batch_dir = controlnetFileBrowser.value;
    inferSettings.controlnet_batch_find = document.getElementById("controlnet_batch_find").value;
    inferSettings.controlnet_batch_replace = document.getElementById("controlnet_batch_replace").value;
    inferSettings.controlnet_batch_use_prompt = document.getElementById("controlnet_batch_use_prompt").checked;

    if (enableControlNet.checked && autoLoadResolution.checked && inferSettings.image !== undefined) {
        inferSettings.width = controlnetImageEditor.originalResolution.width;
        inferSettings.height = controlnetImageEditor.originalResolution.height
        inferSettings.image = controlnetImageEditor.imageSource;
    } else {
        if (userConfig["show_aspect_ratios"]) {
            const selectedRatio = document.querySelector(".aspectButton.btn-selected");
            setResolution(selectedRatio.dataset.ratio);
        } else {
            inferSettings.width = parseInt(widthSlider.value);
            inferSettings.height = parseInt(heightSlider.value);
        }
    }
}