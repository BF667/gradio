<script lang="ts">
	import { onMount, untrack } from "svelte";
	import { Music } from "@gradio/icons";
	import { format_time, type I18nFormatter } from "@gradio/utils";
	import { skip_audio, process_audio } from "../shared/utils";
	import WaveformControls from "../shared/WaveformControls.svelte";
	import { Empty } from "@gradio/atoms";
	import type { FileData } from "@gradio/client";
	import type { WaveformOptions, SubtitleData } from "../shared/types";
	import { loadWaveSurfer, loadHls, preloadWaveSurfer, preloadHls } from "../shared/lazy";

	type WaveSurferType = typeof import("wavesurfer.js").default;
	type HlsType = typeof import("hls.js").default;

	let {
		value = null,
		subtitles = null,
		label,
		i18n,
		dispatch_blob = () => Promise.resolve(),
		interactive = false,
		editable = true,
		trim_region_settings = {},
		waveform_settings,
		waveform_options,
		mode = $bindable(),
		loop,
		handle_reset_value = () => {},
		playback_position = $bindable(),
		onstop,
		onplay,
		onpause,
		onedit,
		onload
	}: {
		value?: null | FileData;
		subtitles?: null | string | SubtitleData[];
		label: string;
		i18n: I18nFormatter;
		dispatch_blob?: (
			blobs: Uint8Array[] | Blob[],
			event: "stream" | "change" | "stop_recording"
		) => Promise<void>;
		interactive?: boolean;
		editable?: boolean;
		trim_region_settings?: Record<string, any>;
		waveform_settings: Record<string, any>;
		waveform_options: WaveformOptions;
		mode?: string;
		loop?: boolean;
		handle_reset_value?: () => void;
		playback_position?: number;
		onstop?: () => void;
		onplay?: () => void;
		onpause?: () => void;
		onedit?: () => void;
		onload?: () => void;
	} = $props();

	let url = $derived(value?.url);
	let old_playback_position = $state(0);

	let container: HTMLDivElement;
	let waveform: InstanceType<WaveSurferType> | undefined;
	let waveform_ready = $state(false);
	let waveform_loading = $state(false);
	let waveform_component_wrapper: HTMLDivElement;
	let playing = $state(false);

	let subtitle_container: HTMLDivElement;

	let timeRef: HTMLTimeElement;
	let durationRef: HTMLTimeElement;
	let audio_duration = $state<number>(0);

	let trimDuration = $state(0);

	let show_volume_slider = $state(false);
	let audio_player: HTMLAudioElement;

	let stream_active = false;
	let hls_instance: InstanceType<HlsType> | null = null;
	let subtitles_toggle = $state(true);
	let subtitle_event_handlers: (() => void)[] = [];

	let use_waveform = $derived(
		waveform_options.show_recording_waveform && !value?.is_stream
	);

	// Preload WaveSurfer when value is present (audio will be played soon)
	$effect(() => {
		if (value && use_waveform) {
			preloadWaveSurfer();
		}
		if (value?.is_stream) {
			preloadHls();
		}
	});

	$effect(() => {
		if (
			waveform_ready &&
			old_playback_position !== playback_position &&
			audio_duration
		) {
			waveform?.seekTo(playback_position / audio_duration);
			old_playback_position = playback_position;
		}
	});

	const create_waveform = async (): Promise<void> => {
		if (waveform_loading) return; // Prevent double-creation
		waveform_loading = true;

		try {
			const { WaveSurfer } = await loadWaveSurfer();
			waveform = WaveSurfer.create({
				container: container,
				...waveform_settings
			});
			if (subtitles && waveform) {
				if (subtitles_toggle) {
					add_subtitles_to_waveform(waveform, subtitles);
				} else {
					hide_subtitles();
				}
			}

			waveform?.on("init", () => {
				waveform_ready = true;
			});
			waveform?.on("decode", (duration: any) => {
				audio_duration = duration;
				durationRef && (durationRef.textContent = format_time(duration));
			});

			let firstTimeUpdate = true;
			waveform?.on("timeupdate", (currentTime: any) => {
				timeRef && (timeRef.textContent = format_time(currentTime));
				if (firstTimeUpdate) {
					firstTimeUpdate = false;
					return;
				}
				playback_position = currentTime;
				old_playback_position = currentTime;
			});

			waveform?.on("interaction", () => {
				const currentTime = waveform?.getCurrentTime() || 0;
				timeRef && (timeRef.textContent = format_time(currentTime));
				playback_position = currentTime;
				old_playback_position = currentTime;
			});

			waveform?.on("ready", () => {
				if (!waveform_settings.autoplay) {
					waveform?.stop();
				} else {
					waveform?.play();
				}
			});

			waveform?.on("finish", () => {
				if (loop) {
					waveform?.play();
				} else {
					playing = false;
					onstop?.();
				}
			});
			waveform?.on("pause", () => {
				playing = false;
				onpause?.();
			});
			waveform?.on("play", () => {
				playing = true;
				onplay?.();
			});

			waveform?.on("load", () => {
				onload?.();
			});
		} catch (e) {
			console.error("Failed to load WaveSurfer:", e);
		} finally {
			waveform_loading = false;
		}
	};

	$effect(() => {
		if (url && waveform_ready) {
			untrack(() => {
				if (value?.url && waveform) {
					waveform.load(value.url).catch((e: Error) => {
						if (e.name !== "AbortError") {
							console.error("Waveform load error:", e);
						}
					});
				}
			});
		}
	});

	const handle_trim_audio = async (
		start: number,
		end: number
	): Promise<void> => {
		mode = "";
		const decodedData = waveform?.getDecodedData();
		if (decodedData) {
			const trimmedBlob = await process_audio(
				decodedData,
				start,
				end,
				waveform_settings.sampleRate
			);
			await dispatch_blob([trimmedBlob], "change");
		}
		onedit?.();
	};

	async function load_audio(data: string): Promise<void> {
		stream_active = false;

		if (waveform_options.show_recording_waveform) {
			waveform?.load(data);
		} else if (audio_player) {
			audio_player.src = data;
		}
	}

	$effect(() => {
		if (subtitles && waveform) {
			if (subtitles_toggle) {
				add_subtitles_to_waveform(waveform, subtitles);
			} else {
				hide_subtitles();
			}
		}
	});

	async function load_stream(value: FileData | null): Promise<void> {
		if (!value || !value.is_stream || !value.url) return;

		// Destroy previous HLS instance if exists
		if (hls_instance) {
			hls_instance.destroy();
			hls_instance = null;
			stream_active = false;
		}

		const { Hls } = await loadHls();

		if (Hls.isSupported() && !stream_active) {
			// Optimized HLS config for faster audio loading:
			// - Increased maxBufferLength from 1→5 for smoother playback
			// - Added maxMaxBufferLength cap to prevent memory bloat
			// - Enable backBufferLength to auto-clean played segments
			// - startFragPrefetch for faster initial load
			const hls = new Hls({
				maxBufferLength: 5,
				maxMaxBufferLength: 30,
				backBufferLength: 10,
				lowLatencyMode: true,
				startFragPrefetch: true,
				// Progressive: start playing as soon as first segment is available
				progressive: true,
				// Reduce initial segment fetch delay
				liveSyncDurationCount: 1,
				liveMaxLatencyDurationCount: 3,
				// Better error recovery
				fragLoadingMaxRetry: 6,
				fragLoadingMaxRetryTimeout: 64000,
				// Manifest loading tweaks
				manifestLoadingMaxRetry: 4,
				manifestLoadingRetryDelay: 1000,
				levelLoadingMaxRetry: 4
			});
			hls.loadSource(value.url);
			hls.attachMedia(audio_player);
			hls.on(Hls.Events.MANIFEST_PARSED, function () {
				if (waveform_settings.autoplay) audio_player.play();
			});
			hls.on(Hls.Events.ERROR, function (event, data) {
				console.error("HLS error:", event, data);
				if (data.fatal) {
					switch (data.type) {
						case Hls.ErrorTypes.NETWORK_ERROR:
							console.error(
								"Fatal network error encountered, trying to recover"
							);
							hls.startLoad();
							break;
						case Hls.ErrorTypes.MEDIA_ERROR:
							console.error("Fatal media error encountered, trying to recover");
							hls.recoverMediaError();
							break;
						default:
							console.error("Fatal error, cannot recover");
							hls.destroy();
							break;
					}
				}
			});
			hls_instance = hls;
			stream_active = true;
		} else if (!stream_active) {
			audio_player.src = value.url;
			if (waveform_settings.autoplay) audio_player.play();
			stream_active = true;
		}
	}

	$effect(() => {
		if (audio_player && url && waveform_ready && url) {
			load_audio(url);
		}
	});

	$effect(() => {
		if (audio_player && value?.is_stream) {
			load_stream(value);
		}
	});

	onMount(() => {
		// Lazy-create waveform: only load WaveSurfer when actually needed
		if (use_waveform) {
			create_waveform();
		}
		const handleKeydown = (e: KeyboardEvent): void => {
			if (!waveform || show_volume_slider) return;

			const is_focused_in_waveform =
				waveform_component_wrapper &&
				waveform_component_wrapper.contains(document.activeElement);
			if (!is_focused_in_waveform) return;
			if (e.key === "ArrowRight" && mode !== "edit") {
				skip_audio(waveform, 0.1);
			} else if (e.key === "ArrowLeft" && mode !== "edit") {
				skip_audio(waveform, -0.1);
			}
		};
		window.addEventListener("keydown", handleKeydown);

		return () => {
			waveform?.destroy();
			hls_instance?.destroy();
			hls_instance = null;
			window.removeEventListener("keydown", handleKeydown);
		};
	});

	async function add_subtitles_to_waveform(
		wavesurfer: InstanceType<WaveSurferType>,
		subtitle_data: string | SubtitleData[]
	): Promise<void> {
		clear_subtitles();
		try {
			let subtitles: SubtitleData[];
			if (Array.isArray(subtitle_data)) {
				subtitles = subtitle_data;
			} else {
				const response = await fetch(subtitle_data);
				const subtitle_content = await response.text();
				subtitles = parse_subtitles(subtitle_content);
			}

			if (subtitles.length > 0) {
				let current_subtitle = "";
				if (subtitle_container) {
					subtitle_container.style.display = "";
					const audioProcessHandler = (time: number): void => {
						const subtitle = subtitles.find(
							(s) => time >= s.start && time <= s.end
						);
						if (subtitle && subtitle.text !== current_subtitle) {
							current_subtitle = subtitle.text;
							subtitle_container.textContent = current_subtitle;
						} else if (!subtitle && current_subtitle !== "") {
							current_subtitle = "";
							subtitle_container.textContent = "";
						}
					};
					wavesurfer.on("audioprocess", audioProcessHandler);
					subtitle_event_handlers.push(() => {
						wavesurfer.un("audioprocess", audioProcessHandler);
					});
				}
			}
		} catch (error) {}
	}

	function hide_subtitles(): void {
		if (subtitle_container) {
			subtitle_container.style.display = "none";
		}
	}

	function clear_subtitles(): void {
		if (subtitle_container) {
			subtitle_container.textContent = "";
		}
		subtitle_event_handlers.forEach((handler) => handler());
		subtitle_event_handlers = [];
	}

	function parse_subtitles(subtitle_content: string): SubtitleData[] {
		const lines = subtitle_content.split("\n");
		const subtitles: SubtitleData[] = [];

		for (let i = 0; i < lines.length; i++) {
			const line = lines[i].trim();
			if (line.includes(" --> ")) {
				const [start_time, end_time] = line.split(" --> ");
				const start = parse_time_to_seconds(start_time);
				const end = parse_time_to_seconds(end_time);

				let text = "";
				for (let j = i + 1; j < lines.length && lines[j].trim() !== ""; j++) {
					if (text) text += " ";
					text += lines[j].trim();
				}

				if (text) {
					subtitles.push({ start, end, text });
				}
			}
		}

		return subtitles;
	}

	function parse_time_to_seconds(time_str: string): number {
		const parts = time_str.split(":");
		if (parts.length === 3) {
			const hours = parseInt(parts[0]);
			const minutes = parseInt(parts[1]);
			const seconds = parseFloat(parts[2]);
			return hours * 3600 + minutes * 60 + seconds;
		}
		return 0;
	}
</script>

<audio
	class="standard-player"
	class:hidden={use_waveform}
	controls
	autoplay={waveform_settings.autoplay}
	{onload}
	bind:this={audio_player}
	onended={() => onstop?.()}
	onplay={() => onplay?.()}
	preload="metadata"
>
</audio>
{#if value === null}
	<Empty size="small">
		<Music />
	</Empty>
{:else if use_waveform}
	<div
		class="component-wrapper"
		data-testid={label ? "waveform-" + label : "unlabelled-audio"}
		bind:this={waveform_component_wrapper}
	>
		<div class="waveform-container">
			{#if waveform_loading}
				<div class="waveform-loading" style:height="58px">
					<div class="loading-pulse"></div>
				</div>
			{/if}
			<div
				id="waveform"
				bind:this={container}
				style:height={container ? null : "58px"}
			/>
		</div>

		<div class="timestamps">
			<time bind:this={timeRef} id="time">0:00</time>
			<div>
				{#if mode === "edit" && trimDuration > 0}
					<time id="trim-duration">{format_time(trimDuration)}</time>
				{/if}
				<time bind:this={durationRef} id="duration">0:00</time>
			</div>
		</div>

		<div
			bind:this={subtitle_container}
			class="subtitle-display"
			data-testid="subtitle-display"
		></div>

		<WaveformControls
			{container}
			{waveform}
			{playing}
			{audio_duration}
			{i18n}
			{interactive}
			{handle_trim_audio}
			bind:mode
			bind:trimDuration
			bind:show_volume_slider
			bind:subtitles_toggle
			show_redo={interactive}
			{handle_reset_value}
			{waveform_options}
			{trim_region_settings}
			{editable}
			show_subtitles={subtitles !== null}
		/>
	</div>
{/if}

<style>
	.component-wrapper {
		padding: var(--size-3);
		width: 100%;
	}

	:global(::part(wrapper)) {
		margin-bottom: var(--size-2);
	}

	.timestamps {
		display: flex;
		justify-content: space-between;
		align-items: center;
		width: 100%;
		padding: var(--size-1) 0;
	}

	#time {
		color: var(--neutral-400);
	}

	#duration {
		color: var(--neutral-400);
	}

	#trim-duration {
		color: var(--color-accent);
		margin-right: var(--spacing-sm);
	}
	.waveform-container {
		display: flex;
		align-items: center;
		justify-content: center;
		width: var(--size-full);
	}

	#waveform {
		width: 100%;
		height: 100%;
		position: relative;
	}

	.standard-player {
		width: 100%;
		padding: var(--size-2);
	}

	.subtitle-display {
		color: var(--text-secondary);
		font-size: var(--text-lg);
		text-align: center;
		max-width: 600px;
		line-height: 1.3;
		min-height: var(--size-4);
		font-family: var(--font-sans);
		font-weight: normal;
		margin: var(--size-2) auto;
		padding: var(--size-1) var(--size-2);
		border-radius: 2px;
		transition: opacity 0.2s ease-in-out;
	}

	.hidden,
	.subtitle-display:empty {
		display: none;
	}

	/* Loading state for lazy-loaded waveform */
	.waveform-loading {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
	}

	.loading-pulse {
		width: 100%;
		height: 4px;
		background: linear-gradient(
			90deg,
			var(--neutral-200) 25%,
			var(--neutral-300) 50%,
			var(--neutral-200) 75%
		);
		background-size: 200% 100%;
		animation: pulse-slide 1.5s ease-in-out infinite;
		border-radius: var(--radius-full);
	}

	@keyframes pulse-slide {
		0% {
			background-position: 200% 0;
		}
		100% {
			background-position: -200% 0;
		}
	}
</style>
