export default [
  {
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: "script",
      globals: {
        FunUtil: "readonly",
        PluginApi: "readonly",
        console: "readonly",
        document: "readonly",
        window: "readonly",
        setTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        fetch: "readonly",
        DOMParser: "readonly",
        Element: "readonly",
        HTMLElement: "readonly"
      }
    },
    rules: {
      "no-unused-vars": "warn",
      "no-undef": "error"
    }
  }
];
