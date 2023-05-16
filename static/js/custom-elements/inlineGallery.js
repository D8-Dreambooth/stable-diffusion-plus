class InlineGallery {
    constructor(parentSelector, options = {}) {
        this.parent = typeof parentSelector === "string" ? document.querySelector(parentSelector) : parentSelector;
        this.options = this._readOptions(options);
        this._initGallery();
        let selector = "";
        if (this.parent.hasAttribute("id")) {
            selector = "#" + this.parent.getAttribute("id");
        } else {
            selector = "." + this.parent.getAttribute("class").split(" ").join(".");
        }
        keyListener.register("ArrowLeft", selector, function () {
            this.selectPrevious();
        }.bind(this));
        keyListener.register("ArrowRight", selector, function () {
            this.selectNext();
        }.bind(this));
        registerSocketMethod("inlineGallery2", "status", this.socketUpdate.bind(this));
    }

    selectPrevious() {
        let leftArrow = this.primaryContainer.querySelector('.left-arrow');
        leftArrow.click();
    }

    selectNext() {
        let rightArrow = this.primaryContainer.querySelector('.right-arrow');
        rightArrow.click();
    }

    _readOptions(options) {
        const defaultOptions = {
            maxHeight: "300px",
            allowFullscreen: true,
            allowDownload: true,
            showThumbnails: true,
            showCaptions: true,
            loop: true,
            transitionTime: 400,
            data: [],
            id: Math.random().toString(36).substring(7),
        };

        const dataAttributes = Array.from(this.parent.attributes).reduce((acc, attr) => {
            if (attr.name.startsWith('data-')) {
                acc[attr.name.slice(5)] = attr.value;
            }
            return acc;
        }, {});

        return Object.assign({}, defaultOptions, dataAttributes, options);
    }

    _initGallery() {
        this._createContainers();
        this._populateGallery();
        this._addEventListeners();
    }

    _createContainers() {
        this.galleryContainer = document.createElement('div');
        this.galleryContainer.classList.add('gallery-container');
        this.parent.appendChild(this.galleryContainer);

        if (this.options.showCaptions) {
            this.captionContainer = document.createElement('div');
            this.captionContainer.classList.add('caption-container');
            this.parent.appendChild(this.captionContainer);
        }

        if (this.options.showThumbnails) {
            this.thumbnailContainer = document.createElement('div');
            this.thumbnailContainer.classList.add('thumbnail-container');
            this.parent.appendChild(this.thumbnailContainer);
        }
    }

    _populateGallery() {
        const {data, allowFullscreen, allowDownload} = this.options;
        const randomId = Math.random().toString(36).substring(7);
        // Create primary and preview containers
        this.primaryContainer = document.createElement('div');
        this.primaryContainer.classList.add('primary-container');
        this.primaryContainer.setAttribute('id', `primary-container-${randomId}`);
        this.galleryContainer.appendChild(this.primaryContainer);

        this.previewContainer = document.createElement('div');
        this.previewContainer.classList.add('preview-container');
        this.previewContainer.setAttribute('id', `preview-container-${randomId}`);
        this.galleryContainer.appendChild(this.previewContainer);

        // Click the fullscreen button on double-click of this.galleryContainer
        this.galleryContainer.addEventListener('dblclick', (event) => {
            // If a div with the class .primary-image.selected exists
            if (this.primaryContainer.querySelector('.primary-image.selected')) {
                event.preventDefault();
                event.stopPropagation();
                const fullscreenButton = this.primaryContainer.querySelector('.fullscreen-button');
                fullscreenButton.click();
            }
        });

        let lastTapTime = 0;
        let tapTimeout;

        this.galleryContainer.addEventListener('touchstart', (event) => {
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTapTime;

            if (tapLength < 500 && tapLength > 0) {
                // If a div with the class .primary-image.selected exists
                if (this.primaryContainer.querySelector('.primary-image.selected')) {
                    event.preventDefault();
                    event.stopPropagation();
                    const fullscreenButton = this.primaryContainer.querySelector('.fullscreen-button');
                    fullscreenButton.click();
                }
            } else {
                clearTimeout(tapTimeout);
                tapTimeout = setTimeout(() => {
                    clearTimeout(tapTimeout);
                }, 500);
            }

            lastTapTime = currentTime;
        });


        // Populate primary container, thumbnail container, and caption container

        data.forEach((imageData, index) => {
            // Primary image
            const primaryImage = document.createElement('img');
            primaryImage.src = imageData.src;
            primaryImage.classList.add('primary-image');
            primaryImage.style.display = index === 0 ? 'block' : 'none';
            this.primaryContainer.appendChild(primaryImage);

            // Caption
            if (this.options.showCaptions) {
                const caption = document.createElement('div');
                caption.classList.add('caption');
                caption.innerHTML = imageData.caption || '';
                caption.style.display = index === 0 ? 'block' : 'none';
                this.captionContainer.appendChild(caption);
            }

            // Thumbnail
            if (this.options.showThumbnails) {
                const thumbnail = document.createElement('img');
                thumbnail.src = imageData.thumbnail || imageData.src;
                thumbnail.classList.add('thumbnail');
                thumbnail.dataset.index = index;
                this.thumbnailContainer.appendChild(thumbnail);
            }
        });

        // Add fullscreen button
        if (allowFullscreen) {
            const fullscreenButton = document.createElement('button');
            fullscreenButton.classList.add('fullscreen-button', 'inlineButton');
            this.primaryContainer.appendChild(fullscreenButton);
        }

        // Add download button
        if (allowDownload) {
            const downloadButton = document.createElement('div');
            downloadButton.classList.add('download-button', 'inlineButton');
            this.primaryContainer.appendChild(downloadButton);
        }

        // Add navigation arrows
        const leftArrow = document.createElement('button');
        leftArrow.classList.add('left-arrow', 'inlineButton');
        this.primaryContainer.appendChild(leftArrow);

        const rightArrow = document.createElement('button');
        rightArrow.classList.add('right-arrow', 'inlineButton');
        this.primaryContainer.appendChild(rightArrow);
    }

    _addEventListeners() {
        const primaryImages = this.primaryContainer.querySelectorAll('.primary-image');
        const captions = this.captionContainer ? this.captionContainer.querySelectorAll('.caption') : [];
        const thumbnails = this.thumbnailContainer ? this.thumbnailContainer.querySelectorAll('.thumbnail') : [];

        let currentIndex = 0;

        // Disable clicks on primaryImages
        primaryImages.forEach((primaryImage) => {
            primaryImage.addEventListener('click', (event) => {
                event.preventDefault();
            });
        });
        const updateGallery = (newIndex) => {
            // If we have a latent image and the gallery was selected, make it a thumbnail button
            let latentImage = this.previewContainer.querySelector('.latent-image');
            if (latentImage) {
                this.previewContainer.classList.add("thumb-container");
                latentImage.classList.add('thumb-btn');
                latentImage.addEventListener('click', () => {
                    latentImage.classList.remove('thumb-btn');
                    this.previewContainer.classList.remove("thumb-container");
                });
            }
            // Hide all elements in primaryImages and captions
            primaryImages.forEach((primaryImage) => {
                primaryImage.style.display = 'none';
            });
            captions.forEach((caption) => {
                caption.style.display = 'none';
            });
            thumbnails.forEach((thumbnail) => {
                thumbnail.classList.remove('active');
            });

            if (newIndex < primaryImages.length) primaryImages[newIndex].style.display = 'block';

            if (this.options.showCaptions && newIndex < captions.length) captions[newIndex].style.display = 'block';

            if (this.options.showThumbnails && newIndex < thumbnails.length) _scrollToThumbnail(newIndex);

            if (this.options.allowDownload) downloadButton.href = this.options.data[newIndex].src;
            currentIndex = newIndex;
        };

        let totalImages = this.galleryContainer.querySelectorAll('.primary-image').length;
        const downloadButton = this.primaryContainer.querySelector('.download-button');
        const leftArrow = this.primaryContainer.querySelector('.left-arrow');
        const rightArrow = this.primaryContainer.querySelector('.right-arrow');
        const fullscreenButton = this.primaryContainer.querySelector('.fullscreen-button');

        if (totalImages === 0) {
            $(".inlineButton").hide();
        } else if (totalImages === 1) {
            downloadButton.style.display = 'block';
            fullscreenButton.style.display = 'block';
        } else {
            $(".inlineButton").show();
        }

        leftArrow.addEventListener('click', () => {
            let newIndex = currentIndex - 1;
            if (newIndex < 0) {
                newIndex = this.options.loop ? this.options.data.length - 1 : 0;
            }
            updateGallery(newIndex);
        });

        rightArrow.addEventListener('click', () => {
            let newIndex = currentIndex + 1;
            if (newIndex >= this.options.data.length) {
                newIndex = this.options.loop ? 0 : this.options.data.length - 1;
            }
            updateGallery(newIndex);
        });
        const _scrollToThumbnail = (index) => {
            if (!this.options.showThumbnails || !this.thumbnailContainer) {
                return;
            }

            const thumbnail = this.thumbnailContainer.querySelectorAll('.thumbnail')[index];
            if (!thumbnail) {
                return;
            }

            thumbnail.classList.add('active');
            const containerWidth = this.thumbnailContainer.clientWidth;
            const containerScrollLeft = this.thumbnailContainer.scrollLeft;
            const thumbnailLeft = thumbnail.offsetLeft;
            const thumbnailWidth = thumbnail.clientWidth;

            const scrollPosition = thumbnailLeft - (containerWidth / 2) + (thumbnailWidth / 2);
            this.thumbnailContainer.scrollTo({
                left: scrollPosition,
                behavior: 'smooth'
            });
        };

        if (this.options.allowFullscreen) {
            fullscreenButton.addEventListener('click', () => {
                try {
                    const requestFullscreenMethod = this.primaryContainer.requestFullscreen
                        || this.primaryContainer.webkitRequestFullscreen
                        || this.primaryContainer.mozRequestFullScreen
                        || this.primaryContainer.msRequestFullscreen;

                    const exitFullscreenMethod = document.exitFullscreen
                        || document.webkitExitFullscreen
                        || document.mozCancelFullScreen
                        || document.msExitFullscreen;

                    if (document.fullscreenElement
                        || document.webkitFullscreenElement
                        || document.mozFullScreenElement
                        || document.msFullscreenElement) {
                        exitFullscreenMethod.call(document).then(r => r);
                    } else {
                        requestFullscreenMethod.call(this.primaryContainer).then(r => r);
                    }
                } catch {

                }
            });
        }

        if (this.options.showThumbnails) {
            thumbnails.forEach((thumbnail, index) => {
                thumbnail.addEventListener('click', () => {
                    updateGallery(index);
                    _scrollToThumbnail(index);
                });
            });
        }
    }

    async socketUpdate(data) {
        if (data.hasOwnProperty("target") && data.target !== this.options.id) {
            return;
        }

        let [imageList, latent, append] = this.extractImageData(data);
        this.update(imageList, latent, append);

    }

    extractImageData(data) {
        const status = data.status;
        let append = true;
        let latent = null;

        if (!status.active) {
            append = false;
        }

        if (status.hasOwnProperty("latents")) {
            latent = status.latents;
        }

        const images = status.images || [];
        const descriptions = status.descriptions || [];
        const prompts = status.prompts || [];

        const imageList = [];
        for (let i = 0; i < images.length; i++) {
            const imagePath = images[i];

            let caption = '';
            if (prompts.length > i && typeof prompts[i] === 'string') {
                caption = prompts[i];
            }

            let description = '';
            if (descriptions.length > i && typeof descriptions[i] === 'string') {
                description = descriptions[i];
            }

            imageList.push({src: imagePath, caption: caption, description: description});
        }

        return [imageList, latent, append];
    }

    update(imageList, latent, append = false) {
        if (!append) {
            this._clearGallery();
        }

        // Preview
        if (latent !== null) {
            let latentImage = this.previewContainer.querySelector('.latent-image');
            if (latentImage !== null) {
                latentImage.src = latent;
                this.previewContainer.classList.remove("hidden");
            } else {
                const latentImage = document.createElement('img');
                latentImage.src = latent;
                latentImage.classList.add('latent-image');
                this.previewContainer.appendChild(latentImage);
                this.previewContainer.classList.remove("hidden");
            }
        } else {
            this.previewContainer.classList.add("hidden");
        }

        imageList.forEach(imageData => {
            const existingImage = this.primaryContainer.querySelector(`img[src="${imageData.src}"]`);
            const existingThumbnail = this.thumbnailContainer ? this.thumbnailContainer.querySelector(`img[src="${imageData.thumbnail || imageData.src}"]`) : null;

            if (existingImage || existingThumbnail) {
                return;
            }

            // Primary image
            const primaryImage = document.createElement('img');
            primaryImage.src = imageData.src;
            primaryImage.classList.add('primary-image');
            primaryImage.style.display = 'none';
            this.primaryContainer.appendChild(primaryImage);
            let doSelect = false;
            // If primary container has has no selected image and we have no latents, select this image
            if (this.primaryContainer.querySelector('.primary-image.selected') === null && latent === null) {
                primaryImage.classList.add('selected');
                primaryImage.style.display = 'block';
                doSelect = true;
            }

            // Caption
            if (this.options.showCaptions) {
                const caption = document.createElement('div');
                caption.classList.add('caption');
                caption.innerHTML = imageData.caption || '';
                caption.style.display = 'none';
                this.captionContainer.appendChild(caption);
                if (doSelect) {
                    caption.style.display = 'block';
                }
            }

            // Thumbnail
            if (this.options.showThumbnails) {
                const thumbnail = document.createElement('img');
                thumbnail.src = imageData.thumbnail || imageData.src;
                thumbnail.classList.add('thumbnail');
                thumbnail.dataset.index = this.options.data.length;
                this.thumbnailContainer.appendChild(thumbnail);
                if (doSelect) {
                    thumbnail.classList.add('selected');
                }
                // If more than one image, show thumbnails
                if (this.thumbnailContainer.children.length > 1) {
                    this.thumbnailContainer.style.display = 'flex';
                } else {
                    this.thumbnailContainer.style.display = 'none';
                }
            }

            // Update options data
            this.options.data.push({
                src: imageData.src,
                caption: imageData.caption || '',
                description: imageData.description || ''
            });
        });

        this._addEventListeners();

    }

    _clearGallery() {
        // Remove primary images
        const primaryImages = this.primaryContainer.querySelectorAll('.primary-image');
        primaryImages.forEach(img => img.remove());

        // Remove captions
        if (this.options.showCaptions) {
            const captions = this.captionContainer.querySelectorAll('.caption');
            captions.forEach(caption => caption.remove());
        }

        // Remove thumbnails
        if (this.options.showThumbnails) {
            const thumbnails = this.thumbnailContainer.querySelectorAll('.thumbnail');
            thumbnails.forEach(thumbnail => thumbnail.remove());
        }

        // Hide preview
        this.previewContainer.innerHTML = "";

        $(".inlineButton").hide();

        // Reset options data
        this.options.data = [];
    }

    clear() {
        this._clearGallery();
    }
}

// jQuery constructor
if (typeof jQuery !== 'undefined') {
    jQuery.fn.inlineGallery = function (options) {
        return this.each(function () {
            new InlineGallery(this, options);
        });
    };
}
