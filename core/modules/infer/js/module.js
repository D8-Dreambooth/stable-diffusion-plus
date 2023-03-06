let gallery;
let moduleSelect;
let inferProgress;

let inferSettings = {
    "prompt": "",
    "negative_prompt": "",
    "steps": 20,
    "scale": 7.5,
    "num_images": 1,
    "batch_size": 1,
    "model": undefined
}

function inferResponse(data) {
    console.log("Inference response received: ", data);
}
// Wait till the doc is loaded
document.addEventListener("DOMContentLoaded", function () {
    // Register the module with the UI. Icon is from boxicons by default.
    registerModule("Inference", "moduleInfer", "images", true)
    registerSocketMethod("infer", "infer", inferResponse);
    // Sample stuff, just to play with the gallery.
    const dynamicElements = [
        {
            path: "https://www.hollywoodreporter.com/wp-content/uploads/2023/01/Nicholas-Cage-Butchers-Crossing-Pre-Premiere-Party-Getty-1422410956-H-2023.jpg?w=1296",
            caption: "Nicholas Cage at Butchers Crossing Pre-Premiere Party",
            description: "Nicholas Cage attends the pre-premiere party of Butchers Crossing.",
        },
        {
            path: "https://trekmovie.com/wp-content/uploads/2023/01/cagepike2-head-777x437.jpg",
            caption: "Nicholas Cage and Anson Mount in Star Trek: Strange New Worlds",
            description: "Nicholas Cage and Anson Mount appear in the new Star Trek series, Strange New Worlds.",
        },
        {
            path: "https://assets-prd.ignimgs.com/2022/04/20/nic-cage-lotr-matrix-1650496166807.jpg",
            caption: "Nicholas Cage to appear in Lord of the Rings and The Matrix sequels",
            description: "Nicholas Cage has signed on to appear in the upcoming sequels to Lord of the Rings and The Matrix.",
        },
        {
            path: "https://cdn.mos.cms.futurecdn.net/grU4VrTscKgjJRMgUU6wiH-1200-80.jpg",
            caption: "Nicholas Cage to star in new action thriller",
            description: "Nicholas Cage has been cast in a new action thriller set to release later this year.",
        },
    ];

    let promptEl = document.getElementById("infer_prompt");
    let negEl = document.getElementById("infer_negative_prompt");
    let seedEl = document.getElementById("infer_seed");

    promptEl.addEventListener("change", function () {
        inferSettings["prompt"] = promptEl.value;
    });

    negEl.addEventListener("change", function () {
        inferSettings["negativePrompt"] = negEl.value;
    });

    seedEl.addEventListener("change", function () {
        inferSettings["seed"] = parseInt(seedEl.value);
    });
    // fileTest = new FileBrowser(document.getElementById("fileTest"), true, true);

    // Create model select element
    moduleSelect = new ModelSelect(document.getElementById("inferModel"), {
        label: "Model Selection:",
        load_on_select: true, // Enable auto-loading model on selected...needs code in modelHandler
        "model_type": "diffusers" // Type of model...duh.
    });

    // Example change handler for module Selector, use it to update info about the loaded model or something.
    moduleSelect.setOnChangeHandler(function (data) {
        // The data element is the whole model info, not just a string.
        console.log("Model changed: ", data);
        inferSettings.model = data;
    });

    // Progress group example. Options can also be passed to inferProgress.update() in the same format.
    inferProgress = new ProgressGroup(document.getElementById("inferProgress"), {
        "primary_status": "Status 1", // Status 1 text
        "secondary_status": "Status 2", // Status 2...
        "bar1_progress": 10, // Progressbar 1 position
        "bar2_progress": 40 // etc
    });

    // Gallery creation. Options can also be passed to .update()
    gallery = new InlineGallery(document.getElementById('inferGallery'),
        {
            "thumbnail": true,
            "closeable": false,
            "show_maximize": true,
            "start_open": true,
            "data": dynamicElements
        }
    );

    let scaleTest = new BootstrapSlider(document.getElementById("infer_scale"), {
        elem_id: "scaleSlid",
        min: 1,
        max: 20,
        step: 0.1,
        value: 7.5,
        label: "Scale"
    });

    scaleTest.setOnChange(function (value) {
        inferSettings.scale = value
    })

    let widthSlider = new BootstrapSlider(document.getElementById("infer_width"), {
        elem_id: "widthSlid",
        min: 256,
        max: 4096,
        value: 512,
        step: 64,
        label: "Width"
    });

    let heightSlider = new BootstrapSlider(document.getElementById("infer_height"), {
        elem_id: "heightSlid",
        min: 256,
        max: 4096,
        value: 512,
        step: 64,
        label: "Height"
    });



    let stepTest = new BootstrapSlider(document.getElementById("infer_steps"), {
        elem_id: "stepSlid",
        min: 5,
        max: 100,
        value: 40,
        step: 1,
        label: "Steps"
    });

    stepTest.setOnChange(function (value) {
        inferSettings.steps = value
    })

    let numImages = new BootstrapSlider(document.getElementById("infer_num_images"), {
        elem_id: "numImages",
        min: 1,
        max: 100,
        value: 1,
        step: 1,
        label: "Number of Images"
    });

    numImages.setOnChange(function (value) {
        inferSettings.num_images = value
    })

    // Same as above. Why not?
    let batchSize = new BootstrapSlider(document.getElementById("infer_batch_size"), {
        elem_id: "batchSize",
        min: 1,
        max: 100,
        value: 1,
        step: 1,
        label: "Batch Size",
        model: undefined
    });

    batchSize.setOnChange(function (value) {
        inferSettings.batch_size = value
    })

    let submit = document.getElementById("startInfer");
    let cancel = document.getElementById("stopInfer");

    submit.addEventListener("click", function () {
        console.log("Clicked?")
        startInference().then(function (result) {
            console.log("Inference started.", result);
        })
    });
});

async function startInference() {
    return sendMessage("start_inference", inferSettings, false);
}
