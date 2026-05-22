/**
 * PrimeVue Component Registration
 *
 * Import this file to register all PrimeVue components as Web Components
 * that can be used in Svelte templates.
 *
 * Usage:
 *   import "@gradio/primevue-bridge/components";
 *
 * Then in Svelte:
 *   <primevue-button label="Submit" severity="success" onclick={handleClick} />
 */
import { wrapPrimeVueComponent } from "./index";

// Lazy-load PrimeVue components to avoid bloating the initial bundle
// Each component is dynamically imported only when first needed.

// --------------- Form Components ---------------
export function registerButton(): void {
	import("primevue/button").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-button");
	});
}

export function registerInputText(): void {
	import("primevue/inputtext").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-inputtext");
	});
}

export function registerInputNumber(): void {
	import("primevue/inputnumber").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-inputnumber");
	});
}

export function registerSlider(): void {
	import("primevue/slider").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-slider");
	});
}

export function registerToggleSwitch(): void {
	import("primevue/toggleswitch").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-toggleswitch");
	});
}

export function registerSelect(): void {
	import("primevue/select").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-select");
	});
}

export function registerCheckbox(): void {
	import("primevue/checkbox").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-checkbox");
	});
}

export function registerTextarea(): void {
	import("primevue/textarea").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-textarea");
	});
}

// --------------- Data Display ---------------
export function registerDataTable(): void {
	import("primevue/datatable").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-datatable");
	});
}

export function registerColumn(): void {
	import("primevue/column").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-column");
	});
}

export function registerTag(): void {
	import("primevue/tag").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-tag");
	});
}

export function registerBadge(): void {
	import("primevue/badge").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-badge");
	});
}

export function registerProgressBar(): void {
	import("primevue/progressbar").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-progressbar");
	});
}

// --------------- Panel Components ---------------
export function registerPanel(): void {
	import("primevue/panel").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-panel");
	});
}

export function registerAccordion(): void {
	import("primevue/accordion").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-accordion");
	});
}

export function registerAccordionPanel(): void {
	import("primevue/accordionpanel").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-accordionpanel");
	});
}

export function registerDialog(): void {
	import("primevue/dialog").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-dialog");
	});
}

export function registerTooltip(): void {
	import("primevue/tooltip").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-tooltip");
	});
}

// --------------- Menu Components ---------------
export function registerMenu(): void {
	import("primevue/menu").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-menu");
	});
}

export function registerMenuBar(): void {
	import("primevue/menubar").then((m) => {
		wrapPrimeVueComponent(m.default, "primevue-menubar");
	});
}

// --------------- Eager Registration for Core Components ---------------
/**
 * Register the most commonly used PrimeVue components eagerly.
 * Other components can be registered on-demand via the individual
 * register functions above.
 */
export function registerCorePrimeVueComponents(): void {
	registerButton();
	registerInputText();
	registerSlider();
	registerToggleSwitch();
	registerSelect();
	registerTag();
	registerProgressBar();
}
