const STORAGE_KEY = 'parametric_process.workflow.v1';

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function downloadJson(filename, data) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

function safeFilename(value) {
    return String(value || 'workflow')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9_-]+/g, '_')
        .replace(/^_+|_+$/g, '') || 'workflow';
}

export class WorkflowModeler {
    constructor(options = {}) {
        this.options = options;
        this.catalog = {};
        this.graph = { schema_version: 1, name: 'Balanced Urban Optimization', nodes: [], edges: [] };
        this.selectedNodeId = null;
        this.selectedEdgeId = null;
        this.connectingSourceId = null;
        this.nextId = 1;
        this.lastResult = null;
        this.dragState = null;

        this.view = document.getElementById('workflow-modeler-view');
        this.canvas = document.getElementById('workflow-canvas');
        this.nodeLayer = document.getElementById('workflow-node-layer');
        this.edgeLayer = document.getElementById('workflow-edge-layer');
        this.emptyHint = document.getElementById('workflow-empty-hint');
        this.paletteList = document.getElementById('workflow-palette-list');
        this.oneClickToggle = document.getElementById('workflow-one-click');
        this.nameInput = document.getElementById('workflow-name');
        this.templateSelect = document.getElementById('workflow-template');
        this.inspectorTitle = document.getElementById('workflow-inspector-title');
        this.inspectorDescription = document.getElementById('workflow-inspector-description');
        this.inspectorFields = document.getElementById('workflow-inspector-fields');
        this.deleteNodeButton = document.getElementById('workflow-delete-node');
        this.runButton = document.getElementById('workflow-run');
        this.status = document.getElementById('workflow-run-status');
        this.runLog = document.getElementById('workflow-run-log');
        this.resultActions = document.getElementById('workflow-result-actions');
    }

    async init() {
        if (!this.view || !this.canvas) return;
        this.bindControls();
        try {
            const response = await fetch('/api/workflow/catalog');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            this.catalog = data.nodes || {};
            this.renderPalette();
            if (!this.restore()) this.loadTemplate('balanced');
            if (window.location.hash === '#workflow') this.options.onOpen?.();
        } catch (error) {
            this.setStatus(`Workflow catalog unavailable: ${error.message}`, 'error');
            this.options.notify?.('Workflow Modeler could not load its component catalog.', 'error');
        }
    }

    bindControls() {
        document.getElementById('workflow-new')?.addEventListener('click', () => {
            this.loadTemplate(this.templateSelect?.value || 'balanced');
        });
        document.getElementById('workflow-save')?.addEventListener('click', () => this.save());
        document.getElementById('workflow-export')?.addEventListener('click', () => {
            const graph = this.serialize();
            downloadJson(`${safeFilename(graph.name)}.ppworkflow.json`, graph);
        });
        const importInput = document.getElementById('workflow-import-file');
        document.getElementById('workflow-import')?.addEventListener('click', () => importInput?.click());
        importInput?.addEventListener('change', event => this.importFile(event));
        this.runButton?.addEventListener('click', () => this.run());
        this.deleteNodeButton?.addEventListener('click', () => this.deleteSelection());
        document.getElementById('workflow-preview-result')?.addEventListener('click', () => this.previewResult());
        document.getElementById('workflow-sync-result')?.addEventListener('click', () => this.syncResult());
        document.getElementById('workflow-open-guide')?.addEventListener('click', () => {
            this.options.onGuide?.('guide-workflow');
        });
        this.nameInput?.addEventListener('change', () => {
            this.graph.name = this.nameInput.value.trim() || 'Untitled Workflow';
        });

        this.canvas.addEventListener('dragover', event => event.preventDefault());
        this.canvas.addEventListener('drop', event => {
            event.preventDefault();
            const type = event.dataTransfer?.getData('application/x-parametric-node');
            if (!type || !this.catalog[type]) return;
            const rect = this.canvas.getBoundingClientRect();
            this.addNode(type, event.clientX - rect.left - 95, event.clientY - rect.top - 25);
        });
        this.canvas.addEventListener('click', event => {
            if (event.target === this.canvas || event.target === this.nodeLayer) {
                this.cancelConnection();
                this.selectNode(null);
            }
        });
        this.canvas.addEventListener('keydown', event => this.handleKey(event));
        window.addEventListener('keydown', event => {
            if (!this.view.classList.contains('hidden')) this.handleKey(event);
        });
        window.addEventListener('resize', () => this.renderEdges());
    }

    handleKey(event) {
        if (event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement) return;
        if (event.key === 'Delete' || event.key === 'Backspace') {
            event.preventDefault();
            this.deleteSelection();
        } else if (event.key === 'Escape') {
            this.cancelConnection();
        }
    }

    defaultsFor(type) {
        const params = {};
        Object.entries(this.catalog[type]?.params || {}).forEach(([name, spec]) => {
            params[name] = clone(spec.default);
        });
        return params;
    }

    makeNode(type, x, y, id = null, params = null) {
        const nodeId = id || this.nextIdentifier(type);
        return {
            id: nodeId,
            type,
            x: Math.max(20, Math.min(1780, Number(x) || 20)),
            y: Math.max(20, Math.min(1050, Number(y) || 20)),
            params: { ...this.defaultsFor(type), ...(params || {}) },
        };
    }

    nextIdentifier(prefix) {
        const used = new Set([
            ...this.graph.nodes.map(node => node.id),
            ...this.graph.edges.map(edge => edge.id),
        ]);
        let candidate;
        do {
            candidate = `${prefix}_${this.nextId++}`;
        } while (used.has(candidate));
        return candidate;
    }

    smartPredecessor(type) {
        if (!this.catalog[type]?.accepts_input) return null;
        if (this.selectedNodeId && this.graph.nodes.some(node => node.id === this.selectedNodeId)) {
            return this.selectedNodeId;
        }
        const connectedSources = new Set(this.graph.edges.map(edge => edge.source));
        const terminals = this.graph.nodes.filter(node => !connectedSources.has(node.id));
        return terminals.length === 1 ? terminals[0].id : null;
    }

    connectNodes(sourceId, targetId) {
        const sourceNode = this.graph.nodes.find(node => node.id === sourceId);
        const targetNode = this.graph.nodes.find(node => node.id === targetId);
        if (!sourceNode || !targetNode || sourceId === targetId || !this.catalog[targetNode.type]?.accepts_input) {
            return false;
        }
        if (this.wouldCreateCycle(sourceId, targetId)) {
            this.options.notify?.('That connection would create a workflow cycle.', 'warning');
            return false;
        }
        this.graph.edges = this.graph.edges.filter(edge => edge.target !== targetId);
        if (!this.graph.edges.some(edge => edge.source === sourceId && edge.target === targetId)) {
            this.graph.edges.push({ id: this.nextIdentifier('edge'), source: sourceId, target: targetId });
        }
        return true;
    }

    addNode(type, x = null, y = null, { smartConnect = false } = {}) {
        if (!this.catalog[type] || this.graph.nodes.length >= 64) return;
        const predecessorId = smartConnect ? this.smartPredecessor(type) : null;
        const index = this.graph.nodes.length;
        const node = this.makeNode(
            type,
            x ?? 40 + (index % 5) * 215,
            y ?? 50 + Math.floor(index / 5) * 145,
        );
        this.graph.nodes.push(node);
        const connected = predecessorId ? this.connectNodes(predecessorId, node.id) : false;
        this.renderGraph();
        this.selectNode(node.id);
        this.setStatus(
            connected
                ? `${this.catalog[type].label} added, selected and connected.`
                : `${this.catalog[type].label} added and selected.`,
            'success',
        );
    }

    renderPalette() {
        this.paletteList.replaceChildren();
        const grouped = new Map();
        Object.entries(this.catalog).forEach(([type, spec]) => {
            const category = spec.category || 'Other';
            if (!grouped.has(category)) grouped.set(category, []);
            grouped.get(category).push([type, spec]);
        });
        grouped.forEach((entries, category) => {
            const group = document.createElement('section');
            group.className = 'workflow-palette-group';
            const heading = document.createElement('h3');
            heading.textContent = category;
            group.appendChild(heading);
            entries.forEach(([type, spec]) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'workflow-palette-button';
                button.draggable = true;
                button.style.setProperty('--node-color', spec.color || '#1f9b8e');
                const title = document.createElement('strong');
                title.textContent = spec.label;
                const detail = document.createElement('small');
                detail.textContent = spec.description;
                button.append(title, detail);
                button.addEventListener('click', () => this.addNode(type, null, null, {
                    smartConnect: this.oneClickToggle?.checked !== false,
                }));
                button.addEventListener('dragstart', event => {
                    event.dataTransfer?.setData('application/x-parametric-node', type);
                    if (event.dataTransfer) event.dataTransfer.effectAllowed = 'copy';
                });
                group.appendChild(button);
            });
            this.paletteList.appendChild(group);
        });
    }

    renderGraph() {
        this.nodeLayer.replaceChildren();
        this.graph.nodes.forEach(node => this.nodeLayer.appendChild(this.renderNode(node)));
        this.emptyHint?.classList.toggle('hidden', this.graph.nodes.length > 0);
        requestAnimationFrame(() => this.renderEdges());
        this.renderInspector();
    }

    renderNode(node) {
        const spec = this.catalog[node.type];
        const element = document.createElement('article');
        element.className = `workflow-node${node.id === this.selectedNodeId ? ' selected' : ''}`;
        element.dataset.nodeId = node.id;
        element.style.left = `${node.x}px`;
        element.style.top = `${node.y}px`;
        element.style.setProperty('--node-color', spec.color || '#1f9b8e');

        const header = document.createElement('header');
        header.className = 'workflow-node-header';
        const category = document.createElement('span');
        category.className = 'workflow-node-category';
        category.textContent = spec.category;
        const title = document.createElement('span');
        title.className = 'workflow-node-title';
        title.textContent = spec.label;
        header.append(category, title);

        const body = document.createElement('div');
        body.className = 'workflow-node-body';
        body.textContent = this.nodeCaption(node);

        const ports = document.createElement('footer');
        ports.className = 'workflow-node-port-row';
        const inputLabel = document.createElement('span');
        inputLabel.textContent = spec.accepts_input ? 'data in' : 'source';
        const outputLabel = document.createElement('span');
        outputLabel.textContent = 'data out';
        ports.append(inputLabel, outputLabel);
        if (spec.accepts_input) ports.appendChild(this.makePort(node.id, 'input'));
        ports.appendChild(this.makePort(node.id, 'output'));

        header.addEventListener('pointerdown', event => this.startNodeDrag(event, node));
        element.addEventListener('pointerdown', event => {
            if (event.button === 0) this.selectNode(node.id);
        });
        element.addEventListener('click', event => {
            event.stopPropagation();
            this.selectNode(node.id);
        });
        element.append(header, body, ports);
        return element;
    }

    nodeCaption(node) {
        const params = node.params || {};
        if (node.type === 'zoning_rules') return `BCR ${params.max_bcr} · FAR ${params.max_far} · ${params.max_height} m`;
        if (node.type === 'evolutionary_solver') return `${String(params.algorithm).toUpperCase()} · ${params.population} × ${params.generations}`;
        if (node.type === 'subdivide_block') return `${params.strategy} subdivision`;
        if (node.type === 'ppud_pipeline') return `${params.strategy} · ${params.block_typology}`;
        if (node.type === 'select_best') return `${params.method} · top ${params.count}`;
        return this.catalog[node.type].description;
    }

    makePort(nodeId, direction) {
        const port = document.createElement('button');
        port.type = 'button';
        port.className = `workflow-port ${direction}`;
        port.dataset.nodeId = nodeId;
        port.dataset.direction = direction;
        port.title = direction === 'output' ? 'Start connection' : 'Complete connection';
        port.addEventListener('click', event => {
            event.stopPropagation();
            if (direction === 'output') this.beginConnection(nodeId);
            else this.completeConnection(nodeId);
        });
        return port;
    }

    beginConnection(nodeId) {
        this.cancelConnection();
        this.connectingSourceId = nodeId;
        const port = this.findPort(nodeId, 'output');
        port?.classList.add('connecting');
        this.setStatus('Choose an input port to complete the connection.', 'idle');
    }

    completeConnection(targetId) {
        const sourceId = this.connectingSourceId;
        if (!sourceId || sourceId === targetId) return;
        this.connectNodes(sourceId, targetId);
        this.cancelConnection();
        this.renderEdges();
    }

    cancelConnection() {
        this.connectingSourceId = null;
        this.nodeLayer.querySelectorAll('.workflow-port.connecting').forEach(port => port.classList.remove('connecting'));
    }

    wouldCreateCycle(sourceId, targetId) {
        const adjacency = new Map();
        this.graph.nodes.forEach(node => adjacency.set(node.id, []));
        this.graph.edges.forEach(edge => adjacency.get(edge.source)?.push(edge.target));
        adjacency.get(sourceId)?.push(targetId);
        const stack = [targetId];
        const seen = new Set();
        while (stack.length) {
            const current = stack.pop();
            if (current === sourceId) return true;
            if (seen.has(current)) continue;
            seen.add(current);
            (adjacency.get(current) || []).forEach(next => stack.push(next));
        }
        return false;
    }

    renderEdges() {
        this.edgeLayer.replaceChildren();
        const canvasRect = this.canvas.getBoundingClientRect();
        this.graph.edges.forEach(edge => {
            const source = this.findPort(edge.source, 'output');
            const target = this.findPort(edge.target, 'input');
            if (!source || !target) return;
            const sourceRect = source.getBoundingClientRect();
            const targetRect = target.getBoundingClientRect();
            const x1 = sourceRect.left + sourceRect.width / 2 - canvasRect.left;
            const y1 = sourceRect.top + sourceRect.height / 2 - canvasRect.top;
            const x2 = targetRect.left + targetRect.width / 2 - canvasRect.left;
            const y2 = targetRect.top + targetRect.height / 2 - canvasRect.top;
            const bend = Math.max(60, Math.abs(x2 - x1) * 0.45);
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`);
            path.setAttribute('class', `workflow-edge${edge.id === this.selectedEdgeId ? ' selected' : ''}`);
            path.dataset.edgeId = edge.id;
            path.addEventListener('click', event => {
                event.stopPropagation();
                this.selectedEdgeId = edge.id;
                this.selectedNodeId = null;
                this.renderGraph();
            });
            path.addEventListener('dblclick', event => {
                event.stopPropagation();
                this.graph.edges = this.graph.edges.filter(item => item.id !== edge.id);
                this.selectedEdgeId = null;
                this.renderEdges();
            });
            this.edgeLayer.appendChild(path);
        });
    }

    findPort(nodeId, direction) {
        return Array.from(this.nodeLayer.querySelectorAll(`.workflow-port.${direction}`))
            .find(port => port.dataset.nodeId === nodeId) || null;
    }

    findNodeElement(nodeId) {
        return Array.from(this.nodeLayer.querySelectorAll('.workflow-node'))
            .find(element => element.dataset.nodeId === nodeId) || null;
    }

    startNodeDrag(event, node) {
        event.preventDefault();
        this.selectNode(node.id);
        const start = { x: event.clientX, y: event.clientY, nodeX: node.x, nodeY: node.y };
        const header = event.currentTarget;
        header.setPointerCapture?.(event.pointerId);
        const move = moveEvent => {
            node.x = Math.max(0, Math.min(1810, start.nodeX + moveEvent.clientX - start.x));
            node.y = Math.max(0, Math.min(1080, start.nodeY + moveEvent.clientY - start.y));
            const element = this.findNodeElement(node.id);
            if (element) {
                element.style.left = `${node.x}px`;
                element.style.top = `${node.y}px`;
            }
            this.renderEdges();
        };
        const up = () => {
            header.removeEventListener('pointermove', move);
            header.removeEventListener('pointerup', up);
            header.removeEventListener('pointercancel', up);
        };
        header.addEventListener('pointermove', move);
        header.addEventListener('pointerup', up);
        header.addEventListener('pointercancel', up);
    }

    selectNode(nodeId) {
        this.selectedNodeId = nodeId;
        this.selectedEdgeId = null;
        this.nodeLayer.querySelectorAll('.workflow-node').forEach(element => {
            element.classList.toggle('selected', element.dataset.nodeId === nodeId);
        });
        this.renderInspector();
    }

    renderInspector() {
        const node = this.graph.nodes.find(item => item.id === this.selectedNodeId);
        this.inspectorFields.replaceChildren();
        this.deleteNodeButton?.classList.toggle('hidden', !node);
        if (!node) {
            this.inspectorTitle.textContent = this.selectedEdgeId ? 'Connection selected' : 'Select a node';
            this.inspectorDescription.textContent = this.selectedEdgeId
                ? 'Press Delete to remove this connection.'
                : 'Node parameters appear here.';
            return;
        }
        const spec = this.catalog[node.type];
        this.inspectorTitle.textContent = spec.label;
        this.inspectorDescription.textContent = spec.description;
        Object.entries(spec.params || {}).forEach(([name, paramSpec]) => {
            this.inspectorFields.appendChild(this.renderParamField(node, name, paramSpec));
        });
        if (Object.keys(spec.params || {}).length === 0) {
            const note = document.createElement('p');
            note.className = 'workflow-help';
            note.textContent = 'This component has no editable parameters.';
            this.inspectorFields.appendChild(note);
        }
    }

    renderParamField(node, name, spec) {
        const label = document.createElement('label');
        label.className = 'workflow-inspector-field';
        const title = document.createElement('span');
        title.textContent = name.replace(/_/g, ' ');
        label.appendChild(title);

        if (spec.type === 'boolean') {
            label.classList.add('workflow-switch-field');
            const input = document.createElement('input');
            input.type = 'checkbox';
            input.checked = Boolean(node.params[name]);
            input.addEventListener('change', () => this.updateParam(node, name, input.checked));
            label.appendChild(input);
        } else if (spec.type === 'select') {
            const select = document.createElement('select');
            (spec.options || []).forEach(option => {
                const optionElement = document.createElement('option');
                optionElement.value = option;
                optionElement.textContent = option;
                select.appendChild(optionElement);
            });
            select.value = node.params[name];
            select.addEventListener('change', () => this.updateParam(node, name, select.value));
            label.appendChild(select);
        } else if (spec.type === 'objectives') {
            const container = document.createElement('div');
            container.className = 'workflow-objectives';
            (node.params[name] || []).forEach((objective, index) => {
                const row = document.createElement('div');
                row.className = 'workflow-objective-row';
                const objectiveName = document.createElement('span');
                objectiveName.textContent = objective.name;
                const direction = document.createElement('select');
                ['max', 'min'].forEach(value => {
                    const option = document.createElement('option');
                    option.value = value;
                    option.textContent = value.toUpperCase();
                    direction.appendChild(option);
                });
                direction.value = objective.direction;
                direction.addEventListener('change', () => {
                    const objectives = clone(node.params[name]);
                    objectives[index].direction = direction.value;
                    this.updateParam(node, name, objectives);
                });
                row.append(objectiveName, direction);
                container.appendChild(row);
            });
            label.appendChild(container);
        } else {
            const input = document.createElement('input');
            input.type = 'number';
            input.value = node.params[name];
            if (spec.min !== undefined) input.min = spec.min;
            if (spec.max !== undefined) input.max = spec.max;
            if (spec.step !== undefined) input.step = spec.step;
            input.addEventListener('change', () => {
                const value = spec.type === 'integer' ? parseInt(input.value, 10) : parseFloat(input.value);
                this.updateParam(node, name, value);
            });
            label.appendChild(input);
        }
        return label;
    }

    updateParam(node, name, value) {
        node.params[name] = value;
        this.renderGraph();
        this.selectNode(node.id);
    }

    deleteSelection() {
        if (this.selectedNodeId) {
            const id = this.selectedNodeId;
            this.graph.nodes = this.graph.nodes.filter(node => node.id !== id);
            this.graph.edges = this.graph.edges.filter(edge => edge.source !== id && edge.target !== id);
            this.selectedNodeId = null;
        } else if (this.selectedEdgeId) {
            this.graph.edges = this.graph.edges.filter(edge => edge.id !== this.selectedEdgeId);
            this.selectedEdgeId = null;
        }
        this.renderGraph();
    }

    template(name) {
        const definitions = {
            balanced: [
                ['site_input', 40, 100], ['zoning_rules', 270, 100], ['evolutionary_solver', 500, 100],
                ['topsis_ranker', 730, 100], ['select_best', 960, 100], ['qgis_output', 1190, 100],
            ],
            ppud: [
                ['site_input', 60, 120], ['zoning_rules', 300, 120], ['subdivide_block', 540, 60],
                ['ppud_pipeline', 780, 120],
            ],
            district: [
                ['site_input', 60, 120], ['zoning_rules', 300, 120], ['evolutionary_solver', 540, 120],
                ['district_analysis', 780, 120],
            ],
            blank: [],
        };
        const labels = {
            balanced: 'Balanced Urban Optimization',
            ppud: 'PPUD Rule Chain',
            district: 'District Performance Workflow',
            blank: 'Untitled Workflow',
        };
        const nodes = (definitions[name] || definitions.balanced).map(([type, x, y]) => this.makeNode(type, x, y));
        const edges = [];
        for (let index = 0; index < nodes.length - 1; index += 1) {
            edges.push({ id: this.nextIdentifier('edge'), source: nodes[index].id, target: nodes[index + 1].id });
        }
        return { schema_version: 1, name: labels[name] || labels.balanced, nodes, edges };
    }

    loadTemplate(name) {
        this.cancelConnection();
        this.selectedNodeId = null;
        this.selectedEdgeId = null;
        this.graph = this.template(name);
        this.lastResult = null;
        this.nameInput.value = this.graph.name;
        this.resultActions?.classList.add('hidden');
        this.setStatus('Template loaded. Review component settings, then run.', 'idle');
        this.runLog.replaceChildren();
        const readyItem = document.createElement('li');
        readyItem.textContent = 'Workflow is ready for validation.';
        this.runLog.appendChild(readyItem);
        this.renderGraph();
    }

    serialize() {
        this.graph.name = this.nameInput?.value.trim() || this.graph.name || 'Untitled Workflow';
        return clone({
            schema_version: 1,
            name: this.graph.name,
            nodes: this.graph.nodes,
            edges: this.graph.edges.map(({ id, source, target }) => ({ id, source, target })),
        });
    }

    save() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(this.serialize()));
            this.setStatus('Workflow saved in this browser profile.', 'success');
            this.options.notify?.('Workflow saved.', 'success');
        } catch (error) {
            this.setStatus(`Save failed: ${error.message}`, 'error');
        }
    }

    restore() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return false;
            return this.loadGraph(JSON.parse(raw));
        } catch (error) {
            console.warn('Workflow restore failed', error);
            return false;
        }
    }

    loadGraph(graph) {
        if (!graph || !Array.isArray(graph.nodes) || !Array.isArray(graph.edges)) return false;
        if (graph.nodes.length > 64 || graph.edges.length > 128) return false;
        const nodes = [];
        const ids = new Set();
        for (const rawNode of graph.nodes) {
            if (!rawNode || !this.catalog[rawNode.type] || !rawNode.id || ids.has(String(rawNode.id))) return false;
            ids.add(String(rawNode.id));
            nodes.push(this.makeNode(rawNode.type, rawNode.x, rawNode.y, String(rawNode.id), rawNode.params));
        }
        const edges = graph.edges
            .filter(edge => edge && ids.has(String(edge.source)) && ids.has(String(edge.target)))
            .map(edge => ({ id: String(edge.id || this.nextIdentifier('edge')), source: String(edge.source), target: String(edge.target) }));
        this.graph = { schema_version: 1, name: String(graph.name || 'Imported Workflow').slice(0, 120), nodes, edges };
        this.nameInput.value = this.graph.name;
        this.selectedNodeId = null;
        this.selectedEdgeId = null;
        this.renderGraph();
        this.setStatus('Saved workflow restored.', 'success');
        return true;
    }

    async importFile(event) {
        const file = event.target.files?.[0];
        event.target.value = '';
        if (!file) return;
        if (file.size > 2 * 1024 * 1024) {
            this.options.notify?.('Workflow file is larger than 2 MB.', 'error');
            return;
        }
        try {
            const graph = JSON.parse(await file.text());
            if (!this.loadGraph(graph)) throw new Error('Invalid or unsupported workflow format');
            this.options.notify?.('Workflow imported.', 'success');
        } catch (error) {
            this.setStatus(`Import failed: ${error.message}`, 'error');
        }
    }

    async run() {
        const graph = this.serialize();
        this.runButton.disabled = true;
        this.resultActions?.classList.add('hidden');
        this.setStatus('Executing graph on the live QGIS layer…', 'running');
        this.runLog.replaceChildren();
        const starting = document.createElement('li');
        starting.textContent = `Validating ${graph.nodes.length} nodes and ${graph.edges.length} connections…`;
        this.runLog.appendChild(starting);
        try {
            const response = await fetch('/api/workflow/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workflow: graph,
                    selected_fid: this.options.getSelectedFeatureId?.() ?? null,
                }),
            });
            const data = await response.json();
            if (!response.ok || data.status !== 'ok') throw new Error(data.message || `HTTP ${response.status}`);
            this.lastResult = data.result || {};
            this.renderRunLog(data.node_results || []);
            this.setStatus(`Completed ${data.execution_order?.length || 0} components.`, 'success');
            const canPreview = (this.lastResult.selected_solutions || this.lastResult.pareto_solutions || []).length > 0;
            const canSync = (this.lastResult.qgis_updates || []).length > 0;
            this.resultActions?.classList.toggle('hidden', !canPreview && !canSync);
            document.getElementById('workflow-preview-result').disabled = !canPreview;
            document.getElementById('workflow-sync-result').disabled = !canSync;
            this.options.notify?.('Workflow completed.', 'success');
        } catch (error) {
            this.lastResult = null;
            this.setStatus(`Execution failed: ${error.message}`, 'error');
            const item = document.createElement('li');
            item.textContent = error.message;
            this.runLog.appendChild(item);
            this.options.notify?.(`Workflow failed: ${error.message}`, 'error');
        } finally {
            this.runButton.disabled = false;
        }
    }

    renderRunLog(results) {
        this.runLog.replaceChildren();
        results.forEach(result => {
            const item = document.createElement('li');
            const label = this.catalog[result.type]?.label || result.type;
            const details = [];
            if (result.feature_count !== undefined) details.push(`${result.feature_count} feature(s)`);
            if (result.lot_count !== undefined) details.push(`${result.lot_count} lot(s)`);
            if (result.plot_count !== undefined) details.push(`${result.plot_count} plot(s)`);
            if (result.population !== undefined) details.push(`${result.population} candidates`);
            if (result.pareto_count !== undefined) details.push(`${result.pareto_count} Pareto`);
            if (result.ranked_count !== undefined) details.push(`${result.ranked_count} ranked`);
            if (result.selected_count !== undefined) details.push(`${result.selected_count} selected`);
            if (result.update_count !== undefined) details.push(`${result.update_count} GIS update(s)`);
            item.textContent = `${label}: ${details.join(' · ') || 'completed'}`;
            this.runLog.appendChild(item);
        });
    }

    previewResult() {
        const solutions = this.lastResult?.selected_solutions || this.lastResult?.ranked_solutions || this.lastResult?.pareto_solutions || [];
        if (!solutions.length) return;
        this.options.onPreview?.(solutions[0]);
    }

    async syncResult() {
        const updates = this.lastResult?.qgis_updates || [];
        if (!updates.length) return;
        try {
            await this.options.onSync?.(updates);
        } catch (error) {
            this.options.notify?.(`QGIS sync failed: ${error.message}`, 'error');
        }
    }

    setStatus(message, tone) {
        if (!this.status) return;
        this.status.textContent = message;
        this.status.className = `workflow-status ${tone || 'idle'}`;
    }
}
