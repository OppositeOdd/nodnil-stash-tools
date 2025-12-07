declare global {
  interface Window {
    FunUtil: FunUtilAPI;
  }

  const csLib: StashLib;
  const PluginApi: PluginAPI;
}

interface StashLib {
  callGQL(params: {query: string; variables?: any}): Promise<any>;
  getConfiguration(pluginId: string, defaults: any): Promise<any>;
  callPlugin(pluginId: string, taskName: string, args: any[]): Promise<any>;
}

interface PluginAPI {
  Event: {
    addEventListener(event: string, callback: () => void): void;
  };
}

interface FunUtilAPI {
  callStashGQL(query: string, variables?: any): Promise<any>;
  getPluginConfig(pluginId: string, defaults: any): Promise<any>;
  callPythonPlugin(pluginId: string, taskName: string, args: any[]): Promise<any>;
  waitForStashLibrary(callback: () => void): void;
  fetchSceneData(sceneId: string): Promise<any>;
  getCurrentSceneId(): string | null;
  getHeatmapUrl(oshash: string, type: string, plugin: string, variantId?: string | null): string;
  getHeatmapMappingUrl(oshash: string, plugin: string): string;
  getHeatmapMapping(oshash: string, plugin: string): Promise<any>;
  heatmapExists(url: string): Promise<boolean>;
  getBasePath(videoPath: string): string;
  getDirectory(videoPath: string): string;
  version: string;
}

export {};
