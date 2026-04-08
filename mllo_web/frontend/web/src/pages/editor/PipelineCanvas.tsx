import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {PipelineEditorEdge} from '../../services/api';

export const CANVAS_NODE_WIDTH = 210;
export const CANVAS_NODE_HEIGHT = 122;
const CANVAS_PADDING = 24;
const MIN_SCALE = 0.55;
const MAX_SCALE = 1.8;

export interface CanvasNode {
    id: string;
    title: string;
    kind: 'input' | 'operation' | 'output' | 'model';
    summary: string;
    x: number;
    y: number;
}

interface PipelineCanvasProps {
    nodes: CanvasNode[];
    edges: PipelineEditorEdge[];
    selectedNodeId: string;
    selectedEdgeKey: string | null;
    pendingConnectionSourceId: string | null;
    onSelectNode: (nodeId: string) => void;
    onSelectEdge: (edgeKey: string | null) => void;
    onMoveNode: (nodeId: string, x: number, y: number) => void;
    onEndMove: (nodeId: string) => void;
    onStartConnection: (nodeId: string) => void;
    onCompleteConnection: (targetNodeId: string) => void;
    onCancelConnection: () => void;
}

interface DragState {
    nodeId: string;
    offsetX: number;
    offsetY: number;
}

interface PanState {
    pointerX: number;
    pointerY: number;
    originX: number;
    originY: number;
}

interface ViewportState {
    x: number;
    y: number;
    scale: number;
}

const kindLabel: Record<CanvasNode['kind'], string> = {
    input: 'Input',
    operation: 'Operation',
    output: 'Output',
    model: 'Model',
};

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);
const edgeKeyFor = (edge: PipelineEditorEdge) => `${edge.source}::${edge.target}`;

const PipelineCanvas: React.FC<PipelineCanvasProps> = ({
    nodes,
    edges,
    selectedNodeId,
    selectedEdgeKey,
    pendingConnectionSourceId,
    onSelectNode,
    onSelectEdge,
    onMoveNode,
    onEndMove,
    onStartConnection,
    onCompleteConnection,
    onCancelConnection,
}) => {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const hasAutoFitRef = useRef(false);
    const [dragState, setDragState] = useState<DragState | null>(null);
    const [panState, setPanState] = useState<PanState | null>(null);
    const [canvasSize, setCanvasSize] = useState({width: 960, height: 520});
    const [viewport, setViewport] = useState<ViewportState>({x: 0, y: 0, scale: 1});

    const nodeLookup = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes]);
    const validEdges = useMemo(
        () => edges.filter((edge) => nodeLookup.has(edge.source) && nodeLookup.has(edge.target)),
        [edges, nodeLookup],
    );

    const surfaceBounds = useMemo(() => {
        if (nodes.length === 0) {
            return {
                minX: 0,
                minY: 0,
                maxX: canvasSize.width,
                maxY: canvasSize.height,
                width: canvasSize.width,
                height: canvasSize.height,
            };
        }

        const minX = Math.min(...nodes.map((node) => node.x)) - CANVAS_PADDING;
        const minY = Math.min(...nodes.map((node) => node.y)) - CANVAS_PADDING;
        const maxX = Math.max(...nodes.map((node) => node.x + CANVAS_NODE_WIDTH)) + CANVAS_PADDING;
        const maxY = Math.max(...nodes.map((node) => node.y + CANVAS_NODE_HEIGHT)) + CANVAS_PADDING;
        return {
            minX,
            minY,
            maxX,
            maxY,
            width: Math.max(maxX - minX, canvasSize.width),
            height: Math.max(maxY - minY, canvasSize.height),
        };
    }, [canvasSize.height, canvasSize.width, nodes]);

    const fitToView = useCallback(() => {
        const container = containerRef.current;
        if (!container) {
            return;
        }

        if (nodes.length === 0) {
            setViewport({x: 0, y: 0, scale: 1});
            return;
        }

        const containerRect = container.getBoundingClientRect();
        const availableWidth = Math.max(containerRect.width - 48, 320);
        const availableHeight = Math.max(containerRect.height - 48, 240);
        const nextScale = clamp(
            Math.min(availableWidth / surfaceBounds.width, availableHeight / surfaceBounds.height),
            MIN_SCALE,
            1.1,
        );
        const nextX = (containerRect.width - (surfaceBounds.width * nextScale)) / 2 - (surfaceBounds.minX * nextScale);
        const nextY = (containerRect.height - (surfaceBounds.height * nextScale)) / 2 - (surfaceBounds.minY * nextScale);
        setViewport({x: nextX, y: nextY, scale: nextScale});
    }, [nodes.length, surfaceBounds.height, surfaceBounds.minX, surfaceBounds.minY, surfaceBounds.width]);

    useEffect(() => {
        const container = containerRef.current;
        if (!container || typeof ResizeObserver === 'undefined') {
            return undefined;
        }

        const observer = new ResizeObserver((entries) => {
            const entry = entries[0];
            if (!entry) {
                return;
            }
            const nextWidth = Math.max(entry.contentRect.width, 960);
            const maxX = nodes.reduce((currentMax, node) => Math.max(currentMax, node.x + CANVAS_NODE_WIDTH + CANVAS_PADDING), 0);
            const maxY = nodes.reduce((currentMax, node) => Math.max(currentMax, node.y + CANVAS_NODE_HEIGHT + CANVAS_PADDING), 0);
            setCanvasSize({
                width: Math.max(nextWidth, maxX, 960),
                height: Math.max(520, maxY, 520),
            });
        });

        observer.observe(container);
        return () => observer.disconnect();
    }, [nodes]);

    useEffect(() => {
        if (nodes.length === 0) {
            hasAutoFitRef.current = false;
            setViewport({x: 0, y: 0, scale: 1});
            return;
        }

        if (!hasAutoFitRef.current) {
            fitToView();
            hasAutoFitRef.current = true;
        }
    }, [fitToView, nodes.length]);

    useEffect(() => {
        if (!dragState && !panState) {
            return undefined;
        }

        const handlePointerMove = (event: PointerEvent) => {
            const container = containerRef.current;
            if (!container) {
                return;
            }

            if (dragState) {
                const rect = container.getBoundingClientRect();
                const nextX = clamp(
                    (event.clientX - rect.left - viewport.x) / viewport.scale - dragState.offsetX,
                    CANVAS_PADDING,
                    Math.max(CANVAS_PADDING, canvasSize.width - CANVAS_NODE_WIDTH - CANVAS_PADDING),
                );
                const nextY = clamp(
                    (event.clientY - rect.top - viewport.y) / viewport.scale - dragState.offsetY,
                    CANVAS_PADDING,
                    Math.max(CANVAS_PADDING, canvasSize.height - CANVAS_NODE_HEIGHT - CANVAS_PADDING),
                );
                onMoveNode(dragState.nodeId, nextX, nextY);
                return;
            }

            if (panState) {
                setViewport((current) => ({
                    ...current,
                    x: panState.originX + (event.clientX - panState.pointerX),
                    y: panState.originY + (event.clientY - panState.pointerY),
                }));
            }
        };

        const handlePointerUp = () => {
            if (dragState) {
                onEndMove(dragState.nodeId);
            }
            setDragState(null);
            setPanState(null);
        };

        window.addEventListener('pointermove', handlePointerMove);
        window.addEventListener('pointerup', handlePointerUp);
        return () => {
            window.removeEventListener('pointermove', handlePointerMove);
            window.removeEventListener('pointerup', handlePointerUp);
        };
    }, [canvasSize.height, canvasSize.width, dragState, onEndMove, onMoveNode, panState, viewport.scale, viewport.x, viewport.y]);

    const applyZoom = useCallback((nextScale: number, anchorX?: number, anchorY?: number) => {
        const container = containerRef.current;
        if (!container) {
            return;
        }

        const clampedScale = clamp(nextScale, MIN_SCALE, MAX_SCALE);
        setViewport((current) => {
            const rect = container.getBoundingClientRect();
            const focusX = anchorX ?? rect.width / 2;
            const focusY = anchorY ?? rect.height / 2;
            const canvasX = (focusX - current.x) / current.scale;
            const canvasY = (focusY - current.y) / current.scale;
            return {
                scale: clampedScale,
                x: focusX - (canvasX * clampedScale),
                y: focusY - (canvasY * clampedScale),
            };
        });
    }, []);

    return (
        <div className="pipeline-editor-canvas-shell">
            <div className="pipeline-editor-canvas-toolbar">
                <button type="button" onClick={() => applyZoom(viewport.scale - 0.1)} disabled={viewport.scale <= MIN_SCALE}>-</button>
                <span>{Math.round(viewport.scale * 100)}%</span>
                <button type="button" onClick={() => applyZoom(viewport.scale + 0.1)} disabled={viewport.scale >= MAX_SCALE}>+</button>
                <button type="button" onClick={() => setViewport({x: 0, y: 0, scale: 1})}>Reset View</button>
                <button type="button" onClick={fitToView}>Fit View</button>
            </div>

            <div
                ref={containerRef}
                className={`pipeline-editor-canvas ${panState ? 'panning' : ''}`}
                onClick={() => {
                    onSelectEdge(null);
                    if (pendingConnectionSourceId) {
                        onCancelConnection();
                    }
                }}
                onWheel={(event) => {
                    if (!event.ctrlKey && !event.metaKey) {
                        return;
                    }
                    event.preventDefault();
                    const rect = containerRef.current?.getBoundingClientRect();
                    if (!rect) {
                        return;
                    }
                    applyZoom(
                        viewport.scale + (event.deltaY < 0 ? 0.08 : -0.08),
                        event.clientX - rect.left,
                        event.clientY - rect.top,
                    );
                }}
                onPointerDown={(event) => {
                    if ((event.target as HTMLElement).closest('.pipeline-node, .pipeline-editor-canvas-toolbar')) {
                        return;
                    }
                    setPanState({
                        pointerX: event.clientX,
                        pointerY: event.clientY,
                        originX: viewport.x,
                        originY: viewport.y,
                    });
                }}
            >
                {nodes.length === 0 && (
                    <div className="pipeline-editor-empty-canvas">
                        <strong>Empty canvas</strong>
                        <p>Select an existing pipeline above or start designing a new workflow from scratch.</p>
                    </div>
                )}

                {nodes.length > 0 && (
                    <div
                        className="pipeline-editor-canvas-viewport"
                        style={{transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.scale})`}}
                    >
                        <div
                            className="pipeline-editor-canvas-surface"
                            style={{width: `${canvasSize.width}px`, height: `${canvasSize.height}px`}}
                        >
                            <svg className="pipeline-editor-canvas-svg" aria-hidden="true">
                                <defs>
                                    <marker
                                        id="pipeline-editor-arrow"
                                        markerWidth="10"
                                        markerHeight="10"
                                        refX="8"
                                        refY="5"
                                        orient="auto"
                                    >
                                        <path d="M0,0 L10,5 L0,10 Z" fill="#27445d"/>
                                    </marker>
                                </defs>
                                {validEdges.map((edge) => {
                                    const sourceNode = nodeLookup.get(edge.source);
                                    const targetNode = nodeLookup.get(edge.target);
                                    if (!sourceNode || !targetNode) {
                                        return null;
                                    }

                                    const startX = sourceNode.x + CANVAS_NODE_WIDTH;
                                    const startY = sourceNode.y + (CANVAS_NODE_HEIGHT / 2);
                                    const endX = targetNode.x;
                                    const endY = targetNode.y + (CANVAS_NODE_HEIGHT / 2);
                                    const controlOffset = Math.max(80, Math.abs(endX - startX) * 0.45);
                                    const path = `M ${startX} ${startY} C ${startX + controlOffset} ${startY}, ${endX - controlOffset} ${endY}, ${endX} ${endY}`;
                                    const edgeKey = edgeKeyFor(edge);

                                    return (
                                        <path
                                            key={`${edgeKey}-${edge.relation}`}
                                            className={`pipeline-editor-edge ${selectedEdgeKey === edgeKey ? 'selected' : ''}`}
                                            d={path}
                                            markerEnd="url(#pipeline-editor-arrow)"
                                            onClick={(event) => {
                                                event.stopPropagation();
                                                onSelectEdge(edgeKey);
                                            }}
                                        />
                                    );
                                })}
                            </svg>

                            {nodes.map((node) => {
                                const isSelected = selectedNodeId === node.id;
                                const isConnectingFromNode = pendingConnectionSourceId === node.id;

                                return (
                                    <div
                                        key={node.id}
                                        className={[
                                            'pipeline-node',
                                            `pipeline-node-${node.kind}`,
                                            isSelected ? 'selected' : '',
                                            isConnectingFromNode ? 'connecting' : '',
                                            dragState?.nodeId === node.id ? 'dragging' : '',
                                        ].filter(Boolean).join(' ')}
                                        style={{left: `${node.x}px`, top: `${node.y}px`}}
                                        onClick={(event) => {
                                            event.stopPropagation();
                                            onSelectEdge(null);
                                            onSelectNode(node.id);
                                        }}
                                        onPointerDown={(event) => {
                                            if ((event.target as HTMLElement).closest('button')) {
                                                return;
                                            }
                                            const rect = (event.currentTarget as HTMLDivElement).getBoundingClientRect();
                                            setDragState({
                                                nodeId: node.id,
                                                offsetX: (event.clientX - rect.left) / viewport.scale,
                                                offsetY: (event.clientY - rect.top) / viewport.scale,
                                            });
                                        }}
                                    >
                                        <button
                                            type="button"
                                            className="pipeline-node-handle pipeline-node-handle-in"
                                            title={pendingConnectionSourceId && pendingConnectionSourceId !== node.id ? `Connect into ${node.title}` : 'Incoming connection point'}
                                            onClick={(event) => {
                                                event.stopPropagation();
                                                if (!pendingConnectionSourceId || pendingConnectionSourceId === node.id) {
                                                    return;
                                                }
                                                onCompleteConnection(node.id);
                                            }}
                                        />

                                        <div className="pipeline-node-body">
                                            <div className="pipeline-node-topline">
                                                <span className="pipeline-node-kind">{kindLabel[node.kind]}</span>
                                                <span className="pipeline-node-drag-badge">Drag</span>
                                            </div>
                                            <strong>{node.title}</strong>
                                            <p>{node.summary}</p>
                                        </div>

                                        <button
                                            type="button"
                                            className="pipeline-node-handle pipeline-node-handle-out"
                                            title={isConnectingFromNode ? 'Cancel connection' : `Start connection from ${node.title}`}
                                            onClick={(event) => {
                                                event.stopPropagation();
                                                if (isConnectingFromNode) {
                                                    onCancelConnection();
                                                    return;
                                                }
                                                onStartConnection(node.id);
                                            }}
                                        />
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default PipelineCanvas;
