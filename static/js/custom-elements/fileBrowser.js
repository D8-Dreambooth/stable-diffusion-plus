class FileBrowser {
    constructor(parentElement, options = {}) {
        this.onDoubleClickCallbacks = [];
        this.onClickCallbacks = [];
        this.onSelectCallbacks = [];
        this.onCancelCallbacks = [];
        this.selected = "";
        this.startLink = ""
        this.getValue = this.getValue.bind(this);
        this.setValue = this.setValue.bind(this);

        let wrapper = document.createElement("div");
        wrapper.classList.add("row", "fileBrowserContainer");
        parentElement.innerHTML = "";
        this.container = parentElement;
        this.parentElement = wrapper;
        this.infoPanel = undefined;
        this.currentPath = "";
        if (options["initialPath"] !== undefined) {
            this.setCurrentPath(options["initialPath"]);
        }

        this.currentParent = "";
        this.value = "";
        this.selectedLink = undefined;
        this.sortType = "name";
        this.sortOrder = "desc";
        this.sortId = "fileSortButton" + Math.floor(Math.random() * 1000000);

        if (options["selectedElement"] !== undefined && options["selectedElement"] !== "") {
            const path = options["selectedElement"];
            const lastSeparatorIndex = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
            if (lastSeparatorIndex !== -1) {
                const parentDirectory = path.slice(0, lastSeparatorIndex);
                const directory = path.slice(lastSeparatorIndex + 1);
                this.setCurrentPath(parentDirectory);
                this.selectedLinks = [];
                this.selected = directory;
                this.value = path;
            } else {
                this.selectedLinks = [];
                this.selected = path;
                this.value = path;
            }
            this.setValue(path);
            console.log("Value set to: ", this.value);
        }

        this.treeContainer = document.createElement("div");
        this.treeContainer.classList.add("tree");

        this.treeParent = document.createElement("div");
        this.treeParent.classList.add("tree-container", "col", "borderSection");
        this.showTitle = options["showTitle"] !== undefined ? options["showTitle"] : true;
        this.showInfo = options["showInfo"] !== undefined ? options["showInfo"] : true;
        this.allowShared = options["allowShared"] !== undefined ? options["allowShared"] : false;
        this.allowProtected = options["allowProtected"] !== undefined ? options["allowProtected"] : false;
        this.baseDir = "user";
        this.style = options["style"] !== undefined ? options["style"] : "";
        this.placeholder = options["placeholder"] || "Select something...";
        this.showSelectButton = options["showSelectButton"] || false;
        this.listFiles = options["listFiles"] || false;
        this.expanded = options["expand"] || false;
        this.multiselect = options["multiselect"] || false;
        this.dropdown = options["dropdown"] !== undefined ? options["dropdown"] : false;
        this.editor = null;
        if (this.dropdown) {
            this.parentElement.classList.add("dropdown");
            this.treeParent.classList.add("dropdown");
        }
        if (this.showSelectButton) this.treeContainer.classList.add("selectSibling");

        if (!this.showInfo) {
            this.treeParent.classList.add("no-info");
        }

        if (this.expanded) {
            this.treeParent.classList.add("full");
        }
        if (this.style !== "") {
            this.treeParent.style.cssText = this.style;
        }

        this.addKeyboardListener();

        let inputGroup = this.buildInput();

        this.buildTree().then(() => {
            this.parentElement.prepend(inputGroup);
            this.treeParent.appendChild(this.treeContainer);

            if (this.showSelectButton) {
                const selectButton = document.createElement("button");
                selectButton.classList.add("btn", "btn-primary");
                selectButton.textContent = "Select";
                selectButton.addEventListener("click", () => {
                    this.selectedLink = this.selectedLinks.length > 0 ? this.selectedLinks[0] : undefined;
                    if (this.selectedLink !== undefined) {
                        if (this.selectedLink.dataset.path === '..') {
                            this.input.value = this.currentParent;
                            this.value = this.currentParent;
                        } else {
                            this.input.value = this.selectedLink.dataset.path;
                            this.value = this.selectedLink.dataset.fullPath;
                        }
                        this.setValue(this.value);
                        this.container.dataset.value = this.value;
                        for (let i = 0; i < this.onSelectCallbacks.length; i++) {
                            this.onSelectCallbacks[i](this.value);
                        }
                        console.log("Selected: " + this.value);
                        this.toggleTree();
                    }
                });
                const cancelButton = document.createElement("button");
                cancelButton.classList.add("btn", "btn-secondary");
                cancelButton.textContent = "Cancel  ";
                cancelButton.addEventListener("click", (event) => {
                    event.preventDefault();
                    this.toggleTree();
                });

                const btnGroup = document.createElement("div");
                btnGroup.classList.add("btn-group", "file-buttons", "hide");
                btnGroup.appendChild(selectButton);
                btnGroup.appendChild(cancelButton);
                this.parentElement.appendChild(btnGroup);
            }

            if (!this.dropdown) {
                const fileButtons = this.buildFileButtons();
                parentElement.append(fileButtons);
                if (this.allowProtected || this.allowShared) {
                    const pathButtons = this.buildPathButtons();
                    parentElement.append(pathButtons);
                }
            }


            parentElement.appendChild(wrapper);

            this.parentElement.append(this.treeParent);

            if (this.showInfo) {
                this.onClickCallbacks.push(this.showFileInfo);
                this.infoPanel = document.createElement("div");
                this.infoPanel.classList.add("infoPanel", "borderSection", "closed", "col-sm-12", "col-md-6", "col-lg-4");
                this.parentElement.appendChild(this.infoPanel);
                this.createImageModal("");
                this.createTextModal("");
            }
            //this.attachEventHandlers();
        });
    }

    async refresh() {
        await this.buildTree();
    }

    getValue() {
        console.log("Getting value: ", this.value);
        return this.value;
    }

    setValue(value) {
        this.value = value;
    }

    setCurrentPath(path) {
        this.currentPath = path;
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


    buildFileButtons() {
        let buttonCol = document.createElement("div");
        buttonCol.classList.add("col-12", "text-center", "buttonCol");

        let buttonGroup = document.createElement("div");
        buttonGroup.classList.add("btn-group", "btn-group-sm");

        let uploadButton = document.createElement("button");
        uploadButton.innerHTML = '<i class="bx bx-upload"></i>';
        uploadButton.classList.add("btn", "btn-primary");
        uploadButton.title = "Upload a file to the current directory";
        uploadButton.dataset["function"] = "upload";

        let refreshButton = document.createElement("button");
        refreshButton.innerHTML = '<i class="bx bx-refresh"></i>';
        refreshButton.classList.add("btn", "btn-secondary");
        refreshButton.title = "Refresh the current directory";
        refreshButton.dataset["function"] = "refresh";

        let newButton = document.createElement("button");
        newButton.innerHTML = '<i class="bx bx-plus"></i>';
        newButton.classList.add("btn", "btn-secondary");
        newButton.title = "Create a new directory";
        newButton.dataset["function"] = "new";

        let renameButton = document.createElement("button");
        renameButton.innerHTML = '<i class="bx bx-rename"></i>';
        renameButton.classList.add("btn", "btn-secondary");
        renameButton.title = "Rename the selected file or directory";
        renameButton.dataset["function"] = "rename";

        let deleteButton = document.createElement("button");
        deleteButton.innerHTML = '<i class="bx bx-trash"></i>';
        deleteButton.classList.add("btn", "btn-danger");
        deleteButton.title = "Delete the selected file or directory";
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

    buildPathButtons() {
        let pathCol = document.createElement("div");
        pathCol.classList.add("col-12", "text-center", "pathCol");

        let pathGroup = document.createElement("div");
        pathGroup.classList.add("btn-group", "btn-group-sm");

        let userButton = document.createElement("button");
        userButton.innerHTML = '<i class="bx bx-user"></i>';
        userButton.classList.add("btn", "btn-secondary", "active", "pathBtn");
        userButton.dataset["base"] = "user";
        userButton.title = "View user files.";
        pathGroup.appendChild(userButton);


        if (this.allowShared) {
            let sharedButton = document.createElement("button");
            sharedButton.innerHTML = '<i class="bx bx-share-alt"></i>';
            sharedButton.classList.add("btn", "btn-secondary", "pathBtn");
            sharedButton.dataset["base"] = "shared";
            sharedButton.title = "View shared files";
            pathGroup.appendChild(sharedButton);
        }

        if (this.allowProtected) {
            let protectedButton = document.createElement("button");
            protectedButton.innerHTML = '<i class="bx bx-lock"></i>';
            protectedButton.classList.add("btn", "btn-secondary", "pathBtn");
            protectedButton.dataset["base"] = "protected";
            protectedButton.title = "View protected files";
            pathGroup.appendChild(protectedButton);
        }

        pathGroup.querySelectorAll("button").forEach(button => {
            // Get the data-base attribute of the selected element
            button.addEventListener("click", () => {
                this.setCurrentPath("");
                let newBase = button.dataset.base;
                if (this.baseDir !== newBase) {
                    this.baseDir = newBase;
                    console.log("New base dir: " + this.baseDir);
                    $(".pathBtn.active").removeClass("active");
                    button.classList.add("active");
                    this.refresh();
                }
            });
        });

        pathCol.appendChild(pathGroup);
        let pathRow = document.createElement("div");
        pathRow.classList.add("row", "pathRow");
        pathRow.appendChild(pathCol);
        return pathRow;
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
        let show_shared = this.baseDir === "shared";
        let show_protected = this.baseDir === "protected";
        const selectedFiles = [];
        selected.forEach((item) => {
            selectedFiles.push(item.dataset.fullPath);
        });
        switch (method) {
            case "refresh":
                // call the async this.refresh() method
                this.refresh().then(() => {
                });
                break;
            case "delete":
                // Send the list of selected files
                if (selectedFiles.length > 0) {
                    if (confirm(`Are you sure you want to delete these ${selectedFiles.length} file(s)? This action is irreversible.`)) {
                        const data = {
                            dir: fileCurrent.innerHTML,
                            files: selectedFiles,
                            method: method,
                            shared: show_shared,
                            protected: show_protected
                        };
                        sendMessage("handleFile", data).then(() => {
                            this.refresh().then(() => {
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
                            newName: newFileName,
                            shared: show_shared,
                            protected: show_protected
                        };
                        sendMessage("handleFile", data).then(() => {
                            this.refresh().then(() => {
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
                    const fileData = [];
                    files.forEach((file) => {
                        fileData.push({name: file.name, dest: fileCurrent.innerText + "/" + file.name});
                        formData.append("files", file);
                    });
                    formData.append("dir", fileCurrent.innerText);
                    formData.append("file_data", JSON.stringify(fileData));
                    let upDiv = $(".upDiv");
                    upDiv.show();
                    const response = await fetch("/files/upload", {
                        method: "POST",
                        body: formData,
                    });
                    const data = await response.json();
                    upDiv.hide();
                    await this.refresh();
                });


                input.click();
                break;

            case "new":
                // Open a dialog asking for the folder name, then sendMessage to handleFile with the user input for the dir name under "files".
                const folderName = prompt("Enter the folder name:");
                if (folderName) {
                    const data = {
                        dir: fileCurrent.innerHTML,
                        files: [folderName],
                        method: method,
                        shared: show_shared,
                        protected: show_protected
                    };
                    sendMessage("handleFile", data).then(() => {
                        this.refresh().then(() => {
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
                this.handleLinkClick(sibling, ctrl_pressed, shift_pressed);
            }
        } else {
            const firstChild = this.treeContainer.querySelector(".fileLi");
            if (firstChild) {
                this.handleLinkClick(firstChild, ctrl_pressed, shift_pressed);
            }
        }

        const images = document.querySelector(".img-info");
        const fullScreen = document.querySelector(".img-fullscreen");
        if (images) {
            fullScreen.src = images.src;
            fullScreen.dataset["name"] = images.dataset["name"];
        }

    }

    addKeyboardListener() {
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
                    const selectedLi = focusedElement.closest(".fileLi.selected");
                    if (selectedLi !== null && selectedLi.classList.contains("fileLi")) {
                        selectedLi.dispatchEvent(new MouseEvent('dblclick', {bubbles: true}));
                    }
                }
            }

            const imageModal = document.getElementById("imageInfoModal");
            if (imageModal.classList.contains("show")) {
                if (event.key === "ArrowLeft") {
                    // Left arrow key
                    this.selectNextItem(-1);
                } else if (event.key === "ArrowRight") {
                    // Right arrow key
                    this.selectNextItem(1);
                } else if (event.key === "Escape") {
                    // Escape key
                    $("#imageInfoModal").removeClass("show");
                }
            }
        }.bind(this));


        let timeoutId = null;
        const delay = 200;

        this.treeContainer.addEventListener('dragenter', (e) => {
            e.preventDefault();
            const tempDiv = document.querySelector(".tempDiv");
            tempDiv.classList.add('show');
        });

        this.treeContainer.addEventListener('dragover', (e) => {
            e.preventDefault();
            clearTimeout(timeoutId);
        });

        this.treeContainer.addEventListener('dragleave', (e) => {
            e.preventDefault();
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                const tempDiv = document.querySelector(".tempDiv");
                tempDiv.classList.remove('show');
            }, delay);
        });


        this.treeContainer.addEventListener("drop", async (e) => {
            e.preventDefault();
            const tempDiv = document.querySelector(".tempDiv");
            tempDiv.classList.remove("show");
            const fileCurrent = this.treeContainer.querySelector(".fileCurrent");
            const items = Array.from(e.dataTransfer.items);
            const formData = new FormData();
            const fileData = [];
            formData["is_dir"] = false;
            const files = [];
            for (let i = 0; i < items.length; i++) {
                const entry = items[i].webkitGetAsEntry();
                if (entry.isDirectory) {
                    await this.handleDirectoryEntry(entry, fileCurrent.innerText, fileData, files, true);
                } else {
                    const file = items[i].getAsFile();
                    files.push(file);
                    fileData.push({name: file.name, dest: fileCurrent.innerText});
                }
            }

            formData.append("dir", fileCurrent.innerText);
            formData.append("file_data", JSON.stringify(fileData));
            files.forEach((file) => {
                formData.append("files", file);
            });
            let upDiv = $(".upDiv");
            upDiv.show();
            const response = await fetch("/files/upload", {
                method: "POST",
                body: formData,
            });
            await response.json();
            upDiv.hide();
            await this.refresh();
        });
    }

    async handleDirectoryEntry(directory, parentPath, fileData, files, root = false) {
        const dirReader = directory.createReader();
        const entries = await this.readEntries(dirReader);

        for (let i = 0; i < entries.length; i++) {
            const entry = entries[i];
            if (entry.isDirectory) {
                const dirPath = parentPath + this.separator + directory.name + this.separator + entry.name;
                await this.handleDirectoryEntry(entry, dirPath, fileData, files);
            } else {
                let dirPath = parentPath;
                if (root) {
                    dirPath = parentPath + this.separator + directory.name + this.separator + entry.name;
                }
                const file = await this.getFile(entry);
                files.push(file);
                fileData.push({name: file.name, dest: dirPath});
            }
        }
    }

    async readEntries(dirReader) {
        return new Promise((resolve, reject) => {
            dirReader.readEntries((entries) => {
                resolve(entries);
            }, (error) => {
                reject(error);
            });
        });
    }

    async getFile(entry) {
        return new Promise((resolve, reject) => {
            entry.file((file) => {
                resolve(file);
            }, (error) => {
                reject(error);
            });
        });
    }

    buildInfoPanel(fileInfo) {
        const panelContainer = document.createElement("div");
        panelContainer.classList.add("row");

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
            pre.id = "dataPanelText";
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


        return panelContainer;
    }

    downloadImage(src, name) {
        const link = document.createElement("a");
        link.href = src;
        link.download = name;
        link.click();
    }

    createTextModal(src) {
        const modal = document.createElement('div');
        modal.classList.add('modal', 'fade');
        modal.id = 'jsonEditModal';
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('aria-labelledby', 'jsonEditModalLabel');
        modal.setAttribute('aria-hidden', 'true');

        const modalDialog = document.createElement('div');
        modalDialog.classList.add('modal-dialog', 'modal-fullscreen');
        modal.appendChild(modalDialog);

        const modalContent = document.createElement('div');
        modalContent.classList.add('modal-content');
        modalDialog.appendChild(modalContent);

        const modalHeader = document.createElement('div');
        modalHeader.classList.add('modal-header');
        modalContent.appendChild(modalHeader);

        const modalTitle = document.createElement('h5');
        modalTitle.classList.add('modal-title');
        modalTitle.id = 'exampleModalLabel';
        modalTitle.innerText = 'File Editor';
        modalHeader.appendChild(modalTitle);
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.classList.add('btn-close');
        closeButton.setAttribute('data-bs-dismiss', 'modal');
        closeButton.setAttribute('aria-label', 'Close');
        modalHeader.appendChild(closeButton);

        const modalBody = document.createElement('div');
        modalBody.classList.add('modal-body');
        modalContent.appendChild(modalBody);

        // Add your own custom code here for the modal body

        const modalFooter = document.createElement('div');
        modalFooter.classList.add('modal-footer');
        modalContent.appendChild(modalFooter);

        const closeButton2 = document.createElement('button');
        closeButton2.type = 'button';
        closeButton2.classList.add('btn', 'btn-secondary');
        closeButton2.setAttribute('data-bs-dismiss', 'modal');
        closeButton2.innerText = 'Close';
        modalFooter.appendChild(closeButton2);


        const options = {};
        const modalEditor = document.createElement('div');
        modalEditor.classList.add('textEditor');
        modalBody.appendChild(modalEditor);
        this.editor = new JSONEditor(modalEditor, options);
        const saveButton = document.createElement('button');
        saveButton.type = 'button';
        saveButton.classList.add('btn', 'btn-primary');
        saveButton.innerText = 'Save changes';
        modalFooter.appendChild(saveButton);
        saveButton.addEventListener('click', () => {
            let data = this.editor.get();
            let show_protected = false;
            let show_shared = false;
            console.log("Fetching", this.baseDir);
            if (this.baseDir === "shared") show_shared = true;
            if (this.baseDir === "protected") show_protected = true;
            console.log("We should save this: ", data);
            let saveData = {
                path: this.editFile,
                file_data: data,
                protected: show_protected,
                shared: show_shared
            }
            console.log("Saving", saveData);
            sendMessage("saveFile", saveData, true).then((response) => {
                console.log("Saved?", response);
            });
        });

        document.body.appendChild(modal);
        this.textModal = new bootstrap.Modal(document.getElementById('jsonEditModal'), options);
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
        if (!this.dropdown) {
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
        toggleButton.addEventListener("click", (event) => {
            event.preventDefault();
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
        console.log("Response: " + response);
        if (!response.hasOwnProperty("items")) {
            console.log("No items found");
            return;
        }
        let show_shared = response["show_shared"] || false;
        let show_protected = response["show_protected"] || false;
        this.allowProtected = show_protected;
        this.allowShared = show_shared;
        console.log("Show shared/protected: " + show_shared + "/" + show_protected);
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
        currentPath.classList.add("card-header", "fileCurrent", "fit");
        if (this.dropdown) currentPath.classList.add("dropdown");
        currentPathCol.appendChild(currentPath);

        let sortCol = this.createSortCol();
        currentPathContainer.appendChild(currentPathCol);
        currentPathContainer.appendChild(sortCol);

        this.treeContainer.appendChild(currentPathContainer);
        this.treeContainer.appendChild(tree);


        if (this.infoPanel) {
            this.infoPanel.classList.add("closed");
        }

        const tempDiv = document.createElement('div');
        tempDiv.textContent = 'Drop files to upload';
        tempDiv.className = 'tempDiv';
        this.treeContainer.appendChild(tempDiv);

        const upDiv = document.createElement('div');
        upDiv.textContent = 'Uploading...';
        upDiv.className = 'upDiv';
        this.treeContainer.appendChild(upDiv);

        this.attachEventHandlers();
        this.sortTree();
    }

    createSortCol() {
        let sortCol = document.createElement("div");
        sortCol.classList.add("col-auto", "fileSortCol");
        let sortDropdown = document.createElement("div");
        sortDropdown.classList.add("dropdown", "fileSortDropdown");

        let sortButton = document.createElement("button");
        // Write a switch statement to set the current sortButton icon based on this.sortType
        let sortIcon = "bx-text";
        switch (this.sortType) {
            case "name":
                sortIcon = "bx-text";
                break;
            case "date":
                sortIcon = "bx-calendar";
                break;
            case "size":
                sortIcon = "bx-hdd";
                break;
            case "type":
                sortIcon = "bx-file-blank";
                break;
        }
        let orderIcon = "bx-sort-up";
        if (this.sortOrder === "desc") {
            orderIcon = "bx-sort-down";
        }
        sortButton.innerHTML = '<i class="bx ' + sortIcon + '"></i><i class="bx ' + orderIcon + '"></i>';
        sortButton.classList.add("btn", "btn-outline-primary", "fileSortButton", "dropdown-toggle");
        sortButton.dataset["type"] = "name";
        sortButton.setAttribute("data-bs-toggle", "dropdown");
        sortButton.setAttribute("aria-haspopup", "true");
        sortButton.setAttribute("aria-expanded", "false");
        // Random ID
        sortButton.id = this.sortId;
        sortDropdown.appendChild(sortButton);

        let sortMenu = document.createElement("div");
        sortMenu.classList.add("dropdown-menu", "fileSortMenu");
        sortMenu.setAttribute("aria-labelledby", sortButton.id);

        // Sort by name menu item
        let sortByNameMenuItem = document.createElement("a");
        sortByNameMenuItem.innerHTML = '<i class="bx bx-text"></i> Name';
        sortByNameMenuItem.dataset["type"] = "name";
        sortByNameMenuItem.classList.add("dropdown-item", "fileSortMenuItem");
        if (this.sortType === "name") sortByNameMenuItem.classList.add("active");
        sortMenu.appendChild(sortByNameMenuItem);

        // Sort by size menu item
        let sortBySizeMenuItem = document.createElement("a");
        sortBySizeMenuItem.innerHTML = '<i class="bx bxs-hdd"></i> Size';
        sortBySizeMenuItem.dataset["type"] = "size";
        sortBySizeMenuItem.classList.add("dropdown-item", "fileSortMenuItem");
        if (this.sortType === "size") sortBySizeMenuItem.classList.add("active");
        sortMenu.appendChild(sortBySizeMenuItem);

        // Sort by date menu item
        let sortByDateMenuItem = document.createElement("a");
        sortByDateMenuItem.innerHTML = '<i class="bx bx-calendar"></i> Date';
        sortByDateMenuItem.dataset["type"] = "date";
        sortByDateMenuItem.classList.add("dropdown-item", "fileSortMenuItem");
        if (this.sortType === "date") sortByDateMenuItem.classList.add("active");
        sortMenu.appendChild(sortByDateMenuItem);

        // Sort by type menu item
        let sortByTypeMenuItem = document.createElement("a");
        sortByTypeMenuItem.innerHTML = '<i class="bx bxs-file-blank"></i> Type';
        sortByTypeMenuItem.dataset["type"] = "type";
        sortByTypeMenuItem.classList.add("dropdown-item", "fileSortMenuItem");
        if (this.sortType === "type") sortByTypeMenuItem.classList.add("active");
        sortMenu.appendChild(sortByTypeMenuItem);

        sortDropdown.appendChild(sortMenu);
        sortCol.appendChild(sortDropdown);

        return sortCol;
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
        let keys = Object.keys(response);
        let index = keys.indexOf("..");
        let parent = null;
        link.innerHTML = "..";
        listItem.dataset.path = "..";
        listItem.dataset.type = "directory";

        if (index !== -1) {
            parent = Object.assign({}, response[keys[index]]);
            delete response[keys[index]];
            listItem.dataset.fullPath = parent.path + this.separator + "..";
        }

        if (this.currentParent !== "") {
            listItem.appendChild(link);
            root.appendChild(listItem);
        }

        for (const [path, details] of Object.entries(response)) {
            const dateModified = details.time;
            const size = details.size;
            const type = details.type;
            const children = details.data;
            const fullPath = details.fullPath;
            const listItem = document.createElement("li");
            listItem.classList.add("fileLi");
            listItem.dataset.path = path;
            listItem.dataset.fullPath = fullPath;
            listItem.dataset.type = type;
            listItem.dataset.date = dateModified;
            listItem.dataset.size = size;
            const shortPath = fullPath.split(this.separator).pop();
            const icon = document.createElement("i");
            const iconClass = this.getClass(type);
            icon.classList.add("bx", iconClass, "fileIcon");
            listItem.appendChild(icon);
            const link = document.createElement("a");
            link.innerHTML = shortPath;
            listItem.appendChild(link);
            if (children) {
                const childList = document.createElement("ul");
                listItem.appendChild(childList);
            }
            root.appendChild(listItem);
            if (this.selected && this.selected === shortPath) {
                listItem.classList.add("selected");
                this.selected = "";
                this.selectedLink = listItem;
                this.selectedLinks.push(listItem);
                this.input.value = listItem.dataset.path;
                this.value = this.input.value;
                this.setValue(this.value);
                console.log("Setting value to " + this.value);
            }

        }
        return root;
    }

    attachEventHandlers() {
        const allLinks = this.treeContainer.querySelectorAll(".fileLi");
        allLinks.forEach((link) => {
            let lastTouchTime = 0;
            if (link.dataset.path) {
                link.addEventListener("dblclick", () => {
                    this.handleLinkDblClick(link);
                });

                link.addEventListener('touchstart', (event) => {
                    if (event.touches.length > 1) {
                        return;
                    }

                    const touchTime = new Date().getTime();

                    if (touchTime - lastTouchTime < 500) {
                        event.preventDefault();
                        this.handleLinkDblClick(link);
                    }

                    lastTouchTime = touchTime;
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
        let sortButtons = this.treeContainer.querySelectorAll(".fileSortMenuItem");
        sortButtons.forEach(button => {
            button.addEventListener("click", event => {
                event.preventDefault();
                let activeButton = this.treeContainer.querySelector(".fileSortMenuItem.active");
                activeButton.classList.remove("active");
                let type = event.currentTarget.dataset.type;
                if (this.sortType === type) {
                    if (this.sortOrder === "asc") {
                        this.sortOrder = "desc";
                    } else {
                        this.sortOrder = "asc";
                    }
                } else {
                    this.sortType = type;
                }
                let sortButton = document.getElementById(this.sortId);
                // Write a switch statement to set the current sortButton icon based on this.sortType
                let sortIcon = "bx-text";
                switch (this.sortType) {
                    case "name":
                        sortIcon = "bx-text";
                        break;
                    case "date":
                        sortIcon = "bx-calendar";
                        break;
                    case "size":
                        sortIcon = "bx-hdd";
                        break;
                    case "type":
                        sortIcon = "bx-file-blank";
                        break;
                }
                let orderIcon = "bx-sort-up";
                if (this.sortOrder === "desc") {
                    orderIcon = "bx-sort-down";
                }
                sortButton.innerHTML = '<i class="bx ' + sortIcon + '"></i><i class="bx ' + orderIcon + '"></i>';


                event.currentTarget.classList.add("active");

                this.sortTree();
            });
        });

    }

    handleLinkDblClick(link) {
        if (link.dataset.type === "directory") {
            this.currentPath = link.dataset.fullPath;

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
        } else if (link.dataset.type === ".txt" || link.dataset.type === ".json") {
            if (this.showInfo) {
                console.log("Link data: ", link.dataset);
                this.fetchFileData(link.dataset.path).then((data) => {
                    console.log("File data: ", data);
                    if (data.length > 0) {
                        let fileData = data[0];
                        if (fileData.hasOwnProperty("data")) {
                            let fileText = fileData.data;
                            try {
                                fileText = JSON.parse(fileText);
                            } catch (e) {
                                console.log("Not JSON");
                            }
                            this.editor.set(fileText);
                            this.editFile = link.dataset.fullPath;
                            this.textModal.toggle();

                        }
                    }

                });
            }
        }
        this.onDoubleClickCallbacks.forEach((callback) =>
            callback(link.dataset.fullPath, link.dataset.type)
        )
    }

    // Define sortTree function
    sortTree() {
        let treeRoot = this.treeContainer.querySelector(".treeRoot");
        let treeItems = Array.from(treeRoot.children);
        // Pop the first element and store it
        let firstElement = treeItems.shift();

        // Sort the remaining items
        treeItems.sort((a, b) => {
            let aVal = a.dataset[this.sortType];
            let bVal = b.dataset[this.sortType];
            if (this.sortType === "name") {
                aVal = b.dataset["path"];
                bVal = a.dataset["path"];
            } else if (this.sortType === "size") {
                aVal = parseInt(aVal);
                bVal = parseInt(bVal);
            } else if (this.sortType === "date") {
                aVal = parseFloat(aVal);
                bVal = parseFloat(bVal);
            }
            if (this.sortType === "size" || this.sortType === "date") {
                if (this.sortOrder === "asc") {
                    return (aVal < bVal) ? -1 : (aVal > bVal) ? 1 : 0;
                } else {
                    return (bVal < aVal) ? -1 : (bVal > aVal) ? 1 : 0;
                }
            } else {
                if (this.sortOrder === "asc") {
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
            callback.call(this, link, link.dataset.fullPath, link.dataset.type)
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
        let show_protected = false;
        let show_shared = false;
        console.log("Fetching", this.baseDir);
        if (this.baseDir === "shared") show_shared = true;
        if (this.baseDir === "protected") show_protected = true;
        const data = {
            start_dir: directory,
            include_files: this.listFiles,
            recursive: recursive,
            filter: filter,
            protected: show_protected,
            shared: show_shared
        };
        const response = await sendMessage("files", data);
        this.setCurrentPath(response["current"]);
        return response;
    }

    showFileInfo(link, data1, data2) {
        if (!this.showInfo) return;
        if (data1.indexOf("..") !== -1) {
            this.infoPanel.classList.add("closed");
            return;
        }
        this.fetchFileData(data1).then((data) => {
            let panel = this.buildInfoPanel(data[0]);
            this.infoPanel.innerHTML = panel.innerHTML;
            if (this.infoPanel.classList.contains("closed")) {
                this.infoPanel.classList.remove("closed");
                this.treeParent.classList.add("full", "hasInfo");
            }
            let leftIcon = document.querySelector(".info-icon-left");
            let rightIcon = document.querySelector(".info-icon-right");
            if (leftIcon) {
                leftIcon.addEventListener("click", () => {
                    this.downloadImage(data[0].src, data[0].filename);
                });
            }
            if (rightIcon) {
                rightIcon.addEventListener("click", () => {
                    let img = document.getElementById("infoModalImage");
                    img.src = data[0].src;
                    img.dataset["name"] = data[0].filename;
                    $("#imageInfoModal").toggleClass("show");
                });
            }

        });
    }

    async fetchFileData(file) {
        const data = {
            files: file,
            protected: this.baseDir === "protected",
            shared: this.baseDir === "shared"
        };
        const response = await sendMessage("file", data);
        if (response.hasOwnProperty("files")) {
            return response.files;
        }
        return response;
    }

    val() {
        return this.input.value;
    }
}

$.fn.fileBrowser = function (options) {
    this.each(function () {
        const $this = $(this);
        let fileBrowser = $this.data('FileBrowser');
        if (!fileBrowser) {
            fileBrowser = new FileBrowser(this, options);
            $this.data("FileBrowser", fileBrowser);
        } else {
            console.log("FileBrowser already initialized");
        }
    });
    return this.data('FileBrowser');
};

