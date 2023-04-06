class FileBrowser {
    constructor(parentElement, options = {}) {
        this.onDoubleClickCallbacks = [];
        this.onClickCallbacks = [];
        this.onSelectCallbacks = [];
        this.onCancelCallbacks = [];
        this.selected = "";
        this.startLink = "";
        let wrapper = document.createElement("div");
        wrapper.classList.add("row", "fileBrowserContainer");
        parentElement.appendChild(wrapper);
        this.parentElement = wrapper;
        this.infoPanel = undefined;
        this.endpoint = "files";
        this.fileEndpoint = "file";
        this.currentPath = "";
        this.currentParent = "";
        this.selectedLink = undefined;
        console.log("Options: ", options);
        this.treeContainer = document.createElement("div");
        this.treeContainer.classList.add("tree");
        this.treeParent = document.createElement("div");
        this.treeParent.classList.add("tree-container", "col");
        this.placeholder = options["placeholder"] || "Select something...";
        this.showSelectButton = options["showSelectButton"] || false;
        this.listFiles = options["listFiles"] || false;
        this.expanded = options["expand"] || false;
        this.multiselect = options["multiselect"] || false;
        this.dropdown = options["dropdown"] !== undefined ? options["dropdown"] : false;
        if (this.dropdown) {
            this.parentElement.classList.add("dropdown");
            this.treeParent.classList.add("dropdown");
        }
        if (this.showSelectButton) this.treeContainer.classList.add("selectSibling");
        this.currentSort = {
            type: "name",
            order: "asc"
        };
        this.showTitle = options["showTitle"] !== undefined ? options["showTitle"] : true;
        this.showInfo = options["showInfo"] !== undefined ? options["showInfo"] : true;
        this.style = options["style"] !== undefined ? options["style"] : "";
        if (this.expanded) {
            this.treeParent.classList.add("full");
        }
        if (this.style !== "") {
            this.treeParent.style.cssText = this.style;
        }

        this.addKeyboardListener();


        this.buildTree().then(() => {
            let inputGroup = this.buildInput();
            this.parentElement.prepend(inputGroup);
            this.treeParent.appendChild(this.treeContainer);

            if (this.showSelectButton) {
                const selectButton = document.createElement("button");
                selectButton.classList.add("btn", "btn-primary");
                selectButton.textContent = "Select";
                selectButton.addEventListener("click", () => {
                    console.log("SELCLICK.");
                    this.selectedLink = this.selectedLinks.length > 0 ? this.selectedLinks[0] : undefined;
                    if (this.selectedLink !== undefined) {
                        console.log("Selected: ", this.selectedLink);
                        this.currentPath = this.selectedLink.dataset.path;
                        let base = this.currentParent === this.separator ? this.currentParent : this.currentParent + this.separator;
                        this.input.value = base + this.currentPath;
                        console.log("SET: ", this.input.value);
                        this.toggleTree();
                    }
                });
                const cancelButton = document.createElement("button");
                cancelButton.classList.add("btn", "btn-secondary");
                cancelButton.textContent = "Cancel  ";
                cancelButton.addEventListener("click", () => {
                    this.toggleTree();
                });
                const btnGroup = document.createElement("div");
                btnGroup.classList.add("btn-group", "file-buttons", "hide");
                btnGroup.appendChild(selectButton);
                btnGroup.appendChild(cancelButton);
                this.parentElement.appendChild(btnGroup);

            }
            this.parentElement.append(this.treeParent);

            if (!this.dropdown) {
                const fileButtons = this.buildFileButtons();
                parentElement.append(fileButtons);
            }


            if (this.showInfo) {
                this.onClickCallbacks.push(this.showFileInfo);
                this.infoPanel = document.createElement("div");
                this.infoPanel.classList.add("infoPanel", "closed", "col-sm-12", "col-md-6", "col-lg-4");
                this.parentElement.appendChild(this.infoPanel);
                this.createImageModal("");
            }
            this.attachEventHandlers();
        });


    }

    buildFileButtons() {
        let buttonCol = document.createElement("div");
        buttonCol.classList.add("col-12", "text-center", "buttonCol");

        let buttonGroup = document.createElement("div");
        buttonGroup.classList.add("btn-group", "btn-group-sm");

        let uploadButton = document.createElement("button");
        uploadButton.innerHTML = '<i class="bx bx-upload"></i>';
        uploadButton.classList.add("btn", "btn-primary");
        uploadButton.dataset["function"] = "upload";

        let refreshButton = document.createElement("button");
        refreshButton.innerHTML = '<i class="bx bx-refresh"></i>';
        refreshButton.classList.add("btn", "btn-secondary");
        refreshButton.dataset["function"] = "refresh";

        let newButton = document.createElement("button");
        newButton.innerHTML = '<i class="bx bx-plus"></i>';
        newButton.classList.add("btn", "btn-secondary");
        newButton.dataset["function"] = "new";

        let renameButton = document.createElement("button");
        renameButton.innerHTML = '<i class="bx bx-rename"></i>';
        renameButton.classList.add("btn", "btn-secondary");
        renameButton.dataset["function"] = "rename";

        let deleteButton = document.createElement("button");
        deleteButton.innerHTML = '<i class="bx bx-trash"></i>';
        deleteButton.classList.add("btn", "btn-danger");
        deleteButton.dataset["function"] = "delete";

        buttonGroup.appendChild(uploadButton);
        buttonGroup.appendChild(refreshButton);
        buttonGroup.appendChild(newButton);
        buttonGroup.appendChild(renameButton);
        buttonGroup.appendChild(deleteButton);

        buttonGroup.querySelectorAll("button").forEach(button => {
            button.addEventListener("click", () => {
                this.handleFileMethod(button.dataset.function);
            });
        });

        buttonCol.appendChild(buttonGroup);
        buttonCol.appendChild(buttonGroup);
        let btnRow = document.createElement("div");
        btnRow.classList.add("row", "fileBtnRow");
        btnRow.appendChild(buttonCol);
        return btnRow;
    }

    handleFileMethod(method) {
        // Get data-path attribute of each of these elements
        const selected = this.treeContainer.querySelectorAll(".fileLi.selected");

        // The innerHTML of this contains the current path
        const fileCurrent = this.treeContainer.querySelector(".fileCurrent");

        // Methods are delete, rename, new, refresh, upload
        // If the method is upload, we can .
        // Otherwise, we need to call the async 'sendMessage("handleFile", {dir=CURRENT_PATH, files={selected_files}),
        // populating files as described below.
        const selectedFiles = [];
        selected.forEach((item) => {
            selectedFiles.push(item.dataset.path);
        });
        switch (method) {
            case "refresh":
                // call the async this.refresh() method
                this.refresh().then(() => {
                    console.log("Refreshed!");
                });
                break;
            case "delete":
                // Send the list of selected files
                if (selectedFiles.length > 0) {
                    if (confirm(`Are you sure you want to delete these ${selectedFiles.length} file(s)? This action is irreversible.`)) {
                        const data = {dir: fileCurrent.innerHTML, files: selectedFiles, method: method};
                        sendMessage("handleFile", data).then(() => {
                            this.refresh().then(() => {
                                console.log("Deleted and refreshed!");
                            })
                        });
                    }
                }
                break;
            case "rename":
                // Prompt the user for new filename if only one file is selected

                if (selectedFiles.length === 1) {
                    const existingFileName = selectedFiles[0].split("/").pop();
                    const newFileName = prompt(`Enter a new name for ${existingFileName}:`, existingFileName);
                    if (newFileName) {
                        const data = {
                            dir: fileCurrent.innerHTML,
                            files: selectedFiles,
                            method: method,
                            newName: newFileName
                        };
                        sendMessage("handleFile", data).then(() => {
                            this.refresh().then(() => {
                                console.log("Renamed and refreshed!");
                            })
                        });
                    }
                } else {
                    alert("Please select only one file to rename.");
                }

                break;
            case "upload":
                // Open an explorer window and let the user select files
                const input = document.createElement("input");
                input.type = "file";
                input.multiple = true;
                input.addEventListener("change", async () => {
                    const files = Array.from(input.files);
                    const formData = new FormData();
                    formData.append("dir", fileCurrent.innerText);
                    files.forEach((file) => {
                        formData.append("files", file);
                    });
                    const response = await fetch("/files/upload", {
                        method: "POST",
                        body: formData,
                    });
                    const data = await response.json();
                    console.log(data);
                    await this.refresh();
                });

                input.click();
                break;

            case "new":
                // Open a dialog asking for the folder name, then sendMessage to handleFile with the user input for the dir name under "files".
                const folderName = prompt("Enter the folder name:");
                if (folderName) {
                    const data = {dir: fileCurrent.innerHTML, files: [folderName], method: method};
                    sendMessage("handleFile", data).then(() => {
                        this.refresh().then(() => {
                            console.log("Created folder!");
                        });
                    });
                }
                break;
        }
    }


    selectNextItem(direction, ctrl_pressed, shift_pressed) {
        const selected = this.treeContainer.querySelector(".fileLi.selected");

        if (selected) {
            const sibling = direction === -1 ?
                selected.previousElementSibling : selected.nextElementSibling;
            if (sibling) {
                console.log("Found sibling.");
                // if (multi === false) selected.classList.remove("selected");
                // sibling.classList.add("selected");
                // sibling.click();
                this.handleLinkClick(sibling, ctrl_pressed, shift_pressed);
            }
        } else {
            const firstChild = this.treeContainer.querySelector(".fileLi");
            if (firstChild) {
                // firstChild.classList.add("selected");
                // console.log("Firstchild");
                // firstChild.click();
                this.handleLinkClick(firstChild, ctrl_pressed, shift_pressed);
            }
        }

        console.log("NEXT!", direction);
        const images = document.querySelector(".img-info");
        const fullScreen = document.querySelector(".img-fullscreen");
        fullScreen.src = images.src;
        fullScreen.dataset["name"] = images.dataset["name"];
    }

    addKeyboardListener() {
        console.log("Adding keylistener.");
        document.addEventListener("keydown", function (event) {
            const focusedElement = document.activeElement;
            if (this.treeContainer.contains(focusedElement)) {
                if (event.key === "ArrowUp" || event.key === "ArrowDown") {
                    event.preventDefault();
                    const direction = event.key === "ArrowUp" ? -1 : 1;
                    this.selectNextItem(direction, event.ctrlKey, event.shiftKey);
                }
                if (event.key === "Enter") {
                    event.preventDefault();
                    if (event.srcElement.classList.contains("fileLi") && event.srcElement.classList.contains("selected")) {
                        console.log("We got us a selected li: ", event.srcElement);
                        event.srcElement.dispatchEvent(new MouseEvent('dblclick', {bubbles: true}));
                    }
                }
            }
        }.bind(this));


        let dragCounter = 0;
        let timeoutId = null;
        const delay = 200; // Delay in milliseconds

        this.treeContainer.addEventListener('dragenter', (e) => {
            e.preventDefault();
            console.log("ENTER");
            const tempDiv = document.querySelector(".tempDiv");
            tempDiv.classList.add('show');
        });

        this.treeContainer.addEventListener('dragover', (e) => {
            e.preventDefault();
            clearTimeout(timeoutId);
        });

        this.treeContainer.addEventListener('dragleave', (e) => {
            e.preventDefault();
            console.log("LEAVE!");
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                const tempDiv = document.querySelector(".tempDiv");
                tempDiv.classList.remove('show');
            }, delay);
        });


        this.treeContainer.addEventListener('drop', async (e) => {
            e.preventDefault();
            const tempDiv = document.querySelector(".tempDiv");
            tempDiv.classList.remove('show');
            const fileCurrent = this.treeContainer.querySelector(".fileCurrent");
            const files = Array.from(e.dataTransfer.files);
            const formData = new FormData();
            formData.append('dir', fileCurrent.innerText);
            files.forEach((file) => {
                formData.append('files', file);
            });
            const response = await fetch('/files/upload', {
                method: 'POST',
                body: formData,
            });
            const data = await response.json();
            console.log(data);
            await this.refresh();
        });
    }


    buildInfoPanel(fileInfo) {
        console.log("Building: ", fileInfo);
        const panelContainer = document.createElement("div");
        panelContainer.classList.add("row");

        // File info panel
        const infoPanel = document.createElement("div");
        infoPanel.classList.add("panelWrap");
        const infoList = document.createElement("ul");
        infoList.classList.add("list-group", "list-group-flush");
        const filename = document.createElement("li");
        filename.classList.add("list-group-item", "active");
        filename.textContent = fileInfo.filename;
        infoList.appendChild(filename);
        const created = document.createElement("li");
        created.classList.add("list-group-item");
        created.textContent = `Created: ${fileInfo.date_created}`;
        infoList.appendChild(created);
        const modified = document.createElement("li");
        modified.classList.add("list-group-item");
        modified.textContent = `Modified: ${fileInfo.date_modified}`;
        infoList.appendChild(modified);
        const size = document.createElement("li");
        size.classList.add("list-group-item");
        size.textContent = `Size: ${fileInfo.size}`;
        infoList.appendChild(size);
        infoPanel.appendChild(infoList);
        panelContainer.appendChild(infoPanel);

        // Image panel
        if (fileInfo.src) {
            const imgPanel = document.createElement("div");
            imgPanel.classList.add("imgPanel", "mt-2");

            const leftIcon = document.createElement("i");
            leftIcon.classList.add("bx", "bx-download", "info-icon-left", "infoBtn");
            imgPanel.appendChild(leftIcon);

            const rightIcon = document.createElement("i");
            rightIcon.classList.add("bx", "bx-fullscreen", "info-icon-right", "infoBtn");
            imgPanel.appendChild(rightIcon);
            const img = document.createElement("img");
            img.classList.add("img-info");
            img.dataset["name"] = fileInfo.filename;
            img.src = fileInfo.src;
            imgPanel.appendChild(img);
            panelContainer.appendChild(imgPanel);
        }

        // Data panel
        if (fileInfo.data) {
            const dataPanel = document.createElement("div");
            dataPanel.classList.add("mt-2", "dataPanel");
            const pre = document.createElement("pre");
            pre.classList.add("bg-light", "p-3", "border");
            pre.textContent = fileInfo.data;
            dataPanel.appendChild(pre);
            if (fileInfo.src) {
                panelContainer.appendChild(dataPanel);
            } else {
                const dataWrapper = document.createElement("div");
                dataWrapper.classList.add("col-12", "dataPanel");
                dataPanel.classList.remove("dataPanel");
                dataWrapper.appendChild(dataPanel);
                panelContainer.appendChild(dataWrapper);
            }
        }

        return panelContainer;
    }

    // Function to download image

    downloadImage(src, name) {
        const link = document.createElement("a");
        link.href = src;
        link.download = name;
        link.click();
    }


    createImageModal(src) {
        let modal = document.createElement("div");
        modal.classList.add("infoModal", "fade");
        modal.id = "imageInfoModal";
        modal.setAttribute("tabindex", "-1");
        modal.setAttribute("role", "dialog");
        modal.setAttribute("aria-hidden", "true");
        modal.innerHTML = `
    <img class="img-fullscreen" id="infoModalImage" src="${src}" />
    <i class="bx bx-download icon-left infoBtn infoDownload"></i>
    <i class="bx bx-fullscreen icon-right infoBtn infoFullscreen"></i>
  `;

        document.body.appendChild(modal);

        const imgFullscreen = document.querySelector(".img-fullscreen");
        const leftNavIcon = document.createElement("i");
        leftNavIcon.classList.add("bx", "bx-chevron-left", "icon-left-nav", "infoBtn", "infoLeft");
        leftNavIcon.addEventListener("click", () => {
            this.selectNextItem(-1);
        });
        imgFullscreen.parentElement.appendChild(leftNavIcon);

        const rightNavIcon = document.createElement("i");
        rightNavIcon.classList.add("bx", "bx-chevron-right", "icon-right-nav", "infoBtn", "infoRight");
        rightNavIcon.addEventListener("click", () => {
            this.selectNextItem(1);
        });
        imgFullscreen.parentElement.appendChild(rightNavIcon);

        const downloadIcon = document.querySelector(".infoDownload");
        downloadIcon.addEventListener("click", () => {
            this.downloadImage(imgFullscreen.src, imgFullscreen.dataset["name"]);
        });

        const fullscreenIcon = document.querySelector(".infoFullscreen");
        fullscreenIcon.addEventListener("click", () => {
            $("#imageInfoModal").toggleClass("show");
        });

        document.addEventListener("keydown", (event) => {
            if (event.keyCode === 37) {
                // Left arrow key
                this.selectNextItem(-1);
            } else if (event.keyCode === 39) {
                // Right arrow key
                this.selectNextItem(1);
            } else if (event.keyCode === 27) {
                // Escape key
                $("#imageInfoModal").removeClass("show");
            }
        });


        const images = document.querySelectorAll(".img-info");
        images.forEach((image) => {
            image.addEventListener("click", () => {
                imgFullscreen.src = image.src;
                imgFullscreen.dataset["name"] = image.dataset["name"];
            });
        });
    }


    buildInput() {
        const inputGroup = document.createElement("div");
        inputGroup.classList.add("input-group", "dropdownGroup");
        if (this.dropdown) {
            console.log("Dropdown enabled.");
        } else {
            console.log("Hide dropdown.")
            inputGroup.classList.add("hide");
        }
        const input = document.createElement("input");
        input.classList.add("form-control");
        input.type = "text";
        input.placeholder = this.placeholder;
        this.input = input;
        inputGroup.appendChild(input);

        const toggleButton = document.createElement("button");
        toggleButton.classList.add("btn", "btn-secondary");

        toggleButton.innerHTML = this.expanded ? `<i class="fas fa-chevron-up"></i>` : `<i class="fas fa-chevron-down"></i>`;
        inputGroup.appendChild(toggleButton);
        toggleButton.addEventListener("click", () => {
            this.toggleTree();
        });
        this.toggleButton = toggleButton;
        return inputGroup;
    }

    toggleTree() {
        const fileButtons = this.parentElement.querySelector(".file-buttons");
        const inputRow = this.parentElement.querySelector(".dropdownGroup");
        inputRow.classList.toggle("hide");
        fileButtons.classList.toggle("hide");
        this.treeParent.classList.toggle("full");
        if (this.showInfo) this.infoPanel.classList.toggle("closed");
        this.expanded = this.treeParent.classList.contains("full");
        this.toggleButton.innerHTML = this.expanded ? `<i class="fas fa-chevron-up"></i>` : `<i class="fas fa-chevron-down"></i>`;
    }

    async buildTree() {
        const response = await this.fetchFileTreeData(this.currentPath);
        console.log("FTD: ", response);
        let items = response["items"] || [];
        this.currentParent = response["current"] || "";
        this.separator = response["separator"] || "\\";
        const tree = this.generateTree(items);
        this.treeContainer.innerHTML = "";
        if (this.showTitle) {
            let title = document.createElement("span");
            title.innerHTML = "File Browser";
            title.classList.add("fileTitle");
            this.treeContainer.appendChild(title);
        }

        let currentPathContainer = document.createElement("div");
        currentPathContainer.classList.add("row", "pathContainer");

        let currentPathCol = document.createElement("div");
        currentPathCol.classList.add("col", "fileTitleCol");

        let currentPath = document.createElement("div");
        currentPath.innerHTML = this.currentParent;
        currentPath.classList.add("card-header", "fileCurrent");
        if (this.dropdown) currentPath.classList.add("dropdown");
        currentPathCol.appendChild(currentPath);

        let sortCol = document.createElement("div");
        sortCol.classList.add("col-auto", "fileSortCol");

        let sortButtonsRow = document.createElement("div");
        sortButtonsRow.classList.add("row", "fileSortRow");

// Sort by name button
        let sortByNameButton = document.createElement("button");
        sortByNameButton.innerHTML = '<i class="bx bx-sort-a-z"></i>';
        sortByNameButton.dataset["type"] = "name";
        sortByNameButton.classList.add("btn", "btn-outline-primary", "fileSortButton", "active");
        sortButtonsRow.appendChild(sortByNameButton);

// Sort by size button
        let sortBySizeButton = document.createElement("button");
        sortBySizeButton.innerHTML = '<i class="bx bxs-hdd"></i>';
        sortBySizeButton.dataset["type"] = "size";
        sortBySizeButton.classList.add("btn", "btn-outline-primary", "fileSortButton");
        sortButtonsRow.appendChild(sortBySizeButton);

// Sort by date button
        let sortByDateButton = document.createElement("button");
        sortByDateButton.innerHTML = '<i class="bx bx-calendar"></i>';
        sortByDateButton.dataset["type"] = "date";
        sortByDateButton.classList.add("btn", "btn-outline-primary", "fileSortButton");
        sortButtonsRow.appendChild(sortByDateButton);

// Sort by type button
        let sortByTypeButton = document.createElement("button");
        sortByTypeButton.innerHTML = '<i class="bx bxs-file-blank"></i>';
        sortByTypeButton.dataset["type"] = "type";
        sortByTypeButton.classList.add("btn", "btn-outline-primary", "fileSortButton");
        sortButtonsRow.appendChild(sortByTypeButton);

        let sortOrderIndicator = document.createElement("div");
        sortOrderIndicator.innerHTML = '<i class="bx bx-sort-down"></i>';
        sortOrderIndicator.dataset["type"] = "type";
        sortOrderIndicator.classList.add("fileSortIndicator");
        sortButtonsRow.appendChild(sortOrderIndicator);

        sortCol.appendChild(sortButtonsRow);
        currentPathContainer.appendChild(currentPathCol);
        currentPathContainer.appendChild(sortCol);

        this.treeContainer.appendChild(currentPathContainer);
        this.treeContainer.appendChild(tree);


        if (this.infoPanel) {
            this.infoPanel.classList.add("closed");
        }

        if (this.showSelectButton) {

        }

        const tempDiv = document.createElement('div');
        tempDiv.textContent = 'Drop files to upload';
        tempDiv.className = 'tempDiv';
        this.treeContainer.appendChild(tempDiv);

        this.attachEventHandlers();
    }

    generateTree(response) {
        const root = document.createElement("ul");
        root.classList.add("treeRoot");
        const listItem = document.createElement("li");
        const icon = document.createElement("i");
        icon.classList.add("bx", "bx-hdd", "fileIcon");
        listItem.appendChild(icon);
        listItem.classList.add("fileLi");
        const link = document.createElement("a");
        link.innerHTML = "..";
        listItem.dataset.path = "..";
        listItem.dataset.type = "directory";
        listItem.appendChild(link);
        root.appendChild(listItem);
        for (const [path, details] of Object.entries(response)) {
            const [dateModified, size, type, children] = details;
            const splitPath = path.split(this.separator);

            if (splitPath.length === 1) {
                const listItem = document.createElement("li");
                listItem.classList.add("fileLi");
                listItem.dataset.path = path;
                listItem.dataset.type = type;
                listItem.dataset.date = dateModified;
                listItem.dataset.size = size;

                const icon = document.createElement("i");
                const iconClass = this.getClass(type);
                icon.classList.add("bx", iconClass, "fileIcon");
                listItem.appendChild(icon);
                const link = document.createElement("a");
                link.innerHTML = splitPath[0];
                listItem.appendChild(link);
                if (children) {
                    const childList = document.createElement("ul");
                    listItem.appendChild(childList);
                }
                root.appendChild(listItem);
            } else if (splitPath.length === 2) {
                const parentPath = splitPath[0];
                const currentPath = splitPath[1];
                const parentElement = root.querySelector(
                    `a[data-path="${parentPath}"]`
                ).parentElement;
                const listItem = document.createElement("li");
                listItem.dataset.path = path;
                listItem.dataset.type = type;
                listItem.dataset.date = dateModified;
                listItem.dataset.size = size;
                const link = document.createElement("a");
                link.innerHTML = currentPath;
                listItem.appendChild(link);
                if (children) {
                    const childList = document.createElement("ul");
                    listItem.appendChild(childList);
                }
                parentElement.querySelector("ul").appendChild(listItem);
            }
        }
        return root;
    }

    attachEventHandlers() {
        const allLinks = this.treeContainer.querySelectorAll(".fileLi");
        allLinks.forEach((link) => {
            if (link.dataset.path) {
                link.addEventListener("dblclick", () => {
                    if (link.dataset.type === "directory") {
                        this.currentPath = link.dataset.path;
                        this.buildTree().then(() => {
                            const selectFirstFileLi = (element) => {
                                if (element.classList && element.classList.contains("fileLi")) {
                                    element.classList.add("selected");
                                    element.click();
                                    return true;
                                }
                                for (let i = 0; i < element.children.length; i++) {
                                    const child = element.children[i];
                                    if (selectFirstFileLi(child)) {
                                        return true;
                                    }
                                }
                                return false;
                            };
                            selectFirstFileLi(this.treeContainer);
                        });
                    } else if (link.dataset.type === ".jpg" || link.dataset.type === ".png" || link.dataset.type === ".jpeg") {
                        if (this.showInfo) {
                            let img = document.getElementById("infoModalImage");
                            let infoImg = document.querySelector(".img-info");
                            img.src = infoImg.src;
                            img.dataset["name"] = infoImg.dataset["name"];
                            $("#imageInfoModal").addClass("show");
                        }
                    }
                    this.onDoubleClickCallbacks.forEach((callback) =>
                        callback(link.dataset.path, link.dataset.type)
                    );
                });
                link.addEventListener("click", (event) => {
                    event.preventDefault();
                    const ctrlKeyPressed = event.ctrlKey;
                    const shiftKeyPressed = event.shiftKey;
                    this.handleLinkClick(link, ctrlKeyPressed, shiftKeyPressed);
                });
            } else {
                console.log("No path: ", link);
            }
        });
        let sortButtons = this.treeContainer.querySelectorAll(".fileSortButton");
        sortButtons.forEach(button => {
            button.addEventListener("click", event => {
                let activeButton = this.treeContainer.querySelector(".fileSortButton.active");
                activeButton.classList.remove("active");
                let sortIndicator = this.treeContainer.querySelector(".fileSortIndicator").querySelector(".bx");
                let type = event.currentTarget.dataset.type;
                event.currentTarget.classList.add('active');
                if (type === this.currentSort.type) {
                    // Reverse the sort order if we're already sorting by this type
                    this.currentSort.order = (this.currentSort.order === "asc") ? "desc" : "asc";
                    sortIndicator.classList.toggle("bx-sort-down");
                    sortIndicator.classList.toggle("bx-sort-up");
                    if (type === "name") {
                        let thisIcon = event.currentTarget.querySelector(".bx");
                        thisIcon.classList.toggle("bx-sort-a-z");
                        thisIcon.classList.toggle("bx-sort-z-a");
                    }
                } else {
                    // Sort by a new type
                    this.currentSort.type = type;
                    this.currentSort.order = "asc";
                }
                console.log("SORTCLICK: ", this.currentSort);
                this.sortTree();
            });
        });
    }

    // Define sortTree function
    sortTree() {
        let treeRoot = this.treeContainer.querySelector(".treeRoot");
        console.log("TR: ", treeRoot);
        let treeItems = Array.from(treeRoot.children);
        // Pop the first element and store it
        let firstElement = treeItems.shift();

        // Sort the remaining items
        treeItems.sort((a, b) => {
            console.log("ITEM: ", a, b, this.currentSort);
            let aVal = a.dataset[this.currentSort.type];
            let bVal = b.dataset[this.currentSort.type];
            if (this.currentSort.type === "name") {
                aVal = a.dataset["path"];
                bVal = b.dataset["path"];
            } else if (this.currentSort.type === "size") {
                aVal = parseInt(aVal);
                bVal = parseInt(bVal);
            } else if (this.currentSort.type === "date") {
                aVal = parseFloat(aVal);
                bVal = parseFloat(bVal);
            }
            console.log("AB: ", aVal, bVal);
            if (this.currentSort.type === "size" || this.currentSort.type === "date") {
                if (this.currentSort.order === "asc") {
                    return (aVal < bVal) ? -1 : (aVal > bVal) ? 1 : 0;
                } else {
                    return (bVal < aVal) ? -1 : (bVal > aVal) ? 1 : 0;
                }
            } else {
                if (this.currentSort.order === "asc") {
                    return aVal.localeCompare(bVal);
                } else {
                    return bVal.localeCompare(aVal);
                }
            }

        });

        // Prepend the first element
        treeItems.unshift(firstElement);

        // Append the sorted items back to the treeRoot element
        treeItems.forEach(item => treeRoot.appendChild(item));

    }

    handleLinkClick(link, ctrlKeyPressed, shiftKeyPressed) {
        const allLinks = this.treeContainer.querySelectorAll(".fileLi");
        if (ctrlKeyPressed) {
            // Control key is pressed
            if (!this.selectedLinks.includes(link)) {
                this.selectedLinks.push(link);
            } else {
                const index = this.selectedLinks.indexOf(link);
                if (index > -1) {
                    this.selectedLinks.splice(index, 1);
                }
            }
        } else if (shiftKeyPressed) {
            // Shift key is pressed
            if (this.selectedLinks.length > 0) {
                const currentIndex = Array.from(allLinks).indexOf(link);
                const startIndex = Array.from(allLinks).indexOf(this.startLink);
                const [minIndex, maxIndex] = [currentIndex, startIndex].sort((a, b) => a - b);
                for (let i = minIndex; i <= maxIndex; i++) {
                    const selectedLink = allLinks[i];
                    if (!this.selectedLinks.includes(selectedLink)) {
                        this.selectedLinks.push(selectedLink);
                        selectedLink.classList.add("selected");
                    }
                }
            }
        } else {
            link.tabIndex = -1;
            link.focus();
            // Neither control nor shift key is pressed
            this.startLink = link;
            this.selectedLinks = [link];
            allLinks.forEach((cLink) => {
                cLink.classList.remove("selected");
            });
            link.classList.add("selected");
        }
        this.onClickCallbacks.forEach((callback) =>
            callback.call(this, link, link.dataset.path, link.dataset.type)
        );
    }


    getClass(type) {
        switch (type) {
            case '.jpg':
            case '.jpeg':
                return 'bxs-file-jpg';
            case '.gif':
                return 'bxs-file-gif';
            case '.png':
                return 'bxs-file-png';
            case '.txt':
                return 'bxs-file-txt';
            case '.md':
                return 'bxs-file-md';
            case '.json':
                return 'bxs-file-json';
            case '.zip':
            case '.rar':
            case '.tar':
            case '.gz':
                return 'bxs-file-archive';
            case '.ckpt':
            case '.safetensors':
            case '.bin':
            case '.pt':
                return 'bx-data';
            case 'directory':
                return 'bx-folder';
            default:
                return 'bx-file-blank';
        }
    }

    async fetchFileTreeData(directory, recursive = false, filter = []) {
        const data = {
            start_dir: directory,
            include_files: this.listFiles,
            recursive: recursive,
            filter: filter
        };
        const response = await sendMessage(this.endpoint, data);
        console.log("Response received:", response);
        this.setCurrentPath(response["current"]);
        return response;
    }

    showFileInfo(link, data1, data2) {
        if (!this.showInfo) return;
        console.log("File info: ", link, data1, data2);
        if (data1 === "..") {
            this.infoPanel.classList.add("closed");
            return;
        }
        this.fetchFileData(data1).then((data) => {
            console.log("SHOW: ", data);
            let panel = this.buildInfoPanel(data[0]);
            console.log("PANEL: ", panel);
            this.infoPanel.innerHTML = panel.innerHTML;
            if (this.infoPanel.classList.contains("closed")) {
                this.infoPanel.classList.remove("closed");
                this.treeParent.classList.add("full", "hasInfo");
            }
            let leftIcon = document.querySelector(".info-icon-left");
            let rightIcon = document.querySelector(".info-icon-right");
            if (leftIcon) {
                leftIcon.addEventListener("click", () => {
                    console.log("DOWNLOAD IMAGE");
                    this.downloadImage(data[0].src, data[0].filename);
                });
            }
            if (rightIcon) {
                rightIcon.addEventListener("click", () => {
                    console.log("SHOW MODAL");
                    let img = document.getElementById("infoModalImage");
                    img.src = data[0].src;
                    img.dataset["name"] = data[0].filename;
                    $("#imageInfoModal").toggleClass("show");
                });
            }

        });
    }

    async fetchFileData(file) {
        console.log("FFD: ", file);
        const data = {
            files: file
        };
        const response = await sendMessage(this.fileEndpoint, data);
        console.log("Response received:", response);
        if (response.hasOwnProperty("files")) {
            return response.files;
        }
        return response;
    }

    async refresh() {
        await this.buildTree();
    }

    setCurrentPath(path) {
        this.currentPath = path;
        console.log("Current path set:", path);
    }

    addOnDoubleClick(callback) {
        this.onDoubleClickCallbacks.push(callback);
    }

    addOnClick(callback) {
        this.onClickCallbacks.push(callback);
    }

    addOnSelect(callback) {
        this.onSelectCallbacks.push(callback);
    }

    addOnCancel(callback) {
        this.onCancelCallbacks.push(callback);
    }

}
