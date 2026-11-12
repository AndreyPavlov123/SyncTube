'use strict';
const {subscribe} = require('node:diagnostics_channel');
const timeout = Number(process.env.HTTP_REQUEST_TIMEOUT_MS);
if (!Number.isSafeInteger(timeout) || timeout <= 0 || timeout > 86400000) {
  throw new Error('HTTP_REQUEST_TIMEOUT_MS must be a positive duration up to 24 hours');
}
// The unchanged upstream bundle does not expose its http.Server. Node publishes
// that instance before request handlers run, allowing its documented public
// requestTimeout property to be configured without patching upstream functions
// or files. Keep header/inactivity limits; only the total body-read budget grows.
// Node is pinned, and a slow-body integration test exercises this exact channel.
subscribe('http.server.request.start', ({server}) => {
  server.requestTimeout = timeout;
});
