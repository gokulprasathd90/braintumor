'use strict';

/**
 * Timer — Computational Time Tracker
 *
 * Uses process.hrtime.bigint() for nanosecond-precision wall-clock timing.
 * The paper compares computational time in minutes (Figure 10).
 */
class Timer {
  constructor() {
    this._startNs = null;
    this._endNs = null;
  }

  /** Record start timestamp */
  start() {
    this._startNs = process.hrtime.bigint();
    this._endNs = null;
    return this;
  }

  /** Record end timestamp */
  stop() {
    if (!this._startNs) {
      throw new Error('Timer.stop() called before Timer.start()');
    }
    this._endNs = process.hrtime.bigint();
    return this;
  }

  /**
   * Elapsed time in milliseconds.
   * If stop() has not been called yet, measures from start to now.
   * @returns {number}
   */
  elapsedMs() {
    if (!this._startNs) return 0;
    const endNs = this._endNs || process.hrtime.bigint();
    // BigInt subtraction → convert nanoseconds to milliseconds
    return Number(endNs - this._startNs) / 1_000_000;
  }

  /**
   * Elapsed time in minutes.
   * Used for the Computational Time metric compared in paper Figure 10.
   * @returns {number}
   */
  elapsedMinutes() {
    return this.elapsedMs() / 60_000;
  }

  /**
   * Elapsed time in seconds.
   * @returns {number}
   */
  elapsedSeconds() {
    return this.elapsedMs() / 1_000;
  }

  /** Reset all timestamps */
  reset() {
    this._startNs = null;
    this._endNs = null;
    return this;
  }

  /**
   * Convenience: returns a summary object with all time representations.
   * @returns {{ ms: number, seconds: number, minutes: number }}
   */
  summary() {
    const ms = this.elapsedMs();
    return {
      ms: parseFloat(ms.toFixed(3)),
      seconds: parseFloat((ms / 1_000).toFixed(4)),
      minutes: parseFloat((ms / 60_000).toFixed(6)),
    };
  }
}

/**
 * Convenience factory — creates, starts, and returns a running Timer.
 * @returns {Timer}
 */
function startTimer() {
  return new Timer().start();
}

module.exports = { Timer, startTimer };
