declare global {
  const FunUtil: FunUtilAPI;
  const PluginApi: PluginAPI;
}

interface FunUtilAPI {
  fetchSceneData(sceneId: string): Promise<{oshash: string}>;
  getHeatmapUrl(oshash: string, type: string, plugin: string): string;
  heatmapExists(url: string): Promise<boolean>;
  waitForStashLibrary(callback: () => void): void;
}

interface PluginAPI {
  Event: {
    addEventListener(event: string, callback: () => void): void;
  };
}

export {};
