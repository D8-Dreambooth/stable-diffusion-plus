document.addEventListener("DOMContentLoaded", function (event) {
    console.log("Inferload...");
    registerModule("Inference", "moduleInfer", "images");
    let testButton = document.getElementById("testBtn");
    testButton.addEventListener("click", function() {
       sendMessage("infer", {foo: "foo"})
    });
});