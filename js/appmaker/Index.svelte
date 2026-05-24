<script context="module" lang="ts">
	export { default as BaseExample } from "./Example.svelte";
</script>

<script lang="ts">
	import { Gradio } from "@gradio/utils";
	import AppMaker from "./shared/AppMaker.svelte";
	import { StatusTracker } from "@gradio/statustracker";
	import { Block, BlockLabel } from "@gradio/atoms";
	import type { AppMakerProps, AppMakerEvents } from "./types.ts";

	let props = $props();
	const gradio = new Gradio<AppMakerEvents, AppMakerProps>(props);

	let components = $derived(gradio.props.components ?? {});
	let title = $derived(gradio.props.title ?? "Gradio Sketch");
	let dark_mode = $derived(gradio.props.dark_mode ?? true);

	let old_value = $state(gradio.props.value);
	$effect(() => {
		if (JSON.stringify(old_value) !== JSON.stringify(gradio.props.value)) {
			old_value = gradio.props.value;
			gradio.dispatch("change");
		}
	});

	function handle_generate(data: string): void {
		gradio.props.value = data;
		gradio.dispatch("generate", data);
	}
</script>

<Block
	visible={gradio.shared.visible}
	elem_id={gradio.shared.elem_id}
	elem_classes={gradio.shared.elem_classes}
	container={false}
	padding={false}
	overflow_behavior="visible"
>
	{#if gradio.shared.show_label}
		<BlockLabel
			Icon={undefined}
			show_label={gradio.shared.show_label}
			label={gradio.shared.label || title}
			float={true}
		/>
	{/if}

	<StatusTracker
		autoscroll={gradio.shared.autoscroll}
		i18n={gradio.i18n}
		{...gradio.shared.loading_status}
		variant="center"
		on_clear_status={() =>
			gradio.dispatch("clear_status", gradio.shared.loading_status)}
	/>

	<AppMaker
		{components}
		{title}
		{dark_mode}
		on_generate={handle_generate}
	/>
</Block>
