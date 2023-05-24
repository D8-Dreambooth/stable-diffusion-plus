let dragGanEditor;
const dragGanModule = new Module(
    "DragGan", // Module name
    "moduleDraggan", // Module id
    "outline", // Module icon, use https://boxicons.com/ for reference
    false,
    -1,
    initDragGan);

function initDragGan() {
    console.log("Loaded module!: ", dragGanModule.name);
    dragGanEditor = new ImageEditor("dragGanGallery", "512px", "auto", true);
    let dragStopBtn = document.getElementById("dragStopBtnStop");
    let dragStartBtn = document.getElementById("dragStartBtnStart");
    let steps = $("#drag_gan_steps").BootstrapSlider({});
    let mask_radius = $("#drag_gan_mask_radius").BootstrapSlider({});
    let lambda = $("#drag_gan_lambda").BootstrapSlider({});

    dragStartBtn.addEventListener("click", function () {
        let targetImage = dragGanEditor.getDropped();
        if (targetImage) {
            console.log("DragGan: ", targetImage);
            let points = dragGanEditor.points;
            let message = {
                "image": targetImage,
                "points": points,
                "lambda": lambda.val(),
                "steps": steps.val(),
                "mask_radius": mask_radius.val()
            };
            sendMessage("dragGanStart", message, true).then(function (response) {
                console.log("DragGan Response: ", response);
            });
        } else {
            console.log("DragGan: No image dropped!", targetImage);
        }
    });
    dragStopBtn.addEventListener("click", function () {
        sendMessage("dragGanStop", {}, true).then(function (response) {
            console.log("DragGan Stop Response: ", response);
        });
    });
}