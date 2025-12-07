// Type definitions for alternateHeatmaps.js

export interface FunUtilAPI {
  fetchSceneData(sceneId: string): Promise<any>;
  getHeatmapUrl(oshash: string, type: string, plugin: string): string;
  heatmapExists(url: string): Promise<boolean>;
  waitForStashLibrary(callback: () => void): void;
}

export interface PluginAPIEvent {
  addEventListener(event: string, callback: () => void): void;
}

export interface PluginAPI {
  Event: PluginAPIEvent;
}

declare global {
  const FunUtil: FunUtilAPI;
  const PluginApi: PluginAPI;
}
