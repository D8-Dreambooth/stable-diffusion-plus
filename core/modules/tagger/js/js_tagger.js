let imageFileBrowser;
let captionData = {};
let lastSelected = null;
let thresholdSlider = null;
let characterSlider = null;
let tagProgress;
const taggerModule = new Module("Tagger", "moduleTagger", "purchase-tag-alt", false, -1, initTagger);

function initTagger() {
    console.log("Loading module: ", taggerModule.name);
    imageFileBrowser = $("#tagImageFileSelect").fileBrowser({
        "file_type": "image",
        "showSelectButton": true,
        "listFiles": false,
        "showTitle": false,
        "showInfo": false,
        "multiselect": false,
        "dropdown": true,
        "label": "Select Directory"
    });
    tagProgress = new ProgressGroup(document.getElementById("tagProgressGroup"), {"id": "tagProgressGroup"});
    tagProgress.setOnComplete(() => {
        imageFileBrowser.refresh();
    });
    thresholdSlider = $("#tagThreshold").BootstrapSlider({});
    characterSlider = $("#tagCharThreshold").BootstrapSlider({});

    $("#loadTagImages").click(() => {
        let directory = imageFileBrowser.value;
        let recurse = $("#imageRecurse").is(":checked");
        if (directory !== "") {
            let tagContainer = document.getElementById("tagContainer");
            tagContainer.innerHTML = "Loading...";
            loadImages(directory);
            sendMessage("tag_cloud", {
                path: directory,
                recurse: recurse
            }).then((response) => {
                loadTags(response["src"], response["tags"]);
            });
        }
    });

    // Add a document-wide listener for clicks on any .tagDeleteButton element
    document.addEventListener("click", (event) => {
        if (event.target.classList.contains("tagDeleteButton")) {
            event.preventDefault();
            // Get the "tag" from the event target parent's dataset
            const tag = event.target.parentElement.dataset.tag;
            const recurse = $("#imageRecurse").is(":checked");
            const directory = imageFileBrowser.value;
            sendMessage("tag_delete", {
                "tag": tag,
                "path": directory,
                "recurse": recurse
            }).then((response) => {
                event.target.parentNode.remove();
                // Enumerate all the thumbs again
                const updated = response["updated"];
                const thumbs = document.getElementById("imageBrowser").querySelectorAll(".thumb");
                // For each thumb, check the data-path against the keys in updated
                thumbs.forEach((thumb) => {
                    const path = thumb.dataset.path;
                    if (updated[path] !== undefined) {
                        // If the path is in updated, update the tags
                        thumb.dataset.tag = updated[path];
                    }
                });
            });
        }
    });

    $("#tag_edit_toggle").click(() => {
        $(".tagDeleteButton").toggle();
        $(this).toggleClass("active");
    });

    imageFileBrowser.addOnRefresh((file) => {
        let directory = imageFileBrowser.value;
        let recurse = $("#imageRecurse").is(":checked");
        if (directory !== "") {
            loadImages(directory);
            sendMessage("tag_cloud", {
                path: directory,
                recurse: recurse
            }).then((response) => {
                loadTags(response["src"], response["tags"]);
            });
        }
    });

    document.getElementById('sortType').addEventListener('change', sortTags);
    document.getElementById('sortOrder').addEventListener('change', sortTags);

    let selectedIndex = 0;
    // Add a keyboard listener to the document
    document.addEventListener("keydown", (event) => {
        const imageBrowser = document.getElementById("imageBrowser");
        const thumbs = imageBrowser.querySelectorAll(".thumb");
        const captionEditor = document.getElementById("imageCaption");
        let selectedThumbs = imageBrowser.querySelectorAll(".thumb.selected");
        if (thumbs.length === 0) return;
        const rowSize = Math.floor(imageBrowser.offsetWidth / thumbs[0].offsetWidth);
        const colSize = Math.floor(thumbs.length / rowSize);

        // If the focused element is not a thumb, return early
        if (Array.from(thumbs).some((thumb) => thumb === document.activeElement)) {

            // Prevent the default arrow key behavior
            selectedThumbs = imageBrowser.querySelectorAll(".thumb.selected");

            // Get the index of the currently focused thumbs
            const currentIndex = Array.from(thumbs).indexOf(lastSelected);

            // Determine the index of the next thumb to select based on the arrow key
            let selectedIndex = null;
            if (event.key === "ArrowLeft") {
                selectedIndex = currentIndex === 0 ? thumbs.length - 1 : currentIndex - 1;
            } else if (event.key === "ArrowRight") {
                selectedIndex = currentIndex === thumbs.length - 1 ? 0 : currentIndex + 1;
            } else if (event.key === "ArrowUp") {
                const currentRow = Math.floor(currentIndex / rowSize);
                const currentCol = currentIndex % rowSize;
                const newRow = currentRow === 0 ? colSize - 1 : currentRow - 1;
                selectedIndex = newRow * rowSize + currentCol;
            } else if (event.key === "ArrowDown") {
                const currentRow = Math.floor(currentIndex / rowSize);
                const currentCol = currentIndex % rowSize;
                const newRow = currentRow === colSize - 1 ? 0 : currentRow + 1;
                selectedIndex = newRow * rowSize + currentCol;
            }

            if (selectedIndex !== null) {
                event.preventDefault();

                // Handle selection logic for control and shift keys
                if (event.ctrlKey) {
                    // If control is pressed, select the next item and keep the currently selected item
                    thumbs[selectedIndex].classList.toggle("selected");
                } else if (event.shiftKey) {
                    const rowSize = Math.floor(imageBrowser.offsetWidth / thumbs[0].offsetWidth);

                    const last = Array.from(thumbs).indexOf(lastSelected);
                    const next = Array.from(thumbs).indexOf(thumbs[selectedIndex]);

                    // Calculate the top-left and bottom-right corners of the existing square of selected items
                    const selectedIndices = Array.from(selectedThumbs).map(thumb => Array.from(thumbs).indexOf(thumb));
                    const selectedRows = selectedIndices.map(index => Math.floor(index / rowSize));
                    const selectedCols = selectedIndices.map(index => index % rowSize);
                    const selectedStartRow = Math.min(...selectedRows);
                    const selectedEndRow = Math.max(...selectedRows);
                    const selectedStartCol = Math.min(...selectedCols);
                    const selectedEndCol = Math.max(...selectedCols);

                    // Calculate the top-left and bottom-right corners of the new selection square
                    const lastRow = Math.floor(last / rowSize);
                    const lastCol = last % rowSize;
                    const nextRow = Math.floor(next / rowSize);
                    const nextCol = next % rowSize;
                    const startRow = Math.min(lastRow, nextRow, selectedStartRow);
                    const endRow = Math.max(lastRow, nextRow, selectedEndRow);
                    const startCol = Math.min(lastCol, nextCol, selectedStartCol);
                    const endCol = Math.max(lastCol, nextCol, selectedEndCol);

                    // Deselect thumbs that fall outside the new selection square
                    for (let i = 0; i < selectedThumbs.length; i++) {
                        const thumb = selectedThumbs[i];
                        const index = Array.from(thumbs).indexOf(thumb);
                        const row = Math.floor(index / rowSize);
                        const col = index % rowSize;

                        if (row < startRow || row > endRow || col < startCol || col > endCol) {
                            thumb.classList.remove("selected");
                        }
                    }

                    // Select thumbs that fall within the new selection square
                    for (let i = 0; i < thumbs.length; i++) {
                        const thumb = thumbs[i];
                        const row = Math.floor(i / rowSize);
                        const col = i % rowSize;

                        if (row >= startRow && row <= endRow && col >= startCol && col <= endCol) {
                            thumb.classList.add("selected");
                        }
                    }
                } else {
                    // If neither control nor shift is pressed, clear existing selections and select the new item
                    thumbs.forEach(thumb => thumb.classList.remove("selected"));
                    thumbs[selectedIndex].classList.add("selected");
                }

                lastSelected = thumbs[selectedIndex];
                updateThumbSelection().then(() => {
                    console.log("Thumb selection updated?");
                });
            }
            // Set the focus on the newly selected thumb


        }

        if (captionEditor === document.activeElement && event.key === "Enter" && !event.ctrlKey) {
            selectedThumbs = imageBrowser.querySelectorAll(".thumb.selected");

            // Prevent the default arrow key behavior
            event.preventDefault();

            // Get the index of the currently focused thumb
            if (selectedThumbs.length === 1) {
                const currentIndex = Array.from(thumbs).indexOf(document.querySelector(".thumb.selected"));
                console.log("KEY: ", event.key, "CUR: ", currentIndex);
                // Determine the index of the next thumb to select based on the arrow key
                selectedIndex = currentIndex === thumbs.length - 1 ? 0 : currentIndex + 1;
                checkSaveCaption().then(() => {
                    console.log("Check saved...");
                    for (let i = 0; i < thumbs.length; i++) {
                        if (selectedIndex === i) {
                            thumbs[i].classList.add("selected");
                        } else {
                            thumbs[i].classList.remove("selected");
                        }
                    }
                    thumbs[selectedIndex].click();
                    captionEditor.focus();
                });
            } else if (selectedThumbs.length > 1) {
                checkSaveCaptions().then(() => {
                    console.log("Check saved...");
                    captionEditor.focus();
                });
            }

        }

    });
    $("#captionSelected").on("click", function () {
        let selected = document.querySelectorAll("#imageBrowser .thumb.selected");
        startCaption(selected);
    });
    $("#captionAll").on("click", function () {
        let selected = document.querySelectorAll("#imageBrowser .thumb");
        startCaption(selected);
    });
    $("#tag_cloud").on("click", function () {
        let directory = imageFileBrowser.value;
        console.log("Directory: ", directory);
        let recurse = $("#imageRecurse").is(":checked");
        sendMessage("tag_cloud", {
            path: directory,
            recurse: recurse
        }).then((response) => {
            loadTags(response["src"], response["tags"]);
        });

    });
}

function loadTags(cloudImage, tags) {
    console.log("Loading tags: ", tags);
    $("#cloudImage").attr("src", cloudImage);
    let tagContainer = $("#tagContainer");
    tagContainer.empty();
    // Enumerate tags, which is a dictionary
    for (let tag in tags) {
        let tag_count = tags[tag].length;
        console.log("Tag: ", tag, "Count: ", tag_count);
        let tag_badge = $("<span data-count='" + tag_count + "' data-tag='"+tag+"' " +
            "class='badge tagPill rounded-pill bg-secondary'>(" + tag_count + ") "+ tag + "" +
            "<span class='badge bg-danger tagDeleteButton'>X</span></span>");
        tag_badge.on("click", function (event) {
            console.log("Clicked tag: ", $(this).attr("data-tag"));
            $(this).toggleClass("bg-secondary bg-primary");
            // If control isn't pressed, deselect all other tags
            if (!event.ctrlKey) {
                $(".tagPill").not(this).removeClass("bg-primary").addClass("bg-secondary");
                updateTagSelection();
            }
        });
        tagContainer.append(tag_badge);
    }
    $(".tagDeleteButton").hide();
    sortTags();
}

// Define a function to sort the tags
function sortTags() {
    let sortType = document.getElementById('sortType').value;
    let sortOrder = document.getElementById('sortOrder').value;
    
    let container = document.getElementById('tagContainer');
    let tags = Array.from(container.children);
    
    tags.sort(function(a, b) {
        let aValue = sortType === 'alphabetical' ? a.getAttribute('data-tag') : a.getAttribute('data-count');
        let bValue = sortType === 'alphabetical' ? b.getAttribute('data-tag') : b.getAttribute('data-count');
        
        if (sortType !== 'alphabetical') {
            aValue = parseInt(aValue, 10);
            bValue = parseInt(bValue, 10);
        }
        
        if (aValue < bValue) {
            return sortOrder === 'ascending' ? -1 : 1;
        }
        if (aValue > bValue) {
            return sortOrder === 'ascending' ? 1 : -1;
        }
        return 0;
    });
    
    tags.forEach(function(tag) {
        container.appendChild(tag);
    });
}
function startCaption(selected) {

    if (selected.length > 0) {
        let selectedPaths = [];
        for (let i = 0; i < selected.length; i++) {
            selectedPaths.push(selected[i].getAttribute("data-path"));
        }
        let params = {path: selectedPaths};

        let caps = {};
        let captioners = document.querySelectorAll(".tagCapSelect");
        for (let i = 0; i < captioners.length; i++) {
            let captioner = captioners[i];
            let captionerValue = captioner.value;
            // Set to true if checked, false if not
            caps[captionerValue] = captioner.checked;
        }
        params["captioners"] = caps;
        params["threshold"] = thresholdSlider.value;
        params["char_threshold"] = characterSlider.value;
        params["whitelist"] = $("#tagWhitelist").val();
        params["blacklist"] = $("#tagBlacklist").val();
        params["append_existing"] = $("#appendExisting").is(":checked");
        sendMessage("caption_image", params, await = false).then((response) => {
            console.log("Captioned: ", response);
        });
    }
}

function updateTagSelection() {
    // Enumerate the selected tags
    let selectedTags = [];
    $(".tagPill.bg-primary").each(function () {
        selectedTags.push($(this).attr("data-tag"));
    });
    console.log("Selected tags: ", selectedTags);
    let imageThumbs = document.querySelectorAll("#imageBrowser .thumb");
    for (let i = 0; i < imageThumbs.length; i++) {
        let thumb = imageThumbs[i];
        let tags = thumb.getAttribute("data-tag").split(",");
        // Strip tags and convert to lower, just in case
        for (let j = 0; j < tags.length; j++) {
            tags[j] = tags[j].trim().toLowerCase();
        }
        let tagMatch = false;
        for (let j = 0; j < selectedTags.length; j++) {
            let tag = selectedTags[j];
            tagMatch = tags.includes(tag);
        }
        if (tagMatch) {
            thumb.classList.add("selected");
        } else {
            thumb.classList.remove("selected");
        }
    }
    updateThumbSelection().then(() => {
        // Sort the thumbs with the selected ones first
        let selected = document.querySelectorAll("#imageBrowser .thumb.selected");
        let unselected = document.querySelectorAll("#imageBrowser .thumb:not(.selected)");
        let imageBrowser = document.getElementById("imageBrowser");
        imageBrowser.innerHTML = "";
        for (let i = 0; i < selected.length; i++) {
            imageBrowser.appendChild(selected[i]);
        }
        for (let i = 0; i < unselected.length; i++) {
            imageBrowser.appendChild(unselected[i]);
        }
    });
}

async function updateThumbSelection() {
    console.log("UTS!");
    let selectedThumbs = document.querySelectorAll("#imageBrowser .thumb.selected");
    const fullImageWrap = document.querySelector(".fullImgWrap");
    fullImageWrap.innerHTML = "";

    if (selectedThumbs.length === 0) {
        return;
    }

    if (selectedThumbs.length === 1) {
        const path = selectedThumbs[0].getAttribute("data-path");
        const response = await sendMessage("get_images", {directory: path});
        console.log("Res: ", response);
        try {
            let file = response["image_data"][0];
            let src = file["src"];
            let prompt = (file.hasOwnProperty("prompt")) ? file["prompt"] : "";
            const fullImageElem = document.createElement("img");
            fullImageElem.src = src;
            fullImageWrap.appendChild(fullImageElem);
            const imageTagElem = document.getElementById("imageCaption");
            imageTagElem.value = prompt;
        } catch (e) {
            console.error("Error: ", e);
        }
    } else if (selectedThumbs.length > 1) {
        const imageTagElem = document.getElementById("imageCaption");
        let imagesSrcArray = [];
        let imageTagsDict = {};
        selectedThumbs.forEach((thumb) => {
            imagesSrcArray.push(thumb.style.backgroundImage.slice(5, -2));
            if (thumb.dataset.hasOwnProperty("tag")) {
                imageTagsDict[thumb.getAttribute("data-path")] = thumb.dataset.tag;
            }
        });
        fullImageWrap.innerHTML = "";
        imagesSrcArray.forEach((src) => {
            let img = document.createElement("img");
            img.src = src;
            img.classList.add("thumb");
            fullImageWrap.appendChild(img);
        });

        let commonTagsArray = [];
        if (Object.keys(imageTagsDict).length > 1) {
            commonTagsArray = Object.values(imageTagsDict)[0]
                .split(",")
                .map((tag) => tag.trim());
            for (const tags of Object.values(imageTagsDict).slice(1)) {
                let currentTagsArray = tags.split(",").map((tag) => tag.trim());
                commonTagsArray = commonTagsArray.filter((tag) => currentTagsArray.includes(tag));
            }
        }

        let captionData = {};

        for (const [path, tags] of Object.entries(imageTagsDict)) {
            let originalCaption = tags;
            let strippedCaption = originalCaption
                .split(",")
                .map((caption) => caption.trim())
                .filter((caption) => !tags.split(",").map((tag) => tag.trim()).includes(caption));
            captionData[path] = {
                caption: originalCaption,
                unique: strippedCaption,
            };
        }

        let joined = commonTagsArray.join(", ");
        console.log("JOINED: ", joined);
        if (joined !== "undefined" && joined !== undefined && joined !== null) {
            imageTagElem.value = joined;
        } else {
            imageTagElem.value = "";
        }
    }
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

async function checkSaveCaptions() {
    console.log("CHECKSAVECAPTIONS");
    let captionEditor = document.getElementById("imageCaption");
    let caption = captionEditor.value.split(",").map((caption) => caption.trim());
    let selectedThumbs = document.querySelectorAll(".thumb.selected");

    for (const thumb of selectedThumbs) {
        let path = thumb.dataset.path;
        let originalCaption = captionData[path].caption;
        let uniqueCaption = captionData[path].unique;
        let newCaption = [...new Set(uniqueCaption.concat(caption))].join(", ");

        if (newCaption !== originalCaption) {
            console.log("Saving caption: ", {path: path, caption: newCaption});

            //const response = await sendMessage("save_caption", {path: path, caption: newCaption});
            //console.log("Res: ", response);
            // thumb.dataset.tag = response["caption"];
            // captionData[path].caption = newCaption;
            // captionData[path].unique = uniqueCaption.filter((caption) => !newCaption.includes(caption));
        }
    }
}

function loadImages(file) {
    const thumbContainer = document.getElementById("imageBrowser");
    let imageBrowser = document.getElementById("imageBrowser");
    let recurse = document.getElementById("imageRecurse").checked;
    imageBrowser.innerHTML = "Loading...";
    sendMessage("get_images", {
        directory: file,
        recurse: recurse,
        return_thumb: true,
        thumb_size: 128
    }).then((data) => {
        imageBrowser.innerHTML = "";
        const items = data["image_data"];
        for (const path in items) {
            const thumbDataItem = items[path];
            console.log("Parsing: ", thumbDataItem);
            // Create thumbnail element
            const thumbElem = document.createElement("div");
            thumbElem.classList.add("thumb");
            thumbElem.style.backgroundImage = `url(${thumbDataItem.src})`;
            thumbElem.tabIndex = -1;
            // Set path and tag in dataset
            thumbElem.dataset.path = thumbDataItem.path;
            thumbElem.dataset.tag = thumbDataItem.prompt;

            // Add onclick listener
            thumbElem.onclick = async function (event) {
                const shift = event.shiftKey;
                const ctrl = event.ctrlKey;
                console.log("Thumb: ", event);
                const imageBrowser = document.getElementById("imageBrowser");
                let thumbs = imageBrowser.querySelectorAll(".thumb");
                let selectedThumbs = imageBrowser.querySelectorAll(".thumb.selected");

                if (!shift && !ctrl) {
                    thumbs.forEach((thumb) => {
                        thumb.classList.remove("selected");
                    });
                    this.classList.add("selected");
                    this.focus();
                } else if (shift) {
                    this.classList.add("selected");
                    if (selectedThumbs.length === 0) {
                        this.classList.add("selected");
                    } else {
                        let endIndex = Array.from(thumbs).indexOf(this);
                        let startIndex = Array.from(thumbs).indexOf(lastSelected);

                        if (startIndex > endIndex) {
                            let temp = endIndex;
                            endIndex = startIndex;
                            startIndex = temp;
                        }
                        console.log("Start: ", startIndex, "End: ", endIndex);
                        for (let i = startIndex; i <= endIndex; i++) {
                            thumbs[i].classList.add("selected");
                        }
                    }
                } else if (ctrl) {
                    console.log("WTF, control: ", this);
                    if (!this.classList.contains("selected")) {
                        console.log("Selecting");
                        this.classList.add("selected");
                    } else {
                        if (selectedThumbs.length > 1) {
                            console.log("DeSelecting");
                            this.classList.remove("selected");
                        }
                    }
                }
                lastSelected = this;
                updateThumbSelection().then(() => {
                    console.log("Thumb selection updated?");
                });
            };


            // Append thumbnail element to container
            thumbContainer.appendChild(thumbElem);
        }
        console.log("Response: ", data);
    });
}


