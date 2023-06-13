class ImageEditor {
    constructor(container, width, height) {
        // If container is a string, assume it is an id
        let containerId = container;
        if (typeof container === "string") {
            this.container = document.getElementById(container);
        } else {
            this.container = container;
            containerId = container.id;
        }
        this.container.classList.add("image_editor");
        this.scaleFactor = 0;
        this.containerId = containerId;
        this.wrapper = document.createElement("div");
        this.container.appendChild(this.wrapper);
        this.canvasWrapper = document.createElement('div');
        this.canvasWrapper.classList.add("canvasWrapper");
        this.canvasWrapper.style.width = width;
        this.canvasWrapper.style.height = height;
        this.dropCanvas = document.createElement('canvas');
        this.dropCanvas.classList.add("editorCanvas", "dropCanvas");
        this.dropCanvas.style.cursor = 'none';
        this.drawCanvas = document.createElement('canvas');
        this.drawCanvas.classList.add("editorCanvas", "drawCanvas");
        this.drawCanvas.style.cursor = 'none';
        this.canvasWrapper.appendChild(this.drawCanvas);
        this.canvasWrapper.appendChild(this.dropCanvas);
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
        this.undoStack.push({type: 'draw', imageData: state});
        this.brushSize = 10;
        this.brushColor = 'black';
        this.scale = 1;
        registerImageReceiver(containerId, this.importImage.bind(this));
        registerMaskReceiver(containerId, this.importMask.bind(this));
        this.drawCanvas.addEventListener('touchstart', this.handleInputStart.bind(this));
        this.drawCanvas.addEventListener('mousedown', this.handleInputStart.bind(this));
        this.drawCanvas.addEventListener('mouseenter', this.handleInputStart.bind(this));
        this.drawCanvas.addEventListener('touchmove', this.handleInputMove.bind(this));
        this.drawCanvas.addEventListener('mousemove', this.handleInputMove.bind(this));
        this.drawCanvas.addEventListener('touchend', this.handleInputEnd.bind(this));
        this.drawCanvas.addEventListener('mouseleave', this.handleInputEnd.bind(this));
        this.drawCanvas.addEventListener('mouseup', this.handleInputEnd.bind(this));
        this.drawCanvas.addEventListener('dragover', this.handleDragOver.bind(this));
        this.drawCanvas.addEventListener('drop', this.handleDrop.bind(this));

        this.addButton('share-alt', this.showShareMenu.bind(this));
        this.addButton('x', this.clear.bind(this));
        this.addButton('undo', this.undo.bind(this));
        this.addButton('brush', this.showBrushSizeDialog.bind(this));
        this.addButton('palette', this.showColorPicker.bind(this));
        this.updateCursorStyle();
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

    importImage(image) {
        this.updateCanvases(image, false);
    }

    updateCanvases(image, isMask) {
        if (isMask) {
            console.log("Updating mask");
        } else {
            console.log("Updating image");
        }
        const dropCtx = this.dropCanvas.getContext('2d');
        dropCtx.clearRect(0, 0, this.dropCanvas.width, this.dropCanvas.height);
        const drawCtx = this.drawCanvas.getContext('2d');
        drawCtx.clearRect(0, 0, this.drawCanvas.width, this.drawCanvas.height);
        const img = new Image();
        img.onload = () => {
            console.log("Loaded image");
            this.drawCanvas.width = img.width;
            this.drawCanvas.height = img.height;
            this.dropCanvas.width = img.width;
            this.dropCanvas.height = img.height;
            let state;
            if (isMask) {
                drawCtx.drawImage(img, 0, 0);
                state = drawCtx.getImageData(0, 0, this.dropCanvas.width, this.dropCanvas.height);
            } else {
                dropCtx.drawImage(img, 0, 0);
                state = dropCtx.getImageData(0, 0, this.dropCanvas.width, this.dropCanvas.height);
            }
            this.undoStack.push({type: isMask ? 'drop' : 'draw', imageData: state});
        };
        console.log("Setting source.");
        img.src = image;
        if (!isMask) this.imageSource = image.src;
        this.updateCursorStyle()
    }

    getDropped() {
        return this.dropCanvas.toDataURL('image/png');
    }

    getMask() {
        return this.drawCanvas.toDataURL('image/png');
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
        this.undoStack = [];
        let drawCtx = this.drawCanvas.getContext('2d');
        let dropCtx = this.dropCanvas.getContext('2d');
        drawCtx.clearRect(0, 0, this.drawCanvas.width, this.drawCanvas.height);
        dropCtx.clearRect(0, 0, this.dropCanvas.width, this.dropCanvas.height);
        let state = drawCtx.getImageData(0, 0, this.drawCanvas.width, this.drawCanvas.height);
        this.undoStack.push({type: 'draw', imageData: state});
        const colorPickerDialog = document.querySelector('.color-picker-dialog');
        if (colorPickerDialog) document.body.removeChild(colorPickerDialog);
        this.brushColor = "black";
        this.brushSize = 10;
        this.updateCursorStyle()
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
        const rect = this.drawCanvas.getBoundingClientRect();
        const scaleX = this.drawCanvas.width / rect.width;
        const scaleY = this.drawCanvas.height / rect.height;
        const x = (data.clientX - rect.left) * scaleX;
        const y = (data.clientY - rect.top) * scaleY;
        return [x, y];
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
            const ctx = this.drawCanvas.getContext('2d');
            ctx.moveTo(x, y);
        }
        this.isDrawing = true;
        this.drawLine(x, y); // Draw a circle when the mouse is pressed
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

    handleInputEnd(event) {
        let x, y;
        [x, y] = this.getCursorPosition(event);
        if (!this.isDrawing) return;
        this.isDrawing = false;
        const ctx = this.drawCanvas.getContext('2d');
        const state = ctx.getImageData(0, 0, this.drawCanvas.width, this.drawCanvas.height);
        this.undoStack.push({type: 'draw', imageData: state});
    }

    drawLine(x, y) {
        const ctx = this.drawCanvas.getContext('2d');
        ctx.lineJoin = 'round'; // Use round corners
        ctx.lineCap = 'round'; // Use round line ends
        ctx.lineWidth = this.brushSize;
        ctx.strokeStyle = this.brushColor;
        ctx.lineTo(x, y);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x, y);
    }

    updateCursorStyle() {
        const brushSize = this.brushSize;
        const brushColor = this.brushColor;

        // Calculate the scale factor
        const scaleFactor = this.drawCanvas.clientHeight / this.drawCanvas.height;
        this.scaleFactor = scaleFactor;
        const scaledBrushSize = brushSize * scaleFactor;
        console.log("Scale factor is " + scaleFactor, this.containerId);

        const circleSize = scaledBrushSize;
        const viewBoxSize = scaledBrushSize * 2;
        const hotspot = circleSize;

        const svgString = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 ${viewBoxSize} ${viewBoxSize}' width='${viewBoxSize}' height='${viewBoxSize}'><circle cx='${circleSize}' cy='${circleSize}' r='${circleSize / 2}' fill='${brushColor}'/></svg>`;
        this.drawCanvas.style.cursor = `url("data:image/svg+xml,${encodeURIComponent(svgString)}") ${hotspot} ${hotspot}, auto`;
    }


    undo() {
        if (this.undoStack.length === 0) return;
        const lastAction = this.undoStack.pop();
        if (lastAction.type === 'draw') {
            const ctx = this.drawCanvas.getContext('2d');
            ctx.putImageData(lastAction.imageData, 0, 0);
        } else if (lastAction.type === 'drop') {
            const dropCtx = this.dropCanvas.getContext('2d');
            dropCtx.putImageData(lastAction.imageData, 0, 0);
        }
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