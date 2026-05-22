/**
 * Lazy-loading utilities for heavy audio dependencies.
 *
 * WaveSurfer.js (~200KB) and HLS.js (~150KB) are the two largest
 * dependencies in the audio component. By deferring their import
 * until actually needed, we reduce the initial page load significantly.
 *
 * Usage:
 *   const { WaveSurfer } = await loadWaveSurfer();
 *   const { Hls } = await loadHls();
 */

let wavesurferCache: typeof import("wavesurfer.js") | null = null;
let hlsCache: typeof import("hls.js") | null = null;
let recordPluginCache: any = null;

/**
 * Lazy-load WaveSurfer.js with caching.
 * Only loaded when an audio player is actually rendered.
 */
export async function loadWaveSurfer(): Promise<{
	WaveSurfer: typeof import("wavesurfer.js").default;
}> {
	if (wavesurferCache) {
		return { WaveSurfer: wavesurferCache.default };
	}
	const mod = await import("wavesurfer.js");
	wavesurferCache = mod;
	return { WaveSurfer: mod.default };
}

/**
 * Lazy-load the WaveSurfer Record plugin.
 * Only needed when microphone recording is active.
 */
export async function loadRecordPlugin(): Promise<{
	RecordPlugin: any;
}> {
	if (recordPluginCache) {
		return { RecordPlugin: recordPluginCache };
	}
	const mod = await import("wavesurfer.js/dist/plugins/record.js");
	recordPluginCache = mod.default;
	return { RecordPlugin: mod.default };
}

/**
 * Lazy-load HLS.js with caching.
 * Only loaded when streaming audio playback is needed.
 */
export async function loadHls(): Promise<{
	Hls: typeof import("hls.js").default;
}> {
	if (hlsCache) {
		return { Hls: hlsCache.default };
	}
	const mod = await import("hls.js");
	hlsCache = mod;
	return { Hls: mod.default };
}

/**
 * Preload WaveSurfer.js in the background after page load.
 * Call this when you know audio will likely be needed soon
 * (e.g., when an audio component mounts with a value).
 */
export function preloadWaveSurfer(): void {
	if (!wavesurferCache) {
		import("wavesurfer.js").then((mod) => {
			wavesurferCache = mod;
		}).catch(() => {
			// Silent fail - will retry on actual use
		});
	}
}

/**
 * Preload HLS.js in the background.
 * Call this when streaming mode is detected.
 */
export function preloadHls(): void {
	if (!hlsCache) {
		import("hls.js").then((mod) => {
			hlsCache = mod;
		}).catch(() => {
			// Silent fail - will retry on actual use
		});
	}
}
