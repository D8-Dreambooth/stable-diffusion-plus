const analyzeModule = new Module(
    "Analyze", // Module name
    "moduleAnalyze", // Module id
    "analyse", // Module icon, use https://boxicons.com/ for reference
    false,
    -1,
    initAnalyze);

function initAnalyze() {
    console.log("Loaded module!: ", analyzeModule.name);
    // Your code here

}