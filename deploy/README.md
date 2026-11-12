# Application deployment

These changes live on `werecoder`. Keep `master` as the clean upstream mirror;
rebase `werecoder` onto upstream updates instead of mixing infra changes into it.

This fork owns its Dockerfile, runtime storage code and Kubernetes base. The
infrastructure AppCI pipeline builds the root Dockerfile for AMD64 and ARM64,
publishes the application image, and pins both the image and deploy/k8s revision
in infra. It does not use the tools-image pipeline.

The image packages committed JavaScript; it does not compile Haxe. Source changes
in src/server and the committed build/server.js implement the same storage hooks.
Runtime modules live in deploy/runtime. The build runs all test/deployment tests
against the actual Node server before publishing. Local verification:

    npm ci --omit=dev --ignore-scripts
    python3 -m unittest discover -s test/deployment -p 'test_*.py'

Completed uploads are fsynced and indexed atomically before HTTP success. Active
streams reserve their entire declared size and cannot be evicted; interruption
releases the reservation. Recovery validates completed file identity so reused
filenames cannot make partial transfers durable. The runtime index is independent
of graceful room-state checkpoints. Age retention is provided by the launcher.

Configuration is mounted at /etc/synctube/config.json and persistent data at
/app/user. HTTP_REQUEST_TIMEOUT_MS and UPLOAD_RETENTION_SECONDS must be set by
the deployment. Authentication and public routing belong to infrastructure.
