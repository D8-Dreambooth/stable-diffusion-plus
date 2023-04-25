let gallery;
let moduleSelect;
let inferProgress;
let scaleTest, stepTest, numImages, batchSize, widthSlider, heightSlider;
let userConfig;
let imageEditor;
let controlnetFileBrowser;

let inferSettings = {
    "prompt": "",
    "negative_prompt": "",
    "steps": 20,
    "scale": 7.5,
    "num_images": 1,
    "batch_size": 1,
    "width": 512,
    "height": 512,
    "model": undefined,
    "mask": undefined,
    "image": undefined,
    "controlnet": false,
    "controlnet_type": undefined,
    "controlnet_preprocess": true,
    "controlnet_batch": false,
    "controlnet_batch_dir": "",
    "controlnet_batch_find": "",
    "controlnet_batch_replace": "",
    "controlnet_batch_use_prompt": false
}

function inferResponse(data) {
    //console.log("Inference response received: ", data);
}

const ratioContainer = $("#infer_ratios");
const inferWidth = $("#infer_width");
const inferHeight = $("#infer_height");
const advancedSettings = $("#advancedInferSettings");
moduleSelect = $("#inferModel").modelSelect();
advancedSettings.hide();
ratioContainer.hide();
inferWidth.hide();
inferHeight.hide();

// Wait till the doc is loaded
document.addEventListener("DOMContentLoaded", function () {
    // Register the module with the UI. Icon is from boxicons by default.
    registerModule("Inference", "moduleInfer", "images", true, 1);
    registerSocketMethod("infer", "infer", inferResponse);
    keyListener.register("ctrl+Enter", "#inferSettings", startInference);

    let promptEl = document.getElementById("infer_prompt");
    let negEl = document.getElementById("infer_negative_prompt");
    let seedEl = document.getElementById("infer_seed");


    // Progress group example. Options can also be passed to inferProgress.update() in the same format.
    inferProgress = new ProgressGroup(document.getElementById("inferProgress"), {
        "primary_status": "Status 1", // Status 1 text
        "secondary_status": "Status 2", // Status 2...
        "bar1_progress": 0, // Progressbar 1 position
        "bar2_progress": 0 // etc
    });

    // Gallery creation. Options can also be passed to .update()
    gallery = new InlineGallery(document.getElementById('inferGallery'),
        {
            "thumbnail": true,
            "closeable": false,
            "show_maximize": true,
            "start_open": true
        }
    );

    scaleTest = new BootstrapSlider(document.getElementById("infer_scale"), {
        elem_id: "scaleSlid",
        min: 1,
        max: 20,
        step: 0.1,
        value: 7.5,
        label: "Scale"
    });


    widthSlider = new BootstrapSlider(document.getElementById("infer_width"), {
        elem_id: "widthSlid",
        min: 256,
        max: 4096,
        value: 512,
        step: 64,
        label: "Width"
    });

    heightSlider = new BootstrapSlider(document.getElementById("infer_height"), {
        elem_id: "heightSlid",
        min: 256,
        max: 4096,
        value: 512,
        step: 64,
        label: "Height"
    });

    stepTest = new BootstrapSlider(document.getElementById("infer_steps"), {
        elem_id: "stepSlid",
        min: 5,
        max: 100,
        value: 20,
        step: 1,
        label: "Steps"
    });


    numImages = new BootstrapSlider(document.getElementById("infer_num_images"), {
        elem_id: "numImages",
        min: 1,
        max: 100,
        value: 1,
        step: 1,
        label: "Number of Images"
    });


    // Same as above. Why not?
    batchSize = new BootstrapSlider(document.getElementById("infer_batch_size"), {
        elem_id: "batchSize",
        min: 1,
        max: 100,
        value: 1,
        step: 1,
        label: "Batch Size",
        model: undefined
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

    promptEl.addEventListener("change", function () {
        inferSettings["prompt"] = promptEl.value;
    });

    negEl.addEventListener("change", function () {
        inferSettings["negativePrompt"] = negEl.value;
    });

    seedEl.addEventListener("change", function () {
        inferSettings["seed"] = parseInt(seedEl.value);
    });

    $("#controlnetBatchInput").on("change", function () {
        let singleDivs = $(".controlnetSingle");
        let batchDivs = $(".controlnetBatch");
        if ($(this).is(":checked")) {
            singleDivs.hide();
            batchDivs.show();
        } else {
            singleDivs.show();
            batchDivs.hide();
        }
    });

    scaleTest.setOnChange(function (value) {
        inferSettings.scale = value
    })

    stepTest.setOnChange(function (value) {
        inferSettings.steps = value
    })

    numImages.setOnChange(function (value) {
        inferSettings.num_images = value
    })


    batchSize.setOnChange(function (value) {
        inferSettings.batch_size = value
    })

    let submit = document.getElementById("startInfer");
    let cancel = document.getElementById("stopInfer");
    let controlEditor = document.getElementById("controlnetEditor");
    imageEditor = new ImageEditor("controlnetEditor", 512, 512);

    submit.addEventListener("click", function () {
        startInference().then(function (result) {
        })
    });

    sendMessage("get_config", {"section_key": "infer"}).then((data) => {
        userConfig = data;
        loadSettings(data);
        console.log("Infer settings: ", userConfig);
    });
    sendMessage("get_controlnets", {}, true).then((data) => {
        console.log("Controlnets: ", data);
        let controlnetSelect = document.getElementById("controlnetType");
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
});

function loadSettings(data) {
    console.log("Data: ", data);
    const advancedSettings = $("#advancedInferSettings");

    if (data.hasOwnProperty("basic_infer")) {
        if (data.basic_infer) {
            advancedSettings.hide();
        } else {
            advancedSettings.show();
        }
    }
    if (data["show_aspect_ratios"]) {
        addRatioCards(data["max_resolution"]);
        ratioContainer.show();
    } else {
        inferWidth.show();
        inferHeight.show();
    }
}

function addRatioCards(max_resolution) {
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
    imageEditor.scaleCanvas(width, height);

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
        let seedEl = document.getElementById("infer_seed");
        let enableControlNet = document.getElementById("enableControlNet");
        let controlnetType = document.getElementById("controlnetType");
        let autoLoadResolution = document.getElementById("autoLoadResolutionOn");
        let mask = imageEditor.getMask();
        let image = imageEditor.getDropped();
        inferSettings.model = model;
        inferSettings.prompt = promptEl.value;
        inferSettings.negativePrompt = negEl.value;
        inferSettings.seed = parseInt(seedEl.value);
        inferSettings.scale = scaleTest.value;
        inferSettings.steps = parseInt(stepTest.value);
        inferSettings.num_images = parseInt(numImages.value);
        inferSettings.batch_size = parseInt(batchSize.value);
        inferSettings.mask = mask;
        inferSettings.image = image;
        inferSettings.enable_controlnet = enableControlNet.checked;
        inferSettings.controlnet_type = controlnetType.value;
        inferSettings.controlnet_preprocess = document.getElementById("controlnetPreProcess").checked;
        inferSettings.controlnet_batch = document.getElementById("controlnetBatchInput").checked;
        inferSettings.controlnet_batch_dir = controlnetFileBrowser.value;
        inferSettings.controlnet_batch_find = document.getElementById("controlnetBatchFind").value;
        inferSettings.controlnet_batch_replace = document.getElementById("controlnetBatchReplace").value;
        inferSettings.controlnet_batch_use_prompt = document.getElementById("controlnetBatchUsePrompt").checked;

        if (enableControlNet.checked && autoLoadResolution.checked && inferSettings.image !== undefined) {
            inferSettings.width = imageEditor.originalResolution.width;
            inferSettings.height = imageEditor.originalResolution.height
            inferSettings.image = imageEditor.imageSource;
        } else {
            if (userConfig["show_aspect_ratios"]) {
                const selectedRatio = document.querySelector(".aspectButton.btn-selected");
                setResolution(selectedRatio.dataset.ratio);
            } else {
                inferSettings.width = parseInt(widthSlider.value);
                inferSettings.height = parseInt(heightSlider.value);
            }
        }
        return sendMessage("start_inference", inferSettings, true);
    }
}
