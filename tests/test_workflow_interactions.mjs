import assert from 'node:assert/strict';

globalThis.document = { getElementById: () => null };

const { WorkflowModeler } = await import('../web/src/workflow_modeler.js');

const modeler = new WorkflowModeler();
modeler.catalog = {
    site_input: { accepts_input: false, label: 'QGIS Site Layer' },
    zoning_rules: { accepts_input: true, label: 'Zoning Envelope' },
    evolutionary_solver: { accepts_input: true, label: 'Evolutionary Solver' },
};
modeler.graph = {
    nodes: [
        { id: 'site_1', type: 'site_input' },
        { id: 'zoning_1', type: 'zoning_rules' },
    ],
    edges: [],
};
modeler.selectedNodeId = 'site_1';

assert.equal(modeler.smartPredecessor('zoning_rules'), 'site_1');
assert.equal(modeler.smartPredecessor('site_input'), null);
assert.equal(modeler.connectNodes('site_1', 'zoning_1'), true);
assert.deepEqual(
    modeler.graph.edges.map(({ source, target }) => ({ source, target })),
    [{ source: 'site_1', target: 'zoning_1' }],
);

modeler.selectedNodeId = null;
assert.equal(modeler.smartPredecessor('evolutionary_solver'), 'zoning_1');

modeler.graph.nodes.push({ id: 'solver_1', type: 'evolutionary_solver' });
assert.equal(modeler.connectNodes('zoning_1', 'solver_1'), true);
assert.equal(modeler.wouldCreateCycle('solver_1', 'site_1'), true);

console.log('WORKFLOW_INTERACTIONS_OK');
