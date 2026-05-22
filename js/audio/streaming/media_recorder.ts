import type { IMediaRecorderConstructor } from "extendable-media-recorder";

let media_recorder_initialized = false;
let media_recorder: IMediaRecorderConstructor;

/**
 * Initialize the extendable MediaRecorder with WAV encoder.
 * Uses dynamic imports so the media-recorder packages are only
 * loaded when streaming is actually needed.
 */
export async function init_media_recorder(): Promise<IMediaRecorderConstructor> {
	if (media_recorder_initialized && media_recorder) {
		return media_recorder;
	}

	const { MediaRecorder, register } = await import("extendable-media-recorder");
	const { connect } = await import("extendable-media-recorder-wav-encoder");

	register(await connect());
	media_recorder_initialized = true;
	media_recorder = MediaRecorder;
	return media_recorder;
}

/**
 * Assemble a WAV blob from header + payload chunks using a Web Worker.
 * Falls back to main-thread assembly if the worker is unavailable.
 */
export async function assembleWavBlob(
	header: Uint8Array,
	chunks: Uint8Array[],
	payload: Uint8Array
): Promise<Blob> {
	// Calculate total size
	const totalSize = header.length + chunks.reduce((sum, c) => sum + c.length, 0) + payload.length;

	// Try Web Worker for large payloads (> 1MB)
	if (totalSize > 1 * 1024 * 1024) {
		try {
			const result = await assembleWavBlobWithWorker(header, chunks, payload);
			return result;
		} catch {
			// Fall through to main thread
		}
	}

	// Main-thread assembly for small payloads
	const blobParts = [header, ...chunks, payload];
	return new Blob(blobParts, { type: "audio/wav" });
}

function assembleWavBlobWithWorker(
	header: Uint8Array,
	chunks: Uint8Array[],
	payload: Uint8Array
): Promise<Blob> {
	return new Promise((resolve, reject) => {
		try {
			const worker = new Worker(
				new URL("../shared/audioWorker.ts", import.meta.url),
				{ type: "module" }
			);

			const timeout = setTimeout(() => {
				worker.terminate();
				reject(new Error("Worker assembly timeout"));
			}, 15000);

			worker.onmessage = (e: MessageEvent) => {
				clearTimeout(timeout);
				worker.terminate();
				if (e.data.type === "chunkEncoded") {
					resolve(new Blob([e.data.data], { type: "audio/wav" }));
				} else if (e.data.type === "error") {
					reject(new Error(e.data.error));
				}
			};

			worker.onerror = (e) => {
				clearTimeout(timeout);
				worker.terminate();
				reject(e);
			};

			// Combine all parts into a single payload for the worker
			const allPayload = new Uint8Array(
				chunks.reduce((sum, c) => sum + c.length, 0) + payload.length
			);
			let offset = 0;
			for (const chunk of chunks) {
				allPayload.set(chunk, offset);
				offset += chunk.length;
			}
			allPayload.set(payload, offset);

			worker.postMessage({
				type: "encodeChunk",
				header,
				payload: allPayload
			});
		} catch {
			// Fallback
			const blobParts = [header, ...chunks, payload];
			resolve(new Blob(blobParts, { type: "audio/wav" }));
		}
	});
}
