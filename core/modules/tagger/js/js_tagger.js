let imageFileBrowser;

document.addEventListener("DOMContentLoaded", function (event) {
    sendMessage("get_config", {"section_key": "tagger"}).then((data) => {
        console.log("TAGDATA: ", data);
        if (data["enable"]) {
            loadModule();
        }
    });
});

function loadModule() {
    console.log("Loading tagger module.");
    registerModule("Tagger", "moduleTagger", "purchase-tag-alt", false, -1);
    imageFileBrowser = new FileBrowser(document.getElementById("imageFileSelect"), {
        "file_type": "image",
        "showSelectButton": true,
        "listFiles": false,
        "showTitle": false,
        "showInfo": false,
        "multiselect": false,
        "dropdown": true
    });

    imageFileBrowser.addOnSelect((file) => {
        console.log("FILE: ", file);
        let imageBrowser = document.getElementById("imageBrowser");
        let recursive = document.getElementById("imageRecurse").checked;
        imageBrowser.innerHTML = "";
        sendMessage("files", {
            start_dir: file,
            include_files: true,
            recursive: recursive,
            filter: [".jpg", ".jpeg", ".png", ".gif", ".webp"],
            thumbs: true,
            thumb_size: 128
        }).then((data) => {
            const items = data["items"];
            const thumbContainer = document.getElementById("imageBrowser");

            for (const path in items) {
                const thumbDataItem = items[path];

                // Create thumbnail element
                const thumbElem = document.createElement("div");
                thumbElem.classList.add("thumb");
                thumbElem.style.backgroundImage = `url(${thumbDataItem.thumb})`;
                thumbElem.tabIndex = -1;
                // Set path and tag in dataset
                thumbElem.dataset.path = path;
                thumbElem.dataset.tag = thumbDataItem.tag;

                // Add onclick listener
                thumbElem.onclick = async function () {
                    this.classList.add("selected");
                    this.focus();
                    let thumbElements = document.querySelectorAll("#imageBrowser .thumb");
                    for (const thumbElem of thumbElements) {    // Remove selected class from all other elements
                        if (thumbElem !== this) {
                            thumbElem.classList.remove("selected");
                        }
                    }
                    const response = await sendMessage("file", {files: [path]});
                    console.log("Res: ", response);
                    try {
                        let file = response["files"][0];
                        let src = file["src"];
                        let data = file["data"];
                        const fullImageElem = document.getElementById("fullImage");
                        fullImageElem.src = src;
                        const imageTagElem = document.getElementById("imageCaption");
                        imageTagElem.value = data;
                    } catch (e) {
                        console.error("Error: ", e);
                    }
                };

                // Append thumbnail element to container
                thumbContainer.appendChild(thumbElem);
            }
            console.log("Response: ", data);
        });
    });

    // Select the imageBrowser div and all thumb elements within it

// Set the initial selected index to 0
    let selectedIndex = 0;

// Add a keyboard listener to the document
    document.addEventListener("keydown", (event) => {
        const imageBrowser = document.getElementById("imageBrowser");
        const thumbs = imageBrowser.querySelectorAll(".thumb");
        const captionEditor = document.getElementById("imageCaption");
        // If the focused element is not a thumb, return early
        if (Array.from(thumbs).some((thumb) => thumb === document.activeElement)) {
            // Prevent the default arrow key behavior
            event.preventDefault();

            // Get the index of the currently focused thumb
            const currentIndex = Array.from(thumbs).indexOf(document.activeElement);
            console.log("KEY: ", event.key, "CUR: ", currentIndex);
            // Determine the index of the next thumb to select based on the arrow key
            if (event.key === "ArrowLeft") {
                selectedIndex = currentIndex === 0 ? thumbs.length - 1 : currentIndex - 1;
            } else if (event.key === "ArrowRight") {
                selectedIndex = currentIndex === thumbs.length - 1 ? 0 : currentIndex + 1;
            } else if (event.key === "ArrowUp") {
                const rowSize = Math.floor(imageBrowser.offsetWidth / thumbs[0].offsetWidth);
                const newIndex = currentIndex - rowSize;
                selectedIndex = newIndex < 0 ? thumbs.length + newIndex : newIndex;
            } else if (event.key === "ArrowDown") {
                const rowSize = Math.floor(imageBrowser.offsetWidth / thumbs[0].offsetWidth);
                const newIndex = currentIndex + rowSize;
                selectedIndex = newIndex >= thumbs.length ? newIndex - thumbs.length : newIndex;
            }

            // Set the focus on the newly selected thumb
            thumbs[selectedIndex].click();
        }

        if (captionEditor === document.activeElement && event.key === "Enter" && !event.ctrlKey) {
            // Prevent the default arrow key behavior
            event.preventDefault();

            // Get the index of the currently focused thumb
            const currentIndex = Array.from(thumbs).indexOf(document.querySelector(".thumb.selected"));
            console.log("KEY: ", event.key, "CUR: ", currentIndex);
            // Determine the index of the next thumb to select based on the arrow key
            selectedIndex = currentIndex === thumbs.length - 1 ? 0 : currentIndex + 1;
            checkSaveCaption().then(() => {
                console.log("Checksaved...");
                thumbs[selectedIndex].click();
                captionEditor.focus();
            });


        }

    });

}

async function checkSaveCaption() {
    console.log("CHECKSAVECAPTION");
    let captionEditor = document.getElementById("imageCaption");
    let caption = captionEditor.value;
    let thumb = document.querySelector(".thumb.selected");
    let path = thumb.dataset.path;
    let tag = thumb.dataset.tag;
    console.log("Caption: ", caption, "Tag: ", tag, "Path: ", path);
    if (caption !== tag) {
        console.log("Saving caption: ", caption);
        const response = await sendMessage("save_caption", {path: path, caption: caption});
        console.log("Res: ", response);
        thumb.dataset.tag = response["caption"];
    }
}