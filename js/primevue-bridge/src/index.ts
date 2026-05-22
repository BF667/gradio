/**
 * PrimeVue Bridge for Svelte
 *
 * This module wraps PrimeVue Vue 3 components as Web Components (Custom Elements)
 * so they can be used natively inside Svelte 5 templates.
 *
 * Usage in Svelte:
 *   <primevue-button label="Click Me" severity="primary" />
 *   <primevue-inputtext value="Hello" />
 *   <primevue-slider v-model={50} />
 *
 * Props are passed as HTML attributes (kebab-case) and events are dispatched
 * as CustomEvent on the element.
 */
import { createApp, h, defineCustomElement } from "vue";
import PrimeVue from "primevue/config";
import Aura from "@primevue/themes/aura";

// --------------- PrimeVue Theme Configuration ---------------
const primeVueConfig = {
	theme: {
		preset: Aura,
		options: {
			prefix: "p",
			darkModeSelector: ".dark",
			cssLayer: false
		}
	}
};

// --------------- Wrapper Utility ---------------
/**
 * Wraps a PrimeVue component as a Custom Element (Web Component).
 * Props are read from HTML attributes (converted from kebab-case to camelCase).
 * Events emitted by the Vue component are re-dispatched as DOM CustomEvents.
 */
export function wrapPrimeVueComponent(
	component: any,
	tagName: string
): void {
	const CeClass = defineCustomElement({
		inheritAttrs: false,
		setup(props, { attrs, emit }) {
			// Forward Vue emits as DOM CustomEvents
			const eventHandlers: Record<string, (...args: any[]) => void> = {};
			if (component.emits) {
				for (const emitName of component.emits) {
					eventHandlers[`on${capitalize(emitName)}`] = (
						...args: any[]
					) => {
						emit(emitName, ...args);
					};
				}
			}
			return () =>
				h(component, {
					...attrs,
					...eventHandlers
				});
		}
	});

	// Inject PrimeVue config into the custom element shadow root
	class PrimeVueCustomElement extends CeClass {
		constructor() {
			super();
		}

		connectedCallback() {
			// Apply PrimeVue plugin before Vue mounts
			// @ts-ignore - accessing internal app instance
			const app = this._app || this.__vue_app__;
			if (app) {
				app.use(PrimeVue, primeVueConfig);
			}
			super.connectedCallback();
		}
	}

	if (!customElements.get(tagName)) {
		customElements.define(tagName, PrimeVueCustomElement);
	}
}

function capitalize(str: string): string {
	return str.charAt(0).toUpperCase() + str.slice(1);
}

// Re-export for convenience
export { PrimeVue, Aura, primeVueConfig };
export default wrapPrimeVueComponent;
