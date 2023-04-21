class ImageEditor {
    constructor(containerId, width, height) {
        // Create the canvas and add it to the container
        this.canvasWrapper = document.createElement('div');
        this.canvasWrapper.classList.add("canvasWrapper");
        this.dropCanvas = document.createElement('canvas');
        this.dropCanvas.classList.add("editorCanvas");
        this.dropCanvas.style.cursor = 'none';
        this.canvas = document.createElement('canvas');
        this.canvas.classList.add("editorCanvas", "editCanvas");
        this.canvas.style.cursor = 'crosshair';
        this.container = document.getElementById(containerId);
        this.container.appendChild(this.canvasWrapper);
        this.canvasWrapper.appendChild(this.canvas);
        this.canvasWrapper.appendChild(this.dropCanvas);
        this.buttonGroup = document.createElement("div");
        this.buttonGroup.classList.add("btn-group", "editorButtons");
        this.container.appendChild(this.buttonGroup);
        this.imageSource = null;

        // Store the original resolution of the image
        this.originalResolution = {
            width: width,
            height: height
        };

        // Initialize variables
        this.context = this.canvas.getContext('2d');
        this.isDrawing = false;
        this.lastX = 0;
        this.lastY = 0;
        this.undoStack = [];
        const ctx = this.canvas.getContext('2d');
        const state = ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        // push 'draw' action to stack
        this.undoStack.push({type: 'draw', imageData: state});
        this.brushSize = 10;
        this.brushColor = 'black';
        this.updateCursorStyle();
        this.scale = 1;
        this.minScale = 0.1;
        this.maxScale = 10;
        this.translateX = 0;
        this.translateY = 0;
        this.scaleCanvas(width, height);
        // Add event listeners for canvas interaction
        this.canvas.addEventListener('touchstart', this.handleTouchStart.bind(this));
        this.canvas.addEventListener('touchmove', this.handleTouchMove.bind(this));
        this.canvas.addEventListener('touchend', this.handleTouchEnd.bind(this));
        this.canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.handleMouseUp.bind(this));
        this.canvas.addEventListener('mouseleave', this.handleMouseLeave.bind(this));
        this.canvas.addEventListener('mouseenter', this.handleMouseEnter.bind(this));
        this.canvas.addEventListener('dragover', this.handleDragOver.bind(this));
        this.canvas.addEventListener('drop', this.handleDrop.bind(this));
        //this.canvas.addEventListener('contextmenu', this.handleContextMenu.bind(this));
        //this.canvas.addEventListener('wheel', this.handleWheel.bind(this));


        // Add buttons for clear, undo, brush size, and color
        this.addButton('x', this.clear.bind(this));
        this.addButton('undo', this.undo.bind(this));
        this.addButton('brush', this.showBrushSizeDialog.bind(this));
        this.addButton('palette', this.showColorPicker.bind(this));
    }

    getDropped() {
        for (let i = 1; i < this.undoStack.length; i++) {
            if (this.undoStack[i].type === 'drop') {
                return this.dropCanvas.toDataURL('image/png');
            }
        }
        return "";
    }

    getMask() {
        for (let i = 1; i < this.undoStack.length; i++) {
            if (this.undoStack[i].type === 'draw') {
                return this.canvas.toDataURL('image/png');
            }
        }
        return "";
    }


    scaleCanvas(width, height) {
        // Get the current image data from the canvases
        const imageData = {
            main: this.canvas.getContext('2d').getImageData(0, 0, this.canvas.width, this.canvas.height)
        };
        this.undoStack = [];
        // Resize the canvas elements to the new dimensions
        this.dropCanvas.width = width;
        this.dropCanvas.height = height;
        let resizedState = this.getResizedImageData(imageData.main, this.canvas.width, this.canvas.height);
        this.undoStack.push(resizedState);
        if (null !== this.imageSource) {
            const src_image = new Image();
            src_image.src = this.imageSource;
            const scale = Math.min(
                this.dropCanvas.width / src_image.width,
                this.dropCanvas.height / src_image.height
            );
            const width = src_image.width * scale;
            const height = src_image.height * scale;
            const x = (this.dropCanvas.width - width) / 2;
            const y = (this.dropCanvas.height - height) / 2;
            const ctx = this.dropCanvas.getContext('2d');
            ctx.clearRect(0, 0, this.dropCanvas.width, this.dropCanvas.height);
            const state = ctx.getImageData(0, 0, this.dropCanvas.width, this.dropCanvas.height);
            this.undoStack.push(state);
            ctx.drawImage(src_image, x, y, width, height);
        }
        this.canvas.width = width;
        this.canvas.height = height;

        // Redraw the image data onto the resized canvases
        this.canvas.getContext('2d').putImageData(resizedState, 0, 0);
    }

    getResizedImageData(imageData, width, height) {
        // Create a new canvas element to resize the image data
        const canvas = document.createElement('canvas');
        canvas.width = imageData.width;
        canvas.height = imageData.height;

        // Draw the image data onto the canvas
        canvas.getContext('2d').putImageData(imageData, 0, 0);

        // Create a new image object to hold the resized image data
        const resizedImage = new ImageData(width, height);

        // Draw the canvas onto the resized image object
        const sourceX = (canvas.width - width) / 2;
        const sourceY = (canvas.height - height) / 2;
        const sourceWidth = width;
        const sourceHeight = height;
        const destX = 0;
        const destY = 0;
        const destWidth = width;
        const destHeight = height;
        resizedImage.data.set(canvas.getContext('2d').getImageData(sourceX, sourceY, sourceWidth, sourceHeight).data, 0);

        // Return the resized image data
        return resizedImage;
    }

    // Add a button to the top-right corner of the container
    addButton(iconName, action) {
        const button = document.createElement('button');
        const icon = document.createElement('i');
        icon.classList.add('bx', `bx-${iconName}`);
        button.appendChild(icon);
        //button.style.float = 'right';
        //button.style.marginRight = '10px';
        button.classList.add('btn', 'btn-secondary', 'btn-sm');
        button.addEventListener('click', action);
        this.buttonGroup.appendChild(button);
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

    updateCursorStyle() {
        const brushSize = this.brushSize;
        const brushColor = this.brushColor;
        const circleSize = brushSize;
        const viewBoxSize = brushSize * 2;
        const hotspot = circleSize;
        const svgString = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 ${viewBoxSize} ${viewBoxSize}' width='${viewBoxSize}' height='${viewBoxSize}'><circle cx='${circleSize}' cy='${circleSize}' r='${circleSize / 2}' fill='${brushColor}'/></svg>`;
        this.canvas.style.cursor = `url("data:image/svg+xml,${encodeURIComponent(svgString)}") ${hotspot} ${hotspot}, auto`;
    }


    // Clear the canvas
    clear() {
        this.undoStack = [];
        let ctx = this.canvas.getContext('2d');
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        let state = ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        ctx = this.dropCanvas.getContext('2d');
        ctx.clearRect(0, 0, this.dropCanvas.width, this.dropCanvas.height);

        // push 'draw' action to stack
        this.undoStack.push({type: 'draw', imageData: state});
        const colorPickerDialog = document.querySelector('.color-picker-dialog');
        if (colorPickerDialog) {
            // if it is open, remove it from the document and return
            document.body.removeChild(colorPickerDialog);
        }
        this.brushColor = "black";
        this.brushSize = 10;
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

        // create the brush size dialog element
        const newBrushSizeDialog = document.createElement('div');
        newBrushSizeDialog.classList.add('brush-size-dialog');

        // create the slider element
        const slider = document.createElement('input');
        slider.type = 'range';
        slider.min = 1;
        slider.max = 60;
        slider.value = this.brushSize;

        // update brush size when slider value changes
        slider.addEventListener('input', () => {
            this.setBrushSize(parseInt(slider.value));
        });

        // add slider to brush size dialog
        newBrushSizeDialog.appendChild(slider);

        // position the brush size dialog below the button that was clicked
        const buttonRect = event.target.getBoundingClientRect();
        newBrushSizeDialog.style.position = 'absolute';
        newBrushSizeDialog.style.left = `${buttonRect.left}px`;
        newBrushSizeDialog.style.top = `${buttonRect.bottom}px`;

        // add the brush size dialog to the document body
        document.body.appendChild(newBrushSizeDialog);

        // add a listener to the document for any click that is not on the newBrushSizeDialog element
        const onDocumentClick = (n_event) => {
            if (!newBrushSizeDialog.contains(n_event.target) && n_event !== event) {
                console.log("Hiding brush dialog.", n_event, event);
                document.removeEventListener('click', onDocumentClick);
                document.body.removeChild(newBrushSizeDialog);
            }
        };
        document.addEventListener('click', onDocumentClick);
    }


    // Show a color picker to set the brush color
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
                console.log("Closing color picker.");
                document.removeEventListener('click', onDocumentClick);
                if (newColorPickerDialog) {
                    document.body.removeChild(newColorPickerDialog);
                }
            }
        };
        document.addEventListener('click', onDocumentClick);
    }


    // Draw a line from the last position to the current position


    getCursorPosition(event) {
        const rect = this.canvas.getBoundingClientRect();
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;
        const x = (event.clientX - rect.left) * scaleX;
        const y = (event.clientY - rect.top) * scaleY;
        return [x, y];
    }

    handleMouseDown(event) {
        if (event.button !== 0) return;
        this.isDrawing = true;
        const [x, y] = this.getCursorPosition(event);
        this.lastX = x;
        this.lastY = y;

        const ctx = this.canvas.getContext('2d');
        ctx.beginPath();
        ctx.moveTo(x, y);


    }

    handleMouseMove(event) {
        if (!this.isDrawing) return;
        const [x, y] = this.getCursorPosition(event);
        this.drawLine(x, y);
        this.lastX = x;
        this.lastY = y;
    }

    handleMouseUp() {
        if (!this.isDrawing) return;
        this.isDrawing = false;
        const ctx = this.canvas.getContext('2d');
        const state = ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);

        // push 'draw' action to stack
        this.undoStack.push({type: 'draw', imageData: state});
    }

    handleTouchStart(event) {
        this.isDrawing = true;
        const [x, y] = this.getCursorPosition(event.touches[0]);
        this.lastX = x;
        this.lastY = y;

        const ctx = this.canvas.getContext('2d');
        ctx.beginPath();
        ctx.moveTo(x, y);
    }

    handleTouchMove(event) {
        if (!this.isDrawing) return;
        const [x, y] = this.getCursorPosition(event.touches[0]);
        this.drawLine(x, y);
        this.lastX = x;
        this.lastY = y;
    }

    handleTouchEnd() {
        if (!this.isDrawing) return;
        this.isDrawing = false;
        const ctx = this.canvas.getContext('2d');
        const state = ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);

        // push 'draw' action to stack
        this.undoStack.push({type: 'draw', imageData: state});
    }

    drawLine(x, y) {
        const ctx = this.canvas.getContext('2d');
        ctx.lineWidth = this.brushSize;
        ctx.strokeStyle = this.brushColor;
        ctx.lineTo(x, y);
        ctx.stroke();
    }

    undo() {
        if (this.undoStack.length === 0) {
            console.log("Nothing to undo!");
            return;
        }

        const lastAction = this.undoStack.pop();

        if (lastAction.type === 'draw') {
            const ctx = this.canvas.getContext('2d');
            ctx.putImageData(lastAction.imageData, 0, 0);
        } else if (lastAction.type === 'drop') {
            const dropCtx = this.dropCanvas.getContext('2d');
            dropCtx.putImageData(lastAction.imageData, 0, 0);
        }
    }


    handleContextMenu(event) {
        event.preventDefault();
        this.panStartX = event.clientX;
        this.panStartY = event.clientY;
        window.addEventListener('mousemove', this.handleContextMenuMouseMove);
        window.addEventListener('mouseup', this.handleContextMenuMouseUp);
    }

    // handleContextMenuMouseMove = (event) => {
    //     const dx = event.clientX - this.panStartX;
    //     const dy = event.clientY - this.panStartY;
    //     this.panStartX = event.clientX;
    //     this.panStartY = event.clientY;
    //     this.translateX += dx / this.scale;
    //     this.translateY += dy / this.scale;
    //     this.updateCanvas();
    // }

    handleWheel = (event) => {
        const delta = event.wheelDelta ? event.wheelDelta / 40 : event.deltaY ? event.deltaY : 0;
        if (delta) {
            const x = event.offsetX;
            const y = event.offsetY;
            const zoom = Math.exp(delta * 0.02);
            this.scale *= zoom;
            this.translateX *= zoom;
            this.translateY *= zoom;
            this.translateX -= x * (zoom - 1);
            this.translateY -= y * (zoom - 1);
            this.updateCanvas();
        }
        event.preventDefault();
    }

    handleMouseLeave(event) {
        this.isDrawing = false;
    }

    handleMouseEnter(event) {
        // If the mouse is clicked, set this.isDrawing to true
        if (event.buttons === 1) {
            this.isDrawing = true;
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
            const image = new Image();
            image.addEventListener('load', () => {
                // Store the original resolution
                this.originalResolution = {
                    width: image.width,
                    height: image.height
                };
                const scale = Math.min(
                    this.dropCanvas.width / image.width,
                    this.dropCanvas.height / image.height
                );
                const width = image.width * scale;
                const height = image.height * scale;
                const x = (this.dropCanvas.width - width) / 2;
                const y = (this.dropCanvas.height - height) / 2;
                const ctx = this.dropCanvas.getContext('2d');
                ctx.clearRect(0, 0, this.dropCanvas.width, this.dropCanvas.height);
                const state = ctx.getImageData(0, 0, this.dropCanvas.width, this.dropCanvas.height);
                ctx.drawImage(image, x, y, width, height);
                this.undoStack.push({type: 'drop', imageData: state});
            });
            image.src = reader.result;
            this.imageSource = image.src;
        });

        reader.readAsDataURL(file);
    }


    handleContextMenuMouseUp = (event) => {
        document.removeEventListener('mousemove', this.handleContextMenuMouseMove);
        document.removeEventListener('mouseup', this.handleContextMenuMouseUp);
    }
}