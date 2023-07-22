const scraperModule = new Module(
    "Scraper", // Module name
    "moduleScraper", // Module id
    "image-add", // Module icon, use https://boxicons.com/ for reference
    false,
    -1,
    initScraper);

function initScraper() {
    console.log("Loaded module!: ", scraperModule.name);
    // Your code here
    sendMessage("get_scraper_params", {}, true).then((data) => {
        let params = data["params"];
        let keys = params["keys"];
        console.log("Params: ", params);
        let paramContainer = $("#scraperParams");
        // Enumerate key/value pairs in params
        for (let key in params) {
            let value = params[key];
            value["key"] = key;
            console.log("Key (scraper): ", key, " Value: ", value);
            let element = $("#scraper_" + key);
            if (element.length === 0) {
                element = createElement(value, "scraper", ["scraperParam"]);
                console.log("Element (scraper): ", element);
                if (element != null) {
                    console.log("Appending element (scraper): ", element);
                    paramContainer.append(element);
                } else {
                    console.log("Element (scraper) is null: ", params[key]);
                }
            }

        }
    });
    $("#startScraper").click(() => {
        let elements = $(".scraperParam");
        let params = {};
        for (let i = 0; i < elements.length; i++) {
            let element = elements[i];
            let key = element.id;
            key = key.replace("scraper_", "");
            params[key] = getElementValue(element.id);
        }
        console.log("Scraper params: ", params);
        sendMessage("scrape_images", {"params": params}, true).then((data) => {
            console.log("Scraper started: ", data);
        });
    });
    scraperProgress = new ProgressGroup(document.getElementById("scraperProgress"), {
        "primary_status": "Status 1", // Status 1 text
        "secondary_status": "Status 2", // Status 2...
        "bar1_progress": 0, // Progressbar 1 position
        "bar2_progress": 0,
        "id": "scraper"// etc
    });

    // Gallery creation. Options can also be passed to .update()
    gallery = new InlineGallery(document.getElementById('scraperGallery'), {
        "thumbnail": true,
        "closeable": false,
        "show_maximize": true,
        "start_open": true,
        "id": "scraper"
    });

}