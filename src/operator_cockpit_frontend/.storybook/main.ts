import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  framework: { name: "@storybook/react-vite", options: {} },
  stories: ["../src/foundation.stories.tsx"],
  staticDirs: ["../public"],
  core: { disableTelemetry: true },
  // Stories are fixture-only: drop the app's loopback /api dev proxy so a request can never
  // reach a real backend even if MSW were bypassed.
  viteFinal: async (viteConfig) => ({
    ...viteConfig,
    server: { ...viteConfig.server, proxy: undefined },
  }),
};

export default config;
