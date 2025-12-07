console.log('[FunUtil] ========== SCRIPT FILE EXECUTING ==========');

// @ts-check
/// <reference path="types.d.ts" />

/**
 * FunUtil - Funscript Utilities Library
 * 
 * Provides shared utilities for funscript-related Stash plugins:
 * - Funlib library (SVG generation, funscript parsing)
 * - Stash API helpers (GraphQL, Python plugin calls)
 * - Common utilities (heatmap URLs, file checking)
 */

console.log('[FunUtil] Loading Funscript Utilities Library v0.1.0');

(function() {
  'use strict';

  // Global namespace for other plugins to use
  window.FunUtil = /** @type {any} */ (window.FunUtil || {});

  // ============================
  // Stash API Helpers
  // ============================

  /**
   * Call Stash GraphQL API
   */
  async function callStashGQL(query, variables = {}) {
    try {
      const data = await csLib.callGQL({ query, variables });
      return data;
    } catch (error) {
      console.error('[FunUtil] GraphQL call failed:', error);
      throw error;
    }
  }

  /**
   * Get plugin configuration
   */
  async function getPluginConfig(pluginId, defaults = {}) {
    try {
      const config = await csLib.getConfiguration(pluginId, defaults);
      return config;
    } catch (error) {
      console.error(`[FunUtil] Failed to get config for ${pluginId}:`, error);
      return defaults;
    }
  }

  /**
   * Call a Python plugin task
   */
  async function callPythonPlugin(pluginId, taskName, args) {
    try {
      const response = await csLib.callPlugin(pluginId, taskName, args);
      return response;
    } catch (error) {
      console.error(`[FunUtil] Python plugin call failed (${pluginId}.${taskName}):`, error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Fetch scene data from Stash API
   */
  async function fetchSceneData(sceneId) {
    const query = `
      query FindScene($id: ID!) {
        findScene(id: $id) {
          files {
            path
            fingerprints {
              type
              value
            }
          }
          performers {
            id
          }
        }
      }
    `;
    try {
      const data = await callStashGQL(query, { id: sceneId });
      const files = data?.findScene?.files || [];
      if (files.length > 0) {
        const file = files[0];
        const oshash = file.fingerprints?.find((fp) => fp.type === "oshash")?.value;
        return {
          path: file.path,
          oshash: oshash?.toLowerCase()
        };
      }
    } catch (error) {
      console.error('[FunUtil] Failed to fetch scene data:', error);
    }
    return null;
  }

  /**
   * Get current scene ID from URL
   */
  function getCurrentSceneId() {
    const match = window.location.pathname.match(/\/scenes\/(\d+)/);
    return match ? match[1] : null;
  }

  // ============================
  // Heatmap Utilities
  // ============================

  /**
   * Get heatmap URL for a given oshash
   * @param {string} oshash - Scene oshash
   * @param {string} type - 'overlay' or 'full'
   * @param {string} pluginId - Plugin ID to load from (default: 'funUtil')
   * @param {string} [variantId] - Optional variant ID (e.g., 'var1', 'var2')
   */
  function getHeatmapUrl(oshash, type = 'overlay', pluginId = 'funUtil', variantId = null) {
    if (!oshash) return null;
    const suffix = type === 'full' ? '_full.svg' : '.svg';
    const variant = variantId ? `_${variantId}` : '';
    return `/plugin/${pluginId}/assets/heatmaps/${oshash}/${oshash}${variant}${suffix}`;
  }

  /**
   * Get heatmap mapping file URL
   * @param {string} oshash - Scene oshash
   * @param {string} pluginId - Plugin ID to load from (default: 'funUtil')
   */
  function getHeatmapMappingUrl(oshash, pluginId = 'funUtil') {
    if (!oshash) return null;
    return `/plugin/${pluginId}/assets/heatmaps/${oshash}/${oshash}_map.json`;
  }

  /**
   * Fetch heatmap mapping data
   * @param {string} oshash - Scene oshash
   * @param {string} pluginId - Plugin ID to load from (default: 'funUtil')
   * @returns {Promise<Object|null>} Mapping data or null if not found
   */
  async function getHeatmapMapping(oshash, pluginId = 'funUtil') {
    const url = getHeatmapMappingUrl(oshash, pluginId);
    if (!url) return null;
    
    try {
      const response = await fetch(url);
      if (!response.ok) return null;
      return await response.json();
    } catch (error) {
      console.error('[FunUtil] Error fetching heatmap mapping:', error);
      return null;
    }
  }

  /**
   * Check if heatmap exists
   */
  async function heatmapExists(url) {
    try {
      const response = await fetch(url, { method: "GET" });
      return response.ok;
    } catch {
      return false;
    }
  }

  // ============================
  // File Path Utilities
  // ============================

  /**
   * Get base path from video file path (removes extension)
   */
  function getBasePath(filePath) {
    return filePath.replace(/\.[^.]+$/, '');
  }

  /**
   * Get directory from file path
   */
  function getDirectory(filePath) {
    const lastSlash = Math.max(filePath.lastIndexOf('/'), filePath.lastIndexOf('\\'));
    return lastSlash >= 0 ? filePath.substring(0, lastSlash) : '';
  }

  // ============================
  // Wait for Stash Libraries
  // ============================

  /**
   * Wait for Stash libraries to load before executing callback
   */
  function waitForStashLibrary(callback, maxRetries = 50) {
    let retries = 0;
    const interval = setInterval(() => {
      if (typeof csLib !== 'undefined' && typeof PluginApi !== 'undefined') {
        clearInterval(interval);
        callback();
      } else if (++retries >= maxRetries) {
        clearInterval(interval);
        console.error('[FunUtil] Failed to load Stash libraries');
      }
    }, 100);
  }

  // ============================
  // Export Public API
  // ============================

  window.FunUtil = {
    // API helpers
    callStashGQL,
    getPluginConfig,
    callPythonPlugin,
    fetchSceneData,
    getCurrentSceneId,

    // Heatmap utilities
    getHeatmapUrl,
    getHeatmapMappingUrl,
    getHeatmapMapping,
    heatmapExists,

    // File utilities
    getBasePath,
    getDirectory,

    // Initialization
    waitForStashLibrary,

    // Version
    version: '0.1.0'
  };

  console.log('[FunUtil] ✓ Utilities loaded');

})();
