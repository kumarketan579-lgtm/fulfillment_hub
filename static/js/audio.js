/**
 * Web Audio Synthesizer for Warehouse Floor Sound Effects.
 * Generates realistic warehouse barcode scanner beeps and error buzzers without external audio files.
 */

class WarehouseAudio {
    constructor() {
        this.ctx = null;
    }

    initContext() {
        if (!this.ctx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.ctx = new AudioContext();
        }
        if (this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    // Success scanner beep (standard warehouse hand-held terminal beep)
    playScanSuccess() {
        try {
            this.initContext();
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = 'sine';
            osc.frequency.setValueAtTime(1760, now); // A6 high pitch
            osc.frequency.setValueAtTime(2349.32, now + 0.06); // D7

            gain.gain.setValueAtTime(0.18, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now);
            osc.stop(now + 0.15);
        } catch (e) {
            console.warn("Audio playback not allowed until user gesture", e);
        }
    }

    // Error buzzer (loud low buzzer for wrong SKU / mismatch)
    playScanError() {
        try {
            this.initContext();
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(160, now);
            osc.frequency.setValueAtTime(130, now + 0.12);

            gain.gain.setValueAtTime(0.3, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now);
            osc.stop(now + 0.35);
        } catch (e) {
            console.warn("Audio error play failed", e);
        }
    }

    // Complete order chime (celebratory chime)
    playOrderComplete() {
        try {
            this.initContext();
            const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
            notes.forEach((freq, idx) => {
                const now = this.ctx.currentTime + (idx * 0.08);
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();

                osc.type = 'triangle';
                osc.frequency.setValueAtTime(freq, now);

                gain.gain.setValueAtTime(0.2, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

                osc.connect(gain);
                gain.connect(this.ctx.destination);

                osc.start(now);
                osc.stop(now + 0.25);
            });
        } catch (e) {
            console.warn("Audio chime failed", e);
        }
    }
}

window.warehouseAudio = new WarehouseAudio();
