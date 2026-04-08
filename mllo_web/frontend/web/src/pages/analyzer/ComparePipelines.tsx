import React, {useEffect, useMemo, useState} from 'react';
import {Link, useSearchParams} from 'react-router-dom';
import {ComparedPipeline, comparePipelines, getExistingPipelines} from '../../services/api';
import './styles/discovery.css';

const toSet = (values: string[]) => new Set(values.filter(Boolean));

const ComparePipelines: React.FC = () => {
    const [searchParams, setSearchParams] = useSearchParams();
    const [existingPipelines, setExistingPipelines] = useState<string[]>([]);
    const [leftSelection, setLeftSelection] = useState(searchParams.get('pipeline_a') || '');
    const [rightSelection, setRightSelection] = useState(searchParams.get('pipeline_b') || '');
    const [pipelines, setPipelines] = useState<ComparedPipeline[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const load = async () => {
            try {
                const names = await getExistingPipelines();
                setExistingPipelines(names);
            } catch (err) {
                setError((err as Error).message);
            }
        };
        void load();
    }, []);

    useEffect(() => {
        const a = searchParams.get('pipeline_a') || '';
        const b = searchParams.get('pipeline_b') || '';
        setLeftSelection(a);
        setRightSelection(b);
    }, [searchParams]);

    useEffect(() => {
        const pipelineA = searchParams.get('pipeline_a');
        const pipelineB = searchParams.get('pipeline_b');
        if (!pipelineA || !pipelineB) {
            setPipelines([]);
            return;
        }

        const load = async () => {
            setLoading(true);
            setError(null);
            try {
                const rows = await comparePipelines([pipelineA, pipelineB]);
                setPipelines(rows);
            } catch (err) {
                setError((err as Error).message);
                setPipelines([]);
            } finally {
                setLoading(false);
            }
        };
        void load();
    }, [searchParams]);

    const compared = useMemo(() => {
        const left = pipelines.find((item) => item.pipeline_name === leftSelection) ?? pipelines[0] ?? null;
        const right = pipelines.find((item) => item.pipeline_name === rightSelection) ?? pipelines[1] ?? null;
        return {left, right};
    }, [leftSelection, pipelines, rightSelection]);

    const comparison = useMemo(() => {
        if (!compared.left || !compared.right) {
            return null;
        }

        const leftComponents = toSet(compared.left.pipeline_components ?? []);
        const rightComponents = toSet(compared.right.pipeline_components ?? []);
        const sharedComponents = [...leftComponents].filter((item) => rightComponents.has(item));
        const leftOnlyComponents = [...leftComponents].filter((item) => !rightComponents.has(item));
        const rightOnlyComponents = [...rightComponents].filter((item) => !leftComponents.has(item));

        return {
            sharedComponents,
            leftOnlyComponents,
            rightOnlyComponents,
            sameType: compared.left.pipeline_type === compared.right.pipeline_type,
            sameInput: compared.left.pipeline_data_input === compared.right.pipeline_data_input,
            sameOutput: compared.left.pipeline_data_output === compared.right.pipeline_data_output,
            sameModel: compared.left.pipeline_associated_model === compared.right.pipeline_associated_model,
        };
    }, [compared.left, compared.right]);

    const handleRunComparison = () => {
        if (!leftSelection || !rightSelection) {
            return;
        }
        setSearchParams({
            pipeline_a: leftSelection,
            pipeline_b: rightSelection,
        });
    };

    const swapSelections = () => {
        setLeftSelection(rightSelection);
        setRightSelection(leftSelection);
    };

    const renderPipelineCard = (pipeline: ComparedPipeline | null, sideLabel: string) => (
        <div className="discovery-panel" style={{display: 'flex', flexDirection: 'column', gap: '0.9rem'}}>
            <div>
                <div style={{fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#6b7280'}}>{sideLabel}</div>
                <h3 style={{margin: '0.3rem 0 0'}}>{pipeline?.pipeline_name || 'Not loaded'}</h3>
            </div>

            {!pipeline ? (
                <p style={{margin: 0, color: '#6b7280'}}>Select two pipelines and run the comparison.</p>
            ) : (
                <>
                    <div style={{display: 'grid', gap: '0.65rem'}}>
                        <div>
                            <strong>Type</strong>
                            <div>{pipeline.pipeline_type || 'Unknown'}</div>
                        </div>
                        <div>
                            <strong>Input</strong>
                            <div>{pipeline.pipeline_data_input || 'None'}</div>
                        </div>
                        <div>
                            <strong>Output</strong>
                            <div>{pipeline.pipeline_data_output || 'None'}</div>
                        </div>
                        <div>
                            <strong>Associated Model</strong>
                            <div>{pipeline.pipeline_associated_model || 'None'}</div>
                        </div>
                        <div>
                            <strong>Components</strong>
                            <ul style={{margin: '0.45rem 0 0 1rem'}}>
                                {(pipeline.pipeline_components ?? []).map((component) => (
                                    <li key={`${pipeline.pipeline_name}-${component}`}>{component}</li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    <div style={{display: 'flex', gap: '0.5rem', flexWrap: 'wrap'}}>
                        <Link to={`/pipelines/edit-pipeline?pipeline-name=${pipeline.pipeline_name}`}>Open in Editor</Link>
                        <Link to={`/chat-with-mllo`}>Ask in Chat</Link>
                    </div>
                </>
            )}
        </div>
    );

    return (
        <div className="discovery-page">
            <div className="discovery-hero">
                <div>
                    <h1>Compare Pipelines</h1>
                    <p>Pick two existing pipelines and compare their real input, output, model, and component structure side by side.</p>
                </div>
            </div>

            <section className="discovery-panel" style={{display: 'grid', gap: '1rem'}}>
                <div style={{display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto minmax(0, 1fr) auto', gap: '0.75rem', alignItems: 'end'}}>
                    <label style={{display: 'flex', flexDirection: 'column', gap: '0.35rem'}}>
                        Left pipeline
                        <select value={leftSelection} onChange={(event) => setLeftSelection(event.target.value)}>
                            <option value="">Select pipeline</option>
                            {existingPipelines.map((name) => (
                                <option key={`left-${name}`} value={name}>{name}</option>
                            ))}
                        </select>
                    </label>

                    <button type="button" onClick={swapSelections}>Swap</button>

                    <label style={{display: 'flex', flexDirection: 'column', gap: '0.35rem'}}>
                        Right pipeline
                        <select value={rightSelection} onChange={(event) => setRightSelection(event.target.value)}>
                            <option value="">Select pipeline</option>
                            {existingPipelines.map((name) => (
                                <option key={`right-${name}`} value={name}>{name}</option>
                            ))}
                        </select>
                    </label>

                    <button type="button" onClick={handleRunComparison} disabled={!leftSelection || !rightSelection || leftSelection === rightSelection}>
                        Compare
                    </button>
                </div>

                <div style={{fontSize: '0.92rem', color: '#4b5563'}}>
                    Use this page when you want a direct structural comparison before opening a pipeline in the editor or asking a comparison question in chat.
                </div>
            </section>

            {error && (
                <section className="discovery-panel">
                    <div style={{color: '#b91c1c'}}>{error}</div>
                </section>
            )}

            {loading && (
                <section className="discovery-panel">
                    <div>Loading comparison…</div>
                </section>
            )}

            {comparison && compared.left && compared.right && (
                <section className="discovery-panel" style={{display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '0.9rem'}}>
                    <div>
                        <strong>{comparison.sharedComponents.length}</strong>
                        <div>Shared components</div>
                    </div>
                    <div>
                        <strong>{comparison.leftOnlyComponents.length}</strong>
                        <div>Left-only components</div>
                    </div>
                    <div>
                        <strong>{comparison.rightOnlyComponents.length}</strong>
                        <div>Right-only components</div>
                    </div>
                    <div>
                        <strong>{comparison.sameType ? 'Same type' : 'Different types'}</strong>
                        <div>Top-level pipeline classification</div>
                    </div>
                </section>
            )}

            <section style={{display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '1rem'}}>
                {renderPipelineCard(compared.left, 'Left pipeline')}
                {renderPipelineCard(compared.right, 'Right pipeline')}
            </section>

            {comparison && (
                <section className="discovery-panel" style={{display: 'grid', gap: '1rem', marginTop: '1rem'}}>
                    <div>
                        <h3 style={{marginTop: 0}}>Comparison Summary</h3>
                        <p style={{marginBottom: '0.5rem'}}>
                            This view shows which parts of the two pipelines overlap and where they diverge before you move into deeper MLLO reasoning or editing.
                        </p>
                    </div>

                    <div style={{display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '1rem'}}>
                        <div>
                            <strong>Shared structure</strong>
                            <ul style={{margin: '0.5rem 0 0 1rem'}}>
                                <li>{comparison.sameType ? 'Same pipeline type' : 'Different pipeline types'}</li>
                                <li>{comparison.sameInput ? 'Same input dataset' : 'Different input datasets'}</li>
                                <li>{comparison.sameOutput ? 'Same output dataset' : 'Different output datasets'}</li>
                                <li>{comparison.sameModel ? 'Same associated model' : 'Different associated models'}</li>
                                {comparison.sharedComponents.map((component) => (
                                    <li key={`shared-${component}`}>{component}</li>
                                ))}
                            </ul>
                        </div>

                        <div>
                            <strong>Differences</strong>
                            <div style={{marginTop: '0.5rem'}}>
                                <div><strong>Only in {compared.left?.pipeline_name}</strong></div>
                                <ul style={{margin: '0.35rem 0 0.8rem 1rem'}}>
                                    {comparison.leftOnlyComponents.length > 0 ? comparison.leftOnlyComponents.map((component) => (
                                        <li key={`left-only-${component}`}>{component}</li>
                                    )) : <li>No unique components</li>}
                                </ul>
                                <div><strong>Only in {compared.right?.pipeline_name}</strong></div>
                                <ul style={{margin: '0.35rem 0 0 1rem'}}>
                                    {comparison.rightOnlyComponents.length > 0 ? comparison.rightOnlyComponents.map((component) => (
                                        <li key={`right-only-${component}`}>{component}</li>
                                    )) : <li>No unique components</li>}
                                </ul>
                            </div>
                        </div>
                    </div>
                </section>
            )}
        </div>
    );
};

export default ComparePipelines;
