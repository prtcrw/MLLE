import React, {useState, useEffect} from 'react';
import {useNavigate} from 'react-router-dom';
import {buildV1Url, downloadFromResponse} from '../../services/api';
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

interface DatasetData {
    datasetName: string;
    datasetUsedAs: string;
    ml_input_timestamp: string;
    datasetShape: string;
    datasetCharacteristics: string[];
    datasetSource: string;
    modelType: string;
    modelOutput: string;
    modelOutputUtilization: string;
}

interface IRIQueryData {
    dataPropertyValuePairs: string;
    annotationPropertyValuePairs: string;
    types: string;
}

const defaultSelectedCheckboxes = {
    "test_data": false,
    "validation_data": false,
    "training_data": false,
    "production_data": false,
    "raw_data": false,
    "direct_type": false,
};

const FindDatasets: React.FC = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const [toggleConstraint, setToggleConstraint] = useState<boolean>(true);
    const [selectedCheckboxes, setSelectedCheckboxes] = useState<{ [key: string]: boolean }>(defaultSelectedCheckboxes);
    const [datasets, setDatasets] = useState<DatasetData[]>([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [itemsPerPage, setItemsPerPage] = useState(10);
    const sortHeaders = [
        "Dataset Name",
        "Dataset Used As",
        "ML Input Timestamp",
        "Dataset Shape",
        "Dataset Characteristics",
        "Dataset Source",
        "Model Type",
        "Model Output",
        "Model Output Utilization",
    ];
    const [currentSorts, setCurrentSorts] = useState<{ key: string; direction: SortDirection }[]>([
        {key: "Dataset Name", direction: "asc"}
    ]);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate(); // Access useNavigate hook
    const [isPopupOpen, setIsPopupOpen] = useState(false);
    const [iriQueryResult, setQueryResult] = useState<IRIQueryData[] | null>(null);
    const [clickedIri, setClickedIri] = useState<string | null>(null);
    const [dateRange, setDateRange] = useState<[Date | null, Date | null]>([null, null]); // State for date range
    const [includeBlankDates, setIncludeBlankDates] = useState(true); // State for include blank dates
    const [filteredDatasets, setFilteredDatasets] = useState<DatasetData[]>([]); // State for filtered datasets

    useEffect(() => {
        // Filter the datasets based on the selected date range and includeBlank setting
        const filtered = datasets.filter(dataset => {
            const datasetDate = dataset.ml_input_timestamp ? new Date(dataset.ml_input_timestamp) : null;
            if (!includeBlankDates && !datasetDate) {
                return false;
            }
            if (datasetDate) {
                const [start, end] = dateRange;
                if ((start && datasetDate < start) || (end && datasetDate > end)) {
                    return false;
                }
            }
            return true;
        });
        setFilteredDatasets(filtered);
    }, [datasets, dateRange, includeBlankDates]);

    const fetchData = async (
        searchTerm: string,
        currentPage: number,
        itemsPerPage: number,
        sorts: { key: string; direction: SortDirection }[],
        selectedCheckboxes: { [key: string]: boolean },
        toggleConstraint: boolean,
        format: string = ''
    ) => {
        setIsLoading(true); // Set loading to true
        setMessage('');
        setError(null);
        try {
            const urlParams = new URLSearchParams({
                search_term: searchTerm,
                page: currentPage.toString(),
                items_per_page: itemsPerPage.toString(),
                type_query: toggleConstraint.toString(),
                direct_type: selectedCheckboxes["direct_type"].toString(),
            });
            // Add sorts as query params
            for (const {key, direction} of sorts) {
                urlParams.append('sort', `${key},${direction}`);
            }

            // Add dataset_role as query params
            Object.keys(selectedCheckboxes).filter(key => selectedCheckboxes[key]).map((key) => {
                urlParams.append('dataset_role', `${key},${selectedCheckboxes[key]}`);
            });

            if (format !== '') {
                urlParams.append('format', format);
            }

            const response = await fetch(buildV1Url(`datasets/?${urlParams.toString()}`));
            if (!response.ok) {
                throw new Error(`Failed to fetch datasets: ${response.statusText}`);
            }

            if (format === '' || format === 'json') {
                const fetchedDatasets = await response.json();
                setCurrentPage(currentPage);
                setTotalPages(fetchedDatasets["total_pages"]);
                setDatasets(fetchedDatasets["data"]);
                if (fetchedDatasets["data"].length === 0) {
                    setMessage("No datasets found.");
                } else {
                    setMessage('');
                }
            } else {
                await downloadFromResponse(response, 'find_datasets.csv');
            }
        } catch (error) {
            console.error('Error fetching datasets:', error);
            setError((error as Error).message);
        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
    };

    const handleSearch = async (searchTerm: string) => {
        setSearchTerm(searchTerm);
        await fetchData(searchTerm, 1, itemsPerPage, currentSorts, selectedCheckboxes, toggleConstraint);
    };

    const handleDownload = async () => {
        await fetchData(searchTerm, 1, itemsPerPage, currentSorts, selectedCheckboxes, toggleConstraint, 'csv');
    };

    const handlePageChange = async (page: number = 1, itemsPerPage: number = 10) => {
        setCurrentPage(page);
        setItemsPerPage(itemsPerPage);
        await fetchData(searchTerm, page, itemsPerPage, currentSorts, selectedCheckboxes, toggleConstraint);
    };

    const handleSort = async (sorts: { key: string; direction: SortDirection }[]) => {
        setCurrentSorts(sorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, sorts, selectedCheckboxes, toggleConstraint);
    };

    const handleRemoveSort = async (key: string) => {
        const newSorts = currentSorts.filter(sort => sort.key !== key);
        setCurrentSorts(newSorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, newSorts, selectedCheckboxes, toggleConstraint); // Update data with new sorts
    };

    const handleToggleConstraint = () => {
        setToggleConstraint(!toggleConstraint); // Toggle between Model and Dataset
        if (!toggleConstraint) {
            setSelectedCheckboxes(prev => ({
                ...prev,
                direct_type: false // Reset direct_type when toggling off Model Type
            }));
        }
    };

    const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const {name, checked} = e.target;
        setSelectedCheckboxes(prev => ({
            ...prev,
            [name]: checked
        }));
    };

    const handleAnalyzeModelOutput = () => {
        navigate('/datasets/analyze-model-output');
    };

    const handlePlotPerformance = () => {
        let url = '/datasets/plot-performance';
        if (searchTerm) {
            url += '?search_term=' + searchTerm+'&';
        }
        url+='type_query=' + toggleConstraint.toString();
        navigate(url);
    };

    const getUniqueIriPart = (iri: string | string[]): string | string[] => {
        if (Array.isArray(iri)) {
            return iri.map(singleIri => {
                const parts = singleIri.split('#');
                return parts.length > 1 ? parts[1] : singleIri; // Return the fragment if exists, else the full IRI
            });
        } else {
            const parts = iri.split('#');
            return parts.length > 1 ? parts[1] : iri; // Return the fragment if exists, else the full IRI
        }
    };

    const mapItemToRow = (header: string, value: any) => {
        if (typeof value === 'string' && value.startsWith('http')) {
            return (
                <a
                    href="#"
                    onClick={(e) => {
                        e.preventDefault();
                        handleIriClick(value);
                    }}
                    style={{color: 'blue', textDecoration: 'underline'}}
                >
                    {pascalCaseToWords(getUniqueIriPart(value))}
                </a>
            );
        }
        if (header === "Dataset Characteristics" && Array.isArray(value)) {
            return (
                <div>
                    {getUniqueIriPart(value).map((iri: string, index: number) => (
                        <div key={index}>
                            <a
                                href="#"
                                onClick={(e) => {
                                    e.preventDefault();
                                    handleIriClick(value[index]);
                                }}
                                style={{color: 'blue', textDecoration: 'underline', marginRight: '8px'}}
                            >
                                {pascalCaseToWords(getUniqueIriPart(iri))}
                            </a>
                        </div>
                    ))}
                </div>
            );
        }
        if (typeof value === 'string') {
            if (/^[A-Z][a-z0-9]+([A-Z][a-z0-9]*)*$/.test(value)) {
                value = pascalCaseToWords(value);
            } else if (/^[a-z ]+$/.test(value)) {
                value = lowercaseToPascalCase(value);
            }
            return (
                <span>{value}</span>
            );
        } else {
            return value;
        }
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
        } catch (error) {
            console.error('Error fetching IRI details:', error);
            setError((error as Error).message);
        }
    };

    const closePopup = () => {
        setIsPopupOpen(false);
        setQueryResult(null);
    };

    return (
        <div>
            <LoadingBar isLoading={isLoading}/>
            <h1>Find Datasets</h1>
            <div style={{margin: '8px 0'}}>
                <Search onSearch={handleSearch} placeholder={!toggleConstraint ? 'Model Name' : 'Model Type'}/>
                <FindDatasetsFilter
                    selectedFilters={selectedCheckboxes}
                    onFilterChange={handleCheckboxChange}
                />
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '8px',
                    border: '1px solid #ccc',
                    borderRadius: '4px'
                }}>
                    <span className="toggle-label">Model Name</span>
                    <ToggleSwitch isChecked={toggleConstraint} onToggle={handleToggleConstraint}/>
                    <span className="toggle-label" style={{marginLeft: '8px'}}>Model Type</span>
                    <label style={{display: 'flex', alignItems: 'center', marginLeft: '16px'}}>
                        <input
                            type="checkbox"
                            name="direct_type"
                            checked={selectedCheckboxes["direct_type"] || false}
                            onChange={handleCheckboxChange}
                            disabled={!toggleConstraint} // Disable when toggle is not on "Model Type"
                            style={{marginRight: '8px'}}
                        />
                        <span>Direct Type</span>
                    </label>
                </div>
            </div>
            <DateRangeSlider
                dates={datasets.map(dataset => dataset.ml_input_timestamp ? new Date(dataset.ml_input_timestamp) : null)}
                onChange={setDateRange}
                includeBlank={includeBlankDates}
                setIncludeBlank={setIncludeBlankDates}
                value={dateRange}
            />
            <div>
                <div style={{margin: '8px 0'}}>
                    <button onClick={handleAnalyzeModelOutput}>Analyze Model Output</button>
                    <button style={{marginLeft: '4px'}} onClick={handlePlotPerformance}>Plot Performance</button>
                </div>
                {filteredDatasets.length > 0 &&
                    <div style={{display: 'flex', justifyContent: 'flex-end'}}>
                        <button onClick={handleDownload}
                                style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
                            <span style={{marginRight: '4px'}}>Download Results</span>
                            <DownloadIcon width={14} height={14}/>
                        </button>
                    </div>
                }
                <Table data={filteredDatasets}
                       headers={sortHeaders}
                       mapItemToRow={mapItemToRow}
                       currentSorts={currentSorts}
                       onSort={handleSort}
                       onRemoveSort={handleRemoveSort}
                       message={message}/>
                <Pagination
                    currentPage={currentPage}
                    totalPages={totalPages}
                    onPageChange={handlePageChange}
                />
            </div>
            {(isPopupOpen && iriQueryResult) && (
                <Modal onClose={closePopup}>
                    <h2 style={{wordBreak: 'break-all', whiteSpace: 'normal'}}>
                        {clickedIri}
                    </h2>
                    <div className="divider"></div>
                    {iriQueryResult.map((value, index) => (
                        <pre style={{whiteSpace: 'pre-wrap'}}>
                            <div key={index}>
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
