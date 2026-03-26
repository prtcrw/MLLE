import React, {useEffect, useMemo, useState} from 'react';
import {useLocation, useNavigate} from 'react-router-dom';
import {buildV1Url} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import ErrorMessage from '../../components/ErrorMessage.tsx';
import Search from '../../components/Search.tsx';
import Table, {SortDirection} from '../../components/Table.tsx';
import Pagination from '../../components/Pagination.tsx';
import ToggleSwitch from '../../components/ToggleSwitch.tsx';
import {DownloadIcon} from '../../components/Icons.tsx';
import FindDatasetsFilter from './FindDatasetsFilter.tsx';
import Modal from '../../components/Modal.tsx';
import {pascalCaseToWords, lowercaseToPascalCase} from '../../components/FormatUtilities';
import DateRangeSlider from '../../components/DateRangeSlider';
import DropdownFilter from '../../components/DropdownFilter';
import './styles/discovery.css';

interface DatasetData {
    model: string;
    model_type: string;
    model_objective: string;
    dataset: string;
    ml_input_timestamp: string;
    model_output: string;
    model_output_utilization: string;
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
    raw_data: false,
    direct_type: false,
};

const DEFAULT_ITEMS_PER_PAGE = 10;
const FETCH_BATCH_SIZE = 250;
const DATASETS_VIEW_STATE_KEY = 'mllo:view-state:datasets';

const sortHeaders = [
    'Model',
    'Model Type',
    'Model Objective',
    'Model Input',
    'ML Input Timestamp',
    'Model Output',
    'Model Output Utilization',
];

const defaultSorts: { key: string; direction: SortDirection }[] = [
    {key: 'Model', direction: 'asc'},
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

const FindDatasets: React.FC = () => {
    const [datasets, setDatasets] = useState<DatasetData[]>([]);
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
            direct_type: parseBoolean(params.get('direct_type')),
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
            toggleConstraint: parseBoolean(params.get('type_query')),
            selectedCheckboxes,
            modelTypes: params.getAll('model_type'),
            currentPage: parsePositiveInt(params.get('page'), 1),
            itemsPerPage: parsePositiveInt(params.get('items_per_page'), DEFAULT_ITEMS_PER_PAGE),
            currentSorts: parsedSorts.length > 0 ? parsedSorts : defaultSorts,
            includeBlankDates: !params.has('include_blank_date') || parseBoolean(params.get('include_blank_date'), true),
            dateRange: [parseDateParam(params.get('start_date')), parseDateParam(params.get('end_date'))] as [Date | null, Date | null],
        };
    }, [location.search]);

    const filteredDatasets = useMemo(() => {
        return datasets.filter((dataset) => {
            const datasetDate = dataset.ml_input_timestamp ? new Date(dataset.ml_input_timestamp) : null;

            if (!datasetDate) {
                return queryState.includeBlankDates;
            }

            const [startDate, endDate] = queryState.dateRange;
            if (startDate && datasetDate < startDate) {
                return false;
            }
            if (endDate) {
                const inclusiveEndDate = new Date(endDate);
                inclusiveEndDate.setHours(23, 59, 59, 999);
                if (datasetDate > inclusiveEndDate) {
                    return false;
                }
            }

            return true;
        });
    }, [datasets, queryState.dateRange, queryState.includeBlankDates]);

    const totalPages = filteredDatasets.length > 0
        ? Math.ceil(filteredDatasets.length / queryState.itemsPerPage)
        : 0;
    const safeCurrentPage = totalPages === 0
        ? 1
        : Math.min(queryState.currentPage, totalPages);

    const paginatedDatasets = useMemo(() => {
        const startIndex = (safeCurrentPage - 1) * queryState.itemsPerPage;
        return filteredDatasets.slice(startIndex, startIndex + queryState.itemsPerPage);
    }, [filteredDatasets, queryState.itemsPerPage, safeCurrentPage]);

    const updateQueryState = (updates: {
        searchTerm?: string;
        toggleConstraint?: boolean;
        selectedCheckboxes?: typeof defaultSelectedCheckboxes;
        modelTypes?: string[];
        currentPage?: number;
        itemsPerPage?: number;
        currentSorts?: { key: string; direction: SortDirection }[];
        includeBlankDates?: boolean;
        dateRange?: [Date | null, Date | null];
    }) => {
        const params = new URLSearchParams(location.search);

        const searchTerm = updates.searchTerm ?? queryState.searchTerm;
        if (searchTerm) {
            params.set('search_term', searchTerm);
        } else {
            params.delete('search_term');
        }

        params.set('type_query', String(updates.toggleConstraint ?? queryState.toggleConstraint));
        params.set('direct_type', String((updates.selectedCheckboxes ?? queryState.selectedCheckboxes).direct_type));
        params.set('page', String(updates.currentPage ?? queryState.currentPage));
        params.set('items_per_page', String(updates.itemsPerPage ?? queryState.itemsPerPage));
        params.set('include_blank_date', String(updates.includeBlankDates ?? queryState.includeBlankDates));

        const selectedCheckboxes = updates.selectedCheckboxes ?? queryState.selectedCheckboxes;
        params.delete('dataset_role');
        Object.entries(selectedCheckboxes)
            .filter(([key, value]) => key !== 'direct_type' && value)
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
        const savedSearch = window.sessionStorage.getItem(DATASETS_VIEW_STATE_KEY);
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
        window.sessionStorage.setItem(DATASETS_VIEW_STATE_KEY, location.search);
    }, [hasHydratedState, location.search]);

    useEffect(() => {
        if (queryState.currentPage !== safeCurrentPage) {
            updateQueryState({currentPage: safeCurrentPage});
        }
    }, [queryState.currentPage, safeCurrentPage]);

    useEffect(() => {
        if (!hasHydratedState || !location.search) {
            setDatasets([]);
            setMessage('Enter a search to load models.');
            return;
        }

        const fetchAllDatasets = async () => {
            setIsLoading(true);
            setMessage('');
            setError(null);

            try {
                const allDatasets: DatasetData[] = [];
                let page = 1;
                let totalRemotePages = 1;

                while (page <= totalRemotePages) {
                    const urlParams = new URLSearchParams({
                        search_term: queryState.searchTerm,
                        page: String(page),
                        items_per_page: String(FETCH_BATCH_SIZE),
                        type_query: String(queryState.toggleConstraint),
                        direct_type: String(queryState.selectedCheckboxes.direct_type),
                    });

                    for (const {key, direction} of queryState.currentSorts) {
                        urlParams.append('sort', `${key},${direction}`);
                    }

                    Object.entries(queryState.selectedCheckboxes)
                        .filter(([key, value]) => key !== 'direct_type' && value)
                        .forEach(([key]) => urlParams.append('dataset_role', `${key},true`));

                    queryState.modelTypes.forEach((type) => {
                        urlParams.append('model_types', type);
                    });

                    const response = await fetch(buildV1Url(`datasets/?${urlParams.toString()}`));
                    if (!response.ok) {
                        throw new Error(`Failed to fetch datasets: ${response.statusText}`);
                    }

                    const payload = await response.json();
                    totalRemotePages = payload.total_pages || 0;
                    allDatasets.push(...payload.data);
                    page += 1;
                }

                setDatasets(allDatasets);
                setMessage(allDatasets.length === 0 ? 'No datasets found.' : '');
            } catch (fetchError) {
                console.error('Error fetching datasets:', fetchError);
                setError((fetchError as Error).message);
            } finally {
                setIsLoading(false);
            }
        };

        void fetchAllDatasets();
    }, [
        hasHydratedState,
        location.search,
        queryState.currentSorts,
        queryState.modelTypes,
        queryState.searchTerm,
        queryState.selectedCheckboxes,
        queryState.toggleConstraint,
    ]);

    const handleSearch = (searchTerm: string) => {
        updateQueryState({searchTerm, currentPage: 1});
    };

    const handleDownload = () => {
        downloadCsv(
            'find_datasets.csv',
            ['model', 'model_type', 'model_objective', 'model_input', 'ml_input_timestamp', 'model_output', 'model_output_utilization'],
            filteredDatasets.map((dataset) => [
                dataset.model,
                dataset.model_type,
                dataset.model_objective,
                dataset.dataset,
                dataset.ml_input_timestamp,
                dataset.model_output,
                dataset.model_output_utilization,
            ]),
        );
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
        const nextToggleConstraint = !queryState.toggleConstraint;
        const nextSelectedCheckboxes = {
            ...queryState.selectedCheckboxes,
            direct_type: nextToggleConstraint ? queryState.selectedCheckboxes.direct_type : false,
        };

        updateQueryState({
            toggleConstraint: nextToggleConstraint,
            selectedCheckboxes: nextSelectedCheckboxes,
            currentPage: 1,
        });
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

    const handleAnalyzeModelOutput = () => {
        navigate('/datasets/analyze-model-output');
    };

    const handlePlotPerformance = () => {
        const urlParams = new URLSearchParams();
        if (queryState.searchTerm) {
            urlParams.set('search_term', queryState.searchTerm);
        }
        urlParams.set('type_query', String(queryState.toggleConstraint));
        navigate(`/datasets/plot-performance?${urlParams.toString()}`);
    };

    const getUniqueIriPart = (iri: string): string => {
        const parts = iri.split('#');
        return parts.length > 1 ? parts[1] : iri;
    };

    const mapItemToRow = (_header: string, value: any): React.ReactNode => {
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
            const response = await fetch(buildV1Url(`datasets/query-iri?iri=${encodedIri}`));
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

    const tableMessage = datasets.length === 0
        ? message
        : filteredDatasets.length === 0
            ? 'No datasets match the selected time filter.'
            : '';

    return (
        <div className="discovery-page">
            <LoadingBar isLoading={isLoading}/>
            <div className="discovery-hero">
                <div>
                    <h1>Find Models</h1>
                    <p>Search models, refine by data role and time, and keep your current view when you navigate away.</p>
                </div>
            </div>

            <section className="discovery-panel">
                <div className="discovery-toolbar">
                    <Search
                        onSearch={handleSearch}
                        placeholder={!queryState.toggleConstraint ? 'Model Name' : 'Objective Type'}
                        value={queryState.searchTerm}
                    />
                    <FindDatasetsFilter
                        selectedFilters={queryState.selectedCheckboxes}
                        onFilterChange={handleCheckboxChange}
                    />
                    <DropdownFilter
                        endpoint={buildV1Url('models/types')}
                        selectedValues={queryState.modelTypes}
                        onChange={(modelTypes) => updateQueryState({modelTypes, currentPage: 1})}
                        label="Model Type"
                    />
                    <div className="discovery-toggle-card">
                        <span className="toggle-label">Model Name</span>
                        <ToggleSwitch isChecked={queryState.toggleConstraint} onToggle={handleToggleConstraint}/>
                        <span className="toggle-label">Objective Type</span>
                    </div>
                </div>

                <div className="discovery-secondary-row">
                    <div className="discovery-date-card">
                        <div className="discovery-card-title">Time Window</div>
                        <DateRangeSlider
                            dates={datasets.map((dataset) => dataset.ml_input_timestamp ? new Date(dataset.ml_input_timestamp) : null)}
                            onChange={(dateRange) => updateQueryState({dateRange, currentPage: 1})}
                            includeBlank={queryState.includeBlankDates}
                            setIncludeBlank={(includeBlankDates) => updateQueryState({includeBlankDates, currentPage: 1})}
                            value={queryState.dateRange}
                        />
                    </div>

                    <div className="discovery-actions">
                        <button onClick={handleAnalyzeModelOutput}>Analyze Model Output</button>
                        <button onClick={handlePlotPerformance}>Plot Performance</button>
                    </div>
                </div>
            </section>

            <section className="discovery-panel">
                <div className="discovery-results-bar">
                    <div>
                        <strong>{filteredDatasets.length}</strong> matching results
                        {filteredDatasets.length > 0 && ` • Page ${safeCurrentPage} of ${totalPages}`}
                    </div>
                    {filteredDatasets.length > 0 && (
                        <button
                            onClick={handleDownload}
                            className="discovery-download-button"
                        >
                            <span>Download Current Results</span>
                            <DownloadIcon width={14} height={14}/>
                        </button>
                    )}
                </div>

                <Table
                    data={paginatedDatasets}
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
                                                <span className="item-name">{key}</span>
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

export default FindDatasets;
