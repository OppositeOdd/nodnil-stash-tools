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
  let useStashInteractiveTools = false;

  // ============================
  // StashInteractiveTools Detection
  // ============================

  function checkStashInteractiveToolsPresent() {
    const interactiveTab = document.querySelector('[data-rb-event-key="scene-interactive-panel"]');
    return !!interactiveTab;
  }

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
    const urlMatch = window.location.pathname.match(/^\/scenes\/(\d+)$/);
    if (!urlMatch) {
      return false;
    }

    // Check if StashInteractiveTools is present
    useStashInteractiveTools = checkStashInteractiveToolsPresent();

    if (useStashInteractiveTools) {
      console.log('[FunscriptSceneTab] StashInteractiveTools detected, will inject into Interactive tab');
      // Don't create a separate tab, content will be injected into Interactive tab
      return true;
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
  // Panel Display
  // ============================

  function showFunscriptsPanel() {
    const sceneTabs = document.querySelector('.scene-tabs');
    if (!sceneTabs) return;

    const allPanels = sceneTabs.querySelectorAll('.tab-content > .tab-pane');
    allPanels.forEach(panel => {
      panel.classList.remove('active', 'show');
    });

    const tabContent = sceneTabs.querySelector('.tab-content');
    if (!tabContent) return;

    let funscriptsPanel;

    if (useStashInteractiveTools) {
      const interactivePanel = tabContent.querySelector('.stash-interactive-tools-tab');
      if (!interactivePanel) {
        console.error('[FunscriptSceneTab] Interactive panel not found');
        return;
      }

      funscriptsPanel = interactivePanel.querySelector('#funscripts-content-wrapper');
      if (!funscriptsPanel) {
        funscriptsPanel = document.createElement('div');
        funscriptsPanel.id = 'funscripts-content-wrapper';
        funscriptsPanel.className = 'funscripts-panel-content';
        interactivePanel.appendChild(funscriptsPanel);
        loadFunscriptData(funscriptsPanel);
      }

      interactivePanel.classList.add('active', 'show');
    } else {
      funscriptsPanel = tabContent.querySelector('#scene-funscripts-panel');

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
      }

      funscriptsPanel.classList.add('active', 'show');
    }
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

  let tabListenerAttached = false;

  function setupInteractiveTabListener() {
    if (tabListenerAttached) return;

    const interactiveTabLink = document.querySelector('[data-rb-event-key="scene-interactive-panel"].nav-link');
    if (!interactiveTabLink) {
      console.log('[FunscriptSceneTab] Interactive tab link not found yet, will retry');
      return;
    }

    console.log('[FunscriptSceneTab] Attaching click listener to Interactive tab');
    interactiveTabLink.addEventListener('click', async () => {
      console.log('[FunscriptSceneTab] Interactive tab clicked');
      await new Promise(resolve => setTimeout(resolve, 150));

      const heatmapExists = await checkHeatmapExists();
      if (!heatmapExists) {
        console.log('[FunscriptSceneTab] No heatmap available for this scene');
        return;
      }

      const interactivePanel = document.querySelector('.scene-tabs .tab-content .stash-interactive-tools-tab');
      if (!interactivePanel) {
        console.error('[FunscriptSceneTab] Interactive panel not found in tab-content');
        return;
      }

      const funscriptsWrapper = interactivePanel.querySelector('#funscripts-content-wrapper');
      if (!funscriptsWrapper) {
        console.log('[FunscriptSceneTab] Injecting funscript content into Interactive tab');
        showFunscriptsPanel();
      } else {
        console.log('[FunscriptSceneTab] Funscript content already present');
      }
    });

    tabListenerAttached = true;
  }

  function init() {
    console.log('[FunscriptSceneTab] Plugin initialized');

    startChecking();

    if (typeof PluginApi !== 'undefined') {
      PluginApi.Event.addEventListener('stash:location', () => {
        console.log('[FunscriptSceneTab] Navigation detected, reinitializing...');
        tabListenerAttached = false; // Reset listener flag on navigation
        startChecking();
      });
    }

    if (checkStashInteractiveToolsPresent()) {
      console.log('[FunscriptSceneTab] Setting up Interactive tab listener');

      setTimeout(setupInteractiveTabListener, 500);
      setTimeout(setupInteractiveTabListener, 1000);
      setTimeout(setupInteractiveTabListener, 2000);
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
