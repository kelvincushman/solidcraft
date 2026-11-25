// GE STARR Design: replaces the offline service worker (sw.js). A browser that installed the old one fetches this on
// its next update check; it takes over and unregisters itself, so the editor is always asked of TRACK (signed in).
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => { event.waitUntil(self.registration.unregister()); });
