import React, {useEffect, useMemo, useState} from 'react';
import {useLocation, useNavigate} from 'react-router-dom';
import {buildV1Url} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import ErrorMessage from '../../components/ErrorMessage.tsx';
import Search from '../../components/Search.tsx';
import {DownloadIcon} from '../../components/Icons.tsx';
import DropdownFilter from '../../components/DropdownFilter';
import Modal from '../../components/Modal.tsx';
import {lowercaseToPascalCase, pascalCaseToWords} from '../../components/FormatUtilities.tsx';
import './styles/discovery.css';

interface ModelRecord {
    model: string;
    model_type: string;
    model_objective_iri: string;
    model_objective: string;
    model_objective_description: string;
    deployment_status: string;
    linked_dataset: string;
    linked_dataset_type: string;
    linked_pipeline: string;
    deployed_on_system: string;
    last_model_update: string;
    last_model_execution: string;
    model_output_utilization: string;
    model_performance_metric: string;
    model_performance_value: string;
}

interface ExplorerModel {
    iri: string;
    label: string;
    modelTypes: string[];
    objectiveIris: string[];
    objectives: string[];
    objectiveDescriptions: string[];
    deploymentStatus: 'Deployed' | 'Undeployed';
    linkedDatasets: { iri: string; typeLabel: string }[];
    linkedPipelines: string[];
    deployedOnSystems: string[];
    outputUtilizations: string[];
    performanceEntries: { metric: string; value: string; relatedDataset: string; relatedDatasetType: string }[];
    lastModelUpdate: string;
    lastModelExecution: string;
}

interface IRIQueryData {
    dataPropertyValuePairs: string;
    annotationPropertyValuePairs: string;
    types: string;
}

const escapeCsvValue = (value: unknown) => {
    const text = value === null || value === undefined ? '' : String(value);
    return `"${text.replace(/"/g, '""')}"`;
};

const downloadCsv = (filename: string, headers: string[], rows: unknown[][]) => {
    const csv = [headers, ...rows]
        .map((row) => row.map(escapeCsvValue).join(','))
        .join('\n');

    const blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
};

const getUniqueIriPart = (iri: string): string => {
    const parts = iri.split('#');
    return parts.length > 1 ? parts[1] : iri;
};

const humanizeText = (value: string) => {
    if (/^[A-Z][a-z0-9]+([A-Z][a-z0-9]*)*$/.test(value)) {
        return pascalCaseToWords(value);
    }
    if (/^[a-z ]+$/.test(value)) {
        return lowercaseToPascalCase(value);
    }
    return value;
};

const formatObjectives = (objectives: string[]) => {
    const formatted = objectives.map(humanizeText).filter(Boolean);
    return formatted.length > 0 ? formatted.join(', ') : 'Objective not recorded';
};

const formatDescriptions = (descriptions: string[]) => {
    const formatted = descriptions.filter((description) => description.trim().length > 0);
    return formatted.length > 0 ? formatted.join(' ') : 'Description not recorded';
};

const FindModels: React.FC = () => {
    const location = useLocation();
    const initialParams = new URLSearchParams(location.search);
    const [searchTerm, setSearchTerm] = useState(initialParams.get('search_term') ?? '');
    const [rows, setRows] = useState<ModelRecord[]>([]);
    const [selectedModelTypes, setSelectedModelTypes] = useState<string[]>([]);
    const [selectedDeploymentStatus, setSelectedDeploymentStatus] = useState<string[]>(initialParams.getAll('deployment_status'));
    const [selectedModelIri, setSelectedModelIri] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [isPopupOpen, setIsPopupOpen] = useState(false);
    const [iriQueryResult, setQueryResult] = useState<IRIQueryData[] | null>(null);
    const [clickedIri, setClickedIri] = useState<string | null>(null);

    const navigate = useNavigate();

    const explorerModels = useMemo<ExplorerModel[]>(() => {
        const grouped = new Map<string, ExplorerModel>();

        const addUnique = (items: string[], value?: string | null) => {
            if (!value || value.trim().length === 0) {
                return;
            }
            if (!items.includes(value)) {
                items.push(value);
            }
        };

        rows.forEach((row) => {
            if (!row.model) {
                return;
            }

            const current = grouped.get(row.model) ?? {
                iri: row.model,
                label: pascalCaseToWords(getUniqueIriPart(row.model)),
                modelTypes: [],
                objectiveIris: [],
                objectives: [],
                objectiveDescriptions: [],
                deploymentStatus: row.deployment_status === 'Deployed' ? 'Deployed' : 'Undeployed',
                linkedDatasets: [],
                linkedPipelines: [],
                deployedOnSystems: [],
                outputUtilizations: [],
                performanceEntries: [],
                lastModelUpdate: row.last_model_update ?? '',
                lastModelExecution: row.last_model_execution ?? '',
            };

            if (row.deployment_status === 'Deployed') {
                current.deploymentStatus = 'Deployed';
            }
            addUnique(current.modelTypes, row.model_type);
            addUnique(current.objectiveIris, row.model_objective_iri);
            addUnique(current.objectives, row.model_objective);
            addUnique(current.objectiveDescriptions, row.model_objective_description);
            if (row.linked_dataset && !current.linkedDatasets.some((dataset) => dataset.iri === row.linked_dataset && dataset.typeLabel === (row.linked_dataset_type || 'Unclassified dataset'))) {
                current.linkedDatasets.push({
                    iri: row.linked_dataset,
                    typeLabel: row.linked_dataset_type || 'Unclassified dataset',
                });
            }
            addUnique(current.linkedPipelines, row.linked_pipeline);
            addUnique(current.deployedOnSystems, row.deployed_on_system);
            addUnique(current.outputUtilizations, row.model_output_utilization);

            if ((row.model_performance_metric && row.model_performance_metric.trim().length > 0)
                || (row.model_performance_value && row.model_performance_value.trim().length > 0)) {
                const entry = {
                    metric: row.model_performance_metric || 'Unspecified metric',
                    value: row.model_performance_value || 'Unspecified value',
                    relatedDataset: row.linked_dataset || '',
                    relatedDatasetType: row.linked_dataset_type || 'Unclassified dataset',
                };
                if (!current.performanceEntries.some((existing) =>
                    existing.metric === entry.metric
                    && existing.value === entry.value
                    && existing.relatedDataset === entry.relatedDataset
                    && existing.relatedDatasetType === entry.relatedDatasetType
                )) {
                    current.performanceEntries.push(entry);
                }
            }

            if ((!current.lastModelUpdate || current.lastModelUpdate < row.last_model_update) && row.last_model_update) {
                current.lastModelUpdate = row.last_model_update;
            }
            if ((!current.lastModelExecution || current.lastModelExecution < row.last_model_execution) && row.last_model_execution) {
                current.lastModelExecution = row.last_model_execution;
            }

            grouped.set(row.model, current);
        });

        return Array.from(grouped.values()).sort((left, right) => {
            if (left.deploymentStatus !== right.deploymentStatus) {
                return left.deploymentStatus === 'Deployed' ? -1 : 1;
            }
            return left.label.localeCompare(right.label);
        });
    }, [rows]);

    const selectedModel = useMemo(() => {
        if (explorerModels.length === 0) {
            return null;
        }
        return explorerModels.find((model) => model.iri === selectedModelIri) ?? explorerModels[0];
    }, [explorerModels, selectedModelIri]);

    const fetchData = async (
        nextSearchTerm: string,
        modelTypes: string[],
        deploymentStatuses: string[],
    ) => {
        setIsLoading(true);
        setMessage('');
        setError(null);
        try {
            const allRows: ModelRecord[] = [];
            let page = 1;
            let totalPages = 1;

            while (page <= totalPages) {
                const urlParams = new URLSearchParams({
                    search_term: nextSearchTerm,
                    page: String(page),
                    items_per_page: '250',
                });

                urlParams.append('sort', 'Model,asc');
                modelTypes.forEach((type) => urlParams.append('model_types', type));
                deploymentStatuses.forEach((status) => urlParams.append('deployment_status', status));

                const response = await fetch(buildV1Url(`models/?${urlParams.toString()}`));
                if (!response.ok) {
                    throw new Error(`Failed to fetch models: ${response.statusText}`);
                }

                const payload = await response.json();
                totalPages = payload.total_pages || 0;
                allRows.push(...payload.data);
                page += 1;
            }

            setRows(allRows);
            setMessage(allRows.length === 0 ? 'No models found.' : '');
        } catch (fetchError) {
            console.error('Error fetching models:', fetchError);
            setError((fetchError as Error).message);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        const params = new URLSearchParams(location.search);
        const seededSearchTerm = params.get('search_term') ?? '';
        const seededDeploymentStatus = params.getAll('deployment_status');
        setSearchTerm(seededSearchTerm);
        setSelectedDeploymentStatus(seededDeploymentStatus);
        void fetchData(seededSearchTerm, selectedModelTypes, seededDeploymentStatus);
    }, [location.search]);

    useEffect(() => {
        if (!selectedModelIri && explorerModels.length > 0) {
            setSelectedModelIri(explorerModels[0].iri);
            return;
        }

        if (selectedModelIri && !explorerModels.some((model) => model.iri === selectedModelIri)) {
            setSelectedModelIri(explorerModels[0]?.iri ?? null);
        }
    }, [explorerModels, selectedModelIri]);

    const handleSearch = async (nextSearchTerm: string) => {
        setSearchTerm(nextSearchTerm);
        await fetchData(nextSearchTerm, selectedModelTypes, selectedDeploymentStatus);
    };

    const handleDownload = () => {
        if (explorerModels.length === 0) {
            return;
        }

        downloadCsv(
            'find_models.csv',
            ['model', 'model_types', 'objective_iris', 'objectives', 'objective_descriptions', 'deployment_status', 'linked_datasets', 'linked_pipelines', 'deployed_on_systems', 'last_model_update', 'last_model_execution', 'output_utilizations', 'performance_entries'],
            explorerModels.map((model) => [
                model.iri,
                model.modelTypes.join('; '),
                model.objectiveIris.join('; '),
                model.objectives.join('; '),
                model.objectiveDescriptions.join('; '),
                model.deploymentStatus,
                model.linkedDatasets.map((dataset) => `${dataset.typeLabel}: ${dataset.iri}`).join('; '),
                model.linkedPipelines.join('; '),
                model.deployedOnSystems.join('; '),
                model.lastModelUpdate,
                model.lastModelExecution,
                model.outputUtilizations.join('; '),
                model.performanceEntries.map((entry) => `${entry.metric}: ${entry.value} @ ${entry.relatedDatasetType} ${entry.relatedDataset}`).join('; '),
            ]),
        );
    };

    const handleIriClick = async (iri: string) => {
        try {
            setClickedIri(iri);
            const encodedIri = encodeURIComponent(iri);
            const response = await fetch(buildV1Url(`models/query-iri?iri=${encodedIri}`));
            if (!response.ok) {
                throw new Error('Failed to fetch IRI details');
            }
            const result = await response.json();
            setQueryResult(result);
            setIsPopupOpen(true);
        } catch (queryError) {
            console.error('Error fetching IRI details:', queryError);
            setError((queryError as Error).message);
        }
    };

    const closePopup = () => {
        setIsPopupOpen(false);
        setQueryResult(null);
    };

    const renderObjectiveLinks = (model: ExplorerModel) => {
        if (model.objectiveIris.length === 0) {
            return formatObjectives(model.objectives);
        }

        return model.objectiveIris.map((iri, index) => (
            <React.Fragment key={iri}>
                {index > 0 && ', '}
                <button
                    type="button"
                    className="model-explorer-inline-link"
                    onClick={() => void handleIriClick(iri)}
                >
                    {humanizeText(model.objectives[index] || getUniqueIriPart(iri))}
                </button>
            </React.Fragment>
        ));
    };

    const handleAnalyzeModels = (model?: ExplorerModel | null) => {
        if (model?.iri) {
            navigate(`/models/analyze-models?search_term=${encodeURIComponent(getUniqueIriPart(model.iri))}`);
            return;
        }
        navigate('/models/analyze-models');
    };

    const renderLinkChip = (iri: string, kind: 'dataset' | 'pipeline' | 'system' | 'other') => {
        const label = pascalCaseToWords(getUniqueIriPart(iri));
        const onClick = () => {
            if (kind === 'dataset') {
                navigate(`/datasets/usages?search_term=${encodeURIComponent(getUniqueIriPart(iri))}`);
                return;
            }
            if (kind === 'pipeline') {
                navigate(`/pipelines?search_term=${encodeURIComponent(getUniqueIriPart(iri))}`);
                return;
            }
            void handleIriClick(iri);
        };

        return (
            <button
                key={`${kind}-${iri}`}
                className="model-explorer-chip"
                onClick={onClick}
                type="button"
            >
                {label}
            </button>
        );
    };

    const groupedDatasets = useMemo(() => {
        if (!selectedModel) {
            return [];
        }

        const groups = new Map<string, { typeLabel: string; datasets: { iri: string; typeLabel: string }[] }>();
        selectedModel.linkedDatasets.forEach((dataset) => {
            const key = dataset.typeLabel || 'Unclassified dataset';
            const existing = groups.get(key) ?? {typeLabel: key, datasets: []};
            existing.datasets.push(dataset);
            groups.set(key, existing);
        });

        return Array.from(groups.values()).sort((left, right) => left.typeLabel.localeCompare(right.typeLabel));
    }, [selectedModel]);

    const topPerformanceEntries = useMemo(() => {
        if (!selectedModel) {
            return [];
        }

        return [...selectedModel.performanceEntries]
            .sort((left, right) => {
                const leftTest = left.relatedDatasetType.toLowerCase().includes('test') ? 0 : 1;
                const rightTest = right.relatedDatasetType.toLowerCase().includes('test') ? 0 : 1;
                if (leftTest !== rightTest) {
                    return leftTest - rightTest;
                }
                return left.metric.localeCompare(right.metric);
            })
            .slice(0, 3);
    }, [selectedModel]);

    return (
        <div className="discovery-page">
            <LoadingBar isLoading={isLoading}/>
            <div className="discovery-hero">
                <div>
                    <h1>Find Models</h1>
                    <p>Explore each MLLO model once, then branch into datasets, pipelines, executions, and deployment context from the same place.</p>
                </div>
            </div>

            <section className="discovery-panel">
                <div className="discovery-toolbar">
                    <Search
                        onSearch={handleSearch}
                        placeholder="Model Name, Dataset Name, or IRI"
                        value={searchTerm}
                    />
                    <DropdownFilter
                        endpoint={buildV1Url('models/types')}
                        selectedValues={selectedModelTypes}
                        onChange={async (modelTypes) => {
                            setSelectedModelTypes(modelTypes);
                            await fetchData(searchTerm, modelTypes, selectedDeploymentStatus);
                        }}
                        label="Model Type"
                    />
                    <DropdownFilter
                        staticOptions={['Deployed', 'Undeployed']}
                        selectedValues={selectedDeploymentStatus}
                        onChange={async (statuses) => {
                            setSelectedDeploymentStatus(statuses);
                            await fetchData(searchTerm, selectedModelTypes, statuses);
                        }}
                        label="Deployment Status"
                    />
                </div>

                <div className="discovery-secondary-row">
                    <div className="discovery-actions">
                        <button onClick={() => handleAnalyzeModels(selectedModel)}>Analyze Selected Model</button>
                    </div>
                </div>
            </section>

            <section className="discovery-panel">
                <div className="discovery-results-bar">
                    <div>
                        <strong>{explorerModels.length}</strong> matching models
                        {selectedModel && ` • Focused on ${selectedModel.label}`}
                    </div>
                    {explorerModels.length > 0 && (
                        <button onClick={handleDownload} className="discovery-download-button">
                            <span>Download Model Inventory</span>
                            <DownloadIcon width={14} height={14}/>
                        </button>
                    )}
                </div>

                {explorerModels.length === 0 ? (
                    <p>{message}</p>
                ) : (
                    <div className="model-explorer-layout">
                        <aside className="model-explorer-sidebar">
                            {explorerModels.map((model) => (
                                <button
                                    key={model.iri}
                                    type="button"
                                    className={`model-explorer-card${selectedModel?.iri === model.iri ? ' is-selected' : ''}`}
                                    onClick={() => setSelectedModelIri(model.iri)}
                                >
                                    <div className="model-explorer-card-top">
                                        <strong>{model.label}</strong>
                                        <span className={`model-explorer-status ${model.deploymentStatus === 'Deployed' ? 'deployed' : 'undeployed'}`}>
                                            {model.deploymentStatus}
                                        </span>
                                    </div>
                                    <div className="model-explorer-card-meta">
                                        <span>{humanizeText(model.modelTypes[0] || 'unknown type')}</span>
                                        <span>{model.linkedDatasets.length} datasets</span>
                                        <span>{model.linkedPipelines.length} pipelines</span>
                                    </div>
                                    <div className="model-explorer-card-objective">
                                        <span>Objective</span>
                                        <strong>{formatObjectives(model.objectives)}</strong>
                                    </div>
                                    <p className="model-explorer-card-description">
                                        {formatDescriptions(model.objectiveDescriptions)}
                                    </p>
                                </button>
                            ))}
                        </aside>

                        {selectedModel && (
                            <div className="model-explorer-detail">
                                <div className="model-explorer-detail-header">
                                    <div>
                                        <div className="model-explorer-kicker">Machine Learning Model</div>
                                        <h2>{selectedModel.label}</h2>
                                        <div className="model-explorer-objective">
                                            {renderObjectiveLinks(selectedModel)}
                                        </div>
                                        <p className="model-explorer-description">
                                            {formatDescriptions(selectedModel.objectiveDescriptions)}
                                        </p>
                                    </div>
                                    <div className={`model-explorer-status-badge ${selectedModel.deploymentStatus === 'Deployed' ? 'deployed' : 'undeployed'}`}>
                                        {selectedModel.deploymentStatus}
                                    </div>
                                </div>

                                <div className="model-explorer-stat-grid">
                                    <div className="model-explorer-stat">
                                        <span>Datasets</span>
                                        <strong>{selectedModel.linkedDatasets.length}</strong>
                                    </div>
                                    <div className="model-explorer-stat">
                                        <span>Development Pipelines</span>
                                        <strong>{selectedModel.linkedPipelines.length}</strong>
                                    </div>
                                    <div className="model-explorer-stat">
                                        <span>Deployed Systems</span>
                                        <strong>{selectedModel.deployedOnSystems.length}</strong>
                                    </div>
                                    <div className="model-explorer-stat">
                                        <span>Performance Entries</span>
                                        <strong>{selectedModel.performanceEntries.length}</strong>
                                    </div>
                                </div>

                                <div className="model-explorer-actions">
                                    <button type="button" onClick={() => void handleIriClick(selectedModel.iri)}>Open Model Details</button>
                                    <button type="button" onClick={() => handleAnalyzeModels(selectedModel)}>Analyze Models Page</button>
                                </div>

                                <div className="model-explorer-section">
                                    <h3>Start Exploration From</h3>
                                    <div className="model-explorer-class-groups">
                                        <details className="model-explorer-group" open>
                                            <summary><code>ml:MachineLearningModel</code></summary>
                                            <div className="model-explorer-chip-row">
                                                <button type="button" className="model-explorer-chip" onClick={() => void handleIriClick(selectedModel.iri)}>
                                                    {selectedModel.label}
                                                </button>
                                            </div>
                                        </details>
                                        <details className="model-explorer-group" open>
                                            <summary><code>ml:MachineLearningDataSet</code></summary>
                                            <div className="model-explorer-chip-row">
                                                {selectedModel.linkedDatasets.length > 0
                                                    ? selectedModel.linkedDatasets.map((dataset) => renderLinkChip(dataset.iri, 'dataset'))
                                                    : <span className="model-explorer-empty">No linked datasets.</span>}
                                            </div>
                                        </details>
                                        <details className="model-explorer-group">
                                            <summary><code>ml:MachineLearningModelDevelopmentPipeline</code></summary>
                                            <div className="model-explorer-chip-row">
                                                {selectedModel.linkedPipelines.length > 0
                                                    ? selectedModel.linkedPipelines.map((iri) => renderLinkChip(iri, 'pipeline'))
                                                    : <span className="model-explorer-empty">No linked pipelines.</span>}
                                            </div>
                                        </details>
                                        <details className="model-explorer-group">
                                            <summary><code>ml:DeployedMachineLearningModelState</code> / <code>ml:ModelExecution</code></summary>
                                            <div className="model-explorer-chip-row">
                                                {selectedModel.deployedOnSystems.length > 0
                                                    ? selectedModel.deployedOnSystems.map((iri) => renderLinkChip(iri, 'system'))
                                                    : <span className="model-explorer-empty">No deployment state recorded.</span>}
                                            </div>
                                        </details>
                                    </div>
                                </div>

                                <div className="model-explorer-section">
                                    <h3>MLLO View</h3>
                                    <ul className="model-explorer-list">
                                        <li><strong>IRI:</strong> {selectedModel.iri}</li>
                                        <li><strong>Model Type:</strong> {selectedModel.modelTypes.map(humanizeText).join(', ') || '-'}</li>
                                        <li><strong>Objective:</strong> {renderObjectiveLinks(selectedModel)}</li>
                                        <li><strong>Objective Description:</strong> {formatDescriptions(selectedModel.objectiveDescriptions)}</li>
                                        <li><strong>Latest Training / Update:</strong> {selectedModel.lastModelUpdate || '-'}</li>
                                        <li><strong>Latest Execution:</strong> {selectedModel.lastModelExecution || '-'}</li>
                                    </ul>
                                </div>

                                <div className="model-explorer-section">
                                    <h3>Linked Datasets via <code>hasDataInput</code> / provenance</h3>
                                    {groupedDatasets.length > 0 ? (
                                        <div className="model-explorer-class-groups">
                                            {groupedDatasets.map((group) => (
                                                <details key={group.typeLabel} className="model-explorer-group" open>
                                                    <summary>{humanizeText(group.typeLabel)} <span className="model-explorer-group-count">{group.datasets.length}</span></summary>
                                                    <div className="model-explorer-chip-row">
                                                        {group.datasets.map((dataset) => renderLinkChip(dataset.iri, 'dataset'))}
                                                    </div>
                                                </details>
                                            ))}
                                        </div>
                                    ) : (
                                        <span className="model-explorer-empty">No linked datasets recorded.</span>
                                    )}
                                </div>

                                <div className="model-explorer-section">
                                    <h3>Linked Pipelines and Processes</h3>
                                    <div className="model-explorer-chip-row">
                                        {selectedModel.linkedPipelines.length > 0
                                            ? selectedModel.linkedPipelines.map((iri) => renderLinkChip(iri, 'pipeline'))
                                            : <span className="model-explorer-empty">No linked pipelines recorded.</span>}
                                    </div>
                                </div>

                                <div className="model-explorer-section">
                                    <h3>Deployment and Runtime Context</h3>
                                    <ul className="model-explorer-list">
                                        <li><strong>Status:</strong> {selectedModel.deploymentStatus}</li>
                                        <li><strong>Deployed On:</strong> {selectedModel.deployedOnSystems.length > 0 ? selectedModel.deployedOnSystems.map((iri) => pascalCaseToWords(getUniqueIriPart(iri))).join(', ') : '-'}</li>
                                        <li><strong>Output Utilization:</strong> {selectedModel.outputUtilizations.length > 0 ? selectedModel.outputUtilizations.map((iri) => pascalCaseToWords(getUniqueIriPart(iri))).join(', ') : '-'}</li>
                                    </ul>
                                </div>

                                <div className="model-explorer-section">
                                    <h3>Performance Snapshot</h3>
                                    {topPerformanceEntries.length > 0 ? (
                                        <ul className="model-explorer-list">
                                            {topPerformanceEntries.map((entry) => (
                                                <li key={`${entry.metric}-${entry.value}-${entry.relatedDataset}`}>
                                                    <strong>{humanizeText(entry.metric)}</strong>: {entry.value}
                                                    {entry.relatedDataset && (
                                                        <>
                                                            {' '}on{' '}
                                                            <button
                                                                type="button"
                                                                className="model-explorer-inline-link"
                                                                onClick={() => navigate(`/datasets/usages?search_term=${encodeURIComponent(getUniqueIriPart(entry.relatedDataset))}`)}
                                                            >
                                                                {pascalCaseToWords(getUniqueIriPart(entry.relatedDataset))}
                                                            </button>
                                                            {' '}({humanizeText(entry.relatedDatasetType)})
                                                        </>
                                                    )}
                                                </li>
                                            ))}
                                        </ul>
                                    ) : (
                                        <span className="model-explorer-empty">No model performance entries recorded.</span>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </section>

            {(isPopupOpen && iriQueryResult) && (
                <Modal onClose={closePopup}>
                    <h2 style={{wordBreak: 'break-all', whiteSpace: 'normal'}}>
                        {clickedIri}
                    </h2>
                    <div className="divider"></div>
                    {iriQueryResult.map((value, index) => (
                        <pre key={index} style={{whiteSpace: 'pre-wrap'}}>
                            <div>
                                <ul>
                                    {Object.entries(value).map(([key, val], idx) => (
                                        val && (
                                            <li key={key + '-' + idx}>
                                                <span className="item-name">{key} </span>
                                                <span className="item-value">{val}</span>
                                            </li>
                                        )
                                    ))}
                                </ul>
                            </div>
                        </pre>
                    ))}
                </Modal>
            )}

            {error && <ErrorMessage message={error}/>}
        </div>
    );
};

export default FindModels;
