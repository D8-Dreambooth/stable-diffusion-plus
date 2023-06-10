const postProcessingModule = new Module(
    "PostProcessing", // Module name
    "modulePostProcessing", // Module id
    "magic-wand", // Module icon, use https://boxicons.com/ for reference
    false,
    -1,
    initPostProcessing);

function initPostProcessing() {
    console.log("Loaded module!: ", postProcessingModule.name);
}