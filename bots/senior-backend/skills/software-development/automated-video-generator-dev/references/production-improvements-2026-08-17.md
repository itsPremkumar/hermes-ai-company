/**
 * production-improvements-2026-08-17.md
 * Production-grade improvements added 2026-08-17.
 *
 * 1. NASA c:\ local-path download bug
 *    - File: src/lib/free-image/providers/nasa.ts
 *    - NASA API sometimes returns local Windows paths (c:\...) as fallback URLs
 *    - These fail the SSRF guard downstream with confusing error
 *    - Fix: validate http(s) only, skip local paths
 *
 * 2. Per-stage timebox (ACQUIRE_TIMEBOX_MS)
 *    - File: src/agentic/orchestrator/pipeline.ts
 *    - Default 120s — prevents pipeline wedging on slow downloads
 *    - Override: ACQUIRE_TIMEBOX_MS env var
 *    - On timeout: proceeds with empty candidates, gate blocks gracefully
 *
 * 3. Retry-After header respect
 *    - File: src/agentic/operations/retry.ts, src/lib/visual-fetcher/download.ts
 *    - Honors Retry-After headers on 429/503 responses
 *    - getRetryAfterMs() extracts delay from response headers
 *    - Overrides exponential backoff when header present
 *
 * 4. Blackdetect fix
 *    - File: src/agentic/media/video-analyzer.ts
 *    - -v error loglevel suppresses blackdetect detection lines
 *    - Changed to -v info (detection lines emitted at info level)
 *    - Removed over-aggressive guard clause that filtered true positives
 *
 * 5. Offline fallback wiring
 *    - File: src/agentic/orchestrator/pipeline.ts
 *    - When gate fails due to missing visuals AND bundled assets exist:
 *      a. Generate voiceovers for offline plan
 *      b. Build manifest for offline plan
 *      c. Render with bundled assets via renderAgenticSlideshow
 *    - Returns result with offlineFallback: true flag
 *
 * 6. Production health check
 *    - File: src/adapters/http/setup-controller.ts
 *    - GET /health returns:
 *      - system: platform, arch, nodeVersion, uptimeSec, memory, diskFreeGB, ffmpegVersion
 *      - offline: available, bundledImages, bundledVideos, bundledMusic
 *
 * 7. GPU auto-detect
 *    - File: src/shared/system-probe.ts
 *    - probeSystem() detects NVENC/QSV/AMF/MF hardware encoders
 *    - Returns optimalConcurrency and optimalQuality based on hardware
 *
 * 8. Output cleanup
 *    - File: src/agentic/management/output-cleanup.ts
 *    - cleanupOutput() removes old renders
 *    - Keeps 5 most recent per config, removes files older than 7 days
 *    - cleanupPreview() shows what would be removed
 */
