let gallery;
let moduleSelect;
let inferProgress;
let scaleTest, stepTest, numImages, batchSize, widthSlider, heightSlider;

let inferSettings = {
    "prompt": "",
    "negative_prompt": "",
    "steps": 20,
    "scale": 7.5,
    "num_images": 1,
    "batch_size": 1,
    "width": 512,
    "height": 512,
    "model": undefined
}

function inferResponse(data) {
    //console.log("Inference response received: ", data);
}
// Wait till the doc is loaded
document.addEventListener("DOMContentLoaded", function () {
    // Register the module with the UI. Icon is from boxicons by default.
    registerModule("Inference", "moduleInfer", "images", true)
    registerSocketMethod("infer", "infer", inferResponse);
    keyListener.register("ctrl+Enter","#inferSettings", startInference);
    let promptEl = document.getElementById("infer_prompt");
    let negEl = document.getElementById("infer_negative_prompt");
    let seedEl = document.getElementById("infer_seed");


    // fileTest = new FileBrowser(document.getElementById("fileTest"), true, true);

    // Create model select element
    moduleSelect = new ModelSelect(document.getElementById("inferModel"), {
        label: "Model Selection:",
        load_on_select: true, // Enable auto-loading model on selected...needs code in modelHandler
        "model_type": "diffusers"
    });

    // Example change handler for module Selector, use it to update info about the loaded model or something.
    moduleSelect.setOnChangeHandler(function (data) {
        inferSettings.model = data;
    });

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
        value: 40,
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

    promptEl.addEventListener("change", function () {
        inferSettings["prompt"] = promptEl.value;
    });

    negEl.addEventListener("change", function () {
        inferSettings["negativePrompt"] = negEl.value;
    });

    seedEl.addEventListener("change", function () {
        inferSettings["seed"] = parseInt(seedEl.value);
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

    submit.addEventListener("click", function () {startInference().then(function (result) {})});
});

async function startInference() {
    gallery.clear();
    inferProgress.clear();
    const model = moduleSelect.getModel();

    if (model === undefined) {
        return alert("Please select a model.");
    } else {
        let promptEl = document.getElementById("infer_prompt");
        let negEl = document.getElementById("infer_negative_prompt");
        let seedEl = document.getElementById("infer_seed");

        inferSettings.model = model;
        inferSettings.prompt = promptEl.value;
        inferSettings.negativePrompt = negEl.value;
        inferSettings.seed = parseInt(seedEl.value);
		inferSettings.scale = scaleTest.value;
        inferSettings.steps = parseInt(stepTest.value);
        inferSettings.num_images = parseInt(numImages.value);
        inferSettings.batch_size = parseInt(batchSize.value);
        return sendMessage("start_inference", inferSettings, false);
    }
}
