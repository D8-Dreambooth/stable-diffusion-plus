// registerModule("Files", "moduleFileBrowser", "folder-open", false, 3);
const fileBrowserModule = new Module("Files", "moduleFileBrowser", "folder-open", false, 3, initFileBrowser);

function initFileBrowser() {
    console.log("FB Init: ", fileBrowserModule);
    // Register the module with the UI. Icon is from boxicons by default.
    new FileBrowser(
        document.getElementById("fileContainer"), {
            "listFiles": true,
            "expand": true,
            "placeholder": "",
            "dropdown": false,
            "showTitle": false,
            "showInfo": true
        });
}