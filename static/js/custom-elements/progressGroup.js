class ProgressGroup {
    constructor(parentElement, options) {
        this.parentElement = parentElement;
        this.update = this.update.bind(this);
        this.onComplete = null;
        this.onCancel = null;
        this.onStart = null;
        this.onUpdate = null;
        this.onCompleteCalled = false;
        this.onCancelCalled = false;
        this.onStartCalled = false;
        registerSocketMethod("progressGroup", "status", this.update);
        // Set options last with update(options)
        this.options = {
            progress_1_current: 0,
            progress_2_current: 0,
            progress_1_total: 0,
            progress_2_total: 0,
            progress_1_css: " progress_main",
            progress_2_css: " progress_secondary",
            status: "",
            status_2: "",
            show_bar1: true,
            show_bar2: true,
            show_primary_status: true,
            show_secondary_status: true,
            show_percent: true
        };
        this.id = (options.hasOwnProperty("id") ? options.id : Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15));

        // Create HTML elements
        this.progressContainer = document.createElement("div");
        this.progressContainer.classList.add("progressContainer");

        const progressRow1 = document.createElement("div");
        progressRow1.classList.add("progressRow");

        this.progressBar1 = document.createElement("div");
        this.progressBar1.classList.add("progress-bar");

        const progressGroup1 = document.createElement("div");
        progressGroup1.classList.add("progress");
        progressGroup1.appendChild(this.progressBar1);
        progressRow1.appendChild(progressGroup1);

        const progressRow2 = document.createElement("div");
        progressRow2.classList.add("progressRow");

        this.progressBar2 = document.createElement("div");
        this.progressBar2.classList.add("progress-bar");

        const progressGroup2 = document.createElement("div");
        progressGroup2.classList.add("progress");
        progressGroup2.appendChild(this.progressBar2);
        progressRow2.appendChild(progressGroup2);

        const statusRowPrimary = document.createElement("div");
        statusRowPrimary.classList.add("row", "statusRowPrimary");

        const primary_status = document.createElement("div");
        primary_status.classList.add("status_primary", "fit");
        primary_status.innerHTML = "";
        this.primary_status = primary_status;
        statusRowPrimary.appendChild(primary_status);

        const statusRowSecondary = document.createElement("div");
        statusRowSecondary.classList.add("row", "statusRowSecondary");

        const secondary_status = document.createElement("div");
        secondary_status.classList.add("status_secondary", "fit");
        secondary_status.innerHTML = "";
        this.secondary_status = secondary_status;
        statusRowSecondary.appendChild(secondary_status);
        this.progressContainer.appendChild(statusRowPrimary);
        this.progressContainer.appendChild(progressRow1);
        this.progressContainer.appendChild(statusRowSecondary);
        this.progressContainer.appendChild(progressRow2);

        // Append to parent element
        this.parentElement.appendChild(this.progressContainer);

        // Update the component with the options
        this.update(options);
    }

    clear() {
        this.options.progress_1_current = 0;
        this.options.progress_2_current = 0;
        this.options.progress_1_total = 0;
        this.options.progress_2_total = 0;
        this.options.status = "";
        this.options.status_2 = "";
        this.onCompleteCalled = false;
        this.onCancelCalled = false;
        this.onStartCalled = false;
        this.update(this.options);
    }

    update(options) {
        if (this.onUpdate !== null) {
            let upOptions = this.onUpdate(options);
            if (upOptions !== undefined && upOptions !== null) {
                options = upOptions;
            }
        }

        if (options.hasOwnProperty("target")) {
            if (this.id !== options.target) {
                return;
            }
        }

        // If options has a status property and it's not a string, assume it's a status object
        if (options.hasOwnProperty("status") && typeof options.status !== "string") {
            options = options.status;
        }

        // Merge user options with default options
        this.options = {...this.options, ...options};
        // Update progress bars
        this.progressBar1.setAttribute("aria-valuenow", this.options.progress_1_current);
        this.progressBar2.setAttribute("aria-valuenow", this.options.progress_2_current);

        let pct_1 = (this.options.progress_1_current / this.options.progress_1_total) * 100;
        let pct_2 = (this.options.progress_2_current / this.options.progress_2_total) * 100;

        if (!isNaN(pct_1) && this.options.progress_1_total > 0) {
            this.progressBar1.parentElement.style.setProperty("display", "block");
            this.progressBar1.style.setProperty("width", pct_1 + "%");
            if (this.options.show_percent) {
                let roundedPct1 = pct_1.toFixed(0);
                this.progressBar1.innerHTML = String(roundedPct1) + "%";
            }
        } else {
            this.progressBar1.parentElement.style.setProperty("display", "none");
        }

        if (!isNaN(pct_2) && this.options.progress_2_total > 0) {
            this.progressBar2.parentElement.style.setProperty("display", "block");
            this.progressBar2.style.setProperty("width", pct_2 + "%");
            if (this.options.show_percent) {
                let roundedPct2 = pct_2.toFixed(0);
                this.progressBar2.innerHTML = String(roundedPct2) + "%";
            }
        } else {
            this.progressBar2.parentElement.style.setProperty("display", "none");
        }

        if (this.options.progress_1_total > 0 && this.options.progress_2_total > 0) {
            this.progressBar1.style.setProperty("border-radius", "5px 5px 0 0");
            this.progressBar1.style.setProperty("border-bottom", "1px solid var(--bs-border-dark)")
            this.progressBar1.style.setProperty("border-radius", "0 0 5px 5px");
        } else {
            this.progressBar1.style.setProperty("border-radius", "5px 5px 5px 5px");
            this.progressBar1.style.setProperty("border-radius", "5px 5px 5px 5px");
            this.progressBar1.style.setProperty("border-bottom", "none");
        }
        // Update status text

        this.primary_status.innerHTML = this.options.status;
        this.secondary_status.innerHTML = this.options.status_2;

        // Update status text visibility
        if (this.options.status !== "") {
            this.primary_status.style.setProperty("display", "block");
        } else {
            this.primary_status.style.setProperty("display", "none");
        }


        if (this.options.status_2 !== "") {
            this.secondary_status.style.setProperty("display", "block");
        } else {
            this.secondary_status.style.setProperty("display", "none");
        }

        // Update progress bar CSS classes
        this.progressBar1.className = "progress-bar" + this.options.progress_1_css;
        this.progressBar2.className = "progress-bar" + this.options.progress_2_css;

        if (options["canceled"] === true && !this.onCancelCalled) {
            // If this.onCancel is a function, call it
            if (this.onCancel !== null) {
                this.onCancelCalled = true;
                this.onCancel();
            }
        }
        if (options["active"] === false && !this.onCompleteCalled) {
            // If this.onComplete is a function, call it
            if (this.onComplete !== null) {
                this.onCompleteCalled = true;
                this.onComplete();
            }
        } else {
            if (!this.onStartCalled) {
                if (this.onStart !== null) {
                    console.log("onStart called: ", this.onStart);
                    // If this.onStart is a function, call it
                    this.onStartCalled = true;
                    this.onStart();
                }
            }
        }
    }

    setOnCancel(callback) {
        this.onCancel = callback;
    }

    setOnComplete(callback) {
        this.onComplete = callback;
    }

    setOnStart(callback) {
        console.log("Onstart set? ", callback)
        this.onStart = callback;
    }

    setOnUpdate(callback) {
        this.onUpdate = callback;
    }

}
     
