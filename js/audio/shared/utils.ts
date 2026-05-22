import type WaveSurfer from "wavesurfer.js";
import { audioBufferToWav } from "./audioBufferToWav";

export interface LoadedParams {
	autoplay?: boolean;
}

export function blob_to_data_url(blob: Blob): Promise<string> {
	return new Promise((fulfill, reject) => {
		let reader = new FileReader();
		reader.onerror = reject;
		reader.onload = () => fulfill(reader.result as string);
		reader.readAsDataURL(blob);
	});
}

// --------------- Web Worker for off-main-thread audio processing ---------------
let audioWorker: Worker | null = null;
let workerSupported: boolean | null = null;

/**
 * Get or create the audio Web Worker.
 * Falls back to main-thread processing if Workers are not available.
 */
function getAudioWorker(): Worker | null {
	if (workerSupported === false) return null;
	if (audioWorker) return audioWorker;

	try {
		audioWorker = new Worker(
			new URL("./audioWorker.ts", import.meta.url),
			{ type: "module" }
		);
		workerSupported = true;
		return audioWorker;
	} catch {
		workerSupported = false;
		console.warn("Web Worker not supported, falling back to main thread audio processing");
		return null;
	}
}

/**
 * Process (trim) audio using a Web Worker to avoid blocking the main thread.
 * Falls back to synchronous processing if Workers are unavailable.
 */
export const process_audio = async (
	audioBuffer: AudioBuffer,
	start?: number,
	end?: number,
	waveform_sample_rate?: number
): Promise<Uint8Array> => {
	const sampleRate = waveform_sample_rate || audioBuffer.sampleRate;
	const numberOfChannels = audioBuffer.numberOfChannels;

	let startOffset = 0;
	let trimmedLength = audioBuffer.length;
	if (start != null && end != null) {
		startOffset = Math.round(start * sampleRate);
		const endOffset = Math.round(end * sampleRate);
		trimmedLength = endOffset - startOffset;
	}

	// Extract channel data for the trimmed region
	const channelDataArray: Float32Array[] = [];
	for (let channel = 0; channel < numberOfChannels; channel++) {
		const fullChannelData = audioBuffer.getChannelData(channel);
		const trimmedData = new Float32Array(trimmedLength);
		for (let i = 0; i < trimmedLength; i++) {
			trimmedData[i] = fullChannelData[startOffset + i];
		}
		channelDataArray.push(trimmedData);
	}

	// Try to use Web Worker for encoding
	const worker = getAudioWorker();
	if (worker) {
		return new Promise<Uint8Array>((resolve, reject) => {
			const timeout = setTimeout(() => {
				reject(new Error("Audio worker timeout"));
			}, 30000); // 30s timeout

			const handleMessage = (e: MessageEvent) => {
				if (e.data.type === "encoded") {
					clearTimeout(timeout);
					worker.removeEventListener("message", handleMessage);
					resolve(e.data.data);
				} else if (e.data.type === "error") {
					clearTimeout(timeout);
					worker.removeEventListener("message", handleMessage);
					reject(new Error(e.data.error));
				}
			};

			worker.addEventListener("message", handleMessage);
			worker.postMessage({
				type: "encode",
				channelData: channelDataArray,
				sampleRate,
				numberOfChannels,
				startSample: 0,
				endSample: trimmedLength
			});
		}).catch(() => {
			// Fallback to main thread on worker error
			return process_audio_main_thread(audioBuffer, start, end, waveform_sample_rate);
		});
	}

	// Fallback: process on main thread
	return process_audio_main_thread(audioBuffer, start, end, waveform_sample_rate);
};

/**
 * Main-thread fallback for audio processing.
 */
const process_audio_main_thread = async (
	audioBuffer: AudioBuffer,
	start?: number,
	end?: number,
	waveform_sample_rate?: number
): Promise<Uint8Array> => {
	const audioContext = new AudioContext({
		sampleRate: waveform_sample_rate || audioBuffer.sampleRate
	});
	const numberOfChannels = audioBuffer.numberOfChannels;
	const sampleRate = waveform_sample_rate || audioBuffer.sampleRate;

	let trimmedLength = audioBuffer.length;
	let startOffset = 0;
	if (start != null && end != null) {
		startOffset = Math.round(start * sampleRate);
		const endOffset = Math.round(end * sampleRate);
		trimmedLength = endOffset - startOffset;
	}

	const trimmedAudioBuffer = audioContext.createBuffer(
		numberOfChannels,
		trimmedLength,
		sampleRate
	);

	for (let channel = 0; channel < numberOfChannels; channel++) {
		const channelData = audioBuffer.getChannelData(channel);
		const trimmedData = trimmedAudioBuffer.getChannelData(channel);
		for (let i = 0; i < trimmedLength; i++) {
			trimmedData[i] = channelData[startOffset + i];
		}
	}

	return audioBufferToWav(trimmedAudioBuffer);
};

export function loaded(
	node: HTMLAudioElement,
	{ autoplay }: LoadedParams = {}
): void {
	async function handle_playback(): Promise<void> {
		if (!autoplay) return;
		node.pause();
		await node.play();
	}
}

export const skip_audio = (waveform: WaveSurfer, amount: number): void => {
	if (!waveform) return;
	waveform.skip(amount);
};

export const get_skip_rewind_amount = (
	audio_duration: number,
	skip_length?: number | null
): number => {
	if (!skip_length) {
		skip_length = 5;
	}
	return (audio_duration / 100) * skip_length || 5;
};
