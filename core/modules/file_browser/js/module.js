document.addEventListener("DOMContentLoaded", function () {
    // Register the module with the UI. Icon is from boxicons by default.
    registerModule("Files", "moduleFileBrowser", "folder-open", false);
    let fc = new FileBrowser(
        document.getElementById("fileContainer"), {
            "listFiles": true,
            "expand": true,
            "placeholder": "",
            "dropdown": false,
            "showTitle": false,
            "style": "width: 100%; height: 100%;",
            "showInfo": true
        });
});