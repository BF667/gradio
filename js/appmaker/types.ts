export interface ComponentDef {
	type: string;
	icon: string;
	category: string;
	width: number;
	height: number;
	defaults: Record<string, any>;
	code: string;
}

export interface CanvasItem {
	id: string;
	type: string;
	x: number;
	y: number;
	width: number;
	height: number;
	props: Record<string, any>;
}

export interface AppMakerProps {
	value: string;
	components: Record<string, ComponentDef>;
	title: string;
	show_label: boolean;
	min_height: number | undefined;
	props: Record<string, any>;
}

export interface AppMakerEvents {
	change: string;
	generate: string;
}
