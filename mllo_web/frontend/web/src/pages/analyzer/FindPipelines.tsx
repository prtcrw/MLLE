import React, {useEffect, useMemo, useState} from 'react';
import {Link, useLocation, useNavigate} from 'react-router-dom';
import {buildV1Url, downloadFromResponse} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import ErrorMessage from '../../components/ErrorMessage.tsx';
import Search from '../../components/Search.tsx';
import Table, {SortDirection} from '../../components/Table.tsx';
import Pagination from '../../components/Pagination.tsx';
import ToggleSwitch from '../../components/ToggleSwitch.tsx';
import DropdownFilter from '../../components/DropdownFilter.tsx';
import {DownloadIcon} from '../../components/Icons.tsx';
import {pascalCaseToWords, lowercaseToPascalCase} from '../../components/FormatUtilities';
import './styles/discovery.css';

interface PipelineData {
    pipelineName: string;
    pipelineType: string;
    pipelineComponents: string[];
    pipelineDataInput: string;
    pipelineDataOutput: string;
    pipelineAssociatedModel: string;
}

const DEFAULT_ITEMS_PER_PAGE = 10;
const PIPELINES_VIEW_STATE_KEY = 'mllo:view-state:pipelines';

const sortHeaders = [
    'Pipeline Name',
    'Pipeline Type',
    'Pipeline Components',
    'Pipeline Data Input',
    'Pipeline Data Output',
    'Pipeline Associated Model',
];

const defaultSorts: { key: string; direction: SortDirection }[] = [
    {key: 'Pipeline Name', direction: 'asc'},
];

const parseBoolean = (value: string | null, fallback = false) => {
    if (value === null) {
        return fallback;
    }
    return value === 'true';
};

const parsePositiveInt = (value: string | null, fallback: number) => {
    const parsed = Number.parseInt(value ?? '', 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

const FindPipelines: React.FC = () => {
    const [pipelines, setPipelines] = useState<PipelineData[]>([]);
    const [totalPages, setTotalPages] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [hasHydratedState, setHasHydratedState] = useState(false);

    const navigate = useNavigate();
    const location = useLocation();

    const queryState = useMemo(() => {
        const params = new URLSearchParams(location.search);
        const parsedSorts = params.getAll('sort')
            .map((value) => {
                const [key, direction] = value.split(',');
                if (!key || (direction !== 'asc' && direction !== 'desc')) {
                    return null;
                }

                return {key, direction: direction as SortDirection};
            })
            .filter((value): value is { key: string; direction: SortDirection } => value !== null);

        return {
            searchTerm: params.get('search_term') ?? '',
            toggleConstraint: parseBoolean(params.get('toggle_constraint')),
            currentPage: parsePositiveInt(params.get('page'), 1),
            itemsPerPage: parsePositiveInt(params.get('items_per_page'), DEFAULT_ITEMS_PER_PAGE),
            currentSorts: parsedSorts.length > 0 ? parsedSorts : defaultSorts,
            pipelineTypes: params.getAll('pipeline_type'),
        };
    }, [location.search]);

    const updateQueryState = (updates: {
        searchTerm?: string;
        toggleConstraint?: boolean;
        currentPage?: number;
        itemsPerPage?: number;
        currentSorts?: { key: string; direction: SortDirection }[];
        pipelineTypes?: string[];
    }) => {
        const params = new URLSearchParams(location.search);

        const searchTerm = updates.searchTerm ?? queryState.searchTerm;
        if (searchTerm) {
            params.set('search_term', searchTerm);
        } else {
            params.delete('search_term');
        }

        params.set('toggle_constraint', String(updates.toggleConstraint ?? queryState.toggleConstraint));
        params.set('page', String(updates.currentPage ?? queryState.currentPage));
        params.set('items_per_page', String(updates.itemsPerPage ?? queryState.itemsPerPage));

        const currentSorts = updates.currentSorts ?? queryState.currentSorts;
        params.delete('sort');
        currentSorts
            .filter((sort) => sort.direction !== null)
            .forEach((sort) => params.append('sort', `${sort.key},${sort.direction}`));

        const pipelineTypes = updates.pipelineTypes ?? queryState.pipelineTypes;
        params.delete('pipeline_type');
        pipelineTypes.forEach((type) => params.append('pipeline_type', type));

        navigate({pathname: location.pathname, search: params.toString()}, {replace: false});
    };

    useEffect(() => {
        const savedSearch = window.sessionStorage.getItem(PIPELINES_VIEW_STATE_KEY);
        if (!location.search && savedSearch) {
            navigate({pathname: location.pathname, search: savedSearch}, {replace: true});
            return;
        }
        setHasHydratedState(true);
    }, [location.pathname, location.search, navigate]);

    useEffect(() => {
        if (!hasHydratedState) {
            return;
        }
        window.sessionStorage.setItem(PIPELINES_VIEW_STATE_KEY, location.search);
    }, [hasHydratedState, location.search]);

    useEffect(() => {
        if (!hasHydratedState || !location.search) {
            setPipelines([]);
            setTotalPages(0);
            setMessage('Enter a search to load pipelines.');
            return;
        }

        const fetchData = async () => {
            setIsLoading(true);
            setMessage('');
            setError(null);

            try {
                const urlParams = new URLSearchParams({
                    search_term: queryState.searchTerm,
                    page: String(queryState.currentPage),
                    items_per_page: String(queryState.itemsPerPage),
                    toggle_constraint: String(queryState.toggleConstraint),
                });

                queryState.pipelineTypes.forEach((type) => {
                    urlParams.append('pipeline_types', type);
                });

                for (const {key, direction} of queryState.currentSorts) {
                    urlParams.append('sort', `${key},${direction}`);
                }

                const response = await fetch(buildV1Url(`pipelines/?${urlParams.toString()}`));
                if (!response.ok) {
                    throw new Error(`Failed to fetch pipelines: ${response.statusText}`);
                }

                const fetchedPipelines = await response.json();
                setPipelines(fetchedPipelines.data);
                setTotalPages(fetchedPipelines.total_pages ?? 0);
                if (fetchedPipelines.data.length === 0) {
                    setMessage('No pipelines found.');
                }
            } catch (fetchError) {
                console.error('Error fetching pipelines:', fetchError);
                setError((fetchError as Error).message);
            } finally {
                setIsLoading(false);
            }
        };

        void fetchData();
    }, [
        hasHydratedState,
        location.search,
        queryState.currentPage,
        queryState.currentSorts,
        queryState.itemsPerPage,
        queryState.pipelineTypes,
        queryState.searchTerm,
        queryState.toggleConstraint,
    ]);

    useEffect(() => {
        if (totalPages > 0 && queryState.currentPage > totalPages) {
            updateQueryState({currentPage: totalPages});
        }
    }, [queryState.currentPage, totalPages]);

    const handleSearch = (searchTerm: string) => {
        updateQueryState({searchTerm, currentPage: 1});
    };

    const handleDownload = async () => {
        const urlParams = new URLSearchParams({
            search_term: queryState.searchTerm,
            page: '1',
            items_per_page: String(queryState.itemsPerPage),
            toggle_constraint: String(queryState.toggleConstraint),
            format: 'csv',
        });

        queryState.pipelineTypes.forEach((type) => {
            urlParams.append('pipeline_types', type);
        });

        for (const {key, direction} of queryState.currentSorts) {
            urlParams.append('sort', `${key},${direction}`);
        }

        try {
            const response = await fetch(buildV1Url(`pipelines/?${urlParams.toString()}`));
            if (!response.ok) {
                throw new Error(`Failed to fetch pipelines: ${response.statusText}`);
            }
            await downloadFromResponse(response, 'find_pipelines.csv');
        } catch (fetchError) {
            console.error('Error downloading pipelines:', fetchError);
            setError((fetchError as Error).message);
        }
    };

    const handlePageChange = (page: number = 1, itemsPerPage: number = DEFAULT_ITEMS_PER_PAGE) => {
        updateQueryState({currentPage: page, itemsPerPage});
    };

    const handleSort = (sorts: { key: string; direction: SortDirection }[]) => {
        updateQueryState({currentSorts: sorts, currentPage: 1});
    };

    const handleRemoveSort = (key: string) => {
        const newSorts = queryState.currentSorts.filter((sort) => sort.key !== key);
        updateQueryState({currentSorts: newSorts.length > 0 ? newSorts : defaultSorts, currentPage: 1});
    };

    const handleToggleConstraint = () => {
        updateQueryState({toggleConstraint: !queryState.toggleConstraint, currentPage: 1});
    };

    const handleComparePipelines = () => {
        navigate('/pipelines/compare-pipelines');
    };

    const handleViewPipeline = () => {
        navigate('/pipelines/edit-pipeline');
    };

    const mapItemToRow = (header: string, value: any): React.ReactNode => {
        if (header === 'Pipeline Name' && typeof value === 'string') {
            return <Link to={`/pipelines/edit-pipeline?pipeline-name=${value}`}>{pascalCaseToWords(value)}</Link>;
        }
        if (header === 'Pipeline Components') {
            return (value && Array.isArray(value))
                ? value.map((component) => lowercaseToPascalCase(component)).join('; ')
                : '';
        }
        if (typeof value === 'string') {
            let formattedValue = value;
            if (/^[A-Z][a-z0-9]+([A-Z][a-z0-9]*)*$/.test(formattedValue)) {
                formattedValue = pascalCaseToWords(formattedValue);
            } else if (/^[a-z ]+$/.test(formattedValue)) {
                formattedValue = lowercaseToPascalCase(formattedValue);
            }
            return <span>{formattedValue}</span>;
        }
        return value;
    };

    const placeholder = queryState.searchTerm
        ? `${pascalCaseToWords(queryState.searchTerm)}`
        : !queryState.toggleConstraint
            ? 'Model Constraint'
            : 'Dataset Constraint';

    return (
        <div className="discovery-page">
            <LoadingBar isLoading={isLoading}/>
            <div className="discovery-hero">
                <div>
                    <h1>Find Pipelines</h1>
                    <p>Navigate between pages without losing your filters, and keep pipeline exploration consistent across routes.</p>
                </div>
            </div>

            <section className="discovery-panel">
                <div className="discovery-toolbar">
                    <Search
                        onSearch={handleSearch}
                        placeholder={placeholder}
                        value={queryState.searchTerm}
                    />
                    <div className="discovery-toggle-card">
                        <span className="toggle-label">Model Constraint</span>
                        <ToggleSwitch isChecked={queryState.toggleConstraint} onToggle={handleToggleConstraint}/>
                        <span className="toggle-label">Dataset Constraint</span>
                    </div>
                    <DropdownFilter
                        endpoint={buildV1Url('pipelines/types')}
                        selectedValues={queryState.pipelineTypes}
                        onChange={(pipelineTypes) => updateQueryState({pipelineTypes, currentPage: 1})}
                        label="Pipeline Types"
                    />
                </div>

                <div className="discovery-actions">
                    <button onClick={handleComparePipelines}>Compare Pipelines</button>
                    <button onClick={handleViewPipeline}>View Pipeline</button>
                </div>
            </section>

            <section className="discovery-panel">
                <div className="discovery-results-bar">
                    <div>{queryState.searchTerm ? `Showing results for ${pascalCaseToWords(queryState.searchTerm)}` : 'Run a search to load pipelines'}</div>
                    {pipelines.length > 0 && (
                        <button onClick={handleDownload} className="discovery-download-button">
                            <span>Download Results</span>
                            <DownloadIcon width={14} height={14}/>
                        </button>
                    )}
                </div>

                <Table
                    data={pipelines}
                    headers={sortHeaders}
                    mapItemToRow={mapItemToRow}
                    currentSorts={queryState.currentSorts}
                    onSort={handleSort}
                    onRemoveSort={handleRemoveSort}
                    message={message}
                />
                <Pagination
                    currentPage={queryState.currentPage}
                    totalPages={totalPages}
                    itemsPerPage={queryState.itemsPerPage}
                    onPageChange={handlePageChange}
                />
            </section>

            {error && <ErrorMessage message={error}/>}
        </div>
    );
};

export default FindPipelines;
