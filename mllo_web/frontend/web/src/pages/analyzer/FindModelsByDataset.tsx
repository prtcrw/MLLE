import React, {useEffect, useMemo, useState} from 'react';
import {useLocation, useNavigate} from 'react-router-dom';
import {buildV1Url} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import ErrorMessage from '../../components/ErrorMessage.tsx';
import Search from '../../components/Search.tsx';
import Table, {SortDirection} from '../../components/Table.tsx';
import Pagination from '../../components/Pagination.tsx';
import {DownloadIcon} from '../../components/Icons.tsx';
import FindModelsFilter from './FindModelsFilter.tsx';
import Modal from '../../components/Modal.tsx';
import {pascalCaseToWords, lowercaseToPascalCase} from '../../components/FormatUtilities';
import DropdownFilter from '../../components/DropdownFilter';
import DateRangeSlider from '../../components/DateRangeSlider';
import './styles/discovery.css';

interface ModelData {
    dataset: string;
    dataset_used_as: string;
    dataset_used_for: string;
    dataset_characteristics: string[] | string;
    ml_input_timestamp: string;
    model_name: string;
    model_performance_metric: string;
    model_performance_value: number;
}

interface IRIQueryData {
    dataPropertyValuePairs: string;
    annotationPropertyValuePairs: string;
    types: string;
}

const defaultSelectedCheckboxes = {
    test_data: false,
    validation_data: false,
    training_data: false,
    production_data: false,
    raw_data: true,
};

const DEFAULT_ITEMS_PER_PAGE = 20;
const FETCH_BATCH_SIZE = 250;
const DATASET_USAGES_VIEW_STATE_KEY = 'mllo:view-state:dataset-usages';

const sortHeaders = [
    'Dataset Name',
    'Dataset Used As',
    'Dataset Used For',
    'Dataset Characteristics',
    'ML Input Timestamp',
    'Model Name',
    'Model Performance Metric',
    'Model Performance Value',
];

const defaultSorts: { key: string; direction: SortDirection }[] = [
    {key: 'Dataset Name', direction: 'asc'},
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

const parseDateParam = (value: string | null): Date | null => {
    if (!value) {
        return null;
    }

    const parsed = new Date(`${value}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const formatDateParam = (value: Date | null) => {
    if (!value) {
        return null;
    }

    return value.toISOString().slice(0, 10);
};

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

const FindModelsByDataset: React.FC = () => {
    const [models, setModels] = useState<ModelData[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [isPopupOpen, setIsPopupOpen] = useState(false);
    const [iriQueryResult, setQueryResult] = useState<IRIQueryData[] | null>(null);
    const [clickedIri, setClickedIri] = useState<string | null>(null);
    const [hasHydratedState, setHasHydratedState] = useState(false);

    const navigate = useNavigate();
    const location = useLocation();

    const queryState = useMemo(() => {
        const params = new URLSearchParams(location.search);
        const selectedRoles = params.getAll('dataset_role');
        const selectedCheckboxes = {
            ...defaultSelectedCheckboxes,
        };

        for (const role of selectedRoles) {
            if (role in selectedCheckboxes) {
                selectedCheckboxes[role as keyof typeof selectedCheckboxes] = true;
            }
        }

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
            selectedCheckboxes,
            modelTypes: params.getAll('model_type'),
            currentPage: parsePositiveInt(params.get('page'), 1),
            itemsPerPage: parsePositiveInt(params.get('items_per_page'), DEFAULT_ITEMS_PER_PAGE),
            currentSorts: parsedSorts.length > 0 ? parsedSorts : defaultSorts,
            includeBlank: !params.has('include_blank_date') || parseBoolean(params.get('include_blank_date'), true),
            dateRange: [parseDateParam(params.get('start_date')), parseDateParam(params.get('end_date'))] as [Date | null, Date | null],
        };
    }, [location.search]);

    const filteredModels = useMemo(() => {
        return models.filter((model) => {
            const modelDate = model.ml_input_timestamp ? new Date(model.ml_input_timestamp) : null;

            if (!modelDate) {
                return queryState.includeBlank;
            }

            const [startDate, endDate] = queryState.dateRange;
            if (startDate && modelDate < startDate) {
                return false;
            }
            if (endDate) {
                const inclusiveEndDate = new Date(endDate);
                inclusiveEndDate.setHours(23, 59, 59, 999);
                if (modelDate > inclusiveEndDate) {
                    return false;
                }
            }

            return true;
        });
    }, [models, queryState.dateRange, queryState.includeBlank]);

    const totalPages = filteredModels.length > 0
        ? Math.ceil(filteredModels.length / queryState.itemsPerPage)
        : 0;
    const safeCurrentPage = totalPages === 0
        ? 1
        : Math.min(queryState.currentPage, totalPages);

    const paginatedModels = useMemo(() => {
        const startIndex = (safeCurrentPage - 1) * queryState.itemsPerPage;
        return filteredModels.slice(startIndex, startIndex + queryState.itemsPerPage);
    }, [filteredModels, queryState.itemsPerPage, safeCurrentPage]);

    const updateQueryState = (updates: {
        searchTerm?: string;
        selectedCheckboxes?: typeof defaultSelectedCheckboxes;
        modelTypes?: string[];
        currentPage?: number;
        itemsPerPage?: number;
        currentSorts?: { key: string; direction: SortDirection }[];
        includeBlank?: boolean;
        dateRange?: [Date | null, Date | null];
    }) => {
        const params = new URLSearchParams(location.search);

        const searchTerm = updates.searchTerm ?? queryState.searchTerm;
        if (searchTerm) {
            params.set('search_term', searchTerm);
        } else {
            params.delete('search_term');
        }

        params.set('page', String(updates.currentPage ?? queryState.currentPage));
        params.set('items_per_page', String(updates.itemsPerPage ?? queryState.itemsPerPage));
        params.set('include_blank_date', String(updates.includeBlank ?? queryState.includeBlank));

        const selectedCheckboxes = updates.selectedCheckboxes ?? queryState.selectedCheckboxes;
        params.delete('dataset_role');
        Object.entries(selectedCheckboxes)
            .filter(([, value]) => value)
            .forEach(([key]) => params.append('dataset_role', key));

        const modelTypes = updates.modelTypes ?? queryState.modelTypes;
        params.delete('model_type');
        modelTypes.forEach((type) => params.append('model_type', type));

        const currentSorts = updates.currentSorts ?? queryState.currentSorts;
        params.delete('sort');
        currentSorts
            .filter((sort) => sort.direction !== null)
            .forEach((sort) => params.append('sort', `${sort.key},${sort.direction}`));

        const dateRange = updates.dateRange ?? queryState.dateRange;
        const [startDate, endDate] = dateRange;
        const formattedStart = formatDateParam(startDate);
        const formattedEnd = formatDateParam(endDate);
        if (formattedStart) {
            params.set('start_date', formattedStart);
        } else {
            params.delete('start_date');
        }
        if (formattedEnd) {
            params.set('end_date', formattedEnd);
        } else {
            params.delete('end_date');
        }

        navigate({pathname: location.pathname, search: params.toString()}, {replace: false});
    };

    useEffect(() => {
        const savedSearch = window.sessionStorage.getItem(DATASET_USAGES_VIEW_STATE_KEY);
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
        window.sessionStorage.setItem(DATASET_USAGES_VIEW_STATE_KEY, location.search);
    }, [hasHydratedState, location.search]);

    useEffect(() => {
        if (queryState.currentPage !== safeCurrentPage) {
            updateQueryState({currentPage: safeCurrentPage});
        }
    }, [queryState.currentPage, safeCurrentPage]);

    useEffect(() => {
        if (!hasHydratedState || !location.search) {
            setModels([]);
            setMessage('Enter a search to load dataset usages.');
            return;
        }

        const fetchAllModels = async () => {
            setIsLoading(true);
            setMessage('');
            setError(null);

            try {
                const allModels: ModelData[] = [];
                let page = 1;
                let totalRemotePages = 1;

                while (page <= totalRemotePages) {
                    const urlParams = new URLSearchParams({
                        search_term: queryState.searchTerm,
                        page: String(page),
                        items_per_page: String(FETCH_BATCH_SIZE),
                    });

                    for (const {key, direction} of queryState.currentSorts) {
                        urlParams.append('sort', `${key},${direction}`);
                    }

                    Object.entries(queryState.selectedCheckboxes)
                        .filter(([, value]) => value)
                        .forEach(([key]) => urlParams.append('dataset_role', `${key},true`));

                    queryState.modelTypes.forEach((type) => {
                        urlParams.append('model_types', type);
                    });

                    const response = await fetch(buildV1Url(`models/?${urlParams.toString()}`));
                    if (!response.ok) {
                        throw new Error(`Failed to fetch models: ${response.statusText}`);
                    }

                    const payload = await response.json();
                    totalRemotePages = payload.total_pages || 0;
                    allModels.push(...payload.data);
                    page += 1;
                }

                setModels(allModels);
                setMessage(allModels.length === 0 ? 'No models found.' : '');
            } catch (fetchError) {
                console.error('Error fetching models:', fetchError);
                setError((fetchError as Error).message);
            } finally {
                setIsLoading(false);
            }
        };

        void fetchAllModels();
    }, [
        hasHydratedState,
        location.search,
        queryState.currentSorts,
        queryState.modelTypes,
        queryState.searchTerm,
        queryState.selectedCheckboxes,
    ]);

    const handleSearch = (searchTerm: string) => {
        updateQueryState({searchTerm, currentPage: 1});
    };

    const handleDownload = () => {
        downloadCsv(
            'find_models.csv',
            ['dataset', 'dataset_used_as', 'dataset_used_for', 'dataset_characteristics', 'ml_input_timestamp', 'model_name', 'model_performance_metric', 'model_performance_value'],
            filteredModels.map((model) => [
                model.dataset,
                model.dataset_used_as,
                model.dataset_used_for,
                Array.isArray(model.dataset_characteristics)
                    ? model.dataset_characteristics.join('; ')
                    : model.dataset_characteristics,
                model.ml_input_timestamp,
                model.model_name,
                model.model_performance_metric,
                model.model_performance_value,
            ]),
        );
    };

    const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const {name, checked} = e.target;
        updateQueryState({
            selectedCheckboxes: {
                ...queryState.selectedCheckboxes,
                [name]: checked,
            },
            currentPage: 1,
        });
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

    const handleAnalyzeDeployedModels = () => {
        navigate('/models/analyze-deployed-models');
    };

    const getUniqueIriPart = (iri: string): string => {
        const parts = iri.split('#');
        return parts.length > 1 ? parts[1] : iri;
    };

    const mapItemToRow = (header: string, value: any): React.ReactNode => {
        if (header === 'Dataset Name' && typeof value === 'string') {
            return (
                <a
                    href="#"
                    onClick={(e) => {
                        e.preventDefault();
                        if (e.altKey) {
                            navigate(`/pipelines?search_term=${getUniqueIriPart(value)}&toggle_constraint=true`);
                            return;
                        }
                        void handleIriClick(value);
                    }}
                    style={{color: '#2563eb', textDecoration: 'underline'}}
                >
                    {pascalCaseToWords(getUniqueIriPart(value))}
                </a>
            );
        }

        if (typeof value === 'string' && value.startsWith('http')) {
            return (
                <a
                    href="#"
                    onClick={(e) => {
                        e.preventDefault();
                        void handleIriClick(value);
                    }}
                    style={{color: '#2563eb', textDecoration: 'underline'}}
                >
                    {pascalCaseToWords(getUniqueIriPart(value))}
                </a>
            );
        }

        if (header === 'Dataset Characteristics' && Array.isArray(value)) {
            return (
                <div>
                    {value.length > 0 ? (
                        value.map((characteristic, index) => (
                            <div key={index} style={{marginBottom: '4px'}}>
                                {characteristic};
                            </div>
                        ))
                    ) : (
                        <span>-</span>
                    )}
                </div>
            );
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

    const tableMessage = models.length === 0
        ? message
        : filteredModels.length === 0
            ? 'No dataset usages match the selected time filter.'
            : '';

    return (
        <div className="discovery-page">
            <LoadingBar isLoading={isLoading}/>
            <div className="discovery-hero">
                <div>
                    <h1>Find Dataset Usages</h1>
                    <p>Review where datasets are used, narrow by time without page gaps, and keep your exact view sharable.</p>
                </div>
            </div>

            <section className="discovery-panel">
                <div className="discovery-toolbar">
                    <Search
                        onSearch={handleSearch}
                        placeholder="Dataset Name"
                        value={queryState.searchTerm}
                    />
                    <FindModelsFilter
                        selectedFilters={queryState.selectedCheckboxes}
                        onFilterChange={handleCheckboxChange}
                    />
                    <DropdownFilter
                        endpoint={buildV1Url('models/types')}
                        selectedValues={queryState.modelTypes}
                        onChange={(modelTypes) => updateQueryState({modelTypes, currentPage: 1})}
                        label="Model Type"
                    />
                </div>

                <div className="discovery-secondary-row">
                    <div className="discovery-date-card">
                        <div className="discovery-card-title">Time Window</div>
                        <DateRangeSlider
                            dates={models.map((model) => model.ml_input_timestamp ? new Date(model.ml_input_timestamp) : null)}
                            onChange={(dateRange) => updateQueryState({dateRange, currentPage: 1})}
                            includeBlank={queryState.includeBlank}
                            setIncludeBlank={(includeBlank) => updateQueryState({includeBlank, currentPage: 1})}
                            value={queryState.dateRange}
                        />
                    </div>

                    <div className="discovery-actions">
                        <button onClick={handleAnalyzeDeployedModels}>Analyze Deployed Models</button>
                    </div>
                </div>
            </section>

            <section className="discovery-panel">
                <div className="discovery-results-bar">
                    <div>
                        <strong>{filteredModels.length}</strong> matching results
                        {filteredModels.length > 0 && ` • Page ${safeCurrentPage} of ${totalPages}`}
                    </div>
                    {filteredModels.length > 0 && (
                        <button onClick={handleDownload} className="discovery-download-button">
                            <span>Download Current Results</span>
                            <DownloadIcon width={14} height={14}/>
                        </button>
                    )}
                </div>

                <Table
                    data={paginatedModels}
                    headers={sortHeaders}
                    mapItemToRow={mapItemToRow}
                    currentSorts={queryState.currentSorts}
                    onSort={handleSort}
                    onRemoveSort={handleRemoveSort}
                    message={tableMessage}
                />
                <Pagination
                    currentPage={safeCurrentPage}
                    totalPages={totalPages}
                    itemsPerPage={queryState.itemsPerPage}
                    onPageChange={handlePageChange}
                />
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

export default FindModelsByDataset;
