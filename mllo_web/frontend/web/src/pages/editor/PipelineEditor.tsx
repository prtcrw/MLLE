import React, {useEffect, useMemo, useState} from 'react';
import {Link, useSearchParams} from 'react-router-dom';
import {
    getExistingPipelines,
    getPipelineEditorState,
    PipelineEditorDraft,
    PipelineEditorEdge,
    PipelineEditorNodeMetadata,
    PipelineEditorVersion,
    publishPipelineDraft,
    resetPipelineDraft,
    savePipelineDraft,
    validatePipelineDraft,
} from '../../services/api';
import PipelineCanvas, {CANVAS_NODE_HEIGHT, CANVAS_NODE_WIDTH, CanvasNode} from './PipelineCanvas';
import './styles/pipeline_editor.css';

type EditorTab = 'overview' | 'compare' | 'reasoning' | 'history';
type DrawerPanel = 'inspector' | 'export' | null;

interface PipelineNode extends CanvasNode {
    iri: string;
    rules: string[];
    observedStructure: string[];
    ontologyClasses: string[];
    ontologyRelations: string[];
    impact: string;
}

const compareFindings = [
    'Compare two saved pipeline versions here once the second pipeline is loaded.',
    'Use the editor to inspect structural differences before sending a draft for validation.',
    'Ontology-based validation can be layered on top of these structural comparisons later.',
];

const customChecks = [
    'MLLO restriction checks for component classes',
    'Observed pipeline ordering checks',
    'Required input/output/model presence',
    'Custom organizational release gates before publish',
];

const kindLabel: Record<PipelineNode['kind'], string> = {
    input: 'Input',
    operation: 'Operation',
    output: 'Output',
    model: 'Model',
};

const NODE_X_GAP = 50;
const NODE_Y_GAP = 48;
const DEFAULT_NODE_X = 48;
const DEFAULT_NODE_Y = 72;

const sanitizeNodeId = (value: string) => {
    const slug = value
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
    return slug || 'pipeline-node';
};

const compareByLayout = (left: {x: number; y: number; title: string}, right: {x: number; y: number; title: string}) => {
    if (left.x !== right.x) {
        return left.x - right.x;
    }
    if (left.y !== right.y) {
        return left.y - right.y;
    }
    return left.title.localeCompare(right.title);
};

const buildFallbackNodePosition = (position: number) => ({
    x: DEFAULT_NODE_X + (position * (CANVAS_NODE_WIDTH + NODE_X_GAP)),
    y: DEFAULT_NODE_Y,
});

const sortNodesForDraft = (nodes: PipelineNode[], edges: PipelineEditorEdge[]) => {
    const nodeMap = new Map(nodes.map((node) => [node.id, node]));
    const incoming = new Map<string, number>(nodes.map((node) => [node.id, 0]));
    const outgoing = new Map<string, string[]>(nodes.map((node) => [node.id, []]));
    const seenEdges = new Set<string>();

    edges.forEach((edge) => {
        if (!nodeMap.has(edge.source) || !nodeMap.has(edge.target) || edge.source === edge.target) {
            return;
        }
        const key = `${edge.source}::${edge.target}`;
        if (seenEdges.has(key)) {
            return;
        }
        seenEdges.add(key);
        incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1);
        outgoing.set(edge.source, [...(outgoing.get(edge.source) ?? []), edge.target]);
    });

    const queue = nodes
        .filter((node) => (incoming.get(node.id) ?? 0) === 0)
        .sort(compareByLayout);
    const ordered: PipelineNode[] = [];
    const visited = new Set<string>();

    while (queue.length > 0) {
        const current = queue.shift();
        if (!current || visited.has(current.id)) {
            continue;
        }
        visited.add(current.id);
        ordered.push(current);

        const nextIds = [...(outgoing.get(current.id) ?? [])]
            .sort((leftId, rightId) => compareByLayout(nodeMap.get(leftId)!, nodeMap.get(rightId)!));

        nextIds.forEach((nextId) => {
            incoming.set(nextId, (incoming.get(nextId) ?? 0) - 1);
            if ((incoming.get(nextId) ?? 0) === 0) {
                const nextNode = nodeMap.get(nextId);
                if (nextNode && !visited.has(nextId)) {
                    queue.push(nextNode);
                    queue.sort(compareByLayout);
                }
            }
        });
    }

    const remaining = nodes
        .filter((node) => !visited.has(node.id))
        .sort(compareByLayout);

    return [...ordered, ...remaining];
};

const computeAutoLayout = (nodes: PipelineNode[], edges: PipelineEditorEdge[]) => {
    const orderedNodes = sortNodesForDraft(nodes, edges);
    const nodeMap = new Map(nodes.map((node) => [node.id, node]));
    const predecessors = new Map<string, string[]>(nodes.map((node) => [node.id, []]));

    edges.forEach((edge) => {
        if (!nodeMap.has(edge.source) || !nodeMap.has(edge.target) || edge.source === edge.target) {
            return;
        }
        predecessors.set(edge.target, [...(predecessors.get(edge.target) ?? []), edge.source]);
    });

    const laneCounts = new Map<number, number>();
    const positions = new Map<string, {x: number; y: number}>();

    orderedNodes.forEach((node) => {
        const sourceIds = predecessors.get(node.id) ?? [];
        const layer = sourceIds.reduce((maxLayer, sourceId) => {
            const sourcePosition = positions.get(sourceId);
            if (!sourcePosition) {
                return maxLayer;
            }
            const sourceLayer = Math.round((sourcePosition.x - DEFAULT_NODE_X) / (CANVAS_NODE_WIDTH + NODE_X_GAP));
            return Math.max(maxLayer, sourceLayer + 1);
        }, 0);
        const laneIndex = laneCounts.get(layer) ?? 0;
        positions.set(node.id, {
            x: DEFAULT_NODE_X + (layer * (CANVAS_NODE_WIDTH + NODE_X_GAP)),
            y: DEFAULT_NODE_Y + (laneIndex * (CANVAS_NODE_HEIGHT + NODE_Y_GAP)),
        });
        laneCounts.set(layer, laneIndex + 1);
    });

    return positions;
};

const normalizeEdges = (edges: PipelineEditorEdge[], validNodeIds: Set<string>, orderedNodes: PipelineNode[]) => {
    const deduped: PipelineEditorEdge[] = [];
    const seen = new Set<string>();

    edges.forEach((edge) => {
        if (!validNodeIds.has(edge.source) || !validNodeIds.has(edge.target) || edge.source === edge.target) {
            return;
        }
        const key = `${edge.source}::${edge.target}`;
        if (seen.has(key)) {
            return;
        }
        seen.add(key);
        deduped.push({...edge, relation: edge.relation || 'isStructurallyFollowedBy'});
    });

    if (deduped.length > 0 || orderedNodes.length < 2) {
        return deduped;
    }

    return orderedNodes.slice(0, -1).map((node, index) => ({
        source: node.id,
        target: orderedNodes[index + 1].id,
        relation: 'isStructurallyFollowedBy',
    }));
};

const PipelineEditor: React.FC = () => {
    const [searchParams, setSearchParams] = useSearchParams();
    const pipelineName = searchParams.get('pipeline-name') || '';
    const [selectedTab, setSelectedTab] = useState<EditorTab>('overview');
    const [selectedNodeId, setSelectedNodeId] = useState<string>('');
    const [selectedEdgeKey, setSelectedEdgeKey] = useState<string | null>(null);
    const [activeDrawer, setActiveDrawer] = useState<DrawerPanel>('inspector');
    const [pendingConnectionSourceId, setPendingConnectionSourceId] = useState<string | null>(null);
    const [nodes, setNodes] = useState<PipelineNode[]>([]);
    const [edges, setEdges] = useState<PipelineEditorEdge[]>([]);
    const [nodeNotes, setNodeNotes] = useState<Record<string, string>>({});
    const [saveMessage, setSaveMessage] = useState<string>('Editor ready. Load a pipeline or name a new one to begin.');
    const [validationStatus, setValidationStatus] = useState<'unknown' | 'passed' | 'failed'>('unknown');
    const [validationMessage, setValidationMessage] = useState<string>('Run consistency checks before publishing this draft.');
    const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
    const [historyItems, setHistoryItems] = useState<PipelineEditorVersion[]>([]);
    const [isBusy, setIsBusy] = useState<boolean>(false);
    const [sourceDraft, setSourceDraft] = useState<PipelineEditorDraft | null>(null);
    const [existingPipelines, setExistingPipelines] = useState<string[]>([]);
    const [pipelinePickerValue, setPipelinePickerValue] = useState<string>('');
    const [newPipelineName, setNewPipelineName] = useState<string>(pipelineName);

    const applyEmptyState = (message: string) => {
        setNodes([]);
        setEdges([]);
        setSelectedNodeId('');
        setSelectedEdgeKey(null);
        setPendingConnectionSourceId(null);
        setNodeNotes({});
        setValidationStatus('unknown');
        setValidationMessage('Run consistency checks before publishing this draft.');
        setLastSavedAt(null);
        setHistoryItems([]);
        setSourceDraft(null);
        setSaveMessage(message);
    };

    const applyDraftState = (draft: PipelineEditorDraft, metadata: Record<string, PipelineEditorNodeMetadata> = {}) => {
        const orderedNodes: PipelineNode[] = draft.nodes
            .slice()
            .sort((left, right) => left.position - right.position)
            .map((savedNode) => {
                const nodeMetadata = metadata[savedNode.id];
                const fallbackPosition = buildFallbackNodePosition(savedNode.position);

                return {
                    id: savedNode.id,
                    title: savedNode.title,
                    kind: savedNode.kind,
                    iri: savedNode.iri,
                    summary: nodeMetadata?.summary || savedNode.note || `Loaded from ${draft.pipelineName}.`,
                    rules: nodeMetadata?.rules || [],
                    observedStructure: nodeMetadata?.observed_structure || [],
                    ontologyClasses: nodeMetadata?.ontology_classes || [],
                    ontologyRelations: nodeMetadata?.ontology_relations || [],
                    impact: nodeMetadata?.impact || 'Changes to this node affect downstream validation and export behavior.',
                    x: savedNode.x ?? fallbackPosition.x,
                    y: savedNode.y ?? fallbackPosition.y,
                };
            });

        const validNodeIds = new Set(orderedNodes.map((node) => node.id));

        setNodes(orderedNodes);
        setEdges(normalizeEdges(draft.edges, validNodeIds, orderedNodes));
        setSelectedNodeId(orderedNodes[0]?.id ?? '');
        setSelectedEdgeKey(null);
        setPendingConnectionSourceId(null);
        setNodeNotes(Object.fromEntries(draft.nodes.map((node) => [node.id, node.note])));
        setValidationStatus(draft.validationStatus);
        setValidationMessage(draft.validationMessage);
        setLastSavedAt(draft.savedAt);
    };

    useEffect(() => {
        setPipelinePickerValue(pipelineName);
        setNewPipelineName(pipelineName);
    }, [pipelineName]);

    useEffect(() => {
        let cancelled = false;

        const loadExisting = async () => {
            try {
                const pipelines = await getExistingPipelines();
                if (!cancelled) {
                    setExistingPipelines(pipelines);
                }
            } catch {
                if (!cancelled) {
                    setExistingPipelines([]);
                }
            }
        };

        void loadExisting();
        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        let cancelled = false;

        const draftsAreCompatible = (savedDraft: PipelineEditorDraft, liveDraft: PipelineEditorDraft | null) => {
            if (!liveDraft) {
                return true;
            }
            const liveIds = new Set(liveDraft.nodes.map((node) => node.id));
            if (liveIds.size === 0) {
                return true;
            }
            const overlap = savedDraft.nodes.filter((node) => liveIds.has(node.id)).length;
            return overlap / liveIds.size >= 0.6;
        };

        const loadEditorState = async () => {
            if (!pipelineName) {
                applyEmptyState('Editor ready. Load a pipeline or name a new one to begin.');
                return;
            }

            setIsBusy(true);
            try {
                const payload = await getPipelineEditorState(pipelineName);
                if (cancelled) {
                    return;
                }

                setSourceDraft(payload.source_draft ?? null);
                setHistoryItems(payload.history);

                if (payload.draft && draftsAreCompatible(payload.draft, payload.source_draft ?? null)) {
                    applyDraftState(payload.draft, payload.source_metadata ?? {});
                    setSaveMessage(`Loaded saved draft for ${pipelineName}.`);
                    return;
                }

                if (payload.source_draft) {
                    applyDraftState(payload.source_draft, payload.source_metadata ?? {});
                    setSaveMessage(payload.draft
                        ? `Ignored an outdated saved draft and loaded the live GraphDB structure for ${pipelineName}.`
                        : `Loaded live pipeline structure for ${pipelineName} from GraphDB.`);
                    return;
                }

                applyEmptyState(`No saved draft or graph structure found for ${pipelineName}.`);
            } catch {
                if (!cancelled) {
                    applyEmptyState('Pipeline editor backend state could not be loaded.');
                }
            } finally {
                if (!cancelled) {
                    setIsBusy(false);
                }
            }
        };

        void loadEditorState();
        return () => {
            cancelled = true;
        };
    }, [pipelineName]);

    const orderedNodes = useMemo(() => sortNodesForDraft(nodes, edges), [edges, nodes]);
    const orderIndexLookup = useMemo(
        () => new Map(orderedNodes.map((node, index) => [node.id, index + 1])),
        [orderedNodes],
    );

    const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? null;
    const selectedNodeNote = selectedNode ? (nodeNotes[selectedNode.id] ?? '') : '';

    const draftPayload = useMemo<PipelineEditorDraft>(() => ({
        pipelineName: pipelineName || 'UntitledPipeline',
        savedAt: lastSavedAt ?? new Date().toISOString(),
        validationStatus,
        validationMessage,
        nodes: orderedNodes.map((node, index) => ({
            id: node.id,
            iri: node.iri,
            title: node.title,
            kind: node.kind,
            position: index,
            note: nodeNotes[node.id] ?? '',
            x: node.x,
            y: node.y,
        })),
        edges: normalizeEdges(edges, new Set(nodes.map((node) => node.id)), orderedNodes),
    }), [edges, lastSavedAt, nodeNotes, nodes, orderedNodes, pipelineName, validationMessage, validationStatus]);

    const updateValidationForStructureChange = (message: string) => {
        setSelectedEdgeKey(null);
        setPendingConnectionSourceId(null);
        setValidationStatus('unknown');
        setValidationMessage('Structure changed. Run consistency checks before publishing this draft.');
        setSaveMessage(message);
    };

    const handleSelectPipeline = () => {
        if (!pipelinePickerValue) {
            return;
        }
        setSearchParams({'pipeline-name': pipelinePickerValue});
    };

    const handleStartNew = () => {
        const trimmedName = newPipelineName.trim();
        if (!trimmedName) {
            setSaveMessage('Enter a pipeline name before starting a new pipeline.');
            return;
        }
        setSearchParams({'pipeline-name': trimmedName});
        applyEmptyState(`Started a new empty pipeline canvas for ${trimmedName}.`);
    };

    const toggleDrawer = (panel: DrawerPanel) => {
        setActiveDrawer((current) => (current === panel ? null : panel));
    };

    const handleSaveDraft = () => {
        const saveDraft = async () => {
            if (!pipelineName) {
                setSaveMessage('Name or load a pipeline before saving a draft.');
                return;
            }
            setIsBusy(true);
            try {
                const savedAt = new Date().toISOString();
                const response = await savePipelineDraft({...draftPayload, savedAt});
                setLastSavedAt(savedAt);
                setHistoryItems(response.history);
                setSaveMessage(`Draft saved to backend at ${new Date(savedAt).toLocaleTimeString()}.`);
            } catch (error) {
                setSaveMessage(error instanceof Error ? error.message : 'Failed to save draft to backend.');
            } finally {
                setIsBusy(false);
            }
        };

        void saveDraft();
    };

    const handleResetDraft = () => {
        const resetDraft = async () => {
            if (!pipelineName) {
                applyEmptyState('Reset to an empty canvas.');
                return;
            }
            setIsBusy(true);
            try {
                await resetPipelineDraft(pipelineName);
                if (sourceDraft) {
                    applyDraftState(sourceDraft);
                    setSaveMessage('Draft reset to the live GraphDB pipeline structure.');
                } else {
                    applyEmptyState('Draft reset to an empty canvas.');
                }
            } catch (error) {
                setSaveMessage(error instanceof Error ? error.message : 'Failed to reset backend draft.');
            } finally {
                setIsBusy(false);
            }
        };

        void resetDraft();
    };

    const handleRunReasoner = () => {
        const runValidation = async () => {
            setIsBusy(true);
            try {
                const response = await validatePipelineDraft(draftPayload);
                setValidationStatus(response.validation_status);
                setValidationMessage(response.validation_message);
                setSaveMessage(response.ok
                    ? 'Consistency check passed. Save the draft or publish it to the backend.'
                    : 'Consistency check failed. Fix the draft before publishing.');
            } catch (error) {
                setSaveMessage(error instanceof Error ? error.message : 'Failed to validate draft.');
            } finally {
                setIsBusy(false);
            }
        };

        void runValidation();
    };

    const handleUploadDraft = () => {
        const publishDraft = async () => {
            if (!pipelineName) {
                setSaveMessage('Name or load a pipeline before publishing.');
                return;
            }
            if (validationStatus !== 'passed') {
                setSaveMessage('Run a successful consistency check before publishing this draft.');
                return;
            }
            setIsBusy(true);
            try {
                const response = await publishPipelineDraft(draftPayload);
                setValidationStatus(response.draft.validationStatus);
                setValidationMessage(response.draft.validationMessage);
                setLastSavedAt(response.published_at);
                setHistoryItems(response.history);
                setSaveMessage(`Draft published to backend as ${response.version.version}.`);
            } catch (error) {
                setSaveMessage(error instanceof Error ? error.message : 'Failed to publish draft.');
            } finally {
                setIsBusy(false);
            }
        };

        void publishDraft();
    };

    const handleMoveNode = (nodeId: string, x: number, y: number) => {
        setNodes((current) => current.map((node) => node.id === nodeId ? {...node, x, y} : node));
    };

    const handleEndMoveNode = (nodeId: string) => {
        const movedNode = nodes.find((node) => node.id === nodeId);
        if (!movedNode) {
            return;
        }
        updateValidationForStructureChange(`Moved ${movedNode.title} on the canvas.`);
    };

    const handleAddComponent = () => {
        const basisNode = selectedNode ?? nodes[nodes.length - 1] ?? null;
        const nextIndex = nodes.length + 1;
        const title = `Operation ${nextIndex}`;
        let nextId = sanitizeNodeId(title);
        const existingIds = new Set(nodes.map((node) => node.id));
        let suffix = 2;
        while (existingIds.has(nextId)) {
            nextId = `${sanitizeNodeId(title)}-${suffix}`;
            suffix += 1;
        }

        const nextNode: PipelineNode = {
            id: nextId,
            title,
            kind: 'operation',
            iri: pipelineName
                ? `http://www.semanticweb.org/mnd14/ml/${pipelineName}#${nextId}`
                : `urn:mllo:pipeline:${nextId}`,
            summary: 'New pipeline component. Connect it into the workflow and update its note in the inspector.',
            rules: [],
            observedStructure: [],
            ontologyClasses: [],
            ontologyRelations: [],
            impact: 'Changes here affect downstream validation and export behavior.',
            x: basisNode ? basisNode.x + CANVAS_NODE_WIDTH + NODE_X_GAP : DEFAULT_NODE_X,
            y: basisNode ? basisNode.y : DEFAULT_NODE_Y,
        };

        setNodes((current) => [...current, nextNode]);
        setSelectedNodeId(nextNode.id);
        setNodeNotes((current) => ({...current, [nextNode.id]: ''}));
        if (basisNode) {
            setEdges((current) => normalizeEdges([
                ...current,
                {
                    source: basisNode.id,
                    target: nextNode.id,
                    relation: 'isStructurallyFollowedBy',
                },
            ], new Set([...nodes.map((node) => node.id), nextNode.id]), [...nodes, nextNode]));
        }
        updateValidationForStructureChange(`Added ${nextNode.title} to the canvas.`);
    };

    const handleDeleteSelectedNode = () => {
        if (!selectedNode) {
            return;
        }
        setNodes((current) => current.filter((node) => node.id !== selectedNode.id));
        setEdges((current) => current.filter((edge) => edge.source !== selectedNode.id && edge.target !== selectedNode.id));
        setNodeNotes((current) => {
            const next = {...current};
            delete next[selectedNode.id];
            return next;
        });
        setSelectedNodeId('');
        updateValidationForStructureChange(`Removed ${selectedNode.title} from the draft.`);
    };

    const handleDeleteSelectedEdge = () => {
        if (!selectedEdgeKey) {
            return;
        }
        setEdges((current) => current.filter((edge) => `${edge.source}::${edge.target}` !== selectedEdgeKey));
        updateValidationForStructureChange('Removed the selected connection from the draft.');
    };

    const handleAutoLayout = () => {
        const nextPositions = computeAutoLayout(nodes, edges);
        setNodes((current) => current.map((node) => ({
            ...node,
            x: nextPositions.get(node.id)?.x ?? node.x,
            y: nextPositions.get(node.id)?.y ?? node.y,
        })));
        updateValidationForStructureChange('Canvas auto-layout updated for the current graph structure.');
    };

    const handleStartConnection = (nodeId: string) => {
        setSelectedEdgeKey(null);
        setSelectedNodeId(nodeId);
        setPendingConnectionSourceId((current) => {
            const nextSourceId = current === nodeId ? null : nodeId;
            setSaveMessage(nextSourceId ? 'Select a target node input handle to create a connection.' : 'Connection cancelled.');
            return nextSourceId;
        });
    };

    const handleCompleteConnection = (targetNodeId: string) => {
        if (!pendingConnectionSourceId || pendingConnectionSourceId === targetNodeId) {
            return;
        }

        const validNodeIds = new Set(nodes.map((node) => node.id));
        const nextEdges = normalizeEdges([
            ...edges,
            {
                source: pendingConnectionSourceId,
                target: targetNodeId,
                relation: 'isStructurallyFollowedBy',
            },
        ], validNodeIds, nodes);

        setEdges(nextEdges);
        setSelectedNodeId(targetNodeId);
        updateValidationForStructureChange('Connected pipeline components on the canvas.');
    };

    const handleRemoveSelectedConnections = () => {
        if (!selectedNode) {
            return;
        }
        setEdges((current) => current.filter((edge) => edge.source !== selectedNode.id && edge.target !== selectedNode.id));
        updateValidationForStructureChange(`Removed connections for ${selectedNode.title}.`);
    };

    return (
        <div className="pipeline-editor-page">
            <section className="pipeline-editor-hero">
                <div className="pipeline-editor-hero-copy">
                    <div className="pipeline-editor-kicker">MLLO Editor</div>
                    <h1>{pipelineName || 'Pipeline Editor'}</h1>
                    <p>
                        Build and rearrange pipeline instances on a freeform canvas, keep MLLO mappings in the inspector,
                        and save explicit workflow connections back into the editor draft.
                    </p>
                </div>

                <div className="pipeline-editor-hero-actions">
                    <button type="button" onClick={handleSaveDraft} disabled={isBusy}>Save Draft</button>
                    <button type="button" className="pipeline-editor-secondary" onClick={handleResetDraft} disabled={isBusy}>Reset Draft</button>
                    <button type="button" className="pipeline-editor-secondary" onClick={handleRunReasoner} disabled={isBusy}>Run Reasoner</button>
                    <button type="button" className="pipeline-editor-secondary" onClick={handleUploadDraft} disabled={isBusy}>Upload Draft</button>
                </div>
            </section>

            <section className="pipeline-editor-launcher pipeline-editor-launcher-merged">
                <div className="pipeline-editor-launcher-copy">
                    <strong>{pipelineName ? `Editing ${pipelineName}` : 'Choose an existing pipeline or start fresh'}</strong>
                    <span>{saveMessage}</span>
                    <span>
                        {isBusy
                            ? 'Working with backend editor services...'
                            : lastSavedAt
                                ? `Last saved ${new Date(lastSavedAt).toLocaleString()}`
                                : 'No saved draft yet.'}
                    </span>
                </div>
                <div className="pipeline-editor-launcher-actions">
                    <select value={pipelinePickerValue} onChange={(event) => setPipelinePickerValue(event.target.value)}>
                        <option value="">Select existing pipeline</option>
                        {existingPipelines.map((name) => (
                            <option key={name} value={name}>{name}</option>
                        ))}
                    </select>
                    <button type="button" className="pipeline-editor-secondary" onClick={handleSelectPipeline} disabled={!pipelinePickerValue}>Load Pipeline</button>
                    <input
                        type="text"
                        value={newPipelineName}
                        onChange={(event) => setNewPipelineName(event.target.value)}
                        placeholder="New pipeline name"
                    />
                    <button type="button" className="pipeline-editor-secondary" onClick={handleStartNew} disabled={!newPipelineName.trim()}>New Pipeline</button>
                    <span className={`pipeline-editor-validation-pill pipeline-editor-validation-pill-${validationStatus}`}>
                        {validationStatus === 'unknown' && 'Validation pending'}
                        {validationStatus === 'passed' && 'Validation passed'}
                        {validationStatus === 'failed' && 'Validation failed'}
                    </span>
                </div>
            </section>

            <details className="pipeline-editor-collapse">
                <summary>Workspace Summary</summary>
                <section className="pipeline-editor-metrics">
                    <div className="pipeline-editor-metric">
                        <span className="pipeline-editor-metric-value">{nodes.length}</span>
                        <span className="pipeline-editor-metric-label">Visual nodes in current workflow</span>
                    </div>
                    <div className="pipeline-editor-metric">
                        <span className="pipeline-editor-metric-value">{draftPayload.edges.length}</span>
                        <span className="pipeline-editor-metric-label">Explicit graph connections stored in the draft</span>
                    </div>
                    <div className="pipeline-editor-metric">
                        <span className="pipeline-editor-metric-value">MLLO</span>
                        <span className="pipeline-editor-metric-label">Ontology rules and mappings shown separately from instance structure</span>
                    </div>
                </section>
            </details>

            <section className="pipeline-editor-tabbar">
                {(['overview', 'compare', 'reasoning', 'history'] as EditorTab[]).map((tab) => (
                    <button
                        key={tab}
                        type="button"
                        className={selectedTab === tab ? 'active' : ''}
                        onClick={() => setSelectedTab(tab)}
                    >
                        {tab === 'overview' && 'Overview'}
                        {tab === 'compare' && 'Compare'}
                        {tab === 'reasoning' && 'Reasoning'}
                        {tab === 'history' && 'History'}
                    </button>
                ))}
            </section>

            <section className="pipeline-editor-layout">
                <div className="pipeline-editor-stage">
                    <div className="pipeline-editor-panel-header">
                        <h2>Pipeline Canvas</h2>
                        <p>
                            Drag cards to rearrange layout, use node handles to connect steps, and rely on the saved graph
                            structure when generating the publishable draft.
                        </p>
                    </div>

                    <PipelineCanvas
                        nodes={nodes}
                        edges={draftPayload.edges}
                        selectedNodeId={selectedNodeId}
                        selectedEdgeKey={selectedEdgeKey}
                        pendingConnectionSourceId={pendingConnectionSourceId}
                        onSelectNode={(nodeId) => {
                            setSelectedEdgeKey(null);
                            setSelectedNodeId(nodeId);
                        }}
                        onSelectEdge={(edgeKey) => {
                            setSelectedNodeId('');
                            setSelectedEdgeKey(edgeKey);
                        }}
                        onMoveNode={handleMoveNode}
                        onEndMove={handleEndMoveNode}
                        onStartConnection={handleStartConnection}
                        onCompleteConnection={handleCompleteConnection}
                        onCancelConnection={() => {
                            setPendingConnectionSourceId(null);
                            setSaveMessage('Connection cancelled.');
                        }}
                    />

                    <div className="pipeline-editor-actions-row">
                        <button type="button" className="pipeline-editor-secondary" onClick={handleAddComponent}>Add Component</button>
                        <button type="button" className="pipeline-editor-secondary" onClick={handleAutoLayout} disabled={nodes.length < 2}>Auto Layout</button>
                        <button type="button" className="pipeline-editor-secondary" onClick={handleDeleteSelectedEdge} disabled={!selectedEdgeKey}>Delete Selected Link</button>
                        <button type="button" className="pipeline-editor-secondary" onClick={handleRemoveSelectedConnections} disabled={!selectedNode}>Clear Selected Links</button>
                        <button type="button" className="pipeline-editor-secondary" onClick={handleDeleteSelectedNode} disabled={!selectedNode}>Delete Selected</button>
                        <span className="pipeline-editor-canvas-hint">
                            {selectedEdgeKey
                                ? 'Edge selected. Delete the selected link or click a node to return to node editing.'
                                : pendingConnectionSourceId
                                ? 'Connection mode is active. Click another node’s input handle to complete the link.'
                                : 'Drag nodes to reposition them. Use the right-side handle to start a connection.'}
                        </span>
                    </div>

                    {selectedTab === 'compare' && (
                        <details className="pipeline-editor-subpanel pipeline-editor-collapse" open>
                            <summary>Comparison Snapshot</summary>
                            <div className="pipeline-editor-panel-header">
                                <p>Use this area for pipeline-to-pipeline comparisons after loading a second workflow.</p>
                            </div>
                            <ul className="pipeline-editor-list">
                                {compareFindings.map((finding) => (
                                    <li key={finding}>{finding}</li>
                                ))}
                            </ul>
                        </details>
                    )}

                    {selectedTab === 'reasoning' && (
                        <details className="pipeline-editor-subpanel pipeline-editor-collapse" open>
                            <summary>Reasoning Checks</summary>
                            <div className="pipeline-editor-panel-header">
                                <p>Keep ontology-derived rules separate from observed instance structure.</p>
                            </div>
                            <div className="pipeline-editor-check-grid">
                                <div>
                                    <div className="pipeline-editor-check-title">Ontology status</div>
                                    <div className={`pipeline-editor-check-pill ${validationStatus === 'failed' ? 'warning' : 'success'}`}>
                                        {validationStatus === 'passed' ? 'Consistent under current draft' : validationStatus === 'failed' ? 'Draft needs correction' : 'Awaiting validation'}
                                    </div>
                                </div>
                                <div>
                                    <div className="pipeline-editor-check-title">Validation summary</div>
                                    <div className={`pipeline-editor-check-pill ${validationStatus === 'failed' ? 'warning' : 'success'}`}>{validationMessage}</div>
                                </div>
                            </div>
                            <ul className="pipeline-editor-list">
                                {customChecks.map((check) => (
                                    <li key={check}>{check}</li>
                                ))}
                            </ul>
                        </details>
                    )}

                    {selectedTab === 'history' && (
                        <details className="pipeline-editor-subpanel pipeline-editor-collapse" open>
                            <summary>Version History</summary>
                            <div className="pipeline-editor-panel-header">
                                <p>Trace edits, releases, and export snapshots over time.</p>
                            </div>
                            {historyItems.length === 0 ? (
                                <p className="pipeline-editor-empty-history">No saved or published versions yet.</p>
                            ) : (
                                <div className="pipeline-editor-history-list">
                                    {historyItems.map((item) => (
                                        <div key={`${item.version}-${item.savedAt}`} className="pipeline-editor-history-item">
                                            <div className="pipeline-editor-history-version">{item.version}</div>
                                            <div>
                                                <strong>{item.label}</strong>
                                                <p>{item.note}</p>
                                            </div>
                                            <span className={`pipeline-editor-history-status pipeline-editor-history-status-${item.status}`}>{item.status}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </details>
                    )}
                </div>

                <aside className={`pipeline-editor-sidebar ${activeDrawer ? 'open' : 'collapsed'}`}>
                    <div className="pipeline-editor-drawer-rail">
                        <button
                            type="button"
                            className={activeDrawer === 'inspector' ? 'active' : ''}
                            onClick={() => toggleDrawer('inspector')}
                            aria-pressed={activeDrawer === 'inspector'}
                            title="Toggle inspector"
                        >
                            Inspector
                        </button>
                        <button
                            type="button"
                            className={activeDrawer === 'export' ? 'active' : ''}
                            onClick={() => toggleDrawer('export')}
                            aria-pressed={activeDrawer === 'export'}
                            title="Toggle export and collaboration"
                        >
                            Export
                        </button>
                    </div>

                    {activeDrawer === 'inspector' && (
                        <section className="pipeline-editor-panel pipeline-editor-drawer">
                            <div className="pipeline-editor-panel-header">
                                <h3>Inspector</h3>
                                <p>Shows instance details, observed structure, and MLLO mappings without mixing them together.</p>
                            </div>

                            {!selectedNode && (
                                <div className="pipeline-editor-inspector-card">
                                    <h3>No selection</h3>
                                    <p>Select a pipeline from the launcher or click a node in the canvas to inspect its MLLO mapping.</p>
                                </div>
                            )}

                            {selectedNode && (
                                <>
                                    <div className="pipeline-editor-inspector-card">
                                        <div className="pipeline-editor-inspector-meta">
                                            <span>{kindLabel[selectedNode.kind]}</span>
                                            <span>Draft order #{orderIndexLookup.get(selectedNode.id) ?? '—'}</span>
                                        </div>
                                        <h3>{selectedNode.title}</h3>
                                        <code>{selectedNode.iri}</code>
                                        <p>{selectedNode.summary}</p>
                                    </div>

                                    <div className="pipeline-editor-sidebar-section">
                                        <h4>Rules and axioms</h4>
                                        <ul className="pipeline-editor-list">
                                            {selectedNode.rules.length > 0 ? selectedNode.rules.map((rule) => (
                                                <li key={rule}>{rule}</li>
                                            )) : <li>No MLLO rule extraction available for this node yet.</li>}
                                        </ul>
                                    </div>

                                    <div className="pipeline-editor-sidebar-section">
                                        <h4>Observed Structure</h4>
                                        <ul className="pipeline-editor-list">
                                            {selectedNode.observedStructure.length > 0 ? selectedNode.observedStructure.map((item) => (
                                                <li key={item}>{item}</li>
                                            )) : <li>No observed structure details available.</li>}
                                        </ul>
                                    </div>

                                    <div className="pipeline-editor-sidebar-section">
                                        <h4>MLLO Mapping</h4>
                                        <div className="pipeline-editor-mapping-block">
                                            <strong>Classes</strong>
                                            <ul className="pipeline-editor-list">
                                                {selectedNode.ontologyClasses.length > 0 ? selectedNode.ontologyClasses.map((item) => (
                                                    <li key={item}>{item}</li>
                                                )) : <li>No MLLO class mapping available.</li>}
                                            </ul>
                                        </div>
                                        <div className="pipeline-editor-mapping-block">
                                            <strong>Relations</strong>
                                            <ul className="pipeline-editor-list">
                                                {selectedNode.ontologyRelations.length > 0 ? selectedNode.ontologyRelations.map((item) => (
                                                    <li key={item}>{item}</li>
                                                )) : <li>No MLLO relation mapping available.</li>}
                                            </ul>
                                        </div>
                                    </div>

                                    <div className="pipeline-editor-sidebar-section">
                                        <h4>Potential impact</h4>
                                        <p>{selectedNode.impact}</p>
                                    </div>

                                    <div className="pipeline-editor-sidebar-section">
                                        <h4>Edit controls</h4>
                                        <div className="pipeline-editor-form">
                                            <label>
                                                Component label
                                                <input
                                                    type="text"
                                                    value={selectedNode.title}
                                                    onChange={(event) => {
                                                        const nextTitle = event.target.value;
                                                        setNodes((current) => current.map((node) => node.id === selectedNode.id ? {...node, title: nextTitle} : node));
                                                        setSaveMessage(`Updated label for ${selectedNode.title}.`);
                                                    }}
                                                />
                                            </label>
                                            <label>
                                                Component kind
                                                <select
                                                    value={selectedNode.kind}
                                                    onChange={(event) => {
                                                        const nextKind = event.target.value as PipelineNode['kind'];
                                                        setNodes((current) => current.map((node) => node.id === selectedNode.id ? {...node, kind: nextKind} : node));
                                                        updateValidationForStructureChange(`Updated ${selectedNode.title} kind to ${kindLabel[nextKind]}.`);
                                                    }}
                                                >
                                                    <option value="input">Input</option>
                                                    <option value="operation">Operation</option>
                                                    <option value="output">Output</option>
                                                    <option value="model">Model</option>
                                                </select>
                                            </label>
                                            <label>
                                                Notes
                                                <textarea
                                                    rows={4}
                                                    value={selectedNodeNote}
                                                    onChange={(event) => {
                                                        const nextValue = event.target.value;
                                                        setNodeNotes((current) => ({
                                                            ...current,
                                                            [selectedNode.id]: nextValue,
                                                        }));
                                                        setSaveMessage(`Updated draft note for ${selectedNode.title}.`);
                                                    }}
                                                />
                                            </label>
                                        </div>
                                    </div>
                                </>
                            )}
                        </section>
                    )}

                    {activeDrawer === 'export' && (
                        <section className="pipeline-editor-panel pipeline-editor-drawer">
                            <div className="pipeline-editor-panel-header">
                                <h3>Export & Collaboration</h3>
                                <p>Prepare the current pipeline for testing, handoff, or further ontology validation.</p>
                            </div>

                            <div className="pipeline-editor-export-card">
                                <div>
                                    <strong>Export target</strong>
                                    <p>Bundle the current pipeline graph, version metadata, and validation summary.</p>
                                </div>
                                <button type="button" onClick={handleUploadDraft} disabled={isBusy}>Publish Draft</button>
                            </div>

                            <div className="pipeline-editor-sidebar-section">
                                <h4>Suggested next actions</h4>
                                <ul className="pipeline-editor-list">
                                    <li>Load an existing pipeline directly from this editor when you want to modify one.</li>
                                    <li>Start from an empty canvas when you want to design a new workflow.</li>
                                    <li>Keep MLLO rules separate from observed structure while editing.</li>
                                </ul>
                            </div>

                            <div className="pipeline-editor-sidebar-section">
                                <h4>Draft payload</h4>
                                <p>{validationMessage}</p>
                                <pre className="pipeline-editor-draft-preview">{JSON.stringify(draftPayload, null, 2)}</pre>
                            </div>

                            <div className="pipeline-editor-sidebar-section">
                                <h4>Related tools</h4>
                                <div className="pipeline-editor-link-stack">
                                    <Link to="/pipelines">Open in Pipeline Search</Link>
                                    <Link to="/pipelines/compare-pipelines">Open Compare Pipelines</Link>
                                    <Link to="/chat-with-mllo">Ask Chat with MLLO</Link>
                                </div>
                            </div>
                        </section>
                    )}
                </aside>
            </section>
        </div>
    );
};

export default PipelineEditor;
