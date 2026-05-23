<script lang="ts">
        import type { ComponentDef, CanvasItem } from "../types.ts";

        let {
                components,
                title = "App Maker",
                on_generate
        }: {
                components: Record<string, ComponentDef>;
                title: string;
                on_generate: (data: string) => void;
        } = $props();

        // ── State ──
        let items: CanvasItem[] = $state([]);
        let selectedId: string | null = $state(null);
        let history: CanvasItem[][] = $state([]);
        let idCounter = 0;
        let addMenuOpen = $state(false);
        let sidebarCollapsed = $state(false);
        let propsCollapsed = $state(false);

        const GRID = 20;

        // ── Categorize components ──
        let inputComps = $derived(
                Object.entries(components)
                        .filter(([_, v]) => v.category === "input")
                        .map(([k, v]) => ({ type: k, ...v }))
        );
        let displayComps = $derived(
                Object.entries(components)
                        .filter(([_, v]) => v.category === "display")
                        .map(([k, v]) => ({ type: k, ...v }))
        );
        let mediaComps = $derived(
                Object.entries(components)
                        .filter(([_, v]) => v.category === "media")
                        .map(([k, v]) => ({ type: k, ...v }))
        );
        let actionComps = $derived(
                Object.entries(components)
                        .filter(([_, v]) => v.category === "action")
                        .map(([k, v]) => ({ type: k, ...v }))
        );

        let selectedItem = $derived(
                selectedId ? items.find((i) => i.id === selectedId) : null
        );

        // ── Actions ──
        function addComponent(type: string): void {
                addMenuOpen = false;
                saveHistory();
                const reg = components[type] || {
                        icon: "📦",
                        width: 200,
                        height: 80,
                        defaults: { label: type }
                };
                const id = "w" + ++idCounter;
                const x = Math.round((100 + items.length * 30) / GRID) * GRID;
                const y = Math.round((60 + items.length * 30) / GRID) * GRID;

                items.push({
                        id,
                        type,
                        x: Math.max(0, x),
                        y: Math.max(0, y),
                        width: reg.width,
                        height: reg.height,
                        props: { ...reg.defaults }
                });
                selectedId = id;
        }

        function removeItem(id: string): void {
                saveHistory();
                items = items.filter((i) => i.id !== id);
                if (selectedId === id) selectedId = null;
        }

        function clearAll(): void {
                if (items.length === 0) return;
                saveHistory();
                items = [];
                selectedId = null;
        }

        function undo(): void {
                if (history.length === 0) return;
                items = history.pop()!;
                selectedId = null;
        }

        function saveHistory(): void {
                history.push(JSON.parse(JSON.stringify(items)));
                if (history.length > 30) history.shift();
        }

        function selectItem(id: string | null): void {
                selectedId = id;
        }

        function updateProp(key: string, value: any): void {
                if (!selectedItem) return;
                saveHistory();
                selectedItem.props[key] = value;
        }

        function updatePosition(axis: "x" | "y", val: number): void {
                if (!selectedItem) return;
                saveHistory();
                selectedItem[axis] = Math.max(0, Math.round(val / GRID) * GRID);
        }

        function updateSize(dim: "width" | "height", val: number): void {
                if (!selectedItem) return;
                saveHistory();
                selectedItem[dim] = Math.max(50, Math.round(val / GRID) * GRID);
        }

        function generateCode(): void {
                const schema = {
                        layout: items.map((i) => ({
                                id: i.id,
                                type: i.type,
                                props: i.props,
                                x: i.x,
                                y: i.y,
                                width: i.width,
                                height: i.height
                        }))
                };
                on_generate(JSON.stringify(schema));
        }

        // ── Drag handling ──
        let dragState: {
                id: string;
                offsetX: number;
                offsetY: number;
                isTouch?: boolean;
        } | null = $state(null);

        let resizeState: {
                id: string;
                startX: number;
                startY: number;
                startW: number;
                startH: number;
                isTouch?: boolean;
        } | null = $state(null);

        function startDrag(e: MouseEvent | TouchEvent, item: CanvasItem): void {
                const isTouch = "touches" in e;
                const clientX = isTouch ? e.touches[0].clientX : (e as MouseEvent).clientX;
                const clientY = isTouch ? e.touches[0].clientY : (e as MouseEvent).clientY;
                const canvasWrap = document.getElementById("am-canvas-wrap");
                if (!canvasWrap) return;
                const rect = canvasWrap.getBoundingClientRect();
                saveHistory();
                selectedId = item.id;
                dragState = {
                        id: item.id,
                        offsetX: clientX - rect.left - item.x + canvasWrap.scrollLeft,
                        offsetY: clientY - rect.top - item.y + canvasWrap.scrollTop,
                        isTouch
                };
                if (isTouch) e.preventDefault();
        }

        function startResize(e: MouseEvent | TouchEvent, item: CanvasItem): void {
                const isTouch = "touches" in e;
                const clientX = isTouch ? e.touches[0].clientX : (e as MouseEvent).clientX;
                const clientY = isTouch ? e.touches[0].clientY : (e as MouseEvent).clientY;
                e.stopPropagation();
                saveHistory();
                selectedId = item.id;
                resizeState = {
                        id: item.id,
                        startX: clientX,
                        startY: clientY,
                        startW: item.width,
                        startH: item.height,
                        isTouch
                };
                if (isTouch) e.preventDefault();
        }

        function handleMouseMove(e: MouseEvent): void {
                if (dragState && !dragState.isTouch) {
                        moveItem(e.clientX, e.clientY);
                }
                if (resizeState && !resizeState.isTouch) {
                        resizeItem(e.clientX, e.clientY);
                }
        }

        function handleTouchMove(e: TouchEvent): void {
                if (dragState?.isTouch) {
                        e.preventDefault();
                        moveItem(e.touches[0].clientX, e.touches[0].clientY);
                }
                if (resizeState?.isTouch) {
                        e.preventDefault();
                        resizeItem(e.touches[0].clientX, e.touches[0].clientY);
                }
        }

        function moveItem(cx: number, cy: number): void {
                if (!dragState) return;
                const item = items.find((i) => i.id === dragState.id);
                if (!item) return;
                const canvasWrap = document.getElementById("am-canvas-wrap");
                if (!canvasWrap) return;
                const rect = canvasWrap.getBoundingClientRect();
                let nx = cx - rect.left - dragState.offsetX + canvasWrap.scrollLeft;
                let ny = cy - rect.top - dragState.offsetY + canvasWrap.scrollTop;
                nx = Math.round(nx / GRID) * GRID;
                ny = Math.round(ny / GRID) * GRID;
                item.x = Math.max(0, nx);
                item.y = Math.max(0, ny);
        }

        function resizeItem(cx: number, cy: number): void {
                if (!resizeState) return;
                const item = items.find((i) => i.id === resizeState.id);
                if (!item) return;
                let nw = resizeState.startW + (cx - resizeState.startX);
                let nh = resizeState.startH + (cy - resizeState.startY);
                nw = Math.max(120, Math.round(nw / GRID) * GRID);
                nh = Math.max(50, Math.round(nh / GRID) * GRID);
                item.width = nw;
                item.height = nh;
        }

        function endDrag(): void {
                dragState = null;
                resizeState = null;
        }

        function handleCanvasClick(e: MouseEvent): void {
                const target = e.target as HTMLElement;
                if (target.id === "am-canvas" || target.classList.contains("am-canvas-wrap")) {
                        selectedId = null;
                }
        }

        function handleKeydown(e: KeyboardEvent): void {
                const tag = (e.target as HTMLElement).tagName;
                if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
                if ((e.key === "Delete" || e.key === "Backspace") && selectedId) {
                        removeItem(selectedId);
                }
                if (e.key === "z" && (e.ctrlKey || e.metaKey)) {
                        undo();
                }
        }

        // ── Widget Preview ──
        function widgetPreview(item: CanvasItem): string {
                const p = item.props;
                switch (item.type) {
                        case "Textbox":
                                return `<label style="font-size:11px;font-weight:500;display:block;margin-bottom:3px">${p.label || "Textbox"}</label><input type="text" placeholder="${p.placeholder || ""}" style="width:100%;padding:5px 8px;border:1px solid #e2e8f0;border-radius:5px;font-size:12px;pointer-events:none" />`;
                        case "Number":
                                return `<label style="font-size:11px;font-weight:500;display:block;margin-bottom:3px">${p.label || "Number"}</label><input type="text" value="${p.value || 0}" style="width:100%;padding:5px 8px;border:1px solid #e2e8f0;border-radius:5px;font-size:12px;pointer-events:none" />`;
                        case "Slider":
                                return `<label style="font-size:11px;font-weight:500;display:block;margin-bottom:3px">${p.label || "Slider"}</label><input type="range" min="${p.minimum || 0}" max="${p.maximum || 100}" value="${p.value || 50}" style="width:100%;pointer-events:none" /><div style="font-size:10px;color:#64748b;text-align:right">${p.value || 50}</div>`;
                        case "Dropdown":
                                return `<label style="font-size:11px;font-weight:500;display:block;margin-bottom:3px">${p.label || "Dropdown"}</label><select style="width:100%;padding:5px;border:1px solid #e2e8f0;border-radius:5px;font-size:12px;pointer-events:none">${(p.choices || []).map((c: string) => "<option>" + c + "</option>").join("")}</select>`;
                        case "Checkbox":
                                return `<label style="display:flex;align-items:center;gap:6px;font-size:12px"><input type="checkbox" ${p.value ? "checked" : ""} style="pointer-events:none" /> ${p.label || "Checkbox"}</label>`;
                        case "Radio":
                                return `<label style="font-size:11px;font-weight:500;display:block;margin-bottom:3px">${p.label || "Radio"}</label>${(p.choices || []).map((c: string) => '<label style="font-size:11px;display:flex;align-items:center;gap:4px"><input type="radio" style="pointer-events:none" />' + c + "</label>").join("")}`;
                        case "Button":
                                return `<button style="background:${p.variant === "primary" ? "#f97316" : "#e2e8f0"};color:${p.variant === "primary" ? "white" : "#1e293b"};border:none;padding:6px 16px;border-radius:6px;font-size:12px;font-weight:600;cursor:default">${p.label || "Button"}</button>`;
                        case "Markdown":
                                return `<div style="font-size:12px;line-height:1.4;white-space:pre-wrap">${(p.value || "").substring(0, 80)}</div>`;
                        case "Code":
                                return `<div style="font-size:11px;background:#1e293b;color:#e2e8f0;padding:6px 8px;border-radius:4px;font-family:monospace;white-space:pre">${(p.value || "").substring(0, 40)}</div>`;
                        case "Image":
                        case "Audio":
                        case "Video":
                        case "Gallery":
                        case "File":
                                return `<div style="border:2px dashed #cbd5e1;border-radius:6px;height:calc(100% - 8px);display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:12px;min-height:40px">${components[item.type]?.icon || "📦"} ${p.label || item.type}</div>`;
                        case "Chatbot":
                                return `<div style="border:1px solid #e2e8f0;border-radius:6px;height:calc(100% - 8px);display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:11px">💬 Chat area</div>`;
                        case "HTML":
                                return `<div style="font-size:12px">${(p.value || "").substring(0, 60)}</div>`;
                        default:
                                return `<div style="color:#94a3b8;font-size:12px;font-style:italic">${components[item.type]?.icon || "📦"} ${p.label || item.type}</div>`;
                }
        }

        $effect(() => {
                window.addEventListener("keydown", handleKeydown);
                return () => window.removeEventListener("keydown", handleKeydown);
        });
</script>

<svelte:window
        onmousemove={handleMouseMove}
        onmouseup={endDrag}
        ontouchmove={handleTouchMove}
        ontouchend={endDrag}
/>

<div class="am-root">
        <!-- Header -->
        <div class="am-header">
                <h1>🎨 {title}</h1>
                <div class="am-header-actions">
                        <button class="am-btn am-mobile-toggle" onclick={() => sidebarCollapsed = !sidebarCollapsed}>📦</button>
                        <button class="am-btn am-mobile-toggle" onclick={() => propsCollapsed = !propsCollapsed}>⚙️</button>
                        <button class="am-btn am-desktop-only" onclick={undo}>↩️ Undo</button>
                        <button class="am-btn am-btn-danger am-desktop-only" onclick={clearAll}>🗑️ Clear</button>
                        <button class="am-btn am-btn-primary" onclick={generateCode}>✨ Generate</button>
                </div>
        </div>

        <div class="am-body">
                <!-- Sidebar: Component palette -->
                <aside class="am-sidebar" class:collapsed={sidebarCollapsed}>
                        {#if actionComps.length > 0}
                                <h3>Action</h3>
                                {#each actionComps as comp}
                                        <button
                                                class="am-sidebar-item"
                                                onclick={() => addComponent(comp.type)}
                                        >
                                                <span class="am-icon">{comp.icon}</span>{comp.type}
                                        </button>
                                {/each}
                        {/if}

                        <h3>Input</h3>
                        {#each inputComps as comp}
                                <button
                                        class="am-sidebar-item"
                                        onclick={() => addComponent(comp.type)}
                                >
                                        <span class="am-icon">{comp.icon}</span>{comp.type}
                                </button>
                        {/each}

                        <h3>Display</h3>
                        {#each displayComps as comp}
                                <button
                                        class="am-sidebar-item"
                                        onclick={() => addComponent(comp.type)}
                                >
                                        <span class="am-icon">{comp.icon}</span>{comp.type}
                                </button>
                        {/each}

                        {#if mediaComps.length > 0}
                                <h3>Media</h3>
                                {#each mediaComps as comp}
                                        <button
                                                class="am-sidebar-item"
                                                onclick={() => addComponent(comp.type)}
                                        >
                                                <span class="am-icon">{comp.icon}</span>{comp.type}
                                        </button>
                                {/each}
                        {/if}
                </aside>

                <!-- Canvas -->
                <div class="am-canvas-wrap" id="am-canvas-wrap" onclick={handleCanvasClick}>
                        <div class="am-canvas" id="am-canvas">
                                {#each items as item (item.id)}
                                        <div
                                                class="am-widget"
                                                class:selected={item.id === selectedId}
                                                style:left="{item.x}px"
                                                style:top="{item.y}px"
                                                style:width="{item.width}px"
                                                style:height="{item.height}px"
                                                onclick={() => selectItem(item.id)}
                                        >
                                                <!-- Delete button -->
                                                <button
                                                        class="am-widget-del"
                                                        onclick={(e) => { e.stopPropagation(); removeItem(item.id); }}
                                                >✕</button>

                                                <!-- Header (drag handle) -->
                                                <div
                                                        class="am-widget-header"
                                                        onmousedown={(e) => startDrag(e, item)}
                                                        ontouchstart={(e) => startDrag(e, item)}
                                                >
                                                        <span class="am-icon">{components[item.type]?.icon || "📦"}</span>{item.type}
                                                </div>

                                                <!-- Body preview -->
                                                <div class="am-widget-body">
                                                        {@html widgetPreview(item)}
                                                </div>

                                                <!-- Resize handle -->
                                                <div
                                                        class="am-widget-resize"
                                                        onmousedown={(e) => startResize(e, item)}
                                                        ontouchstart={(e) => startResize(e, item)}
                                                ></div>
                                        </div>
                                {/each}
                        </div>

                        <!-- Floating add button -->
                        <button class="am-add-fab" onclick={() => addMenuOpen = !addMenuOpen}>+</button>

                        <!-- Add menu popup -->
                        <div class="am-add-menu" class:open={addMenuOpen}>
                                {#if actionComps.length > 0}
                                        <h4>Action</h4>
                                        {#each actionComps as comp}
                                                <button class="am-add-menu-item" onclick={() => addComponent(comp.type)}>
                                                        <span class="am-icon">{comp.icon}</span>{comp.type}
                                                </button>
                                        {/each}
                                {/if}
                                <h4>Input</h4>
                                {#each inputComps as comp}
                                        <button class="am-add-menu-item" onclick={() => addComponent(comp.type)}>
                                                <span class="am-icon">{comp.icon}</span>{comp.type}
                                        </button>
                                {/each}
                                <h4>Display</h4>
                                {#each displayComps as comp}
                                        <button class="am-add-menu-item" onclick={() => addComponent(comp.type)}>
                                                <span class="am-icon">{comp.icon}</span>{comp.type}
                                        </button>
                                {/each}
                                {#if mediaComps.length > 0}
                                        <h4>Media</h4>
                                        {#each mediaComps as comp}
                                                <button class="am-add-menu-item" onclick={() => addComponent(comp.type)}>
                                                        <span class="am-icon">{comp.icon}</span>{comp.type}
                                                </button>
                                        {/each}
                                {/if}
                        </div>
                </div>

                <!-- Properties panel -->
                <aside class="am-props" class:collapsed={propsCollapsed}>
                        <h3>Properties</h3>
                        {#if selectedItem}
                                <div class="am-props-form">
                                        <div class="am-prop-group">
                                                <label>Type</label>
                                                <input type="text" value={selectedItem.type} disabled />
                                        </div>
                                        <div class="am-prop-row">
                                                <div class="am-prop-group">
                                                        <label>X</label>
                                                        <input
                                                                type="number"
                                                                value={selectedItem.x}
                                                                onchange={(e) => updatePosition("x", Number((e.target as HTMLInputElement).value))}
                                                        />
                                                </div>
                                                <div class="am-prop-group">
                                                        <label>Y</label>
                                                        <input
                                                                type="number"
                                                                value={selectedItem.y}
                                                                onchange={(e) => updatePosition("y", Number((e.target as HTMLInputElement).value))}
                                                        />
                                                </div>
                                        </div>
                                        <div class="am-prop-row">
                                                <div class="am-prop-group">
                                                        <label>Width</label>
                                                        <input
                                                                type="number"
                                                                value={selectedItem.width}
                                                                onchange={(e) => updateSize("width", Number((e.target as HTMLInputElement).value))}
                                                        />
                                                </div>
                                                <div class="am-prop-group">
                                                        <label>Height</label>
                                                        <input
                                                                type="number"
                                                                value={selectedItem.height}
                                                                onchange={(e) => updateSize("height", Number((e.target as HTMLInputElement).value))}
                                                        />
                                                </div>
                                        </div>

                                        {#each Object.entries(selectedItem.props) as [key, val]}
                                                <div class="am-prop-group">
                                                        <label>{key}</label>
                                                        {#if key === "choices"}
                                                                <input
                                                                        type="text"
                                                                        value={JSON.stringify(val)}
                                                                        onchange={(e) => {
                                                                                try { updateProp(key, JSON.parse((e.target as HTMLInputElement).value)); } catch {}
                                                                        }}
                                                                />
                                                        {:else if typeof val === "boolean"}
                                                                <select
                                                                        onchange={(e) => updateProp(key, (e.target as HTMLSelectElement).value === "true")}
                                                                >
                                                                        <option value="true" selected={val}>True</option>
                                                                        <option value="false" selected={!val}>False</option>
                                                                </select>
                                                        {:else if typeof val === "number"}
                                                                <input
                                                                        type="number"
                                                                        value={val}
                                                                        onchange={(e) => updateProp(key, Number((e.target as HTMLInputElement).value))}
                                                                />
                                                        {:else}
                                                                <input
                                                                        type="text"
                                                                        value={String(val)}
                                                                        onchange={(e) => updateProp(key, (e.target as HTMLInputElement).value)}
                                                                />
                                                        {/if}
                                                </div>
                                        {/each}
                                </div>
                        {:else}
                                <div class="am-props-empty">Click a widget to edit its properties</div>
                        {/if}
                </aside>
        </div>
</div>

<style>
        :root {
                --am-primary: #f97316;
                --am-primary-light: #fff7ed;
                --am-bg: #f1f5f9;
                --am-surface: #ffffff;
                --am-border: #e2e8f0;
                --am-text: #1e293b;
                --am-text-muted: #64748b;
                --am-radius: 12px;
                --am-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
                --am-shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.12);
                --am-grid: 20px;
        }

        .am-root {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                color: var(--am-text);
                background: var(--am-bg);
                height: 80vh;
                min-height: 500px;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                border-radius: var(--am-radius);
                border: 1px solid var(--am-border);
        }

        /* Header */
        .am-header {
                background: var(--am-surface);
                border-bottom: 1px solid var(--am-border);
                padding: 10px 16px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                z-index: 100;
                flex-shrink: 0;
        }

        .am-header h1 {
                font-size: 16px;
                font-weight: 700;
                display: flex;
                align-items: center;
                gap: 6px;
                margin: 0;
        }

        .am-header-actions {
                display: flex;
                gap: 6px;
                align-items: center;
        }

        .am-btn {
                border: 1px solid var(--am-border);
                background: var(--am-surface);
                color: var(--am-text);
                padding: 6px 14px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.15s;
                display: inline-flex;
                align-items: center;
                gap: 5px;
                white-space: nowrap;
        }

        .am-btn:hover {
                background: var(--am-bg);
                border-color: #cbd5e1;
        }

        .am-btn-primary {
                background: var(--am-primary);
                color: white;
                border-color: var(--am-primary);
        }

        .am-btn-primary:hover {
                background: #ea580c;
        }

        .am-btn-danger {
                color: #ef4444;
        }

        .am-btn-danger:hover {
                background: #fef2f2;
        }

        /* Main layout */
        .am-body {
                display: flex;
                flex: 1;
                overflow: hidden;
        }

        /* Sidebar */
        .am-sidebar {
                width: 200px;
                background: var(--am-surface);
                border-right: 1px solid var(--am-border);
                overflow-y: auto;
                padding: 10px;
                flex-shrink: 0;
        }

        .am-sidebar h3 {
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: var(--am-text-muted);
                margin-bottom: 6px;
                margin-top: 10px;
                padding: 0 4px;
        }

        .am-sidebar h3:first-child {
                margin-top: 0;
        }

        .am-sidebar-item {
                display: flex;
                align-items: center;
                gap: 7px;
                padding: 7px 9px;
                border-radius: 7px;
                cursor: pointer;
                font-size: 12px;
                font-weight: 500;
                border: 1px solid transparent;
                transition: all 0.12s;
                user-select: none;
                width: 100%;
                text-align: left;
                background: none;
                color: var(--am-text);
        }

        .am-sidebar-item:hover {
                background: var(--am-primary-light);
                border-color: #fed7aa;
        }

        .am-sidebar-item:active {
                transform: scale(0.97);
        }

        .am-sidebar-item .am-icon {
                font-size: 14px;
                width: 18px;
                text-align: center;
        }

        /* Canvas area */
        .am-canvas-wrap {
                flex: 1;
                overflow: auto;
                position: relative;
                background: var(--am-bg);
        }

        .am-canvas {
                position: relative;
                width: 2000px;
                height: 2000px;
                background-image: radial-gradient(circle, #cbd5e1 1px, transparent 1px);
                background-size: var(--am-grid) var(--am-grid);
        }

        /* Free-form widget on canvas */
        .am-widget {
                position: absolute;
                background: var(--am-surface);
                border: 2px solid var(--am-border);
                border-radius: 10px;
                cursor: move;
                user-select: none;
                transition: box-shadow 0.15s, border-color 0.15s;
                overflow: hidden;
        }

        .am-widget:hover {
                border-color: #fdba74;
                box-shadow: var(--am-shadow);
                z-index: 10;
        }

        .am-widget.selected {
                border-color: var(--am-primary);
                box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.2);
                z-index: 20;
        }

        .am-widget-header {
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 6px 10px;
                background: #f8fafc;
                border-bottom: 1px solid var(--am-border);
                font-size: 11px;
                font-weight: 600;
                color: var(--am-text-muted);
                text-transform: uppercase;
                letter-spacing: 0.03em;
                cursor: move;
        }

        .am-widget-header .am-icon {
                font-size: 13px;
        }

        .am-widget-body {
                padding: 10px 12px;
                font-size: 13px;
                color: var(--am-text);
                overflow: hidden;
        }

        /* Widget delete handle */
        .am-widget-del {
                position: absolute;
                top: 4px;
                right: 4px;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: #ef4444;
                color: white;
                border: none;
                font-size: 11px;
                cursor: pointer;
                display: none;
                align-items: center;
                justify-content: center;
                z-index: 30;
                line-height: 1;
                padding: 0;
        }

        .am-widget:hover .am-widget-del {
                display: flex;
        }

        /* Resize handle */
        .am-widget-resize {
                position: absolute;
                bottom: 0;
                right: 0;
                width: 16px;
                height: 16px;
                cursor: nwse-resize;
                opacity: 0;
        }

        .am-widget:hover .am-widget-resize,
        .am-widget.selected .am-widget-resize {
                opacity: 1;
        }

        .am-widget-resize::after {
                content: "";
                position: absolute;
                bottom: 3px;
                right: 3px;
                width: 8px;
                height: 8px;
                border-right: 2px solid var(--am-primary);
                border-bottom: 2px solid var(--am-primary);
        }

        /* Add button floating on canvas */
        .am-add-fab {
                position: absolute;
                bottom: 20px;
                right: 20px;
                width: 52px;
                height: 52px;
                border-radius: 50%;
                background: var(--am-primary);
                color: white;
                border: none;
                font-size: 26px;
                cursor: pointer;
                box-shadow: 0 4px 14px rgba(249, 115, 22, 0.4);
                z-index: 50;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.15s, box-shadow 0.15s;
        }

        .am-add-fab:hover {
                transform: scale(1.1);
                box-shadow: 0 6px 20px rgba(249, 115, 22, 0.5);
        }

        /* Add menu popup */
        .am-add-menu {
                position: absolute;
                bottom: 80px;
                right: 20px;
                background: var(--am-surface);
                border: 1px solid var(--am-border);
                border-radius: 12px;
                box-shadow: var(--am-shadow-lg);
                padding: 10px;
                z-index: 60;
                width: 220px;
                max-height: 400px;
                overflow-y: auto;
                display: none;
        }

        .am-add-menu.open {
                display: block;
        }

        .am-add-menu h4 {
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: var(--am-text-muted);
                margin: 6px 0 4px;
                padding: 0 4px;
        }

        .am-add-menu-item {
                display: flex;
                align-items: center;
                gap: 7px;
                padding: 7px 9px;
                border-radius: 7px;
                cursor: pointer;
                font-size: 12px;
                font-weight: 500;
                transition: background 0.1s;
                width: 100%;
                text-align: left;
                background: none;
                border: none;
                color: var(--am-text);
        }

        .am-add-menu-item:hover {
                background: var(--am-primary-light);
        }

        /* Props panel */
        .am-props {
                width: 240px;
                background: var(--am-surface);
                border-left: 1px solid var(--am-border);
                overflow-y: auto;
                padding: 14px;
                flex-shrink: 0;
        }

        .am-props h3 {
                font-size: 13px;
                font-weight: 600;
                margin: 0 0 10px;
                padding-bottom: 6px;
                border-bottom: 1px solid var(--am-border);
        }

        .am-props-empty {
                color: var(--am-text-muted);
                font-size: 12px;
                text-align: center;
                padding: 30px 10px;
        }

        .am-props-form {
                display: flex;
                flex-direction: column;
                gap: 8px;
        }

        .am-prop-group {
                display: flex;
                flex-direction: column;
                gap: 3px;
        }

        .am-prop-group label {
                font-size: 11px;
                font-weight: 500;
                color: var(--am-text-muted);
        }

        .am-prop-group input,
        .am-prop-group select {
                width: 100%;
                padding: 5px 8px;
                border: 1px solid var(--am-border);
                border-radius: 6px;
                font-size: 12px;
                background: var(--am-surface);
                color: var(--am-text);
                outline: none;
                transition: border-color 0.12s;
        }

        .am-prop-group input:focus,
        .am-prop-group select:focus {
                border-color: var(--am-primary);
        }

        .am-prop-group input:disabled {
                opacity: 0.6;
        }

        .am-prop-row {
                display: flex;
                gap: 6px;
        }

        .am-prop-row .am-prop-group {
                flex: 1;
        }

        /* Mobile toggle */
        .am-mobile-toggle {
                display: none;
        }

        /* Collapsed state for mobile */
        .collapsed {
                display: none !important;
        }

        /* Mobile responsive */
        @media (max-width: 900px) {
                .am-sidebar {
                        width: 160px;
                }
                .am-props {
                        width: 200px;
                }
        }

        @media (max-width: 768px) {
                .am-body {
                        flex-direction: column;
                }
                .am-sidebar {
                        width: 100%;
                        max-height: 80px;
                        border-right: none;
                        border-bottom: 1px solid var(--am-border);
                        display: flex;
                        flex-wrap: wrap;
                        gap: 2px;
                        padding: 6px;
                        overflow-x: auto;
                        overflow-y: hidden;
                }
                .am-sidebar.collapsed {
                        display: none !important;
                }
                .am-sidebar h3 {
                        display: none;
                }
                .am-sidebar-item {
                        padding: 5px 8px;
                        font-size: 11px;
                }
                .am-canvas-wrap {
                        flex: 1;
                        min-height: 300px;
                }
                .am-props {
                        width: 100%;
                        max-height: 200px;
                        border-left: none;
                        border-top: 1px solid var(--am-border);
                }
                .am-props.collapsed {
                        display: none !important;
                }
                .am-mobile-toggle {
                        display: inline-flex;
                }
                .am-desktop-only {
                        display: none !important;
                }
        }

        @media (max-width: 480px) {
                .am-header {
                        padding: 6px 10px;
                }
                .am-header h1 {
                        font-size: 14px;
                }
                .am-btn {
                        padding: 4px 8px;
                        font-size: 11px;
                }
                .am-sidebar-item {
                        padding: 4px 6px;
                        font-size: 10px;
                }
        }
</style>
