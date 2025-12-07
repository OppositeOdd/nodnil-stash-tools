/**
 * Alternate Heatmaps - Replace default heatmaps with detailed funscript heatmaps
 *
 * Injects pre-generated heatmap overlays into:
 * - Video scrubber overlay
 * - Scene file info section (full heatmap)
 *
 * Depends on: FunUtil
 * @typedef {import('./types').FunUtilAPI} FunUtilAPI
 * @typedef {import('./types').PluginAPI} PluginAPI
 */

/* global FunUtil, PluginApi */

console.log('[AlternateHeatmaps] Loading plugin v0.1.0');

(function() {
  'use strict';

  const CHECK_INTERVAL = 500;
  const MAX_RETRIES = 20;
  let retryCount = 0;
  let checkTimer = null;

  // ============================
  // Scrubber Overlay Injection
  // ============================

  async function injectScrubberOverlay(oshash) {
    console.log('[AlternateHeatmaps] Attempting to inject scrubber overlay');

    const scrubberHeatmap = /** @type {HTMLElement} */ (document.querySelector('.scrubber-wrapper .scrubber-content .scrubber-heatmap[style]'));
    if (!scrubberHeatmap) {
      console.log('[AlternateHeatmaps] Scrubber heatmap element not found');
      return false;
    }

    const heatmapEl = scrubberHeatmap;

    // Already loaded for this oshash
    if (heatmapEl.dataset.oshash === oshash) {
      console.log('[AlternateHeatmaps] Scrubber overlay already loaded');
      return true;
    }

    heatmapEl.dataset.loading = 'true';

    const url = FunUtil.getHeatmapUrl(oshash, 'overlay', 'funUtil');
    console.log(`[AlternateHeatmaps] Checking for overlay at: ${url}`);

    if (!url) {
      heatmapEl.dataset.loading = 'false';
      return false;
    }

    const exists = await FunUtil.heatmapExists(url);
    console.log(`[AlternateHeatmaps] Overlay exists: ${exists}`);

    if (!exists) {
      heatmapEl.dataset.loading = 'false';
      return false;
    }

    // Replace background with heatmap
    heatmapEl.style.setProperty('background-image', `url('${url}')`, 'important');
    heatmapEl.dataset.oshash = oshash;
    heatmapEl.dataset.loading = 'false';
    heatmapEl.classList.add('funscript-heatmap-loaded');

    console.log(`[AlternateHeatmaps] ✓ Loaded scrubber overlay: ${url}`);
    return true;
  }

  // ============================
  // Full Heatmap Injection
  // ============================

  async function injectFullHeatmap(oshash) {
    console.log('[AlternateHeatmaps] Attempting to inject full heatmap');

    if (document.querySelector(`.funscript-heatmap-full[data-oshash="${oshash}"]`)) {
      console.log('[AlternateHeatmaps] Full heatmap already loaded');
      return true;
    }

    const funscriptTab = document.querySelector('[data-rb-event-key="scene-funscripts-panel"]');
    if (funscriptTab) {
      console.log('[AlternateHeatmaps] funscriptSceneTab detected, skipping injection');
      return true;
    }

    const sceneFileInfo = document.querySelector('.scene-file-info dl.details-list');
    if (!sceneFileInfo) {
      console.log('[AlternateHeatmaps] Scene file info element not found');
      return false;
    }

    const url = FunUtil.getHeatmapUrl(oshash, 'full', 'funUtil');
    console.log(`[AlternateHeatmaps] Checking for full heatmap at: ${url}`);

    if (!url) return false;

    const exists = await FunUtil.heatmapExists(url);
    console.log(`[AlternateHeatmaps] Full heatmap exists: ${exists}`);

    if (!exists) return false;

    const existing = document.querySelector('.funscript-heatmap-full');
    if (existing) existing.remove();

    const img = document.createElement('img');
    img.className = 'funscript-heatmap-full';
    img.src = url;
    img.alt = 'Funscript Heatmap';
    img.dataset.oshash = oshash;
    img.dataset.loading = 'true';

    img.onload = function() {
      /** @type {HTMLImageElement} */ (this).dataset.loading = 'false';
      /** @type {HTMLImageElement} */ (this).classList.add('funscript-heatmap-loaded');
      console.log(`[AlternateHeatmaps] ✓ Loaded full heatmap: ${/** @type {HTMLImageElement} */ (this).src}`);
    };

    img.onerror = function() {
      /** @type {HTMLImageElement} */ (this).dataset.loading = 'false';
      console.error('[AlternateHeatmaps] Failed to load full heatmap');
    };

    sceneFileInfo.insertAdjacentElement('afterend', img);
    return true;
  }

  // ============================
  // Scene Card Heatmap Replacement
  // ============================

  async function replaceSceneCardHeatmaps() {
    const heatmapImages = document.querySelectorAll('img.interactive-heatmap');
    
    for (const img of heatmapImages) {
      // Skip if already processed
      if (img.dataset.alternateProcessed === 'true') continue;
      
      // Extract scene ID from the src URL
      const srcMatch = img.src.match(/\/scene\/(\d+)\/interactive_heatmap/);
      if (!srcMatch) continue;
      
      const sceneId = srcMatch[1];
      
      try {
        const sceneData = await FunUtil.fetchSceneData(sceneId);
        if (!sceneData || !sceneData.oshash) continue;
        
        const url = FunUtil.getHeatmapUrl(sceneData.oshash, 'overlay', 'funUtil');
        if (!url) continue;
        
        const exists = await FunUtil.heatmapExists(url);
        if (!exists) continue;
        
        // Replace the image source
        img.src = url;
        img.dataset.alternateProcessed = 'true';
        console.log(`[AlternateHeatmaps] ✓ Replaced scene card heatmap for scene ${sceneId}`);
      } catch (error) {
        console.error(`[AlternateHeatmaps] Error replacing heatmap for scene ${sceneId}:`, error);
      }
    }
  }

  // ============================
  // Scrubber Position Fix
  // ============================

  function updateScrubberPosition() {
    const video = /** @type {HTMLVideoElement} */ (document.querySelector('video'));
    const indicator = /** @type {HTMLElement} */ (document.querySelector('#scrubber-current-position'));
    const scrubberSlider = document.querySelector('.scrubber-slider');

    if (!video || !indicator || !scrubberSlider) return;

    const percentage = (video.currentTime / video.duration) * 100;
    if (!isNaN(percentage)) {
      indicator.style.left = `${percentage}%`;
    }
  }

  function initScrubberPositionFix() {
    const video = document.querySelector('video');
    if (!video) return;

    video.addEventListener('timeupdate', updateScrubberPosition);
    video.addEventListener('seeking', updateScrubberPosition);
    video.addEventListener('seeked', updateScrubberPosition);

    console.log('[AlternateHeatmaps] ✓ Scrubber position fix initialized');
  }

  // ============================
  // Main Injection Logic
  // ============================

  async function injectHeatmaps() {
    const urlMatch = window.location.pathname.match(/\/scenes\/(\d+)/);
    if (!urlMatch) {
      console.log('[AlternateHeatmaps] Not on a scene page');
      return false;
    }

    const sceneId = urlMatch[1];
    console.log(`[AlternateHeatmaps] On scene page, ID: ${sceneId}`);

    const sceneData = await FunUtil.fetchSceneData(sceneId);
    if (!sceneData || !sceneData.oshash) {
      console.log('[AlternateHeatmaps] No scene data or oshash');
      return false;
    }

    console.log(`[AlternateHeatmaps] Scene oshash: ${sceneData.oshash}`);

    const overlayLoaded = await injectScrubberOverlay(sceneData.oshash);
    await injectFullHeatmap(sceneData.oshash);

    if (overlayLoaded) {
      initScrubberPositionFix();
    }

    return overlayLoaded;
  }

  // ============================
  // Retry Logic
  // ============================

  function startChecking() {
    if (checkTimer) clearInterval(checkTimer);

    retryCount = 0;
    checkTimer = setInterval(async () => {
      const success = await injectHeatmaps();

      if (success || retryCount >= MAX_RETRIES) {
        clearInterval(checkTimer);
        checkTimer = null;
      }

      retryCount++;
    }, CHECK_INTERVAL);
  }

  // ============================
  // Initialization
  // ============================

  function init() {
    console.log('[AlternateHeatmaps] Plugin initialized');

    startChecking();
    
    // Replace scene card heatmaps
    replaceSceneCardHeatmaps();
    
    // Watch for dynamically loaded scene cards
    const observer = new MutationObserver(() => {
      replaceSceneCardHeatmaps();
    });
    
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    if (typeof PluginApi !== 'undefined') {
      PluginApi.Event.addEventListener('stash:location', () => {
        console.log('[AlternateHeatmaps] Navigation detected, reinitializing...');
        startChecking();
        replaceSceneCardHeatmaps();
      });
    }
  }

  function waitForFunUtil(callback, maxRetries = 100) {
    let retries = 0;
    const interval = setInterval(() => {
      if (typeof window.FunUtil !== 'undefined' && window.FunUtil.waitForStashLibrary) {
        clearInterval(interval);
        console.log('[AlternateHeatmaps] FunUtil detected, waiting for Stash libraries...');
        window.FunUtil.waitForStashLibrary(callback);
      } else if (++retries >= maxRetries) {
        clearInterval(interval);
        console.error('[AlternateHeatmaps] Failed to load FunUtil dependency after ' + (maxRetries * 100) + 'ms');
        console.error('[AlternateHeatmaps] window.FunUtil =', typeof window.FunUtil);
        console.error('[AlternateHeatmaps] Make sure funUtil plugin is enabled and loaded');
      }
    }, 100);
  }

  waitForFunUtil(init);

})();
