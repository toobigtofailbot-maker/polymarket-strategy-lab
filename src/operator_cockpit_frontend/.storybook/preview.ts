import { definePreview } from "@storybook/react-vite";
import { http, HttpResponse } from "msw";
import { setupWorker } from "msw/browser";
import addonMsw from "msw-storybook-addon";
import "../src/styles.css";

// Initial handlers survive the addon's per-story reset. Story handlers added with msw.use()
// take precedence; any /api request a story did not mock gets this deterministic closed error
// and never leaves the browser.
const unmockedApi = http.all("/api/*", () =>
  HttpResponse.json({ error: { code: "INTERNAL_ERROR" } }, { status: 500 }),
);

export default definePreview({
  addons: [
    addonMsw(async () => {
      const worker = setupWorker(unmockedApi);
      await worker.start({
        quiet: true,
        onUnhandledRequest(request, print) {
          if (new URL(request.url).pathname.startsWith("/api/")) print.error();
        },
      });
      return worker;
    }),
  ],
  parameters: { layout: "fullscreen" },
});
