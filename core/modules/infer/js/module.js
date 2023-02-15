let gallery;
let fileTest;
document.addEventListener("DOMContentLoaded", function (event) {
    console.log("Inferload...");
    registerModule("Inference", "moduleInfer", "images")

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

    fileTest = new FileBrowser(document.getElementById("fileTest"), true, true);


    gallery = new InlineGallery('inferGallery', {}, dynamicElements);
    gallery.openGallery();
    console.log("Gallery:", gallery);
    let scaleSlider = document.getElementById("scaleSlider");
    let stepSlider = document.getElementById("stepSlider");
    let scaleTest = new BootstrapSlider(scaleSlider, {
        elem_id: "scaleSlid",
        min: 1,
        max: 20,
        step: 0.1,
        value: 7.5,
        label: "Scale"
    });

    let stepTest = new BootstrapSlider(scaleSlider, {
        elem_id: "stepSlid",
        min: 5,
        max: 100,
        value: 40,
        step: 1,
        label: "Steps"
    });

    console.log("Scale Test: ", scaleTest);
    let modelSelection = document.getElementById("inferModelSelection");
    let modelList = sendMessage("list_models", {});
});