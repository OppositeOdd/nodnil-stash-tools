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

(function() {
  'use strict';

  const DEBUG = false; // Set to true to enable debug logging
  const CHECK_INTERVAL = 500;
  const MAX_RETRIES = 20;
  let retryCount = 0;
  let checkTimer = null;

  function log(...args) {
    if (DEBUG) console.log(...args);
  }

  console.log('[AlternateHeatmaps] Loading plugin v0.1.0');

  // ============================
  // Scrubber Overlay Injection
  // ============================

  async function injectScrubberOverlay(oshash) {
    log('[AlternateHeatmaps] Attempting to inject scrubber overlay');

    const scrubberHeatmap = /** @type {HTMLElement} */ (document.querySelector('.scrubber-wrapper .scrubber-content .scrubber-heatmap[style]'));
    if (!scrubberHeatmap) {
      log('[AlternateHeatmaps] Scrubber heatmap element not found');
      return false;
    }

    const heatmapEl = scrubberHeatmap;

    // Already loaded for this oshash
    if (heatmapEl.dataset.oshash === oshash) {
      log('[AlternateHeatmaps] Scrubber overlay already loaded');
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
    log('[AlternateHeatmaps] Attempting to inject full heatmap');

    if (document.querySelector(`.funscript-heatmap-full[data-oshash="${oshash}"]`)) {
      log('[AlternateHeatmaps] Full heatmap already loaded');
      return true;
    }

    const funscriptTab = document.querySelector('[data-rb-event-key="scene-funscripts-panel"]');
    if (funscriptTab) {
      log('[AlternateHeatmaps] funscriptSceneTab detected, skipping injection');
      return true;
    }

    const sceneFileInfo = document.querySelector('.scene-file-info dl.details-list');
    if (!sceneFileInfo) {
      log('[AlternateHeatmaps] Scene file info element not found');
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
    
    // Debug: Check for any images with 'heatmap' in the src
    const allImages = document.querySelectorAll('img[src*="heatmap"]');
    console.log(`[AlternateHeatmaps] Debug: Found ${allImages.length} total images with 'heatmap' in src`);
    console.log(`[AlternateHeatmaps] Debug: Found ${heatmapImages.length} with class 'interactive-heatmap'`);

    if (heatmapImages.length > 0) {
      console.log(`[AlternateHeatmaps] Found ${heatmapImages.length} scene card heatmaps to check`);
    }

    let processedCount = 0;
    let skippedCount = 0;

    for (const img of heatmapImages) {
      // Skip if already processed or failed
      if (img.dataset.alternateProcessed === 'true') {
        skippedCount++;
        continue;
      }
      if (img.dataset.alternateProcessed === 'failed') {
        skippedCount++;
        continue;
      }

      // Extract scene ID from the src URL
      const srcMatch = img.src.match(/\/scene\/(\d+)\/interactive_heatmap/);
      if (!srcMatch) {
        console.log(`[AlternateHeatmaps] Could not extract scene ID from: ${img.src}`);
        img.dataset.alternateProcessed = 'failed';
        continue;
      }

      const sceneId = srcMatch[1];
      console.log(`[AlternateHeatmaps] Checking scene ${sceneId}...`);

      try {
        const sceneData = await FunUtil.fetchSceneData(sceneId);
        if (!sceneData || !sceneData.oshash) {
          console.log(`[AlternateHeatmaps] ✗ Scene ${sceneId}: No scene data/oshash`);
          img.dataset.alternateProcessed = 'failed';
          continue;
        }

        const url = FunUtil.getHeatmapUrl(sceneData.oshash, 'overlay', 'funUtil');
        if (!url) {
          console.log(`[AlternateHeatmaps] ✗ Scene ${sceneId}: No overlay URL`);
          img.dataset.alternateProcessed = 'failed';
          continue;
        }

        const exists = await FunUtil.heatmapExists(url);
        if (!exists) {
          console.log(`[AlternateHeatmaps] ✗ Scene ${sceneId}: Overlay does not exist at ${url}`);
          img.dataset.alternateProcessed = 'failed';
          continue;
        }

        // Replace the image source
        img.src = url;
        img.dataset.alternateProcessed = 'true';
        processedCount++;
        console.log(`[AlternateHeatmaps] ✓ Scene ${sceneId}: Replaced with overlay heatmap`);
      } catch (error) {
        console.error(`[AlternateHeatmaps] ✗ Scene ${sceneId}: Error -`, error);
        img.dataset.alternateProcessed = 'failed';
      }
    }

    if (heatmapImages.length > 0) {
      console.log(`[AlternateHeatmaps] Summary: ${processedCount} replaced, ${skippedCount} skipped, ${heatmapImages.length - processedCount - skippedCount} failed`);
    }
  }

  // ============================
  // Inject Missing Heatmaps
  // ============================

  async function injectMissingHeatmaps() {
    // Find all scene cards
    const sceneCards = document.querySelectorAll('.scene-card');
    console.log(`[AlternateHeatmaps] Checking ${sceneCards.length} scene cards for missing heatmaps`);
    
    let injectedCount = 0;

    for (const card of sceneCards) {
      // Skip if already has a heatmap
      if (card.querySelector('img.interactive-heatmap')) continue;
      if (card.dataset.heatmapInjected === 'true') continue;
      if (card.dataset.heatmapInjected === 'failed') continue;

      // Extract scene ID from the card link
      const link = card.querySelector('a.scene-card-link');
      if (!link) continue;

      const hrefMatch = link.href.match(/\/scenes\/(\d+)/);
      if (!hrefMatch) continue;

      const sceneId = hrefMatch[1];
      console.log(`[AlternateHeatmaps] Scene ${sceneId} missing heatmap, attempting to inject...`);

      try {
        const sceneData = await FunUtil.fetchSceneData(sceneId);
        if (!sceneData || !sceneData.oshash) {
          console.log(`[AlternateHeatmaps] ✗ Scene ${sceneId}: No scene data/oshash`);
          card.dataset.heatmapInjected = 'failed';
          continue;
        }

        const url = FunUtil.getHeatmapUrl(sceneData.oshash, 'overlay', 'funUtil');
        if (!url) {
          console.log(`[AlternateHeatmaps] ✗ Scene ${sceneId}: No overlay URL`);
          card.dataset.heatmapInjected = 'failed';
          continue;
        }

        const exists = await FunUtil.heatmapExists(url);
        if (!exists) {
          console.log(`[AlternateHeatmaps] ✗ Scene ${sceneId}: Overlay does not exist`);
          card.dataset.heatmapInjected = 'failed';
          continue;
        }

        // Inject heatmap image
        const previewSection = card.querySelector('.scene-card-preview');
        if (!previewSection) {
          card.dataset.heatmapInjected = 'failed';
          continue;
        }

        const heatmapImg = document.createElement('img');
        heatmapImg.className = 'interactive-heatmap';
        heatmapImg.src = url;
        heatmapImg.alt = 'interactive heatmap';
        heatmapImg.loading = 'lazy';
        heatmapImg.dataset.alternateProcessed = 'true';

        previewSection.appendChild(heatmapImg);
        card.dataset.heatmapInjected = 'true';
        injectedCount++;
        console.log(`[AlternateHeatmaps] ✓ Scene ${sceneId}: Injected overlay heatmap`);
      } catch (error) {
        console.error(`[AlternateHeatmaps] ✗ Scene ${sceneId}: Error -`, error);
        card.dataset.heatmapInjected = 'failed';
      }
    }

    if (injectedCount > 0) {
      console.log(`[AlternateHeatmaps] Injected ${injectedCount} missing heatmaps`);
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

    log('[AlternateHeatmaps] ✓ Scrubber position fix initialized');
  }

  // ============================
  // Main Injection Logic
  // ============================

  async function injectHeatmaps() {
    const urlMatch = window.location.pathname.match(/\/scenes\/(\d+)/);
    if (!urlMatch) {
      log('[AlternateHeatmaps] Not on a scene page');
      return false;
    }

    const sceneId = urlMatch[1];
    console.log(`[AlternateHeatmaps] On scene page, ID: ${sceneId}`);

    const sceneData = await FunUtil.fetchSceneData(sceneId);
    if (!sceneData || !sceneData.oshash) {
      log('[AlternateHeatmaps] No scene data or oshash');
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

  let sceneCardTimeout = null;
  function debouncedReplaceSceneCardHeatmaps() {
    if (sceneCardTimeout) clearTimeout(sceneCardTimeout);
    sceneCardTimeout = setTimeout(async () => {
      await replaceSceneCardHeatmaps();
      await injectMissingHeatmaps();
    }, 300);
  }

  function init() {
    log('[AlternateHeatmaps] Plugin initialized');

    startChecking();

    // Replace scene card heatmaps after a short delay
    setTimeout(async () => {
      await replaceSceneCardHeatmaps();
      await injectMissingHeatmaps();
    }, 1000);

    // Watch for dynamically loaded scene cards (debounced)
    const observer = new MutationObserver((mutations) => {
      // Only trigger if actual img elements were added
      const hasNewImages = mutations.some(mutation => 
        Array.from(mutation.addedNodes).some(node => 
          node.nodeType === 1 && (
            node.matches && node.matches('img.interactive-heatmap') ||
            node.querySelector && node.querySelector('img.interactive-heatmap')
          )
        )
      );
      
      if (hasNewImages) {
        log('[AlternateHeatmaps] New scene card images detected');
        debouncedReplaceSceneCardHeatmaps();
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    if (typeof PluginApi !== 'undefined') {
      PluginApi.Event.addEventListener('stash:location', () => {
        log('[AlternateHeatmaps] Navigation detected, reinitializing...');
        startChecking();
        setTimeout(async () => {
          await replaceSceneCardHeatmaps();
          await injectMissingHeatmaps();
        }, 500);
      });
    }
  }

  function waitForFunUtil(callback, maxRetries = 100) {
    let retries = 0;
    const interval = setInterval(() => {
      if (typeof window.FunUtil !== 'undefined' && window.FunUtil.waitForStashLibrary) {
        clearInterval(interval);
        log('[AlternateHeatmaps] FunUtil detected, waiting for Stash libraries...');
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
