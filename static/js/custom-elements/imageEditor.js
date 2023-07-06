class ImageEditor {
    constructor(
        container,
        width,
        height,
        canvasWidth = 512,
        canvasHeight = 512,
        scaleMode = "scale",
        useImageScale = true,
        origin = "center"
    ) {
        // If container is a string, assume it is an id
        let containerId = container;
        console.log("Setting origin to " + origin + " and scale mode to " + scaleMode + " for image editor.");
        this.imageOrigin = origin;
        this.canvasWidth = canvasWidth;
        this.canvasHeight = canvasHeight;
        this.scaleMode = scaleMode;

        if (typeof container === "string") {
            this.container = document.getElementById(container);
        } else {
            this.container = container;
            containerId = container.id;
        }
        this.container.classList.add("image_editor");
        this.scaleFactor = 0;
        this.useImageScale = useImageScale;
        this.containerId = containerId;
        this.wrapper = document.createElement("div");
        this.container.appendChild(this.wrapper);
        this.canvasWrapper = document.createElement('div');
        this.canvasWrapper.classList.add("canvasWrapper");
        this.canvasWrapper.style.width = width;
        this.canvasWrapper.style.height = height;
        // This is the canvas we will actually append to the DOM
        this.displayCanvas = document.createElement('canvas');
        this.displayCanvas.classList.add("displayCanvas");
        this.displayCanvas.style.cursor = 'none';
        // This one is for the dropped image, and will not be appended
        this.dropCanvas = document.createElement('canvas');
        this.dropCanvas.classList.add("editorCanvas", "dropCanvas");
        this.dropCanvas.style.cursor = 'none';
        // This one is for the drawing, and will not be appended
        this.drawCanvas = document.createElement('canvas');
        this.drawCanvas.classList.add("editorCanvas", "drawCanvas");
        this.drawCanvas.style.cursor = 'none';
        // This one is for the mask display, and will not be appended
        this.boundsCanvas = document.createElement('canvas');
        this.boundsCanvas.classList.add("editorCanvas", "maskCanvas");
        this.boundsCanvas.width = this.canvasWidth;
        this.boundsCanvas.height = this.canvasHeight;
        this.boundsCanvas.style.cursor = 'none';
        this.canvasWrapper.appendChild(this.displayCanvas);
        this.buttonGroup = document.createElement("div");
        this.buttonGroup.classList.add("btn-group", "editorButtons");
        this.wrapper.appendChild(this.canvasWrapper);
        this.wrapper.appendChild(this.buttonGroup);
        this.imageSource = null;
        this.context = this.drawCanvas.getContext('2d');
        this.isDrawing = false;
        this.undoStack = [];
        const ctx = this.drawCanvas.getContext('2d');
        const state = ctx.getImageData(0, 0, this.drawCanvas.width, this.drawCanvas.height);
        console.log("Pushing initial state to undo stack");
        this.undoStack.push({type: 'draw', imageData: state});
        this.brushSize = 10;
        this.brushColor = 'black';
        this.scale = 1;
        registerImageReceiver(containerId, this.importImage.bind(this));
        registerMaskReceiver(containerId, this.importMask.bind(this));
        this.displayCanvas.addEventListener('touchstart', this.handleInputStart.bind(this));
        this.displayCanvas.addEventListener('mousedown', this.handleInputStart.bind(this));
        this.displayCanvas.addEventListener('mouseenter', this.handleInputStart.bind(this));
        this.displayCanvas.addEventListener('touchmove', this.handleInputMove.bind(this));
        this.displayCanvas.addEventListener('mousemove', this.handleInputMove.bind(this));
        this.displayCanvas.addEventListener('touchend', this.handleInputEnd.bind(this));
        this.displayCanvas.addEventListener('mouseleave', this.handleInputEnd.bind(this));
        this.displayCanvas.addEventListener('mouseup', this.handleInputEnd.bind(this));
        this.displayCanvas.addEventListener('dragover', this.handleDragOver.bind(this));
        this.displayCanvas.addEventListener('drop', this.handleDrop.bind(this));
        this.getDropped.bind(this);
        this.getMask.bind(this);
        this.addButton("upload", this.uploadImage.bind(this))
        this.addButton('share-alt', this.showShareMenu.bind(this));
        this.addButton('x', this.clear.bind(this));
        this.addButton('undo', this.undo.bind(this));
        this.addButton('brush', this.showBrushSizeDialog.bind(this));
        this.addButton('palette', this.showColorPicker.bind(this));
        this.updateCursorStyle();
        // For hiding and showing the bounding rect
        this.clearTimeout = null;
        this.lastWidth = 0;
        this.lastHeight = 0;
    }

    uploadImage() {
        console.log("Uploading image");
        // Open a file picker filtered to images
        let filePicker = document.createElement('input');
        filePicker.type = 'file';
        filePicker.accept = 'image/*';
        filePicker.onchange = (e) => {
            let file = e.target.files[0];
            if (file) {
                let reader = new FileReader();
                reader.onload = (e) => {
                    this.importImage(e.target.result);
                }
                reader.readAsDataURL(file);
            }
        }
        filePicker.click();

    }

    redrawCanvases(targetCanvasWidth, targetCanvasHeight) {
        let showBounds = false;
        if (this.lastHeight !== targetCanvasHeight || this.lastWidth !== targetCanvasWidth) {
            showBounds = true;
            this.lastHeight = targetCanvasHeight;
            this.lastWidth = targetCanvasWidth;
        }
        let ctx = this.displayCanvas.getContext('2d');
        ctx.clearRect(0, 0, this.displayCanvas.width, this.displayCanvas.height);

        let boundsCtx = this.boundsCanvas.getContext('2d');
        let boundsWidth, boundsHeight;

        if (this.useImageScale) {
            boundsWidth = this.dropCanvas.width;
            boundsHeight = this.dropCanvas.height;
        } else {
            boundsWidth = targetCanvasWidth;
            boundsHeight = targetCanvasHeight;
        }

        let maxWidth = Math.max(this.drawCanvas.width, this.dropCanvas.width);
        let maxHeight = Math.max(this.drawCanvas.height, this.dropCanvas.height);

        this.displayCanvas.width = maxWidth;
        this.displayCanvas.height = maxHeight;
        this.boundsCanvas.width = boundsWidth;
        this.boundsCanvas.height = boundsHeight;

        // Update drawCanvas dimensions to match the displayCanvas only when they don't match
        if (this.drawCanvas.width !== boundsWidth || this.drawCanvas.height !== boundsHeight) {
            const tempCanvas = document.createElement('canvas');
            const tempCtx = tempCanvas.getContext('2d');
            tempCanvas.width = this.drawCanvas.width;
            tempCanvas.height = this.drawCanvas.height;

            // Copy the current drawCanvas content to tempCanvas
            tempCtx.drawImage(this.drawCanvas, 0, 0);

            // Resize drawCanvas
            this.drawCanvas.width = boundsWidth;
            this.drawCanvas.height = boundsHeight;

            // Copy the old drawCanvas content from tempCanvas back to the resized drawCanvas
            this.drawCanvas.getContext('2d').drawImage(tempCanvas, 0, 0);
        }

        if (showBounds) {
            // Fill boundsCanvas with semi-opaque red
            boundsCtx.fillStyle = 'rgba(255, 0, 0, 0.25)';
            boundsCtx.fillRect(0, 0, boundsWidth, boundsHeight);
            if (this.clearTimeout) {
                clearTimeout(this.clearTimeout);
            }
            this.clearTimeout = setTimeout(() => {
                // Clear the bounds canvas after 1 second
                boundsCtx.clearRect(0, 0, boundsWidth, boundsHeight);
                // Draw it to the main canvas
                console.log("Clearing bounds canvas")
                let ctx = this.displayCanvas.getContext('2d');
                ctx.clearRect(0, 0, this.displayCanvas.width, this.displayCanvas.height);
                ctx.drawImage(this.dropCanvas, 0, 0, this.dropCanvas.width, this.dropCanvas.height);
                ctx.drawImage(this.boundsCanvas, 0, 0, this.boundsCanvas.width, this.boundsCanvas.height);
                ctx.drawImage(this.drawCanvas, 0, 0, this.drawCanvas.width, this.drawCanvas.height);
            }, 1000);
        }

        ctx.drawImage(this.dropCanvas, 0, 0, this.dropCanvas.width, this.dropCanvas.height);
        ctx.drawImage(this.boundsCanvas, 0, 0, this.boundsCanvas.width, this.boundsCanvas.height);
        ctx.drawImage(this.drawCanvas, 0, 0, this.drawCanvas.width, this.drawCanvas.height);
        this.updateCursorStyle();

    }


    handleInputStart(event) {
        if (this.scaleFactor === 0) {
            this.updateCursorStyle();
        }
        const isNotSingleTouchOrLeftButtonNotPressed = !(event.type.startsWith('touch') && event.touches.length === 1) && !(event.type === 'mousemove') && !(event.type === 'mousedown' && event.button === 0);
        if (isNotSingleTouchOrLeftButtonNotPressed) return;

        event.preventDefault();

        let x, y;
        [x, y] = this.getCursorPosition(event);
        if (!this.isDrawing) {
            const ctx = this.drawCanvas.getContext('2d'); // Get context from drawCanvas
            ctx.beginPath(); // Start new path
            ctx.moveTo(x, y);
        }
        this.isDrawing = true;
        this.drawLine(x, y); // Draw a circle when the mouse is pressed
    }

    drawLine(x, y) {
        if (this.drawCanvas.width === 0 || this.drawCanvas.height === 0) {
            this.drawCanvas.width = this.displayCanvas.width;
            this.drawCanvas.height = this.displayCanvas.height;
        }
        const ctx = this.drawCanvas.getContext('2d');
        ctx.lineJoin = 'round'; // Use round corners
        ctx.lineCap = 'round'; // Use round line ends
        ctx.lineWidth = this.brushSize;
        ctx.strokeStyle = this.brushColor;
        ctx.lineTo(x, y);
        ctx.stroke();
        this.redrawCanvases(this.displayCanvas.width, this.displayCanvas.height);
    }


    handleInputEnd(event) {
        if (!this.isDrawing) return;
        this.isDrawing = false;
        const ctx = this.drawCanvas.getContext('2d');
        const state = ctx.getImageData(0, 0, this.drawCanvas.width, this.drawCanvas.height);
        this.undoStack.push({type: 'draw', imageData: state});
        console.log("Drawing ended, pushing state.", this.undoStack);

        ctx.beginPath(); // Start a new path
    }


    handleInputMove(event) {
        const isNotSingleTouchOrLeftButtonNotPressed = !(event.type.startsWith('touch') && event.touches.length === 1) && !(event.type === 'mousemove') && !(event.type === 'mousedown' && event.button === 0);
        if (isNotSingleTouchOrLeftButtonNotPressed) return;

        event.preventDefault();
        let x, y;
        [x, y] = this.getCursorPosition(event);
        if (this.isDrawing) {
            this.drawLine(x, y);
        }
    }


    updateCanvases(image, isMask) {
        console.log("Canvas update: ", this);
        // Function to calculate the offset for the image based on the origin
        // Step 1: Determine the target canvas dimensions
        let targetCanvasWidth, targetCanvasHeight;

        if (this.useImageScale && image) {
            let img = new Image();
            img.src = image;
            targetCanvasWidth = img.width;
            targetCanvasHeight = img.height;
            console.log("Using image dimensions", targetCanvasWidth, targetCanvasHeight);
        } else {
            targetCanvasWidth = this.canvasWidth;
            targetCanvasHeight = this.canvasHeight;
            console.log("Using default canvas dimensions", targetCanvasWidth, targetCanvasHeight);
        }

        // Update dropCanvas or drawCanvas
        let targetCanvas = isMask ? this.drawCanvas : this.dropCanvas;
        let targetCtx = targetCanvas.getContext('2d');
        if (!image) {
            console.log("No image provided?");
            return;
        }
        let updateHistory = false;
        if (isMask) {
            // Assume image is a mask created by the user drawing in the UI
            targetCtx.clearRect(0, 0, targetCanvas.width, targetCanvas.height); // Clear the drawCanvas
            if (targetCanvas.width !== this.displayCanvas.width || targetCanvas.height !== this.displayCanvas.height) {
                targetCanvas.width = this.displayCanvas.width;
                targetCanvas.height = this.displayCanvas.height;
                updateHistory = true;
            }
            let mask = new Image();
            mask.src = image;
            targetCtx.drawImage(mask, 0, 0, this.displayCanvas.width, this.displayCanvas.height);
            // Find the last "draw" element in the undo stack and replace it with the current contents of the drawCanvas
            if (updateHistory) {
                for (let i = this.undoStack.length - 1; i >= 0; i--) {
                    if (this.undoStack[i].type === 'draw') {
                        console.log("Replacing draw element in undo stack");
                        this.undoStack[i].imageData = targetCtx.getImageData(0, 0, targetCanvas.width, targetCanvas.height);
                        break;
                    }
                }
            }
            this.redrawCanvases(targetCanvasWidth, targetCanvasHeight);
        } else {
            // Assume image is an image dropped by the user
            targetCtx.clearRect(0, 0, targetCanvas.width, targetCanvas.height); // Clear the dropCanvas
            let img = new Image();
            img.onload = () => {
                let [scaleX, scaleY] = this.calculateCanvasDimensions(img, isMask, this.scaleMode, this.dropCanvas, this.canvasWidth, this.canvasHeight);
                if (this.useImageScale) {
                    console.log("Using image scale");
                    scaleX = 1;
                    scaleY = 1;
                }

                // vars returned: [targetCanvasWidth, targetCanvasHeight, targetMaskWidth, targetMaskHeight, scaleX, scaleY]
                console.log("Scalexy: ", scaleX, scaleY);
                // Update dropCanvas or drawCanvas
                let targetCanvas = isMask ? this.drawCanvas : this.dropCanvas;
                let targetCtx = targetCanvas.getContext('2d');

                if (this.useImageScale) {
                    targetCanvasWidth = img.width;
                    targetCanvasHeight = img.height;
                } else {
                    targetCanvasWidth = this.canvasWidth;
                    targetCanvasHeight = this.canvasHeight;
                }

                let scaledWidth = img.width * scaleX;
                let scaledHeight = img.height * scaleY;
                targetCanvas.width = targetCanvasWidth;
                targetCanvas.height = targetCanvasHeight;
                console.log("Scaled image dimensions: ", scaledWidth, scaledHeight);
                if (this.scaleMode === 'pad') {
                    targetCtx.fillStyle = 'black'; // For drawCanvas
                    targetCtx.fillRect(0, 0, targetCanvas.width, targetCanvas.height);
                    console.log("Calculating offset (origin): ", this.imageOrigin);
                    let offset = calculateOriginOffset(this.imageOrigin, targetCanvas.width, targetCanvas.height, scaledWidth, scaledHeight);

                    targetCtx.clearRect(offset.offsetX, offset.offsetY, scaledWidth, scaledHeight); // Clear area for image in drawCanvas
                    targetCtx = this.dropCanvas.getContext('2d');
                    targetCtx.fillStyle = 'transparent';
                    targetCtx.fillRect(0, 0, targetCanvas.width, targetCanvas.height);
                    targetCtx.drawImage(img, offset.offsetX, offset.offsetY, scaledWidth, scaledHeight); // Draw image at offset in dropCanvas
                } else {
                    console.log("Calculating offset canvas (origin): ", this.imageOrigin);
                    let offset = calculateOriginOffset(this.imageOrigin, targetCanvas.width, targetCanvas.height, scaledWidth, scaledHeight);
                    targetCtx.drawImage(img, offset.offsetX, offset.offsetY, scaledWidth, scaledHeight); // Draw image at offset
                }
                // Find the last drop element in the undo stack and replace it with the current contents of the dropCanvas
                let updated = false;
                for (let i = this.undoStack.length - 1; i >= 0; i--) {
                    if (this.undoStack[i].type === 'drop') {
                        console.log("Replacing drop element in undo stack");
                        this.undoStack[i].imageData = targetCtx.getImageData(0, 0, targetCanvas.width, targetCanvas.height);
                        updated = true;
                        break;
                    }
                }
                if (!updated) {
                    console.log("Pushing new drop element to undo stack");
                    this.undoStack.push({
                        type: 'drop',
                        imageData: targetCtx.getImageData(0, 0, targetCanvas.width, targetCanvas.height)
                    });
                }
                this.redrawCanvases(targetCanvasWidth, targetCanvasHeight);
            }
            img.src = image;
        }

    }

    calculateCanvasDimensions(img, useImageScale, scaleMode, dropCanvas, canvasWidth, canvasHeight) {
        console.log("Calculating dims: ", useImageScale, scaleMode);
        let targetCanvasWidth, targetCanvasHeight;
        if (useImageScale) {
            targetCanvasWidth = img.width;
            targetCanvasHeight = img.height;
            console.log("Using image dimensions", targetCanvasWidth, targetCanvasHeight);
        } else {
            targetCanvasWidth = canvasWidth;
            targetCanvasHeight = canvasHeight;
            console.log("Using default canvas dimensions", targetCanvasWidth, targetCanvasHeight);
        }
        let imageWidth = img.width;
        let imageHeight = img.height;

        // Step 3: Calculate the new position and scale of the contents
        let scaleX = 1;
        let scaleY = 1;
        switch (scaleMode) {
            case "scale":
                // Scale the image to fit the canvas
                scaleX = Math.min(targetCanvasWidth / imageWidth, targetCanvasHeight / imageHeight);
                scaleY = scaleX;
                break;
            case "stretch":
                scaleX = targetCanvasWidth / imageWidth;
                scaleY = targetCanvasHeight / imageHeight;
                break;
            case "contain":
                scaleX = scaleY = 1;
                break;
            default:
                console.log("Invalid scale mode: ", scaleMode);
        }
        if (useImageScale) {
            scaleX = scaleY = 1;
        }
        return [scaleX, scaleY];
    }


    updateCanvasWidth(width) {
        this.canvasWidth = width;
        this.updateCanvases(this.imageSource, false);

    }

    updateCanvasHeight(height) {
        this.canvasHeight = height;
        this.updateCanvases(this.imageSource, false);
    }

    updateScaleMode(scaleMode) {
        this.scaleMode = scaleMode;
        this.updateCanvases(this.imageSource, false);
    }

    updateUseImageScale(useImageScale) {
        this.useImageScale = useImageScale;
        this.updateCanvases(this.imageSource, false);
    }

    updateImageOrigin(imageOrigin) {
        console.log("Updating image origin: ", imageOrigin);
        this.imageOrigin = imageOrigin;
        this.updateCanvases(this.imageSource, false);
    }

    addButton(iconName, action) {
        const button = document.createElement('button');
        const icon = document.createElement('i');
        icon.classList.add('bx', `bx-${iconName}`);
        button.appendChild(icon);
        button.classList.add('btn', 'btn-secondary', 'btn-sm');
        button.addEventListener('click', action);

        if (iconName === 'share-alt') {
            button.setAttribute('type', 'button');
            button.setAttribute('id', `${this.containerId}dropdown`);
            button.setAttribute('data-toggle', 'dropdown');
            button.setAttribute('aria-haspopup', 'true');
            button.setAttribute('aria-expanded', 'false');

            const dropdown = document.createElement('div');
            dropdown.classList.add('dropdown-menu');
            dropdown.id = this.containerId + "_dropdownMenu";
            this.buttonGroup.appendChild(button);
            this.buttonGroup.appendChild(dropdown);
        } else {
            this.buttonGroup.appendChild(button);
        }
    }

    importImage(image) {
        this.updateCanvases(image, false);
    }

    showShareMenu(event) {
        event.preventDefault();
        const dropdownMenu = document.getElementById(this.containerId + "_dropdownMenu");
        dropdownMenu.innerHTML = '';

        const hasCanvasContent = this.drawCanvas && this.drawCanvas.getContext('2d').getImageData(0, 0, this.drawCanvas.width, this.drawCanvas.height).data.some(value => value !== 0);
        const hasDropCanvasContent = this.dropCanvas && this.dropCanvas.getContext('2d').getImageData(0, 0, this.dropCanvas.width, this.dropCanvas.height).data.some(value => value !== 0);
        if (!hasCanvasContent && !hasDropCanvasContent) return;
        const receiversList = [imageReceivers, maskReceivers];
        const conditions = [hasDropCanvasContent, hasCanvasContent];
        const canvasDataUrls = [this.dropCanvas.toDataURL(), this.drawCanvas.toDataURL()];

        receiversList.forEach((receivers, index) => {
            for (let key in receivers) {
                if (key.indexOf(this.containerId) !== -1 || !conditions[index]) continue;
                const dropdownItem = document.createElement('a');
                dropdownItem.classList.add('dropdown-item');
                dropdownItem.href = '#';
                dropdownItem.textContent = key + (index === 1 ? " (mask)" : "");

                dropdownItem.addEventListener('click', (event) => {
                    event.preventDefault();
                    dropdownMenu.classList.toggle('show');
                    receivers[key](canvasDataUrls[index]);
                });

                dropdownMenu.appendChild(dropdownItem);
            }
        });


        dropdownMenu.classList.toggle('show');
        console.log("Possible targets: ", imageReceivers);
    }


    getDropped(pop = false) {
        // get the number of "drop" items in this.undoStack
        let dropCount = 0;
        for (let i = 0; i < this.undoStack.length; i++) {
            if (this.undoStack[i].type === "drop") {
                dropCount++;
            }
        }
        if (dropCount > 0) {
            let dataUrl = this.dropCanvas.toDataURL('image/png');
            if (pop) {
                let win = window.open("", "_blank");
                win.document.write("<img src='" + dataUrl + "'/>");
            } else {
                return dataUrl;
            }
        } else {
            console.log("No image to get", dropCount, this.undoStack);
            return null;
        }
    }


    getMask() {
        let drawCount = 0;
        for (let i = 0; i < this.undoStack.length; i++) {
            if (this.undoStack[i].type === "draw") {
                drawCount++;
            }
        }
        if (drawCount > 1) {
            return this.drawCanvas.toDataURL('image/png');
        } else {
            console.log("No mask to get", drawCount);
            return null;
        }
    }

    setDropped(dropped) {
        this.updateCanvases(dropped, false);
    }

    setMask(mask) {
        this.updateCanvases(mask, true);
    }

    // Set the brush size
    setBrushSize(size) {
        this.brushSize = size;
        this.updateCursorStyle();
    }

    // Set the brush color
    setBrushColor(color) {
        this.brushColor = color;
        this.updateCursorStyle();
    }


    // Clear the canvas
    clear() {
        console.log("Clearing pushed...");
        this.undoStack = [];
        let drawCtx = this.drawCanvas.getContext('2d');
        let dropCtx = this.dropCanvas.getContext('2d');
        drawCtx.clearRect(0, 0, this.drawCanvas.width, this.drawCanvas.height);
        dropCtx.clearRect(0, 0, this.dropCanvas.width, this.dropCanvas.height);
        let state = drawCtx.getImageData(0, 0, this.drawCanvas.width, this.drawCanvas.height);
        console.log("Pushing due to clear?");
        this.undoStack.push({type: 'draw', imageData: state});
        const colorPickerDialog = document.querySelector('.color-picker-dialog');
        if (colorPickerDialog) document.body.removeChild(colorPickerDialog);
        this.brushColor = "black";
        this.brushSize = 10;
        this.redrawCanvases(this.lastWidth, this.lastHeight);
    }

    // Show a dialog to set the brush size
    showBrushSizeDialog(event) {
        // check if the brush size dialog is already open
        const brushSizeDialog = document.querySelector('.brush-size-dialog');
        if (brushSizeDialog) {
            // if it is open, remove it from the document and return
            document.body.removeChild(brushSizeDialog);
            return;
        }

        const newBrushSizeDialog = document.createElement('div');
        newBrushSizeDialog.classList.add('brush-size-dialog');

        const slider = document.createElement('input');
        const scaleFactor = this.drawCanvas.clientHeight / this.drawCanvas.height;

        slider.type = 'range';
        slider.min = 1;
        slider.max = 60 / scaleFactor;
        slider.value = this.brushSize;

        slider.addEventListener('input', () => {
            this.setBrushSize(parseInt(slider.value));
        });
        newBrushSizeDialog.appendChild(slider);
        const buttonRect = event.target.getBoundingClientRect();
        newBrushSizeDialog.style.position = 'absolute';
        newBrushSizeDialog.style.left = `${buttonRect.left}px`;
        newBrushSizeDialog.style.top = `${buttonRect.bottom}px`;

        document.body.appendChild(newBrushSizeDialog);

        const onDocumentClick = (n_event) => {
            if (!newBrushSizeDialog.contains(n_event.target) && n_event !== event) {
                document.removeEventListener('click', onDocumentClick);
                document.body.removeChild(newBrushSizeDialog);
            }
        };
        document.addEventListener('click', onDocumentClick);
    }

    importMask(image) {
        this.updateCanvases(image, true);
    }

    showColorPicker(event) {
        // check if the color picker dialog is already open
        const colorPickerDialog = document.querySelector('.color-picker-dialog');
        if (colorPickerDialog) {
            // if it is open, remove it from the document and return
            document.body.removeChild(colorPickerDialog);
            return;
        }

        // create the color picker dialog element
        const newColorPickerDialog = document.createElement('div');
        newColorPickerDialog.classList.add('color-picker-dialog');

        // create the color picker element
        const colorPicker = document.createElement('input');
        colorPicker.type = 'color';
        colorPicker.value = this.brushColor;

        // update brush color when color picker value changes
        colorPicker.addEventListener('input', () => {
            this.setBrushColor(colorPicker.value);
        });

        // add color picker to color picker dialog
        newColorPickerDialog.appendChild(colorPicker);

        // position the color picker dialog at the click event
        newColorPickerDialog.style.position = 'absolute';
        newColorPickerDialog.style.left = `${event.pageX}px`;
        newColorPickerDialog.style.top = `${event.pageY}px`;

        // add the color picker dialog to the document body
        document.body.appendChild(newColorPickerDialog);

        // add a listener to the document for any click that is not on the newColorPickerDialog element
        const onDocumentClick = (n_event) => {
            if (!newColorPickerDialog.contains(n_event.target) && n_event !== event) {
                document.removeEventListener('click', onDocumentClick);
                if (newColorPickerDialog) {
                    document.body.removeChild(newColorPickerDialog);
                }
            }
        };
        document.addEventListener('click', onDocumentClick);
    }

    getCursorPosition(event) {
        let data = event;
        // Determine if the event is from mouse or touch and get the appropriate position
        if (event.changedTouches) {
            data = event.changedTouches[0];
        } else if (event.touches) {
            data = event.touches[0];
        }
        const rect = this.displayCanvas.getBoundingClientRect();
        const scaleX = this.displayCanvas.width / rect.width;
        const scaleY = this.displayCanvas.height / rect.height;
        const x = (data.clientX - rect.left) * scaleX;
        const y = (data.clientY - rect.top) * scaleY;
        return [x, y];
    }


    updateCursorStyle() {
        const brushSize = this.brushSize;
        const brushColor = this.brushColor;

        // Calculate the scale factor
        const scaleFactor = this.displayCanvas.clientHeight / this.displayCanvas.height;
        this.scaleFactor = scaleFactor;
        const scaledBrushSize = brushSize * scaleFactor;

        const circleSize = scaledBrushSize;
        const viewBoxSize = scaledBrushSize * 2;
        const hotspot = circleSize;

        const svgString = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 ${viewBoxSize} ${viewBoxSize}' width='${viewBoxSize}' height='${viewBoxSize}'><circle cx='${circleSize}' cy='${circleSize}' r='${circleSize / 2}' fill='${brushColor}'/></svg>`;
        this.displayCanvas.style.cursor = `url("data:image/svg+xml,${encodeURIComponent(svgString)}") ${hotspot} ${hotspot}, auto`;
    }


    undo() {
        this.undoStack.pop();
        if (this.undoStack.length === 0) return;
        const lastAction = this.undoStack[this.undoStack.length - 1];
        if (lastAction.type === 'draw') {
            console.log("Undoing draw action");
            const ctx = this.drawCanvas.getContext('2d');
            ctx.putImageData(lastAction.imageData, 0, 0);
        } else if (lastAction.type === 'drop') {
            console.log("Undoing drop action");
            const dropCtx = this.dropCanvas.getContext('2d');
            dropCtx.putImageData(lastAction.imageData, 0, 0);
        }
        this.redrawCanvases(this.lastWidth, this.lastHeight);
    }


    handleDragOver(event) {
        event.preventDefault();
    }

    handleDrop(event) {
        event.preventDefault();

        const file = event.dataTransfer.files[0];
        const reader = new FileReader();

        reader.addEventListener('load', () => {
            this.updateCanvases(reader.result, false);
            this.imageSource = reader.result;
        });

        reader.readAsDataURL(file);
    }

}

$.fn.imageEditor = function () {
    this.each(function () {
        const $this = $(this);
        let edit = $this.data("ImageEditor");

        if (!edit) {
            const targetElement = this;
            const targetDataset = targetElement.dataset;
            edit = new ImageEditor(targetElement);
            $this.data("ImageEditor", edit);
        }
    });

    return this.data("ImageEditor");
};

function calculateOriginOffset(origin, canvasWidth, canvasHeight, imgWidth, imgHeight) {
    let offsetX = 0, offsetY = 0;
    console.log("Origin: ", origin, imgWidth, imgHeight);
    origin = origin.indexOf("-") !== -1 ? origin.split("-") : [origin];
    console.log("Origin: ", origin);
    if (origin.includes('right')) offsetX = canvasWidth - imgWidth;
    else if (origin.includes('center')) offsetX = (canvasWidth - imgWidth) / 2;

    if (origin.includes('bottom')) offsetY = canvasHeight - imgHeight;
    else if (origin.includes('center') && !origin.includes('left') && !origin.includes('right')) offsetY = (canvasHeight - imgHeight) / 2;
    console.log("Origin: ", origin, "Offset: ", offsetX, offsetY);
    return {offsetX, offsetY};
}
