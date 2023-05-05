const analyzeFileSelect = document.getElementById("analyzeFileSelect");
let analyzeFileBrowser;
let analyzeImageEditor;
let analyzeOutput;


const analyzeModule = new Module(
    "Analyze", // Module name
    "moduleAnalyze", // Module id
    "analyse", // Module icon, use https://boxicons.com/ for reference
    false,
    -1,
    initAnalyze);

function initAnalyze() {
    console.log("Loaded module!: ", analyzeModule.name);
    analyzeFileBrowser = new FileBrowser(
        analyzeFileSelect, {
            "label": "Directory Selection",
            "listFiles": false,
            "expand": false,
            "placeholder": "Select A Directory",
            "dropdown": true,
            "showTitle": false,
            "showInfo": false,
            "showSelectButton": true,
            "selectedElement": "outputs\\inference"
        });
    analyzeImageEditor = new ImageEditor("analyzeFileContent", 512, 512);

    $("#analyzeFileButton").click(function() {
        let selectedFile = analyzeFileBrowser.value;
        let targetImage = analyzeImageEditor.getDropped();
        if (selectedFile && targetImage) {
            console.log("Analyze: ", selectedFile, targetImage);
            let message = {"path": selectedFile, "image": targetImage};
            sendMessage("analyze", message, true).then(function(response) {
                console.log("Analyze Response: ", response);
                analyzeOutput = response;
                $("#analyzeOutput").html(response);
            });
        }
    });

    new InlineGallery(document.getElementById("analyzeGallery"), {
        "id": "analyze",
    });
    new ProgressGroup(document.getElementById("analyzeProgress"),{
        "id": "analyze"
    })
}