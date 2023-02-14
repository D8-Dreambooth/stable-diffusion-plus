document.addEventListener("DOMContentLoaded", function (event) {
    console.log("Extload...");
    registerModule("Extension", "moduleExtensions", "extension");
    let testButton = document.getElementById("testExtBtn");
    testButton.addEventListener("click", function() {
       sendMessage("extension", {foo: "foo"})
    });
});