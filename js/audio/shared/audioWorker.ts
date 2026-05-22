/**
 * Web Worker for WAV audio encoding
 *
 * Offloads the CPU-intensive audioBufferToWav conversion off the main thread,
 * preventing UI jank during audio processing (e.g., trimming operations).
 *
 * Usage:
 *   const worker = new Worker(new URL('./audioWorker.ts', import.meta.url), { type: 'module' });
 *   worker.postMessage({ type: 'encode', audioData: float32Array, sampleRate, numberOfChannels });
 *   worker.onmessage = (e) => { const wavData = e.data; };
 */

const NUM_HEADER_BYTES = 44;

function writeString(view: DataView, offset: number, string: string): void {
	for (let i = 0; i < string.length; i++) {
		view.setUint8(offset + i, string.charCodeAt(i));
	}
}

function encodeWav(
	channelData: Float32Array[],
	sampleRate: number,
	numberOfChannels: number,
	startSample: number,
	endSample: number
): Uint8Array {
	const length = endSample - startSample;
	const bufferLength = length * numberOfChannels * 2 + NUM_HEADER_BYTES;
	const buffer = new ArrayBuffer(bufferLength);
	const view = new DataView(buffer);
	let offset = 0;

	// Write WAV header
	writeString(view, offset, "RIFF");
	offset += 4;
	view.setUint32(offset, bufferLength - 8, true);
	offset += 4;
	writeString(view, offset, "WAVE");
	offset += 4;
	writeString(view, offset, "fmt ");
	offset += 4;
	view.setUint32(offset, 16, true);
	offset += 4; // Sub-chunk size, 16 for PCM
	view.setUint16(offset, 1, true);
	offset += 2; // PCM format
	view.setUint16(offset, numberOfChannels, true);
	offset += 2;
	view.setUint32(offset, sampleRate, true);
	offset += 4;
	view.setUint32(offset, sampleRate * 2 * numberOfChannels, true);
	offset += 4;
	view.setUint16(offset, numberOfChannels * 2, true);
	offset += 2;
	view.setUint16(offset, 16, true);
	offset += 2;
	writeString(view, offset, "data");
	offset += 4;
	view.setUint32(offset, length * numberOfChannels * 2, true);
	offset += 4;

	// Write PCM audio data
	for (let i = startSample; i < endSample; i++) {
		for (let channel = 0; channel < numberOfChannels; channel++) {
			const sample = Math.max(
				-1,
				Math.min(1, channelData[channel][i])
			);
			view.setInt16(offset, sample * 0x7fff, true);
			offset += 2;
		}
	}

	return new Uint8Array(buffer);
}

// Listen for messages from the main thread
self.onmessage = function (e: MessageEvent) {
	const { type, channelData, sampleRate, numberOfChannels, startSample, endSample } = e.data;

	if (type === "encode") {
		try {
			const result = encodeWav(
				channelData,
				sampleRate,
				numberOfChannels,
				startSample || 0,
				endSample || channelData[0].length
			);
			self.postMessage({ type: "encoded", data: result }, [result.buffer] as any);
		} catch (error: any) {
			self.postMessage({ type: "error", error: error.message });
		}
	}

	if (type === "encodeChunk") {
		// For streaming: encode a single WAV chunk with header
		try {
			const { payload, header } = e.data;
			// Just assemble header + payload for streaming
			const result = new Uint8Array(header.length + payload.length);
			result.set(header, 0);
			result.set(payload, header.length);
			self.postMessage({ type: "chunkEncoded", data: result }, [result.buffer] as any);
		} catch (error: any) {
			self.postMessage({ type: "error", error: error.message });
		}
	}
};

export {};
