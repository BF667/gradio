export interface ComponentDef {
	type: string;
	icon: string;
	category: "layout" | "input" | "output" | "media" | "action";
	width: number;
	height: number;
	defaults: Record<string, any>;
	code: string;
	events?: string[];
}

export interface LayoutNode {
	id: string;
	kind: "layout";
	type: "row" | "column" | "tabs" | "tabitem" | "group" | "accordion";
	children: TreeNode[];
	props: Record<string, any>;
}

export interface ComponentNode {
	id: string;
	kind: "component";
	type: string;
	props: Record<string, any>;
}

export type TreeNode = LayoutNode | ComponentNode;

export interface EventConnection {
	id: string;
	source_id: string;
	event: string;
	fn_name: string;
	inputs: string[];
	outputs: string[];
}

export interface AppSchema {
	layout: TreeNode;
	events: EventConnection[];
	theme: string;
	title: string;
}

export interface TemplateDef {
	name: string;
	icon: string;
	description: string;
	schema: AppSchema;
}

export interface AppMakerProps {
	value: string;
	components: Record<string, ComponentDef>;
	title: string;
	dark_mode: boolean;
	min_height: number | undefined;
}

export interface AppMakerEvents {
	change: string;
	generate: string;
}
