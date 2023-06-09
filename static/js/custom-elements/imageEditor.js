class ImageEditor {
    constructor(containerId, width, height, points = false) {
        // Create the canvas and add it to the container
        this.canvasWrapper = document.createElement('div');
        this.canvasWrapper.classList.add("canvasWrapper");
        this.canvasWrapper.style.width = width;
        this.canvasWrapper.style.height = height;
        this.dropCanvas = document.createElement('canvas');
        this.dropCanvas.classList.add("editorCanvas");
        this.dropCanvas.style.cursor = 'none';
        this.canvas = document.createElement('canvas');
        this.canvas.classList.add("editorCanvas", "editCanvas");
        this.canvas.style.cursor = 'none';
        this.pointCanvas = document.createElement('canvas');
        this.pointCanvas.classList.add("editorCanvas", "pointCanvas");
        this.pointCanvas.style.cursor = 'none';
        this.container = document.getElementById(containerId);
        this.container.appendChild(this.canvasWrapper);
        this.canvasWrapper.appendChild(this.canvas);
        this.canvasWrapper.appendChild(this.pointCanvas);
        this.canvasWrapper.appendChild(this.dropCanvas);
        this.buttonGroup = document.createElement("div");
        this.buttonGroup.classList.add("btn-group", "editorButtons");
        this.container.appendChild(this.buttonGroup);
        this.imageSource = null;
        this.points = [];
        this.pointRadius = 5;
        this.pointMode = points;

        // Initialize variables
        this.context = this.canvas.getContext('2d');
        this.isDrawing = false;
        this.undoStack = [];
        const ctx = this.canvas.getContext('2d');
        const state = ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        // push 'draw' action to stack
        this.undoStack.push({type: 'draw', imageData: state});
        this.brushSize = 10;
        this.brushColor = 'black';
        this.updateCursorStyle();
        this.scale = 1;
        //this.scaleCanvas(width, height);
        // Add event listeners for canvas interaction
        this.canvas.addEventListener('touchstart', this.handleInputStart.bind(this));
        this.canvas.addEventListener('mousedown', this.handleInputStart.bind(this));
        this.canvas.addEventListener('mouseenter', this.handleInputStart.bind(this));

        this.canvas.addEventListener('touchmove', this.handleInputMove.bind(this));
        this.canvas.addEventListener('mousemove', this.handleInputMove.bind(this));

        // These all do the same thing
        this.canvas.addEventListener('touchend', this.handleInputEnd.bind(this));
        this.canvas.addEventListener('mouseleave', this.handleInputEnd.bind(this));
        this.canvas.addEventListener('mouseup', this.handleInputEnd.bind(this));

        this.canvas.addEventListener('dblclick', this.handleMouseDoubleClick.bind(this));
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
                let img = this.dropCanvas.toDataURL('image/png');
                let imgObj = new Image();
                imgObj.src = img;
                imgObj.onload = function () {
                    console.log("Original Image dimensions: " + imgObj.width + "x" + imgObj.height);

                    if (imgObj.width > 2048 || imgObj.height > 2048) {
                        let scaleFactor = Math.max(imgObj.width / 2048, imgObj.height / 2048);
                        let newWidth = Math.round(imgObj.width / scaleFactor);
                        let newHeight = Math.round(imgObj.height / scaleFactor);
                        console.log("Resized Image dimensions: " + newWidth + "x" + newHeight);
                    }
                };
                return img;
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

        // Calculate the scale factor
        const scaleFactor = this.canvas.clientHeight / this.canvas.height;
        const scaledBrushSize = brushSize * scaleFactor;
        console.log("Scale factor is " + scaleFactor);
        this.pointRadius = 5 / scaleFactor;

        const circleSize = scaledBrushSize;
        const viewBoxSize = scaledBrushSize * 2;
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
        const rect = this.canvas.getBoundingClientRect();
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;
        const x = (data.clientX - rect.left) * scaleX;
        const y = (data.clientY - rect.top) * scaleY;
        return [x, y];
    }

    handleMouseDoubleClick(event) {
        if (!this.pointMode) return;
        const [x, y] = this.getCursorPosition(event);
        console.log("double click", x, y);
        this.drawPoint(x, y, 'red');
        this.points.push({x, y, connectedPoint: null}); // store point in the points array
    }

    handleInputStart(event) {
        const isNotSingleTouchOrLeftButtonNotPressed = !(event.type.startsWith('touch') && event.touches.length === 1) && !(event.type === 'mousemove') && !(event.type === 'mousedown' && event.button === 0);
        if (isNotSingleTouchOrLeftButtonNotPressed) return;

        console.log("Input start", event);
        event.preventDefault();

        let x, y;
        [x, y] = this.getCursorPosition(event);
        // Determine if the event is from mouse or touch and get the appropriate position
        console.log("Input start", x, y);
        // check if input is on an existing point
        const point = this.points.find(p => Math.hypot(p.x - x, p.y - y) < this.pointRadius);
        if (this.pointMode && point) {
            this.selectedPoint = point;
            return;
        }
        this.isDrawing = true;
        this.context.beginPath();
        this.context.moveTo(x, y);
    }


    handleInputMove(event) {
        const isNotSingleTouchOrLeftButtonNotPressed = !(event.type.startsWith('touch') && event.touches.length === 1) && !(event.type === 'mousemove') && !(event.type === 'mousedown' && event.button === 0);
        if (isNotSingleTouchOrLeftButtonNotPressed) return;

        event.preventDefault();
        let x, y;
        [x, y] = this.getCursorPosition(event);
        if (this.selectedPoint !== null && this.pointMode) {
            console.log("Pointing: ", x, y);
            this.updatePoint(x, y);
            return;
        }

        if (this.isDrawing) {
            console.log("Drawing: ", x, y);
            this.drawLine(x, y);
        }
    }

    handleInputEnd(event) {
        let x, y;
        [x, y] = this.getCursorPosition(event);

        console.log("Input end: ", x, y);
        if (this.pointMode && this.selectedPoint !== null) {
            this.updatePoint(x, y);
            this.selectedPoint = null;
            return;
        }

        if (!this.isDrawing) return;
        this.isDrawing = false;
        const ctx = this.canvas.getContext('2d');
        const state = ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        this.undoStack.push({type: 'draw', imageData: state});
    }

    updatePoint(x, y) {
        const pointIndex = this.points.findIndex(p => p === this.selectedPoint);
        if (pointIndex !== -1) {
            this.points[pointIndex].connectedPoint = {x, y};
            this.selectedPoint = this.points[pointIndex];
            this.redrawAllPoints();
        }
    }

    redrawAllPoints() {
        this.pointCanvas.getContext('2d').clearRect(0, 0, this.pointCanvas.width, this.pointCanvas.height);
        for (let point of this.points) {
            this.drawPoint(point.x, point.y, 'red');
            if (point.isHighlighted) {
                this.drawPoint(point.x, point.y, 'blue');
            }
            if (point.connectedPoint) {
                this.drawPointLine(point.x, point.y, point.connectedPoint.x, point.connectedPoint.y);
                this.drawPoint(point.connectedPoint.x, point.connectedPoint.y, 'green');
            }
        }
    }

    drawPointLine(x1, y1, x2, y2, color = "white") {
        let pointContext = this.pointCanvas.getContext('2d');
        pointContext.strokeStyle = color;
        pointContext.lineWidth = 4;
        pointContext.beginPath();
        pointContext.moveTo(x1, y1);
        pointContext.lineTo(x2, y2);
        pointContext.stroke();
    }

    drawPoint(x, y, color) {
        let pointContext = this.pointCanvas.getContext('2d');
        pointContext.beginPath();
        pointContext.arc(x, y, this.pointRadius, 0, 2 * Math.PI, false);
        pointContext.fillStyle = color;
        pointContext.fill();
        pointContext.closePath();
    }

    drawLine(x, y) {
        const ctx = this.canvas.getContext('2d');
        //const scaleFactor = this.canvas.clientHeight / this.canvas.height;
        ctx.lineWidth = this.brushSize;
        ctx.strokeStyle = this.brushColor;
        ctx.lineTo(x, y);
        ctx.stroke();
    }

    undo() {
        if (this.undoStack.length === 0) return;

        const lastAction = this.undoStack.pop();

        if (lastAction.type === 'draw') {
            const ctx = this.canvas.getContext('2d');
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
            const image = new Image();
            image.addEventListener('load', () => {
                // Store the original resolution
                this.dropCanvas.width = image.width;
                this.dropCanvas.height = image.height;
                // Preserve the current contents of this.canvas
                const canvasCtx = this.canvas.getContext('2d');
                const currentContent = canvasCtx.getImageData(0, 0, this.canvas.width, this.canvas.height);

                // Store the old dimensions
                const oldWidth = this.canvas.width;
                const oldHeight = this.canvas.height;

                // Resize this.canvas
                this.canvas.width = image.width;
                this.canvas.height = image.height;

                this.pointCanvas.width = image.width;
                this.pointCanvas.height = image.height;
                // Clear the pointCanvas
                this.pointCanvas.getContext('2d').clearRect(0, 0, this.pointCanvas.width, this.pointCanvas.height);
                // Calculate offsets to center the image data on the new canvas
                const xOffset = (this.canvas.width - oldWidth) / 2;
                const yOffset = (this.canvas.height - oldHeight) / 2;

                // Restore its contents at the calculated offsets
                canvasCtx.putImageData(currentContent, xOffset, yOffset);
                // Set the cursor to the new size
                this.updateCursorStyle();
                const ctx = this.dropCanvas.getContext('2d');
                ctx.clearRect(0, 0, this.dropCanvas.width, this.dropCanvas.height);
                const state = ctx.getImageData(0, 0, this.dropCanvas.width, this.dropCanvas.height);
                ctx.drawImage(image, 0, 0, this.dropCanvas.width, this.dropCanvas.height);
                this.undoStack.push({type: 'drop', imageData: state});
                console.log("Pushing dropped: ", this.canvas.width, this.canvas.height);
                this.undoStack.push({
                    type: 'draw',
                    imageData: canvasCtx.getImageData(0, 0, this.canvas.width, this.canvas.height)
                });

            });
            image.src = reader.result;
            this.imageSource = image.src;
        });

        reader.readAsDataURL(file);
    }
}