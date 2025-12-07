// @ts-check
/// <reference path="types.d.ts" />

/**
 * Funscript Scene Tab - Add custom tab to scene pages
 *
 * Displays:
 * - Full heatmap image
 * - Funscript metadata
 * - Stats table (actions, duration, speeds per axis)
 *
 * Depends on: FunUtil, alternateHeatmaps
 */

console.log('[FunscriptSceneTab] Loading plugin v0.1.0');

(function() {
  'use strict';

  const CHECK_INTERVAL = 500;
  const MAX_RETRIES = 20;
  let retryCount = 0;
  let checkTimer = null;

  // ============================
  // Heatmap Check
  // ============================

  async function checkHeatmapExists() {
    const urlMatch = window.location.pathname.match(/\/scenes\/(\d+)/);
    if (!urlMatch) return false;

    const sceneId = urlMatch[1];
    const sceneData = await FunUtil.fetchSceneData(sceneId);

    if (!sceneData || !sceneData.oshash) return false;

    const fullUrl = FunUtil.getHeatmapUrl(sceneData.oshash, 'full', 'funUtil');
    if (!fullUrl) return false;

    const exists = await FunUtil.heatmapExists(fullUrl);
    console.log(`[FunscriptSceneTab] Heatmap exists for scene ${sceneId}: ${exists}`);
    return exists;
  }

  // ============================
  // Tab Creation
  // ============================

  async function injectFunscriptsTab() {
    // Only run on individual scene detail pages, not on /scenes list page
    const urlMatch = window.location.pathname.match(/^\/scenes\/(\d+)$/);
    if (!urlMatch) {
      return false;
    }

    const navTabs = document.querySelector('.scene-tabs .mr-auto.nav.nav-tabs[role="tablist"]');
    if (!navTabs) {
      return false;
    }

    const existingTab = document.querySelector('[data-rb-event-key="scene-funscripts-panel"]');
    if (existingTab) {
      return true;
    }

    const heatmapExists = await checkHeatmapExists();
    if (!heatmapExists) {
      console.log('[FunscriptSceneTab] No heatmap available, skipping tab injection');
      return false;
    }

    const tabItem = document.createElement('div');
    tabItem.className = 'nav-item';

    const tabLink = document.createElement('a');
    tabLink.href = '#';
    tabLink.role = 'tab';
    tabLink.setAttribute('data-rb-event-key', 'scene-funscripts-panel');
    tabLink.setAttribute('aria-selected', 'false');
    tabLink.className = 'nav-link';
    tabLink.textContent = 'Funscripts';

    tabLink.addEventListener('click', (e) => {
      e.preventDefault();

      navTabs.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        link.setAttribute('aria-selected', 'false');
      });

      tabLink.classList.add('active');
      tabLink.setAttribute('aria-selected', 'true');

      showFunscriptsPanel();
    });

    tabItem.appendChild(tabLink);

    const editTab = navTabs.querySelector('[data-rb-event-key="scene-edit-panel"]');
    if (editTab && editTab.parentElement) {
      navTabs.insertBefore(tabItem, editTab.parentElement);
    } else {
      navTabs.appendChild(tabItem);
    }

    navTabs.querySelectorAll('.nav-link:not([data-rb-event-key="scene-funscripts-panel"])').forEach(otherTab => {
      otherTab.addEventListener('click', () => {
        tabLink.classList.remove('active');
        tabLink.setAttribute('aria-selected', 'false');

        // Hide funscripts panel when other tabs are clicked
        const funscriptsPanel = document.querySelector('#scene-funscripts-panel');
        if (funscriptsPanel) {
          funscriptsPanel.classList.remove('active', 'show');
        }
      });
    });

    console.log('[FunscriptSceneTab] ✓ Funscripts tab injected');
    return true;
  }

  // ============================
  // StashInteractiveTools Detection
  // ============================

  let controlsObserver = null;
  let isUpdatingControls = false;

  function isStashInteractiveToolsInstalled() {
    // Check if the plugin's CSS class is present in the DOM
    return document.querySelector('.stash-interactive-tools') !== null;
  }

  function cloneInteractiveControls(panel) {
    // Wait for StashInteractiveTools to inject its controls into File Info
    const fileInfoPanel = document.querySelector('.scene-file-info.stash-interactive-tools');
    if (!fileInfoPanel) {
      console.log('[FunscriptSceneTab] StashInteractiveTools not found in file info panel');
      return;
    }

    // Remove existing controls container to refresh
    let controlsContainer = panel.querySelector('.funscripts-interactive-controls');
    if (controlsContainer) {
      controlsContainer.remove();
    }

    // Look for the interactive controls (script selector, stroke, sync)
    const scriptLabel = fileInfoPanel.querySelector('#stash-interactive-tools-label-funscripts');
    const strokeLabel = Array.from(fileInfoPanel.querySelectorAll('dt')).find(dt => 
      dt.textContent.includes('Stroke:')
    );
    const syncLabel = Array.from(fileInfoPanel.querySelectorAll('dt')).find(dt => 
      dt.textContent.includes('Sync:')
    );

    // If controls aren't rendered yet, wait and try again
    if (!scriptLabel && !strokeLabel && !syncLabel) {
      setTimeout(() => cloneInteractiveControls(panel), 200);
      return;
    }

    // Create container
    controlsContainer = document.createElement('div');
    controlsContainer.className = 'funscripts-interactive-controls';
    controlsContainer.style.padding = '20px';
    controlsContainer.style.borderTop = '1px solid var(--border-color)';
    controlsContainer.style.background = 'rgba(255, 255, 255, 0.02)';

    const dl = document.createElement('dl');
    dl.className = 'scene-file-info';

    // Clone each control group (label + control)
    if (scriptLabel) {
      const clonedLabel = scriptLabel.cloneNode(true);
      const scriptControl = scriptLabel.nextElementSibling;
      if (scriptControl && scriptControl.tagName === 'DD') {
        const clonedControl = scriptControl.cloneNode(true);
        dl.appendChild(clonedLabel);
        dl.appendChild(clonedControl);

        // Copy event listeners by getting the select element and setting up onChange
        const originalSelect = scriptControl.querySelector('select');
        const clonedSelect = clonedControl.querySelector('select');
        if (originalSelect && clonedSelect) {
          clonedSelect.addEventListener('change', (e) => {
            isUpdatingControls = true;
            originalSelect.value = e.target.value;
            originalSelect.dispatchEvent(new Event('change', { bubbles: true }));
            setTimeout(() => { isUpdatingControls = false; }, 200);
          });
        }
      }
    }

    if (strokeLabel) {
      const clonedLabel = strokeLabel.cloneNode(true);
      const strokeControl = strokeLabel.nextElementSibling;
      if (strokeControl && strokeControl.tagName === 'DD') {
        const clonedControl = strokeControl.cloneNode(true);
        dl.appendChild(clonedLabel);
        dl.appendChild(clonedControl);

        const originalInputs = strokeControl.querySelectorAll('input[type="range"]');
        const clonedInputs = clonedControl.querySelectorAll('input[type="range"]');
        originalInputs.forEach((original, index) => {
          const cloned = clonedInputs[index];
          if (cloned) {
            cloned.addEventListener('input', (e) => {
              isUpdatingControls = true;
              original.value = e.target.value;
              original.dispatchEvent(new Event('input', { bubbles: true }));
              setTimeout(() => { isUpdatingControls = false; }, 200);
            });
            cloned.addEventListener('change', (e) => {
              isUpdatingControls = true;
              original.value = e.target.value;
              original.dispatchEvent(new Event('change', { bubbles: true }));
              setTimeout(() => { isUpdatingControls = false; }, 200);
            });
          }
        });
      }
    }

    if (syncLabel) {
      const clonedLabel = syncLabel.cloneNode(true);
      const syncControl = syncLabel.nextElementSibling;
      if (syncControl && syncControl.tagName === 'DD') {
        const clonedControl = syncControl.cloneNode(true);
        dl.appendChild(clonedLabel);
        dl.appendChild(clonedControl);

        // Copy event listeners for sync slider
        const originalInput = syncControl.querySelector('input[type="range"]');
        const clonedInput = clonedControl.querySelector('input[type="range"]');
        if (originalInput && clonedInput) {
          clonedInput.addEventListener('input', (e) => {
            isUpdatingControls = true;
            originalInput.value = e.target.value;
            originalInput.dispatchEvent(new Event('input', { bubbles: true }));
            setTimeout(() => { isUpdatingControls = false; }, 200);
          });
          clonedInput.addEventListener('change', (e) => {
            isUpdatingControls = true;
            originalInput.value = e.target.value;
            originalInput.dispatchEvent(new Event('change', { bubbles: true }));
            setTimeout(() => { isUpdatingControls = false; }, 200);
          });
        }
      }
    }

    controlsContainer.appendChild(dl);
    
    // Insert after the heatmap image
    const heatmapImg = panel.querySelector('.full-heatmap-image');
    if (heatmapImg && heatmapImg.parentNode) {
      heatmapImg.parentNode.insertBefore(controlsContainer, heatmapImg.nextSibling);
    } else {
      const panelContent = panel.querySelector('.funscripts-panel-content');
      if (panelContent) {
        panelContent.appendChild(controlsContainer);
      }
    }

    console.log('[FunscriptSceneTab] Cloned interactive controls to Funscripts tab');
  }

  function setupControlsObserver(panel) {
    // Clean up existing observer
    if (controlsObserver) {
      controlsObserver.disconnect();
    }

    const fileInfoPanel = document.querySelector('.scene-file-info.stash-interactive-tools');
    if (!fileInfoPanel) return;

    // Watch for changes in the File Info panel
    controlsObserver = new MutationObserver((mutations) => {
      // Skip if we're programmatically updating controls
      if (isUpdatingControls) return;
      
      // Check if the script selector or other controls were modified
      const hasRelevantChanges = mutations.some(mutation => {
        return mutation.target.id === 'stash-interactive-tools-select-funscripts' ||
               mutation.target.querySelector('#stash-interactive-tools-select-funscripts') ||
               (mutation.addedNodes.length > 0 && Array.from(mutation.addedNodes).some(node => 
                 node.nodeType === 1 && (node.id === 'stash-interactive-tools-select-funscripts' || 
                 node.querySelector && node.querySelector('#stash-interactive-tools-select-funscripts'))
               ));
      });

      if (hasRelevantChanges) {
        console.log('[FunscriptSceneTab] File Info controls changed, re-cloning...');
        setTimeout(() => cloneInteractiveControls(panel), 100);
      }
    });

    controlsObserver.observe(fileInfoPanel, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['value']
    });

    console.log('[FunscriptSceneTab] Set up MutationObserver for controls');
  }

  // ============================
  // Panel Display
  // ============================

  function showFunscriptsPanel() {
    const sceneTabs = document.querySelector('.scene-tabs');
    if (!sceneTabs) return;

    // Hide all panels within scene-tabs
    const allPanels = sceneTabs.querySelectorAll('.tab-content > .tab-pane');
    allPanels.forEach(panel => {
      panel.classList.remove('active', 'show');
    });

    // Check for existing panel within scene-tabs only
    const tabContent = sceneTabs.querySelector('.tab-content');
    if (!tabContent) return;

    let funscriptsPanel = tabContent.querySelector('#scene-funscripts-panel');

    if (!funscriptsPanel) {
      funscriptsPanel = document.createElement('div');
      funscriptsPanel.id = 'scene-funscripts-panel';
      funscriptsPanel.className = 'tab-pane';
      funscriptsPanel.role = 'tabpanel';
      funscriptsPanel.innerHTML = `
        <div class="funscripts-panel-content" style="padding: 20px;">
          <p>Loading funscript data...</p>
        </div>
      `;

      tabContent.appendChild(funscriptsPanel);
      loadFunscriptData(funscriptsPanel);

      // Clone StashInteractiveTools controls if installed
      if (isStashInteractiveToolsInstalled()) {
        console.log('[FunscriptSceneTab] StashInteractiveTools detected, cloning controls...');
        // Wait for the heatmap to load and StashInteractiveTools to inject
        setTimeout(() => {
          cloneInteractiveControls(funscriptsPanel);
          setupControlsObserver(funscriptsPanel);
        }, 1000);
      }
    }

    funscriptsPanel.classList.add('active', 'show');
  }

  // ============================
  // Data Loading
  // ============================

  async function loadFunscriptData(panel) {
    const urlMatch = window.location.pathname.match(/\/scenes\/(\d+)/);
    if (!urlMatch) {
      panel.innerHTML = '<div class="funscripts-panel-content" style="padding: 20px;"><p>Unable to determine scene ID</p></div>';
      return;
    }

    const sceneId = urlMatch[1];
    const sceneData = await FunUtil.fetchSceneData(sceneId);

    if (!sceneData || !sceneData.oshash) {
      panel.innerHTML = '<div class="funscripts-panel-content" style="padding: 20px;"><p>No funscript data available</p></div>';
      return;
    }

    const fullUrl = FunUtil.getHeatmapUrl(sceneData.oshash, 'full', 'funUtil');
    const fullExists = await FunUtil.heatmapExists(fullUrl);

    if (!fullExists) {
      panel.innerHTML = `
        <div class="funscripts-panel-content" style="padding: 20px;">
          <p>No heatmap available for this scene.</p>
          <p>Run <strong>Generate Heatmaps</strong> from the <strong>alternateHeatmaps</strong> plugin to generate heatmaps.</p>
        </div>
      `;
      return;
    }

    // Parse stats from SVG (if available)
    const axisData = await parseFunscriptStatsFromSVG(fullUrl);
    let tableHTML = '';
    if (axisData && axisData.length > 0) {
      tableHTML = `
        <div style="padding: 20px; overflow-x: auto;">
          <h4 style="margin-bottom: 15px;">Funscript Statistics</h4>
          <table class="funscript-stats-table">
            <thead>
              <tr>
                <th>Axis</th>
                <th>Duration</th>
                <th>Actions</th>
                <th>Max Speed</th>
                <th>Avg Speed</th>
              </tr>
            </thead>
            <tbody>
              ${axisData.map((data, index) => `
                <tr class="${index % 2 === 0 ? 'even' : 'odd'}">
                  <td class="axis-name">${data.axis}</td>
                  <td>${data.Duration || '-'}</td>
                  <td>${data.Actions || '-'}</td>
                  <td>${data.MaxSpeed || '-'}</td>
                  <td>${data.AvgSpeed || '-'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    panel.innerHTML = `
      <div class="funscripts-panel-content">
        <img src="${fullUrl}" alt="Full Funscript Heatmap" class="full-heatmap-image" id="heatmap-img-${sceneId}"/>
        ${tableHTML}
      </div>
      <div class="heatmap-lightbox" id="heatmap-lightbox-${sceneId}">
        <div class="heatmap-lightbox-content">
          <span class="heatmap-lightbox-close" id="heatmap-close-${sceneId}">&times;</span>
          <img src="${fullUrl}" alt="Full Funscript Heatmap" class="heatmap-lightbox-image"/>
        </div>
      </div>
    `;

    // Add lightbox functionality
    const heatmapImg = document.getElementById(`heatmap-img-${sceneId}`);
    const lightbox = document.getElementById(`heatmap-lightbox-${sceneId}`);
    const closeBtn = document.getElementById(`heatmap-close-${sceneId}`);

    if (heatmapImg && lightbox && closeBtn) {
      heatmapImg.addEventListener('click', () => {
        lightbox.classList.add('active');
      });

      closeBtn.addEventListener('click', () => {
        lightbox.classList.remove('active');
      });

      lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox) {
          lightbox.classList.remove('active');
        }
      });

      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && lightbox.classList.contains('active')) {
          lightbox.classList.remove('active');
        }
      });
    }
  }

  // ============================
  // Stats Parsing
  // ============================

  async function parseFunscriptStatsFromSVG(svgUrl) {
    try {
      const response = await fetch(svgUrl);
      if (!response.ok) return null;

      const svgText = await response.text();
      const parser = new DOMParser();
      const svgDoc = parser.parseFromString(svgText, 'image/svg+xml');

      const axisGroups = svgDoc.querySelectorAll('g[transform^="translate"]');
      const axisData = [];

      axisGroups.forEach(group => {
        const axisText = group.querySelector('text.funsvg-axis');
        if (!axisText) return;
        const axis = axisText.textContent.trim();

        const statLabels = Array.from(group.querySelectorAll('text.funsvg-stat-label'));
        const statValues = Array.from(group.querySelectorAll('text.funsvg-stat-value'));

        const stats = {
          axis: axis
        };

        statLabels.forEach((label, index) => {
          const labelText = label.textContent.trim();
          const valueText = statValues[index] ? statValues[index].textContent.trim() : '-';
          stats[labelText] = valueText;
        });

        axisData.push(stats);
      });

      return axisData.length > 0 ? axisData : null;
    } catch (error) {
      console.error('[FunscriptSceneTab] Error parsing stats:', error);
      return null;
    }
  }

  // ============================
  // Retry Logic
  // ============================

  function startChecking() {
    // Only run on scene detail pages
    const urlMatch = window.location.pathname.match(/^\/scenes\/(\d+)$/);
    if (!urlMatch) {
      return;
    }

    if (checkTimer) clearInterval(checkTimer);

    retryCount = 0;
    checkTimer = setInterval(async () => {
      const success = await injectFunscriptsTab();

      if (success || retryCount >= MAX_RETRIES) {
        clearInterval(checkTimer);
        checkTimer = null;
        if (!success && retryCount >= MAX_RETRIES) {
          console.log('[FunscriptSceneTab] Max retries reached, no heatmap found');
        }
      }

      retryCount++;
    }, CHECK_INTERVAL);
  }

  // ============================
  // Initialization
  // ============================

  function init() {
    console.log('[FunscriptSceneTab] Plugin initialized');

    startChecking();

    if (typeof PluginApi !== 'undefined') {
      PluginApi.Event.addEventListener('stash:location', () => {
        console.log('[FunscriptSceneTab] Navigation detected, reinitializing...');
        startChecking();
      });
    }
  }

  function waitForFunUtil(callback, maxRetries = 100) {
    let retries = 0;
    const interval = setInterval(() => {
      if (typeof window.FunUtil !== 'undefined' && window.FunUtil.waitForStashLibrary) {
        clearInterval(interval);
        console.log('[FunscriptSceneTab] FunUtil detected, waiting for Stash libraries...');
        window.FunUtil.waitForStashLibrary(callback);
      } else if (++retries >= maxRetries) {
        clearInterval(interval);
        console.error('[FunscriptSceneTab] Failed to load FunUtil dependency after ' + (maxRetries * 100) + 'ms');
        console.error('[FunscriptSceneTab] window.FunUtil =', typeof window.FunUtil);
        console.error('[FunscriptSceneTab] Make sure funUtil plugin is enabled and loaded');
      }
    }, 100);
  }

  waitForFunUtil(init);

})();
