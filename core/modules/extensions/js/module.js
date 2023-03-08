document.addEventListener("DOMContentLoaded", function (event) {
    sendMessage("get_config",{"section_key": "extensions"}).then((data)=>{
        console.log("EXTDATA: ", data);
        if (data["enable"]) {
            loadModule();
        }
    });
});

function loadModule() {
    registerModule("Extension", "moduleExtensions", "extension");
}