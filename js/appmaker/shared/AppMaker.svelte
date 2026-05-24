<script lang="ts">
        import type { ComponentDef, TreeNode, LayoutNode, ComponentNode, EventConnection, TemplateDef, AppSchema } from "../types.ts";

        let {
                components,
                title = "Gradio Sketch",
                on_generate
        }: {
                components: Record<string, ComponentDef>;
                title: string;
                on_generate: (data: string) => void;
        } = $props();

        // ── State ──
        let tree: TreeNode = $state({
                id: "app",
                kind: "layout",
                type: "column",
                children: [],
                props: {}
        });
        let selectedId: string | null = $state(null);
        let events: EventConnection[] = $state([]);
        let historyStack: string[] = $state([]);
        let futureStack: string[] = $state([]);
        let idCounter = 0;
        let mode: "edit" | "preview" | "code" = $state("edit");
        let searchQuery = $state("");
        let rightTab: "props" | "events" | "tree" = $state("props");
        let templateOpen = $state(false);
        let expandedNodes: Set<string> = $state(new Set(["app"]));
        let dragOverId: string | null = $state(null);

        // ── Vibe Mode (AI chat, like gradio --vibe) ──
        let vibeOpen = $state(false);
        let vibePrompt = $state("");
        let vibeMessages: { text: string; isBot: boolean; hash?: string; diffStats?: { lines_added: number; lines_removed: number } }[] = $state([]);
        let vibeLoading = $state(false);
        let vibeHistory: { code: string; prompt: string }[] = [];

        // ── Helpers ──
        function uid(): string {
                return "n" + ++idCounter;
        }

        function saveHistory(): void {
                historyStack.push(JSON.stringify({ tree, events }));
                if (historyStack.length > 50) historyStack.shift();
                futureStack = [];
        }

        function undo(): void {
                if (historyStack.length === 0) return;
                futureStack.push(JSON.stringify({ tree, events }));
                const snap = JSON.parse(historyStack.pop()!);
                tree = snap.tree;
                events = snap.events;
                selectedId = null;
        }

        function redo(): void {
                if (futureStack.length === 0) return;
                historyStack.push(JSON.stringify({ tree, events }));
                const snap = JSON.parse(futureStack.pop()!);
                tree = snap.tree;
                events = snap.events;
                selectedId = null;
        }

        // ── Tree operations ──
        function findNode(id: string, node: TreeNode = tree): TreeNode | null {
                if (node.id === id) return node;
                if (node.kind === "layout") {
                        for (const child of node.children) {
                                const found = findNode(id, child);
                                if (found) return found;
                        }
                }
                return null;
        }

        function findParent(id: string, node: TreeNode = tree, parent: TreeNode | null = null): { parent: TreeNode | null; index: number } {
                if (node.id === id) return { parent, index: -1 };
                if (node.kind === "layout") {
                        for (let i = 0; i < node.children.length; i++) {
                                if (node.children[i].id === id) return { parent: node, index: i };
                                const result = findParent(id, node.children[i], node);
                                if (result.parent !== null) return result;
                        }
                }
                return { parent: null, index: -1 };
        }

        function isLayout(type: string): boolean {
                return ["row", "column", "tabs", "tabitem", "group", "accordion"].includes(type);
        }

        function isLayoutComponent(type: string): boolean {
                return components[type]?.category === "layout";
        }

        // ── Add component / layout ──
        function addNode(type: string, targetId?: string): void {
                saveHistory();
                const comp = components[type];
                let newNode: TreeNode;

                if (isLayoutComponent(type)) {
                        const layoutType = type.toLowerCase();
                        newNode = {
                                id: uid(),
                                kind: "layout",
                                type: layoutType,
                                children: layoutType === "tabs" ? [
                                        { id: uid(), kind: "layout", type: "tabitem", children: [], props: { label: "Tab 1" } }
                                ] : [],
                                props: { ...comp?.defaults }
                        };
                } else {
                        newNode = {
                                id: uid(),
                                kind: "component",
                                type: type,
                                props: { ...comp?.defaults }
                        };
                }

                // Find target to add to
                let target: TreeNode | null = null;
                if (targetId) {
                        target = findNode(targetId);
                }
                if (!target) {
                        // Add to root or currently selected layout
                        target = selectedId ? findNode(selectedId) : null;
                        if (target && target.kind === "component") {
                                const { parent } = findParent(selectedId!);
                                target = parent;
                        }
                }
                if (!target || target.kind === "component") {
                        target = tree;
                }

                // If target is a layout, add as child
                if (target.kind === "layout") {
                        target.children.push(newNode);
                }
                selectedId = newNode.id;
                expandedNodes.add(target.id);
        }

        function removeNode(id: string): void {
                saveHistory();
                const { parent, index } = findParent(id);
                if (parent && parent.kind === "layout" && index >= 0) {
                        parent.children.splice(index, 1);
                }
                if (selectedId === id) selectedId = null;
                // Remove related events
                events = events.filter(e => e.source_id !== id && !e.inputs.includes(id) && !e.outputs.includes(id));
        }

        function moveNode(id: string, direction: "up" | "down"): void {
                saveHistory();
                const { parent, index } = findParent(id);
                if (!parent || parent.kind !== "layout" || index < 0) return;
                const newIndex = direction === "up" ? index - 1 : index + 1;
                if (newIndex < 0 || newIndex >= parent.children.length) return;
                const tmp = parent.children[index];
                parent.children[index] = parent.children[newIndex];
                parent.children[newIndex] = tmp;
        }

        function clearAll(): void {
                if (tree.kind === "layout" && tree.children.length === 0) return;
                saveHistory();
                tree = { id: "app", kind: "layout", type: "column", children: [], props: {} };
                events = [];
                selectedId = null;
        }

        // ── Event wiring ──
        function addEvent(): void {
                saveHistory();
                events.push({
                        id: uid(),
                        source_id: "",
                        event: "click",
                        fn_name: `fn_${events.length + 1}`,
                        inputs: [],
                        outputs: []
                });
        }

        function removeEvent(id: string): void {
                saveHistory();
                events = events.filter(e => e.id !== id);
        }

        // ── Derived ──
        let selectedNode = $derived(selectedId ? findNode(selectedId) : null);

        let componentNodes = $derived(
                collectComponents(tree)
        );

        function collectComponents(node: TreeNode): ComponentNode[] {
                const result: ComponentNode[] = [];
                if (node.kind === "component") {
                        result.push(node);
                }
                if (node.kind === "layout") {
                        for (const child of node.children) {
                                result.push(...collectComponents(child));
                        }
                }
                return result;
        }

        // Categorized components for palette
        let layoutComps = $derived(
                Object.entries(components).filter(([_, v]) => v.category === "layout").map(([k, v]) => ({ type: k, ...v }))
        );
        let inputComps = $derived(
                Object.entries(components).filter(([_, v]) => v.category === "input").map(([k, v]) => ({ type: k, ...v }))
        );
        let actionComps = $derived(
                Object.entries(components).filter(([_, v]) => v.category === "action").map(([k, v]) => ({ type: k, ...v }))
        );
        let mediaComps = $derived(
                Object.entries(components).filter(([_, v]) => v.category === "media").map(([k, v]) => ({ type: k, ...v }))
        );
        let outputComps = $derived(
                Object.entries(components).filter(([_, v]) => v.category === "output").map(([k, v]) => ({ type: k, ...v }))
        );

        let filteredLayout = $derived(layoutComps.filter(c => c.type.toLowerCase().includes(searchQuery.toLowerCase())));
        let filteredInput = $derived(inputComps.filter(c => c.type.toLowerCase().includes(searchQuery.toLowerCase())));
        let filteredAction = $derived(actionComps.filter(c => c.type.toLowerCase().includes(searchQuery.toLowerCase())));
        let filteredMedia = $derived(mediaComps.filter(c => c.type.toLowerCase().includes(searchQuery.toLowerCase())));
        let filteredOutput = $derived(outputComps.filter(c => c.type.toLowerCase().includes(searchQuery.toLowerCase())));

        // ── Code Generation ──
        function generateCode(): void {
                const schema: AppSchema = {
                        layout: tree,
                        events: events,
                        theme: "soft",
                        title: "My App"
                };
                on_generate(JSON.stringify(schema));
        }

        function getGeneratedCode(): string {
                return schemaToCode(tree, events);
        }

        function schemaToCode(node: TreeNode, evts: EventConnection[], indent: number = 0): string {
                const pad = "    ".repeat(indent);
                const pad1 = "    ".repeat(indent + 1);
                let code = "";

                if (node.kind === "layout") {
                        if (node.id === "app") {
                                // Root
                                code += pad + "with gr.Blocks() as demo:\n";
                                for (const child of node.children) {
                                        code += schemaToCode(child, evts, indent + 1);
                                }
                        } else if (node.type === "row") {
                                code += pad + "with gr.Row():\n";
                                for (const child of node.children) {
                                        code += schemaToCode(child, evts, indent + 1);
                                }
                        } else if (node.type === "column") {
                                const scale = node.props.scale || 1;
                                code += pad + `with gr.Column(scale=${scale}):\n`;
                                for (const child of node.children) {
                                        code += schemaToCode(child, evts, indent + 1);
                                }
                        } else if (node.type === "tabs") {
                                code += pad + "with gr.Tabs():\n";
                                for (const child of node.children) {
                                        code += schemaToCode(child, evts, indent + 1);
                                }
                        } else if (node.type === "tabitem") {
                                const lbl = node.props.label || "Tab";
                                code += pad + `with gr.Tab("${lbl}"):\n`;
                                for (const child of node.children) {
                                        code += schemaToCode(child, evts, indent + 1);
                                }
                        } else if (node.type === "accordion") {
                                const lbl = node.props.label || "Advanced";
                                const opn = node.props.open ?? false;
                                code += pad + `with gr.Accordion("${lbl}", open=${opn}):\n`;
                                for (const child of node.children) {
                                        code += schemaToCode(child, evts, indent + 1);
                                }
                        } else if (node.type === "group") {
                                code += pad + "with gr.Group():\n";
                                for (const child of node.children) {
                                        code += schemaToCode(child, evts, indent + 1);
                                }
                        }
                } else {
                        // Component
                        const reg = components[node.type];
                        if (reg) {
                                try {
                                        code += pad + node.type.toLowerCase() + " = " + reg.code.format(node.props) + "\n";
                                } catch {
                                        code += pad + `${node.type.toLowerCase()} = gr.${node.type}(label="${node.props.label || node.type}")\n`;
                                }
                        } else {
                                code += pad + `${node.type.toLowerCase()} = gr.${node.type}(label="${node.props.label || node.type}")\n`;
                        }
                }
                return code;
        }

        // Add events after the layout
        function getFullCode(): string {
                let code = "import gradio as gr\n\n\n";
                // Generate event handler functions
                for (const evt of events) {
                        const inpVars = evt.inputs.map(id => {
                                const n = findNode(id);
                                return n ? (n.kind === "component" ? n.props.label?.toLowerCase().replace(/\s+/g, "_") || n.type.toLowerCase() : id) : id;
                        });
                        const outVars = evt.outputs.map(id => {
                                const n = findNode(id);
                                return n ? (n.kind === "component" ? n.props.label?.toLowerCase().replace(/\s+/g, "_") || n.type.toLowerCase() : id) : id;
                        });
                        code += `def ${evt.fn_name}(${inpVars.join(", ")}):\n`;
                        code += `    # TODO: Implement this function\n`;
                        code += `    return ${outVars.length > 0 ? outVars.join(", ") : "None"}\n\n`;
                }

                code += schemaToCode(tree, events);

                // Wire up events
                for (const evt of events) {
                        if (!evt.source_id) continue;
                        const srcNode = findNode(evt.source_id);
                        if (!srcNode) continue;
                        const srcVar = srcNode.kind === "component" ? srcNode.props.label?.toLowerCase().replace(/\s+/g, "_") || srcNode.type.toLowerCase() : evt.source_id;
                        const inpVars = evt.inputs.map(id => {
                                const n = findNode(id);
                                return n ? (n.kind === "component" ? n.props.label?.toLowerCase().replace(/\s+/g, "_") || n.type.toLowerCase() : id) : id;
                        });
                        const outVars = evt.outputs.map(id => {
                                const n = findNode(id);
                                return n ? (n.kind === "component" ? n.props.label?.toLowerCase().replace(/\s+/g, "_") || n.type.toLowerCase() : id) : id;
                        });
                        code += `    ${srcVar}.${evt.event}(${evt.fn_name}, inputs=[${inpVars.join(", ")}], outputs=[${outVars.join(", ")}])\n`;
                }

                code += "\ndemo.launch()\n";
                return code;
        }

        // ── Templates ──
        const templates: TemplateDef[] = [
                {
                        name: "Chat App",
                        icon: "💬",
                        description: "AI chatbot interface",
                        schema: {
                                layout: {
                                        id: "app", kind: "layout", type: "column", props: {},
                                        children: [
                                                { id: "t1", kind: "layout", type: "row", props: {}, children: [
                                                        { id: "c1", kind: "component", type: "Chatbot", props: { label: "Chat", height: 500 } },
                                                ]},
                                                { id: "t2", kind: "layout", type: "row", props: {}, children: [
                                                        { id: "c2", kind: "component", type: "Textbox", props: { label: "Message", placeholder: "Type a message...", lines: 1 } },
                                                        { id: "c3", kind: "component", type: "Button", props: { label: "Send", variant: "primary" } },
                                                ]},
                                        ]
                                },
                                events: [
                                        { id: "e1", source_id: "c3", event: "click", fn_name: "chat", inputs: ["c2"], outputs: ["c1"] }
                                ],
                                theme: "soft", title: "Chat App"
                        }
                },
                {
                        name: "Image Gen",
                        icon: "🎨",
                        description: "Text-to-image generator",
                        schema: {
                                layout: {
                                        id: "app", kind: "layout", type: "column", props: {},
                                        children: [
                                                { id: "t1", kind: "layout", type: "row", props: {}, children: [
                                                        { id: "c1", kind: "component", type: "Textbox", props: { label: "Prompt", placeholder: "Describe the image...", lines: 2 } },
                                                        { id: "c2", kind: "component", type: "Slider", props: { label: "Steps", minimum: 1, maximum: 50, value: 20, step: 1 } },
                                                ]},
                                                { id: "t2", kind: "layout", type: "row", props: {}, children: [
                                                        { id: "c3", kind: "component", type: "Button", props: { label: "Generate", variant: "primary" } },
                                                ]},
                                                { id: "t3", kind: "layout", type: "row", props: {}, children: [
                                                        { id: "c4", kind: "component", type: "Image", props: { label: "Result" } },
                                                ]},
                                        ]
                                },
                                events: [
                                        { id: "e1", source_id: "c3", event: "click", fn_name: "generate", inputs: ["c1", "c2"], outputs: ["c4"] }
                                ],
                                theme: "soft", title: "Image Generator"
                        }
                },
                {
                        name: "Data Analysis",
                        icon: "📊",
                        description: "Upload and analyze data",
                        schema: {
                                layout: {
                                        id: "app", kind: "layout", type: "column", props: {},
                                        children: [
                                                { id: "t1", kind: "layout", type: "row", props: {}, children: [
                                                        { id: "c1", kind: "component", type: "File", props: { label: "Upload CSV" } },
                                                        { id: "c2", kind: "component", type: "Dropdown", props: { label: "Analysis", choices: ["Summary", "Correlation", "Distribution"] } },
                                                        { id: "c3", kind: "component", type: "Button", props: { label: "Analyze", variant: "primary" } },
                                                ]},
                                                { id: "t2", kind: "layout", type: "row", props: {}, children: [
                                                        { id: "c4", kind: "component", type: "Dataframe", props: { label: "Data" } },
                                                ]},
                                        ]
                                },
                                events: [
                                        { id: "e1", source_id: "c3", event: "click", fn_name: "analyze", inputs: ["c1", "c2"], outputs: ["c4"] }
                                ],
                                theme: "soft", title: "Data Analysis"
                        }
                },
                {
                        name: "Blank",
                        icon: "✦",
                        description: "Start from scratch",
                        schema: {
                                layout: { id: "app", kind: "layout", type: "column", children: [], props: {} },
                                events: [],
                                theme: "soft", title: "My App"
                        }
                }
        ];

        function applyTemplate(t: TemplateDef): void {
                saveHistory();
                tree = JSON.parse(JSON.stringify(t.schema.layout));
                events = JSON.parse(JSON.stringify(t.schema.events));
                selectedId = null;
                templateOpen = false;
        }

        // ── Prop editing ──
        function updateProp(key: string, value: any): void {
                if (!selectedNode) return;
                saveHistory();
                selectedNode.props[key] = value;
        }

        // ── Vibe Mode ──
        const vibeStarterQueries: string[] = [
                "Add a chatbot with text input and send button",
                "Create an image upload with a process button",
                "Build a data dashboard with dropdown filters",
                "Add tabs for Settings and Results",
        ];

        function vibeSubmit(queryText?: string): void {
                const textToSubmit = queryText || vibePrompt;
                if (!textToSubmit.trim()) return;

                vibeMessages = [...vibeMessages, { text: textToSubmit, isBot: false }];
                if (!queryText) vibePrompt = "";

                const userMsg = textToSubmit;
                vibeLoading = true;

                // Generate the current code as context for the vibe
                const currentCode = getFullCode();

                // Save for undo
                const snapshotHash = "v" + Date.now();
                vibeHistory.push({ code: currentCode, prompt: userMsg });

                // Add a pending bot message
                vibeMessages = [...vibeMessages, { text: "Thinking...", isBot: true, hash: snapshotHash }];

                // Use the Gradio dispatch to send the vibe prompt to Python backend
                // The on_generate callback will handle the code generation
                const vibeSchema: AppSchema = {
                        layout: tree,
                        events: events,
                        theme: "soft",
                        title: "Vibe Edit"
                };

                // Simulate AI response — in production, this calls the Python backend
                // via gradio dispatch which triggers the vibe_edit route
                on_generate(JSON.stringify({
                        ...vibeSchema,
                        vibe_prompt: userMsg,
                        vibe_code: currentCode
                }));

                // For now, add a visual response
                setTimeout(() => {
                        vibeLoading = false;
                        vibeMessages = vibeMessages.map((msg, i) => {
                                if (i === vibeMessages.length - 1 && msg.isBot && msg.text === "Thinking...") {
                                        return {
                                                ...msg,
                                                text: `Code generated from: "${userMsg}"\n\nClick "✨ Generate" to see the updated code, or use the Code tab to view it.`,
                                                diffStats: { lines_added: 3, lines_removed: 0 }
                                        };
                                }
                                return msg;
                        });
                }, 1500);
        }

        function vibeUndo(index: number): void {
                if (vibeHistory.length === 0) return;
                const last = vibeHistory.pop()!;
                // Restore the code state - this would be done via Python in production
                vibeMessages = vibeMessages.slice(0, index);
        }

        // ── Keyboard shortcuts ──
        function handleKeydown(e: KeyboardEvent): void {
                const tag = (e.target as HTMLElement).tagName;
                if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
                if ((e.key === "Delete" || e.key === "Backspace") && selectedId) {
                        e.preventDefault();
                        removeNode(selectedId);
                }
                if (e.key === "z" && (e.ctrlKey || e.metaKey) && !e.shiftKey) {
                        e.preventDefault();
                        undo();
                }
                if ((e.key === "z" && (e.ctrlKey || e.metaKey) && e.shiftKey) || (e.key === "y" && (e.ctrlKey || e.metaKey))) {
                        e.preventDefault();
                        redo();
                }
        }

        $effect(() => {
                window.addEventListener("keydown", handleKeydown);
                return () => window.removeEventListener("keydown", handleKeydown);
        });

        // ── Widget preview rendering ──
        function widgetPreview(node: TreeNode): string {
                if (node.kind === "layout") {
                        const icons: Record<string, string> = { row: "▦", column: "▥", tabs: "⊟", tabitem: "▣", accordion: "▤", group: "◧" };
                        return `<div style="display:flex;align-items:center;gap:6px;color:#a78bfa;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.04em">${icons[node.type] || "◈"} ${node.type} ${node.children.length > 0 ? `(${node.children.length})` : ""}</div>`;
                }
                const p = node.props;
                const isDark = true;
                const border = isDark ? "#334155" : "#e2e8f0";
                const bg = isDark ? "#1e293b" : "#f8fafc";
                const text = isDark ? "#e2e8f0" : "#1e293b";
                const muted = isDark ? "#94a3b8" : "#64748b";
                const inputBg = isDark ? "#0f172a" : "#ffffff";
                const accent = "#8b5cf6";

                switch (node.type) {
                        case "Textbox":
                                return `<label style="font-size:10px;font-weight:500;display:block;margin-bottom:3px;color:${muted}">${p.label || "Textbox"}</label><input type="text" placeholder="${p.placeholder || ""}" style="width:100%;padding:4px 8px;border:1px solid ${border};border-radius:5px;font-size:11px;background:${inputBg};color:${text};pointer-events:none" />`;
                        case "Number":
                                return `<label style="font-size:10px;font-weight:500;display:block;margin-bottom:3px;color:${muted}">${p.label || "Number"}</label><input type="text" value="${p.value || 0}" style="width:100%;padding:4px 8px;border:1px solid ${border};border-radius:5px;font-size:11px;background:${inputBg};color:${text};pointer-events:none" />`;
                        case "Slider":
                                return `<label style="font-size:10px;font-weight:500;display:block;margin-bottom:3px;color:${muted}">${p.label || "Slider"}</label><input type="range" min="${p.minimum || 0}" max="${p.maximum || 100}" value="${p.value || 50}" style="width:100%;accent-color:${accent};pointer-events:none" /><div style="font-size:9px;color:${muted};text-align:right">${p.value || 50}</div>`;
                        case "Dropdown":
                                return `<label style="font-size:10px;font-weight:500;display:block;margin-bottom:3px;color:${muted}">${p.label || "Dropdown"}</label><select style="width:100%;padding:4px;border:1px solid ${border};border-radius:5px;font-size:11px;background:${inputBg};color:${text};pointer-events:none">${(p.choices || []).map((c: string) => `<option>${c}</option>`).join("")}</select>`;
                        case "Checkbox":
                                return `<label style="display:flex;align-items:center;gap:5px;font-size:11px;color:${text}"><input type="checkbox" ${p.value ? "checked" : ""} style="accent-color:${accent};pointer-events:none" /> ${p.label || "Checkbox"}</label>`;
                        case "Radio":
                                return `<label style="font-size:10px;font-weight:500;display:block;margin-bottom:3px;color:${muted}">${p.label || "Radio"}</label>${(p.choices || []).map((c: string) => `<label style="font-size:10px;display:flex;align-items:center;gap:3px;color:${text}"><input type="radio" style="accent-color:${accent};pointer-events:none" />${c}</label>`).join("")}`;
                        case "Button":
                                return `<button style="background:${p.variant === "primary" ? "linear-gradient(135deg, #8b5cf6, #6366f1)" : inputBg};color:${p.variant === "primary" ? "white" : text};border:1px solid ${p.variant === "primary" ? "transparent" : border};padding:5px 14px;border-radius:6px;font-size:11px;font-weight:600;cursor:default">${p.label || "Button"}</button>`;
                        case "Markdown":
                                return `<div style="font-size:11px;line-height:1.4;white-space:pre-wrap;color:${text}">${(p.value || "").substring(0, 80)}</div>`;
                        case "Code":
                                return `<div style="font-size:10px;background:#0f172a;color:#a5f3fc;padding:5px 7px;border-radius:4px;font-family:monospace;white-space:pre">${(p.value || "").substring(0, 40)}</div>`;
                        case "Chatbot":
                                return `<div style="border:1px solid ${border};border-radius:6px;height:60px;display:flex;align-items:center;justify-content:center;color:${muted};font-size:10px;background:${inputBg}">💬 Chat area</div>`;
                        case "Image":
                        case "Audio":
                        case "Video":
                        case "Gallery":
                        case "File":
                                return `<div style="border:1px dashed ${border};border-radius:6px;height:50px;display:flex;align-items:center;justify-content:center;color:${muted};font-size:10px;background:${inputBg}">${components[node.type]?.icon || "◈"} ${p.label || node.type}</div>`;
                        case "HTML":
                                return `<div style="font-size:11px;color:${text}">${(p.value || "").substring(0, 60)}</div>`;
                        default:
                                return `<div style="color:${muted};font-size:11px">${components[node.type]?.icon || "◈"} ${p.label || node.type}</div>`;
                }
        }

        // ── Tree toggle ──
        function toggleExpand(id: string): void {
                if (expandedNodes.has(id)) {
                        expandedNodes.delete(id);
                } else {
                        expandedNodes.add(id);
                }
        }

        // ── Render tree recursively ──
        function renderTreeNode(node: TreeNode, depth: number = 0): string {
                // Used for the tree view in the right panel
                if (node.kind === "layout") {
                        const icon: Record<string, string> = { row: "▦", column: "▥", tabs: "⊟", tabitem: "▣", accordion: "▤", group: "◧", column: "▥" };
                        return `${"  ".repeat(depth)}${icon[node.type] || "◈"} ${node.type}${node.children.length > 0 ? "\n" + node.children.map(c => renderTreeNode(c, depth + 1)).join("\n") : ""}`;
                }
                return `${"  ".repeat(depth)}${components[node.type]?.icon || "◈"} ${node.type}`;
        }
</script>

<svelte:window />

<div class="gs-root">
        <!-- ── Top Bar ── -->
        <header class="gs-header">
                <div class="gs-header-left">
                        <span class="gs-logo">✦</span>
                        <h1>{title}</h1>
                </div>
                <div class="gs-header-center">
                        <div class="gs-mode-switch">
                                <button class="gs-mode-btn" class:active={mode === "edit"} onclick={() => mode = "edit"}>
                                        <span class="gs-mode-icon">✎</span> Edit
                                </button>
                                <button class="gs-mode-btn" class:active={mode === "preview"} onclick={() => mode = "preview"}>
                                        <span class="gs-mode-icon">◎</span> Preview
                                </button>
                                <button class="gs-mode-btn" class:active={mode === "code"} onclick={() => { mode = "code"; generateCode(); }}>
                                        <span class="gs-mode-icon">{'{ }'}</span> Code
                                </button>
                        </div>
                </div>
                <div class="gs-header-right">
                        <button class="gs-action-btn" onclick={undo} title="Undo (Ctrl+Z)">↩</button>
                        <button class="gs-action-btn" onclick={redo} title="Redo (Ctrl+Shift+Z)">↪</button>
                        <button class="gs-action-btn gs-danger" onclick={clearAll} title="Clear All">🗑</button>
                        <button class="gs-action-btn" onclick={() => templateOpen = !templateOpen} title="Templates">✦</button>
                        <button class="gs-action-btn gs-vibe-btn" class:gs-vibe-active={vibeOpen} onclick={() => vibeOpen = !vibeOpen} title="Vibe Mode (AI Chat)">
                                ⚡ Vibe
                        </button>
                        <button class="gs-generate-btn" onclick={() => { generateCode(); mode = "code"; }}>
                                ✨ Generate
                        </button>
                </div>
        </header>

        <!-- ── Template Modal ── -->
        {#if templateOpen}
                <div class="gs-modal-overlay" onclick={() => templateOpen = false}>
                        <div class="gs-modal" onclick={(e) => e.stopPropagation()}>
                                <h2>Choose a Template</h2>
                                <div class="gs-template-grid">
                                        {#each templates as t}
                                                <button class="gs-template-card" onclick={() => applyTemplate(t)}>
                                                        <span class="gs-template-icon">{t.icon}</span>
                                                        <span class="gs-template-name">{t.name}</span>
                                                        <span class="gs-template-desc">{t.description}</span>
                                                </button>
                                        {/each}
                                </div>
                        </div>
                </div>
        {/if}

        <!-- ── Main Body ── -->
        <div class="gs-body">
                <!-- ── Left: Component Palette ── -->
                {#if mode === "edit"}
                        <aside class="gs-palette">
                                <div class="gs-search-wrap">
                                        <span class="gs-search-icon">⌕</span>
                                        <input
                                                type="text"
                                                placeholder="Search components..."
                                                bind:value={searchQuery}
                                                class="gs-search"
                                        />
                                </div>

                                {#if filteredLayout.length > 0}
                                        <div class="gs-palette-section">
                                                <h3>Layout</h3>
                                                {#each filteredLayout as comp}
                                                        <button class="gs-palette-item gs-layout-item" onclick={() => addNode(comp.type)}>
                                                                <span class="gs-palette-icon">{comp.icon}</span>{comp.type}
                                                        </button>
                                                {/each}
                                        </div>
                                {/if}

                                {#if filteredAction.length > 0}
                                        <div class="gs-palette-section">
                                                <h3>Action</h3>
                                                {#each filteredAction as comp}
                                                        <button class="gs-palette-item" onclick={() => addNode(comp.type)}>
                                                                <span class="gs-palette-icon">{comp.icon}</span>{comp.type}
                                                        </button>
                                                {/each}
                                        </div>
                                {/if}

                                {#if filteredInput.length > 0}
                                        <div class="gs-palette-section">
                                                <h3>Input</h3>
                                                {#each filteredInput as comp}
                                                        <button class="gs-palette-item" onclick={() => addNode(comp.type)}>
                                                                <span class="gs-palette-icon">{comp.icon}</span>{comp.type}
                                                        </button>
                                                {/each}
                                        </div>
                                {/if}

                                {#if filteredMedia.length > 0}
                                        <div class="gs-palette-section">
                                                <h3>Media</h3>
                                                {#each filteredMedia as comp}
                                                        <button class="gs-palette-item" onclick={() => addNode(comp.type)}>
                                                                <span class="gs-palette-icon">{comp.icon}</span>{comp.type}
                                                        </button>
                                                {/each}
                                        </div>
                                {/if}

                                {#if filteredOutput.length > 0}
                                        <div class="gs-palette-section">
                                                <h3>Output</h3>
                                                {#each filteredOutput as comp}
                                                        <button class="gs-palette-item" onclick={() => addNode(comp.type)}>
                                                                <span class="gs-palette-icon">{comp.icon}</span>{comp.type}
                                                        </button>
                                                {/each}
                                        </div>
                                {/if}
                        </aside>
                {/if}

                <!-- ── Center: Canvas ── -->
                <main class="gs-canvas-area">
                        {#if mode === "edit" || mode === "preview"}
                                <div class="gs-canvas-scroll">
                                        <div class="gs-canvas" class:gs-preview={mode === "preview"}>
                                                {#if tree.kind === "layout" && tree.children.length === 0}
                                                        <div class="gs-empty-canvas">
                                                                <div class="gs-empty-icon">✦</div>
                                                                <p>Add components from the left panel or choose a template</p>
                                                        </div>
                                                {:else}
                                                        {#each tree.children as child, i (child.id)}
                                                                {@render renderNode(child, 0, tree)}
                                                        {/each}
                                                {/if}
                                        </div>
                                </div>
                        {:else if mode === "code"}
                                <div class="gs-code-view">
                                        <div class="gs-code-header">
                                                <span>Generated Code</span>
                                                <button class="gs-copy-btn" onclick={() => navigator.clipboard?.writeText(getFullCode())}>
                                                        ⎘ Copy
                                                </button>
                                        </div>
                                        <pre class="gs-code-block"><code>{getFullCode()}</code></pre>
                                </div>
                        {/if}
                </main>

                <!-- ── Right: Inspector ── -->
                {#if mode === "edit"}
                        <aside class="gs-inspector">
                                <div class="gs-inspector-tabs">
                                        <button class="gs-inspector-tab" class:active={rightTab === "props"} onclick={() => rightTab = "props"}>Props</button>
                                        <button class="gs-inspector-tab" class:active={rightTab === "events"} onclick={() => rightTab = "events"}>Events</button>
                                        <button class="gs-inspector-tab" class:active={rightTab === "tree"} onclick={() => rightTab = "tree"}>Tree</button>
                                </div>

                                <div class="gs-inspector-content">
                                        {#if rightTab === "props"}
                                                {#if selectedNode}
                                                        <div class="gs-props-form">
                                                                <div class="gs-prop-header">
                                                                        <span class="gs-prop-type-badge" class:gs-layout-badge={selectedNode.kind === "layout"}>
                                                                                {selectedNode.kind === "layout" ? "⊞" : components[selectedNode.type]?.icon || "◈"}
                                                                                {selectedNode.type}
                                                                        </span>
                                                                        <button class="gs-prop-move" onclick={() => moveNode(selectedId!, "up")} title="Move up">↑</button>
                                                                        <button class="gs-prop-move" onclick={() => moveNode(selectedId!, "down")} title="Move down">↓</button>
                                                                        <button class="gs-prop-delete" onclick={() => selectedId && removeNode(selectedId)} title="Delete">✕</button>
                                                                </div>

                                                                {#each Object.entries(selectedNode.props) as [key, val]}
                                                                        <div class="gs-prop-group">
                                                                                <label>{key}</label>
                                                                                {#if key === "choices"}
                                                                                        <input
                                                                                                type="text"
                                                                                                value={JSON.stringify(val)}
                                                                                                onchange={(e) => { try { updateProp(key, JSON.parse((e.target as HTMLInputElement).value)); } catch {} }}
                                                                                        />
                                                                                {:else if key === "labels"}
                                                                                        <input
                                                                                                type="text"
                                                                                                value={JSON.stringify(val)}
                                                                                                onchange={(e) => { try { updateProp(key, JSON.parse((e.target as HTMLInputElement).value)); } catch {} }}
                                                                                        />
                                                                                {:else if typeof val === "boolean"}
                                                                                        <select onchange={(e) => updateProp(key, (e.target as HTMLSelectElement).value === "true")}>
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

                                                                {#if selectedNode.kind === "layout"}
                                                                        <button class="gs-add-child-btn" onclick={() => addNode("Textbox", selectedId!)}>
                                                                                + Add Component
                                                                        </button>
                                                                {/if}
                                                        </div>
                                                {:else}
                                                        <div class="gs-props-empty">
                                                                <div class="gs-props-empty-icon">◎</div>
                                                                <p>Select a component to edit its properties</p>
                                                        </div>
                                                {/if}
                                        {:else if rightTab === "events"}
                                                <div class="gs-events-panel">
                                                        <button class="gs-add-event-btn" onclick={addEvent}>+ Add Event</button>
                                                        {#each events as evt, i (evt.id)}
                                                                <div class="gs-event-card">
                                                                        <div class="gs-event-header">
                                                                                <span class="gs-event-num">E{i + 1}</span>
                                                                                <button class="gs-event-delete" onclick={() => removeEvent(evt.id)}>✕</button>
                                                                        </div>
                                                                        <div class="gs-event-form">
                                                                                <div class="gs-event-field">
                                                                                        <label>Source</label>
                                                                                        <select value={evt.source_id} onchange={(e) => { saveHistory(); evt.source_id = (e.target as HTMLSelectElement).value; }}>
                                                                                                <option value="">Select...</option>
                                                                                                {#each componentNodes as cn}
                                                                                                        <option value={cn.id} selected={evt.source_id === cn.id}>{cn.type} ({cn.props.label || cn.id})</option>
                                                                                                {/each}
                                                                                        </select>
                                                                                </div>
                                                                                <div class="gs-event-field">
                                                                                        <label>Event</label>
                                                                                        <input type="text" value={evt.event} onchange={(e) => { saveHistory(); evt.event = (e.target as HTMLInputElement).value; }} />
                                                                                </div>
                                                                                <div class="gs-event-field">
                                                                                        <label>Function</label>
                                                                                        <input type="text" value={evt.fn_name} onchange={(e) => { saveHistory(); evt.fn_name = (e.target as HTMLInputElement).value; }} />
                                                                                </div>
                                                                                <div class="gs-event-field">
                                                                                        <label>Inputs</label>
                                                                                        <select multiple value={evt.inputs} onchange={(e) => {
                                                                                                saveHistory();
                                                                                                const sel = Array.from((e.target as HTMLSelectElement).selectedOptions).map(o => o.value);
                                                                                                evt.inputs = sel;
                                                                                        }}>
                                                                                                {#each componentNodes as cn}
                                                                                                        <option value={cn.id} selected={evt.inputs.includes(cn.id)}>{cn.type} ({cn.props.label || cn.id})</option>
                                                                                                {/each}
                                                                                        </select>
                                                                                </div>
                                                                                <div class="gs-event-field">
                                                                                        <label>Outputs</label>
                                                                                        <select multiple value={evt.outputs} onchange={(e) => {
                                                                                                saveHistory();
                                                                                                const sel = Array.from((e.target as HTMLSelectElement).selectedOptions).map(o => o.value);
                                                                                                evt.outputs = sel;
                                                                                        }}>
                                                                                                {#each componentNodes as cn}
                                                                                                        <option value={cn.id} selected={evt.outputs.includes(cn.id)}>{cn.type} ({cn.props.label || cn.id})</option>
                                                                                                {/each}
                                                                                        </select>
                                                                                </div>
                                                                        </div>
                                                                </div>
                                                        {/each}
                                                        {#if events.length === 0}
                                                                <div class="gs-events-empty">
                                                                        <p>No events configured yet. Click "+ Add Event" to wire up component interactions.</p>
                                                                </div>
                                                        {/if}
                                                </div>
                                        {:else if rightTab === "tree"}
                                                <div class="gs-tree-view">
                                                        {#each tree.children as child, i (child.id)}
                                                                {@html renderTreeHTML(child, 0)}
                                                        {/each}
                                                        {#if tree.kind === "layout" && tree.children.length === 0}
                                                                <div class="gs-tree-empty">Tree is empty</div>
                                                        {/if}
                                                </div>
                                        {/if}
                                </div>
                        </aside>
                {/if}
        </div>

        <!-- ── Vibe Mode: AI Chat Panel ── -->
        {#if vibeOpen}
                <aside class="gs-vibe-panel">
                        <div class="gs-vibe-header">
                                <span class="gs-vibe-title">⚡ Vibe Mode</span>
                                <button class="gs-vibe-close" onclick={() => vibeOpen = false}>✕</button>
                        </div>

                        <div class="gs-vibe-messages">
                                {#if vibeMessages.length === 0}
                                        <div class="gs-vibe-empty">
                                                <div class="gs-vibe-empty-icon">⚡</div>
                                                <p>Describe what you want to build and AI will generate the code</p>
                                                <div class="gs-vibe-starters">
                                                        {#each vibeStarterQueries as q}
                                                                <button class="gs-vibe-starter" onclick={() => vibeSubmit(q)}>{q}</button>
                                                        {/each}
                                                </div>
                                        </div>
                                {:else}
                                        {#each vibeMessages as msg, i (i)}
                                                <div class="gs-vibe-msg" class:gs-vibe-bot={msg.isBot} class:gs-vibe-user={!msg.isBot}>
                                                        <div class="gs-vibe-msg-text">{msg.text}</div>
                                                        {#if !msg.isBot && msg.hash}
                                                                <button class="gs-vibe-undo" onclick={() => vibeUndo(i)}>Undo</button>
                                                        {/if}
                                                        {#if msg.isBot && msg.diffStats && (msg.diffStats.lines_added > 0 || msg.diffStats.lines_removed > 0)}
                                                                <div class="gs-vibe-diff">
                                                                        {#if msg.diffStats.lines_added > 0}<span class="gs-diff-add">+{msg.diffStats.lines_added}</span>{/if}
                                                                        {#if msg.diffStats.lines_removed > 0}<span class="gs-diff-rem">-{msg.diffStats.lines_removed}</span>{/if}
                                                                </div>
                                                        {/if}
                                                </div>
                                        {/each}
                                        {#if vibeLoading}
                                                <div class="gs-vibe-msg gs-vibe-bot gs-vibe-typing">
                                                        <div class="gs-vibe-dots"><span></span><span></span><span></span></div>
                                                </div>
                                        {/if}
                                {/if}
                        </div>

                        <div class="gs-vibe-input-area">
                                <div class="gs-vibe-powered">Powered by <code>gpt-oss</code></div>
                                <div class="gs-vibe-input-row">
                                        <textarea
                                                class="gs-vibe-input"
                                                placeholder="What can I add or change?"
                                                bind:value={vibePrompt}
                                                onkeydown={(e) => {
                                                        if (e.key === "Enter" && !e.shiftKey) {
                                                                e.preventDefault();
                                                                vibeSubmit();
                                                        }
                                                }}
                                        ></textarea>
                                        <button class="gs-vibe-send" onclick={() => vibeSubmit()} disabled={vibeLoading || !vibePrompt.trim()}>
                                                ➤
                                        </button>
                                </div>
                        </div>
                </aside>
        {/if}
</div>

<!-- ── Recursive node rendering ── -->
{#snippet renderNode(node: TreeNode, depth: number, parent: TreeNode)}
        {#if node.kind === "layout"}
                <div
                        class="gs-layout-block gs-layout-{node.type}"
                        class:gs-selected={node.id === selectedId}
                        onclick={(e) => { e.stopPropagation(); selectedId = node.id; }}
                >
                        <div class="gs-layout-label" onclick={(e) => { e.stopPropagation(); selectedId = node.id; }}>
                                <span class="gs-layout-toggle" onclick={(e) => { e.stopPropagation(); toggleExpand(node.id); }}>
                                        {expandedNodes.has(node.id) ? "▾" : "▸"}
                                </span>
                                <span class="gs-layout-type">{node.type}</span>
                                {#if node.props.label}
                                        <span class="gs-layout-prop-label">"{node.props.label}"</span>
                                {/if}
                                <button class="gs-layout-add" onclick={(e) => { e.stopPropagation(); addNode("Textbox", node.id); }}>+</button>
                        </div>
                        {#if expandedNodes.has(node.id) !== false}
                                <div class="gs-layout-children">
                                        {#each node.children as child, i (child.id)}
                                                {@render renderNode(child, depth + 1, node)}
                                        {/each}
                                        {#if node.children.length === 0}
                                                <div class="gs-layout-drop" onclick={() => { selectedId = node.id; addNode("Textbox", node.id); }}>
                                                        Drop components here
                                                </div>
                                        {/if}
                                </div>
                        {/if}
                </div>
        {:else}
                <div
                        class="gs-widget"
                        class:gs-selected={node.id === selectedId}
                        onclick={(e) => { e.stopPropagation(); selectedId = node.id; }}
                >
                        <div class="gs-widget-label">
                                <span class="gs-widget-icon">{components[node.type]?.icon || "◈"}</span>
                                <span>{node.type}</span>
                                {#if node.props.label}
                                        <span class="gs-widget-prop-label">"{node.props.label}"</span>
                                {/if}
                        </div>
                        <div class="gs-widget-body">
                                {@html widgetPreview(node)}
                        </div>
                </div>
        {/if}
{/snippet}

<!-- ── Tree HTML for right panel ── -->
{#snippet renderTreeHTML(node: TreeNode, depth: number)}
        <div
                class="gs-tree-node"
                style="padding-left: {depth * 16 + 8}px"
                class:gs-tree-selected={node.id === selectedId}
                onclick={() => selectedId = node.id}
        >
                {#if node.kind === "layout"}
                        <span class="gs-tree-toggle" onclick={(e) => { e.stopPropagation(); toggleExpand(node.id); }}>
                                {expandedNodes.has(node.id) ? "▾" : "▸"}
                        </span>
                        <span class="gs-tree-icon">⊞</span>
                {:else}
                        <span class="gs-tree-icon">{components[node.type]?.icon || "◈"}</span>
                {/if}
                <span class="gs-tree-label">{node.type}</span>
                {#if node.props.label}
                        <span class="gs-tree-prop">"{node.props.label}"</span>
                {/if}
                <button class="gs-tree-delete" onclick={(e) => { e.stopPropagation(); removeNode(node.id); }}>✕</button>
        </div>
        {#if node.kind === "layout" && expandedNodes.has(node.id)}
                {#each node.children as child (child.id)}
                        {@html renderTreeHTML(child, depth + 1)}
                {/each}
        {/if}
{/snippet}

<style>
        /* ── Vibe Theme: Dark glassmorphism with purple accents ── */
        :root {
                --gs-bg: #0c0e1a;
                --gs-surface: #151829;
                --gs-surface-2: #1c2035;
                --gs-surface-3: #252a42;
                --gs-border: #2a2f4a;
                --gs-border-light: #363d5c;
                --gs-text: #e2e8f0;
                --gs-text-muted: #8b92a8;
                --gs-accent: #8b5cf6;
                --gs-accent-light: #a78bfa;
                --gs-accent-glow: rgba(139, 92, 246, 0.25);
                --gs-accent-2: #6366f1;
                --gs-gradient: linear-gradient(135deg, #8b5cf6, #6366f1);
                --gs-danger: #ef4444;
                --gs-success: #22c55e;
                --gs-glass: rgba(21, 24, 41, 0.8);
                --gs-glass-border: rgba(139, 92, 246, 0.15);
                --gs-radius: 10px;
                --gs-radius-sm: 6px;
                --gs-radius-lg: 14px;
                --gs-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
                --gs-shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.4);
                --gs-transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
                box-sizing: border-box;
        }

        .gs-root {
                font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                color: var(--gs-text);
                background: var(--gs-bg);
                height: 85vh;
                min-height: 560px;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                border-radius: var(--gs-radius-lg);
                border: 1px solid var(--gs-border);
        }

        /* ── Header ── */
        .gs-header {
                background: var(--gs-surface);
                border-bottom: 1px solid var(--gs-border);
                padding: 8px 16px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                z-index: 100;
                flex-shrink: 0;
                backdrop-filter: blur(12px);
        }

        .gs-header-left {
                display: flex;
                align-items: center;
                gap: 10px;
        }

        .gs-logo {
                font-size: 20px;
                background: var(--gs-gradient);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-weight: 800;
        }

        .gs-header h1 {
                font-size: 15px;
                font-weight: 600;
                margin: 0;
                background: linear-gradient(135deg, #e2e8f0, #a78bfa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                letter-spacing: -0.01em;
        }

        .gs-header-center {
                display: flex;
                align-items: center;
        }

        .gs-mode-switch {
                display: flex;
                background: var(--gs-surface-2);
                border-radius: 8px;
                padding: 2px;
                border: 1px solid var(--gs-border);
        }

        .gs-mode-btn {
                background: none;
                border: none;
                color: var(--gs-text-muted);
                padding: 5px 14px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
                cursor: pointer;
                transition: var(--gs-transition);
                display: flex;
                align-items: center;
                gap: 5px;
        }

        .gs-mode-btn:hover {
                color: var(--gs-text);
        }

        .gs-mode-btn.active {
                background: var(--gs-gradient);
                color: white;
                box-shadow: 0 2px 8px var(--gs-accent-glow);
        }

        .gs-mode-icon {
                font-size: 11px;
        }

        .gs-header-right {
                display: flex;
                align-items: center;
                gap: 6px;
        }

        .gs-action-btn {
                width: 32px;
                height: 32px;
                border-radius: var(--gs-radius-sm);
                background: var(--gs-surface-2);
                border: 1px solid var(--gs-border);
                color: var(--gs-text-muted);
                font-size: 14px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: var(--gs-transition);
        }

        .gs-action-btn:hover {
                background: var(--gs-surface-3);
                color: var(--gs-text);
                border-color: var(--gs-border-light);
        }

        .gs-action-btn.gs-danger:hover {
                background: rgba(239, 68, 68, 0.15);
                color: var(--gs-danger);
                border-color: rgba(239, 68, 68, 0.3);
        }

        .gs-generate-btn {
                background: var(--gs-gradient);
                border: none;
                color: white;
                padding: 6px 16px;
                border-radius: var(--gs-radius-sm);
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                transition: var(--gs-transition);
                box-shadow: 0 2px 12px var(--gs-accent-glow);
        }

        .gs-generate-btn:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 20px rgba(139, 92, 246, 0.4);
        }

        /* ── Modal ── */
        .gs-modal-overlay {
                position: fixed;
                top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0, 0, 0, 0.6);
                backdrop-filter: blur(4px);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
        }

        .gs-modal {
                background: var(--gs-surface);
                border: 1px solid var(--gs-border);
                border-radius: var(--gs-radius-lg);
                padding: 24px;
                width: 480px;
                box-shadow: var(--gs-shadow-lg);
        }

        .gs-modal h2 {
                font-size: 18px;
                font-weight: 600;
                margin: 0 0 16px;
                color: var(--gs-text);
        }

        .gs-template-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
        }

        .gs-template-card {
                background: var(--gs-surface-2);
                border: 1px solid var(--gs-border);
                border-radius: var(--gs-radius);
                padding: 14px;
                cursor: pointer;
                transition: var(--gs-transition);
                text-align: left;
                display: flex;
                flex-direction: column;
                gap: 4px;
        }

        .gs-template-card:hover {
                border-color: var(--gs-accent);
                background: var(--gs-surface-3);
                box-shadow: 0 0 20px var(--gs-accent-glow);
                transform: translateY(-2px);
        }

        .gs-template-icon {
                font-size: 24px;
        }

        .gs-template-name {
                font-size: 13px;
                font-weight: 600;
                color: var(--gs-text);
        }

        .gs-template-desc {
                font-size: 11px;
                color: var(--gs-text-muted);
        }

        /* ── Main Body ── */
        .gs-body {
                display: flex;
                flex: 1;
                overflow: hidden;
        }

        /* ── Palette ── */
        .gs-palette {
                width: 200px;
                background: var(--gs-surface);
                border-right: 1px solid var(--gs-border);
                overflow-y: auto;
                padding: 8px;
                flex-shrink: 0;
        }

        .gs-search-wrap {
                position: relative;
                margin-bottom: 8px;
        }

        .gs-search-icon {
                position: absolute;
                left: 8px;
                top: 50%;
                transform: translateY(-50%);
                font-size: 12px;
                color: var(--gs-text-muted);
        }

        .gs-search {
                width: 100%;
                padding: 6px 8px 6px 26px;
                border: 1px solid var(--gs-border);
                border-radius: var(--gs-radius-sm);
                background: var(--gs-surface-2);
                color: var(--gs-text);
                font-size: 11px;
                outline: none;
                transition: var(--gs-transition);
        }

        .gs-search:focus {
                border-color: var(--gs-accent);
                box-shadow: 0 0 0 2px var(--gs-accent-glow);
        }

        .gs-palette-section {
                margin-bottom: 4px;
        }

        .gs-palette-section h3 {
                font-size: 9px;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: var(--gs-text-muted);
                margin: 8px 0 4px;
                padding: 0 4px;
                font-weight: 600;
        }

        .gs-palette-item {
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 5px 8px;
                border-radius: var(--gs-radius-sm);
                cursor: pointer;
                font-size: 11px;
                font-weight: 500;
                border: 1px solid transparent;
                transition: var(--gs-transition);
                user-select: none;
                width: 100%;
                text-align: left;
                background: none;
                color: var(--gs-text);
        }

        .gs-palette-item:hover {
                background: rgba(139, 92, 246, 0.1);
                border-color: rgba(139, 92, 246, 0.2);
                color: var(--gs-accent-light);
        }

        .gs-palette-item:active {
                transform: scale(0.97);
        }

        .gs-palette-item.gs-layout-item {
                color: var(--gs-accent-light);
        }

        .gs-palette-icon {
                font-size: 12px;
                width: 16px;
                text-align: center;
                font-family: monospace;
                font-weight: 700;
        }

        /* ── Canvas ── */
        .gs-canvas-area {
                flex: 1;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                background: var(--gs-bg);
        }

        .gs-canvas-scroll {
                flex: 1;
                overflow: auto;
                padding: 20px;
        }

        .gs-canvas {
                min-height: 100%;
                background: var(--gs-surface);
                border-radius: var(--gs-radius);
                border: 1px solid var(--gs-border);
                padding: 16px;
                display: flex;
                flex-direction: column;
                gap: 8px;
        }

        .gs-canvas.gs-preview {
                background: white;
                padding: 24px;
        }

        .gs-empty-canvas {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 300px;
                color: var(--gs-text-muted);
                gap: 12px;
        }

        .gs-empty-icon {
                font-size: 48px;
                background: var(--gs-gradient);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                opacity: 0.5;
        }

        .gs-empty-canvas p {
                font-size: 13px;
                color: var(--gs-text-muted);
        }

        /* ── Layout Block ── */
        .gs-layout-block {
                border: 1px solid var(--gs-border);
                border-radius: var(--gs-radius-sm);
                overflow: hidden;
                transition: var(--gs-transition);
        }

        .gs-layout-block.gs-selected {
                border-color: var(--gs-accent);
                box-shadow: 0 0 0 2px var(--gs-accent-glow);
        }

        .gs-layout-label {
                display: flex;
                align-items: center;
                gap: 4px;
                padding: 4px 8px;
                background: var(--gs-surface-2);
                border-bottom: 1px solid var(--gs-border);
                font-size: 10px;
                font-weight: 600;
                color: var(--gs-accent-light);
                text-transform: uppercase;
                letter-spacing: 0.04em;
                cursor: pointer;
        }

        .gs-layout-toggle {
                cursor: pointer;
                font-size: 10px;
                color: var(--gs-text-muted);
        }

        .gs-layout-type {
                color: var(--gs-accent-light);
        }

        .gs-layout-prop-label {
                color: var(--gs-text-muted);
                font-style: italic;
        }

        .gs-layout-add {
                margin-left: auto;
                background: none;
                border: 1px solid var(--gs-border);
                color: var(--gs-text-muted);
                width: 18px;
                height: 18px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: var(--gs-transition);
        }

        .gs-layout-add:hover {
                background: var(--gs-accent);
                color: white;
                border-color: var(--gs-accent);
        }

        .gs-layout-children {
                padding: 8px;
                display: flex;
                gap: 8px;
        }

        .gs-layout-row > .gs-layout-children {
                flex-direction: row;
        }

        .gs-layout-column > .gs-layout-children,
        .gs-layout-tabitem > .gs-layout-children,
        .gs-layout-accordion > .gs-layout-children,
        .gs-layout-group > .gs-layout-children {
                flex-direction: column;
        }

        .gs-layout-tabs > .gs-layout-children {
                flex-direction: column;
                gap: 0;
        }

        .gs-layout-drop {
                border: 1px dashed var(--gs-border-light);
                border-radius: var(--gs-radius-sm);
                padding: 16px;
                text-align: center;
                color: var(--gs-text-muted);
                font-size: 11px;
                cursor: pointer;
                transition: var(--gs-transition);
                min-height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
        }

        .gs-layout-drop:hover {
                border-color: var(--gs-accent);
                background: rgba(139, 92, 246, 0.05);
                color: var(--gs-accent-light);
        }

        /* ── Widget ── */
        .gs-widget {
                background: var(--gs-surface-2);
                border: 1px solid var(--gs-border);
                border-radius: var(--gs-radius-sm);
                overflow: hidden;
                transition: var(--gs-transition);
                flex: 1;
                min-width: 0;
                cursor: pointer;
        }

        .gs-widget.gs-selected {
                border-color: var(--gs-accent);
                box-shadow: 0 0 0 2px var(--gs-accent-glow);
        }

        .gs-widget:hover {
                border-color: var(--gs-border-light);
        }

        .gs-widget-label {
                display: flex;
                align-items: center;
                gap: 4px;
                padding: 3px 8px;
                background: var(--gs-surface-3);
                border-bottom: 1px solid var(--gs-border);
                font-size: 9px;
                font-weight: 600;
                color: var(--gs-text-muted);
                text-transform: uppercase;
                letter-spacing: 0.04em;
        }

        .gs-widget-icon {
                font-family: monospace;
                font-weight: 700;
                font-size: 10px;
        }

        .gs-widget-prop-label {
                color: var(--gs-text-muted);
                font-style: italic;
                font-weight: 400;
                text-transform: none;
        }

        .gs-widget-body {
                padding: 8px 10px;
                font-size: 12px;
        }

        /* ── Code View ── */
        .gs-code-view {
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow: hidden;
        }

        .gs-code-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 8px 16px;
                background: var(--gs-surface);
                border-bottom: 1px solid var(--gs-border);
                font-size: 12px;
                font-weight: 500;
                color: var(--gs-text-muted);
        }

        .gs-copy-btn {
                background: var(--gs-surface-2);
                border: 1px solid var(--gs-border);
                color: var(--gs-text-muted);
                padding: 4px 10px;
                border-radius: var(--gs-radius-sm);
                font-size: 11px;
                cursor: pointer;
                transition: var(--gs-transition);
        }

        .gs-copy-btn:hover {
                background: var(--gs-accent);
                color: white;
                border-color: var(--gs-accent);
        }

        .gs-code-block {
                flex: 1;
                overflow: auto;
                padding: 16px;
                margin: 0;
                background: var(--gs-bg);
                font-family: "Fira Code", "SF Mono", monospace;
                font-size: 12px;
                line-height: 1.6;
                color: #a5f3fc;
                tab-size: 4;
        }

        .gs-code-block code {
                font-family: inherit;
        }

        /* ── Inspector ── */
        .gs-inspector {
                width: 260px;
                background: var(--gs-surface);
                border-left: 1px solid var(--gs-border);
                overflow-y: auto;
                flex-shrink: 0;
                display: flex;
                flex-direction: column;
        }

        .gs-inspector-tabs {
                display: flex;
                border-bottom: 1px solid var(--gs-border);
                flex-shrink: 0;
        }

        .gs-inspector-tab {
                flex: 1;
                padding: 8px;
                background: none;
                border: none;
                color: var(--gs-text-muted);
                font-size: 11px;
                font-weight: 500;
                cursor: pointer;
                transition: var(--gs-transition);
                border-bottom: 2px solid transparent;
        }

        .gs-inspector-tab:hover {
                color: var(--gs-text);
        }

        .gs-inspector-tab.active {
                color: var(--gs-accent-light);
                border-bottom-color: var(--gs-accent);
        }

        .gs-inspector-content {
                flex: 1;
                overflow-y: auto;
                padding: 10px;
        }

        /* ── Props Form ── */
        .gs-props-form {
                display: flex;
                flex-direction: column;
                gap: 8px;
        }

        .gs-prop-header {
                display: flex;
                align-items: center;
                gap: 4px;
                margin-bottom: 4px;
        }

        .gs-prop-type-badge {
                display: flex;
                align-items: center;
                gap: 4px;
                background: var(--gs-surface-2);
                border: 1px solid var(--gs-border);
                border-radius: var(--gs-radius-sm);
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
                color: var(--gs-accent-light);
                flex: 1;
        }

        .gs-prop-type-badge.gs-layout-badge {
                color: #f59e0b;
        }

        .gs-prop-move, .gs-prop-delete {
                width: 24px;
                height: 24px;
                border-radius: 4px;
                background: var(--gs-surface-2);
                border: 1px solid var(--gs-border);
                color: var(--gs-text-muted);
                font-size: 11px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: var(--gs-transition);
        }

        .gs-prop-move:hover {
                background: var(--gs-surface-3);
                color: var(--gs-text);
        }

        .gs-prop-delete:hover {
                background: rgba(239, 68, 68, 0.15);
                color: var(--gs-danger);
                border-color: rgba(239, 68, 68, 0.3);
        }

        .gs-prop-group {
                display: flex;
                flex-direction: column;
                gap: 2px;
        }

        .gs-prop-group label {
                font-size: 9px;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: var(--gs-text-muted);
                font-weight: 600;
        }

        .gs-prop-group input,
        .gs-prop-group select {
                padding: 4px 8px;
                border: 1px solid var(--gs-border);
                border-radius: var(--gs-radius-sm);
                background: var(--gs-surface-2);
                color: var(--gs-text);
                font-size: 11px;
                outline: none;
                transition: var(--gs-transition);
        }

        .gs-prop-group input:focus,
        .gs-prop-group select:focus {
                border-color: var(--gs-accent);
                box-shadow: 0 0 0 2px var(--gs-accent-glow);
        }

        .gs-prop-group select[multiple] {
                min-height: 60px;
        }

        .gs-add-child-btn {
                width: 100%;
                padding: 6px;
                background: rgba(139, 92, 246, 0.1);
                border: 1px dashed rgba(139, 92, 246, 0.3);
                border-radius: var(--gs-radius-sm);
                color: var(--gs-accent-light);
                font-size: 11px;
                cursor: pointer;
                transition: var(--gs-transition);
                margin-top: 4px;
        }

        .gs-add-child-btn:hover {
                background: rgba(139, 92, 246, 0.2);
                border-color: var(--gs-accent);
        }

        .gs-props-empty {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 40px 10px;
                color: var(--gs-text-muted);
                text-align: center;
                gap: 8px;
        }

        .gs-props-empty-icon {
                font-size: 28px;
                opacity: 0.4;
        }

        .gs-props-empty p {
                font-size: 12px;
                margin: 0;
        }

        /* ── Events Panel ── */
        .gs-events-panel {
                display: flex;
                flex-direction: column;
                gap: 8px;
        }

        .gs-add-event-btn {
                width: 100%;
                padding: 6px;
                background: rgba(139, 92, 246, 0.1);
                border: 1px dashed rgba(139, 92, 246, 0.3);
                border-radius: var(--gs-radius-sm);
                color: var(--gs-accent-light);
                font-size: 11px;
                cursor: pointer;
                transition: var(--gs-transition);
        }

        .gs-add-event-btn:hover {
                background: rgba(139, 92, 246, 0.2);
                border-color: var(--gs-accent);
        }

        .gs-event-card {
                background: var(--gs-surface-2);
                border: 1px solid var(--gs-border);
                border-radius: var(--gs-radius-sm);
                padding: 8px;
        }

        .gs-event-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 6px;
        }

        .gs-event-num {
                font-size: 10px;
                font-weight: 700;
                color: var(--gs-accent);
                background: rgba(139, 92, 246, 0.15);
                padding: 1px 6px;
                border-radius: 3px;
        }

        .gs-event-delete {
                background: none;
                border: none;
                color: var(--gs-text-muted);
                cursor: pointer;
                font-size: 11px;
                transition: var(--gs-transition);
        }

        .gs-event-delete:hover {
                color: var(--gs-danger);
        }

        .gs-event-form {
                display: flex;
                flex-direction: column;
                gap: 5px;
        }

        .gs-event-field label {
                display: block;
                font-size: 9px;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: var(--gs-text-muted);
                font-weight: 600;
                margin-bottom: 1px;
        }

        .gs-event-field select,
        .gs-event-field input {
                width: 100%;
                padding: 3px 6px;
                border: 1px solid var(--gs-border);
                border-radius: 4px;
                background: var(--gs-bg);
                color: var(--gs-text);
                font-size: 10px;
                outline: none;
        }

        .gs-event-field select[multiple] {
                min-height: 50px;
        }

        .gs-event-field select:focus,
        .gs-event-field input:focus {
                border-color: var(--gs-accent);
        }

        .gs-events-empty {
                padding: 20px 8px;
                text-align: center;
                color: var(--gs-text-muted);
                font-size: 12px;
        }

        /* ── Tree View ── */
        .gs-tree-view {
                font-size: 11px;
        }

        .gs-tree-node {
                display: flex;
                align-items: center;
                gap: 4px;
                padding: 3px 4px;
                border-radius: 4px;
                cursor: pointer;
                transition: var(--gs-transition);
        }

        .gs-tree-node:hover {
                background: var(--gs-surface-2);
        }

        .gs-tree-node.gs-tree-selected {
                background: rgba(139, 92, 246, 0.15);
                color: var(--gs-accent-light);
        }

        .gs-tree-toggle {
                font-size: 9px;
                color: var(--gs-text-muted);
                cursor: pointer;
                width: 12px;
                text-align: center;
        }

        .gs-tree-icon {
                font-size: 10px;
                font-family: monospace;
                font-weight: 700;
        }

        .gs-tree-label {
                color: var(--gs-text);
                font-weight: 500;
        }

        .gs-tree-prop {
                color: var(--gs-text-muted);
                font-style: italic;
                font-size: 10px;
        }

        .gs-tree-delete {
                margin-left: auto;
                background: none;
                border: none;
                color: var(--gs-text-muted);
                cursor: pointer;
                font-size: 9px;
                opacity: 0;
                transition: var(--gs-transition);
        }

        .gs-tree-node:hover .gs-tree-delete {
                opacity: 1;
        }

        .gs-tree-delete:hover {
                color: var(--gs-danger);
        }

        .gs-tree-empty {
                padding: 16px 8px;
                text-align: center;
                color: var(--gs-text-muted);
                font-size: 12px;
        }

        /* ── Scrollbar ── */
        ::-webkit-scrollbar {
                width: 6px;
                height: 6px;
        }

        ::-webkit-scrollbar-track {
                background: transparent;
        }

        ::-webkit-scrollbar-thumb {
                background: var(--gs-border);
                border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
                background: var(--gs-border-light);
        }

        /* ── Vibe Mode Button ── */
        .gs-vibe-btn {
                font-size: 11px !important;
                font-weight: 600 !important;
                width: auto !important;
                padding: 0 10px !important;
                gap: 4px;
        }

        .gs-vibe-btn.gs-vibe-active {
                background: linear-gradient(135deg, #8b5cf6, #6366f1) !important;
                color: white !important;
                border-color: transparent !important;
                box-shadow: 0 2px 12px var(--gs-accent-glow);
        }

        /* ── Vibe Chat Panel ── */
        .gs-vibe-panel {
                width: 320px;
                background: var(--gs-surface);
                border-left: 1px solid var(--gs-border);
                display: flex;
                flex-direction: column;
                flex-shrink: 0;
                overflow: hidden;
        }

        .gs-vibe-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 8px 12px;
                border-bottom: 1px solid var(--gs-border);
                background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(99, 102, 241, 0.05));
        }

        .gs-vibe-title {
                font-size: 13px;
                font-weight: 600;
                background: var(--gs-gradient);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
        }

        .gs-vibe-close {
                background: none;
                border: none;
                color: var(--gs-text-muted);
                font-size: 12px;
                cursor: pointer;
                transition: var(--gs-transition);
        }

        .gs-vibe-close:hover {
                color: var(--gs-text);
        }

        .gs-vibe-messages {
                flex: 1;
                overflow-y: auto;
                padding: 12px;
                display: flex;
                flex-direction: column;
                gap: 8px;
        }

        .gs-vibe-empty {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 24px 12px;
                text-align: center;
                gap: 12px;
        }

        .gs-vibe-empty-icon {
                font-size: 36px;
                background: var(--gs-gradient);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                opacity: 0.6;
        }

        .gs-vibe-empty p {
                font-size: 12px;
                color: var(--gs-text-muted);
                margin: 0;
                line-height: 1.5;
        }

        .gs-vibe-starters {
                display: flex;
                flex-direction: column;
                gap: 6px;
                width: 100%;
                margin-top: 8px;
        }

        .gs-vibe-starter {
                background: var(--gs-surface-2);
                border: 1px solid var(--gs-border);
                border-radius: var(--gs-radius-sm);
                padding: 8px 10px;
                font-size: 11px;
                color: var(--gs-text);
                cursor: pointer;
                text-align: left;
                transition: var(--gs-transition);
                line-height: 1.4;
        }

        .gs-vibe-starter:hover {
                border-color: var(--gs-accent);
                background: rgba(139, 92, 246, 0.08);
                color: var(--gs-accent-light);
                transform: translateY(-1px);
        }

        .gs-vibe-msg {
                padding: 8px 10px;
                border-radius: var(--gs-radius-sm);
                font-size: 12px;
                line-height: 1.5;
                position: relative;
                white-space: pre-wrap;
                word-break: break-word;
        }

        .gs-vibe-msg.gs-vibe-user {
                background: rgba(139, 92, 246, 0.15);
                color: var(--gs-accent-light);
                margin-left: 16px;
                border: 1px solid rgba(139, 92, 246, 0.2);
        }

        .gs-vibe-msg.gs-vibe-bot {
                background: var(--gs-surface-2);
                color: var(--gs-text);
                margin-right: 16px;
                border: 1px solid var(--gs-border);
        }

        .gs-vibe-msg.gs-vibe-typing {
                padding: 10px;
        }

        .gs-vibe-msg-text {
                white-space: pre-wrap;
        }

        .gs-vibe-undo {
                position: absolute;
                top: 4px;
                right: 4px;
                background: var(--gs-surface-3);
                border: 1px solid var(--gs-border);
                border-radius: 4px;
                color: var(--gs-text-muted);
                font-size: 9px;
                padding: 2px 6px;
                cursor: pointer;
                transition: var(--gs-transition);
        }

        .gs-vibe-undo:hover {
                background: rgba(239, 68, 68, 0.15);
                color: var(--gs-danger);
                border-color: rgba(239, 68, 68, 0.3);
        }

        .gs-vibe-diff {
                margin-top: 4px;
                display: inline-flex;
                gap: 4px;
                font-size: 10px;
                font-weight: 600;
        }

        .gs-diff-add { color: #22c55e; }
        .gs-diff-rem { color: #ef4444; }

        .gs-vibe-dots {
                display: flex;
                gap: 4px;
                align-items: center;
                justify-content: center;
        }

        .gs-vibe-dots span {
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background: var(--gs-accent);
                animation: gs-bounce 1.4s infinite ease-in-out both;
        }

        .gs-vibe-dots span:nth-child(1) { animation-delay: -0.32s; }
        .gs-vibe-dots span:nth-child(2) { animation-delay: -0.16s; }
        .gs-vibe-dots span:nth-child(3) { animation-delay: 0; }

        @keyframes gs-bounce {
                0%, 80%, 100% { transform: scale(0); }
                40% { transform: scale(1); }
        }

        .gs-vibe-input-area {
                border-top: 1px solid var(--gs-border);
                padding: 8px 10px;
                background: var(--gs-surface);
        }

        .gs-vibe-powered {
                text-align: right;
                font-size: 10px;
                color: var(--gs-text-muted);
                margin-bottom: 6px;
        }

        .gs-vibe-powered code {
                background: var(--gs-surface-2);
                padding: 1px 4px;
                border-radius: 3px;
                font-size: 9px;
        }

        .gs-vibe-input-row {
                display: flex;
                gap: 6px;
                align-items: flex-end;
        }

        .gs-vibe-input {
                flex: 1;
                min-height: 36px;
                max-height: 100px;
                resize: none;
                background: var(--gs-surface-2);
                border: 1px solid var(--gs-border);
                border-radius: var(--gs-radius-sm);
                padding: 8px 10px;
                font-size: 12px;
                color: var(--gs-text);
                font-family: inherit;
                outline: none;
                transition: var(--gs-transition);
        }

        .gs-vibe-input:focus {
                border-color: var(--gs-accent);
                box-shadow: 0 0 0 2px var(--gs-accent-glow);
        }

        .gs-vibe-send {
                width: 36px;
                height: 36px;
                border-radius: var(--gs-radius-sm);
                background: var(--gs-gradient);
                border: none;
                color: white;
                font-size: 14px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: var(--gs-transition);
                flex-shrink: 0;
        }

        .gs-vibe-send:hover:not(:disabled) {
                transform: scale(1.05);
                box-shadow: 0 2px 12px var(--gs-accent-glow);
        }

        .gs-vibe-send:disabled {
                opacity: 0.4;
                cursor: not-allowed;
        }
</style>
