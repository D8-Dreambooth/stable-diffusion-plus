class ProgressGroup {
    constructor(parentElement, options) {
        this.parentElement = parentElement;
        this.update = this.update.bind(this);
        this.onComplete = null;
        this.onCancel = null;

        registerSocketMethod("progressGroup", "status", this.update);
      // Set options last with update(options)
        this.options = {
          progress_1_current: 0,
          progress_2_current: 0,
          progress_1_total: 0,
          progress_2_total: 0,
          progress_1_css: " bg-success",
          progress_2_css: " bg-warning",
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

        const progressRow = document.createElement("div");
        progressRow.classList.add("progressRow");

        this.progressBar1 = document.createElement("div");
        this.progressBar1.classList.add("progress-bar");
        this.progressBar2 = document.createElement("div");
        this.progressBar2.classList.add("progress-bar");

        const progressGroup = document.createElement("div");
        progressGroup.classList.add("progress");
        progressGroup.appendChild(this.progressBar1);
        progressGroup.appendChild(this.progressBar2);
        progressRow.appendChild(progressGroup);

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

        this.progressContainer.appendChild(progressRow);
        this.progressContainer.appendChild(statusRowPrimary);
        this.progressContainer.appendChild(statusRowSecondary);

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
        this.update(this.options);
    }

    update(options) {
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

        // Update progress bar visibility
        if (this.options.show_bar1) {
            this.progressBar1.style.setProperty("display", "block");
        } else {
            this.progressBar1.style.setProperty("display", "none");
        }

        if (this.options.show_bar2) {
            this.progressBar2.style.setProperty("display", "block");
        } else {
            this.progressBar2.style.setProperty("display", "none");
        }

        let pct_1 = (this.options.progress_1_current / this.options.progress_1_total) * 100;
        let pct_2 = (this.options.progress_2_current / this.options.progress_2_total) * 100;
        if (!isNaN(pct_1) && !isNaN(pct_2)) {
            if (pct_1 > 0 && pct_2 > 0) {
                let total_pct = pct_1 + pct_2;
                let adj_pct_1 = (pct_1 / total_pct) * 100;
                let adj_pct_2 = (pct_2 / total_pct) * 100;
                this.progressBar1.style.setProperty("width", adj_pct_1 + "%");
                this.progressBar2.style.setProperty("width", adj_pct_2 + "%");
            } else {
                this.progressBar1.style.setProperty("width", pct_1 + "%");
                this.progressBar2.style.setProperty("width", pct_2 + "%");
            }

            if (this.options.show_percent) {
                let roundedPct1 = pct_1.toFixed(0);
                let roundedPct2 = pct_2.toFixed(0);
                this.progressBar1.innerHTML = String(roundedPct1) + "%";
                this.progressBar2.innerHTML = String(roundedPct2) + "%";
            } else {
                this.progressBar1.innerHTML = "";
                this.progressBar2.innerHTML = "";
            }
        } else {
            if (!isNaN(pct_1)) {
                let roundedPct1 = pct_1.toFixed(0);
                this.progressBar1.style.setProperty("width", pct_1 + "%");
                if (this.options.show_percent) {
                    this.progressBar1.innerHTML = String(roundedPct1) + "%";
                }
            } else {
                this.progressBar1.style.setProperty("width", "0");
            }

                this.progressBar2.style.setProperty("width", "0");
        }

        // Update status text
        this.primary_status.innerHTML = this.options.status;
        this.secondary_status.innerHTML = this.options.status_2;

        // Update status text visibility
        if (this.options.show_primary_status) {
            this.primary_status.style.setProperty("display", "block");
        } else {
            this.primary_status.style.setProperty("display", "none");
        }

        if (this.options.show_secondary_status) {
            this.secondary_status.style.setProperty("display", "block");
        } else {
            this.secondary_status.style.setProperty("display", "none");
        }

        // Update progress bar CSS classes
        this.progressBar1.className = "progress-bar" + this.options.progress_1_css;
        this.progressBar2.className = "progress-bar" + this.options.progress_2_css;
        if (options["active"] === false) {
            if (options["canceled"] === true) {
                // If this.onCancel is a function, call it
                if (typeof this.onCancel === "function") {
                    this.onCancel();
                }
            } else {
                // If this.onComplete is a function, call it
                if (typeof this.onComplete === "function") {
                    this.onComplete();
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

}
     
