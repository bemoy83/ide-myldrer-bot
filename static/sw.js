// Minimal service worker — enables PWA install on iOS Safari.
// No caching: the app requires a live connection to the local Ollama backend anyway.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", () => self.clients.claim());
