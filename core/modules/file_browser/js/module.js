document.addEventListener("DOMContentLoaded", function () {
    // Register the module with the UI. Icon is from boxicons by default.
    registerModule("Files", "moduleFileBrowser", "folder-open", false, 3);
    let fc = new FileBrowser(
        document.getElementById("fileContainer"), {
            "listFiles": true,
            "expand": true,
            "placeholder": "",
            "dropdown": false,
            "showTitle": false,
            "showInfo": true
        });
});