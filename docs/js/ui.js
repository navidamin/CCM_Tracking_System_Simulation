/**
 * UI controller: scenario loading, playback controls, stats display.
 */

export class UIController {
    constructor() {
        this.scenarioEl = document.getElementById('scenario');
        this.btnPlay = document.getElementById('btn-play');
        this.timeSlider = document.getElementById('time-slider');
        this.timeDisplay = document.getElementById('time-display');
        this.speedSelect = document.getElementById('speed-select');
        this.legendItems = document.getElementById('legend-items');

        // Stats elements
        this.statTime = document.getElementById('stat-time');
        this.statCast = document.getElementById('stat-cast');
        this.statDelivered = document.getElementById('stat-delivered');
        this.statCoolbed = document.getElementById('stat-coolbed');
        this.statTc = document.getElementById('stat-tc');
        this.statJam = document.getElementById('stat-jam');
        this.jamRow = document.getElementById('jam-row');
        this.statTcUtil = document.getElementById('stat-tc-util');
        this.statTcCycle = document.getElementById('stat-tc-cycle');
        this.statCbMax = document.getElementById('stat-cb-max');
        this.statTableMax = document.getElementById('stat-table-max');
        this.statBottleneck = document.getElementById('stat-bottleneck');

        this.playing = false;
        this.speed = 20;
        this.simTime = 1200; // start at warmup end
        this.duration = 7200;

        this._onScenarioChange = null;

        this._bindEvents();
    }

    _bindEvents() {
        this.btnPlay.addEventListener('click', () => this.togglePlay());

        this.timeSlider.addEventListener('input', () => {
            this.simTime = parseFloat(this.timeSlider.value);
            this._updateTimeDisplay();
        });

        this.speedSelect.addEventListener('change', () => {
            this.speed = parseFloat(this.speedSelect.value);
        });

        this.scenarioEl.addEventListener('change', () => {
            if (this._onScenarioChange) {
                this._onScenarioChange(this.scenarioEl.value);
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space') { e.preventDefault(); this.togglePlay(); }
            if (e.code === 'ArrowRight') { this.simTime = Math.min(this.duration, this.simTime + 30); }
            if (e.code === 'ArrowLeft') { this.simTime = Math.max(0, this.simTime - 30); }
        });
    }

    onScenarioChange(cb) {
        this._onScenarioChange = cb;
    }

    togglePlay() {
        this.playing = !this.playing;
        this.btnPlay.textContent = this.playing ? '\u23F8' : '\u25B6';
    }

    /**
     * Populate scenario dropdown from manifest.
     */
    populateScenarios(manifest) {
        this.scenarioEl.innerHTML = '';
        for (const entry of manifest) {
            const opt = document.createElement('option');
            opt.value = entry.file;
            opt.textContent = entry.label;
            this.scenarioEl.appendChild(opt);
        }
    }

    /**
     * Build strand legend.
     */
    buildLegend(numStrands, colors) {
        this.legendItems.innerHTML = '';
        for (let s = 1; s <= numStrands; s++) {
            const item = document.createElement('div');
            item.className = 'legend-item';
            const swatch = document.createElement('div');
            swatch.className = 'legend-color';
            swatch.style.backgroundColor = '#' + colors[s - 1].toString(16).padStart(6, '0');
            const label = document.createElement('span');
            label.textContent = `Strand ${s}`;
            item.appendChild(swatch);
            item.appendChild(label);
            this.legendItems.appendChild(item);
        }
    }

    /**
     * Show scenario-specific info (jam warning).
     */
    setScenarioInfo(stats) {
        if (stats.traffic_jam) {
            this.jamRow.style.display = 'flex';
            this.statJam.textContent = `${stats.traffic_jam_location} @ ${stats.traffic_jam_time?.toFixed(0)}s`;
        } else {
            this.jamRow.style.display = 'none';
        }
        // Summary stats (from analysis, static per scenario)
        this.statTcUtil.textContent = stats.tc_utilization != null
            ? `${(stats.tc_utilization * 100).toFixed(1)}%` : '—';
        this.statTcCycle.textContent = stats.tc_avg_cycle != null
            ? `${stats.tc_avg_cycle.toFixed(1)}s` : '—';
        this.statCbMax.textContent = stats.max_coolbed_occupancy ?? '—';
        this.statTableMax.textContent = stats.max_table_packs ?? '—';
        this.statBottleneck.textContent = stats.bottleneck
            ? stats.bottleneck.split('(')[0].trim() : '—';
    }

    /**
     * Advance sim time by delta (seconds).
     */
    tick(deltaSec) {
        if (!this.playing) return;
        this.simTime += deltaSec * this.speed;
        if (this.simTime >= this.duration) {
            this.simTime = this.duration;
            this.playing = false;
            this.btnPlay.textContent = '\u25B6';
        }
        this.timeSlider.value = this.simTime;
        this._updateTimeDisplay();
    }

    updateStats(stats) {
        this.statTime.textContent = `${this.simTime.toFixed(0)} s`;
        this.statCast.textContent = stats.castCount;
        this.statDelivered.textContent = stats.deliveredCount;
        this.statCoolbed.textContent = stats.coolbedOcc;
        this.statTc.textContent = stats.tcStatus;
    }

    _updateTimeDisplay() {
        this.timeDisplay.textContent = `${this.simTime.toFixed(0)} / ${this.duration} s`;
    }
}
