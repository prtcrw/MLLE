import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { buildV1Url, downloadFromResponse } from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import ErrorMessage from '../../components/ErrorMessage.tsx';
import Search from '../../components/Search.tsx';
import Table, { SortDirection } from '../../components/Table.tsx';
import Pagination from '../../components/Pagination.tsx';
import { DownloadIcon } from '../../components/Icons.tsx';
import FindDatasetsFilter from './FindDatasetsFilter.tsx';
import Modal from '../../components/Modal.tsx';

interface DatasetData {
    datasetName: string;
    datasetUsedAs: string;
    mlInputTimestamp: string;
    datasetShape: string;
    datasetCharacteristics: string[];
    datasetSource: string;
    modelType: string;
    modelOutput: string;
    modelOutputUtilization: string;
}

const defaultSelectedCheckboxes = {
    "test_data": false,
    "validation_data": false,
    "training_data": false,
    "production_data": false,
    "raw_data": false,
};

const FindDatasets: React.FC = () => {
    const [searchTerm, setSearchTerm] = useState('');
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
        { key: "Dataset Name", direction: "asc" }
    ]);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate(); // Access useNavigate hook
    const [isPopupOpen, setIsPopupOpen] = useState(false);
    const [iriQueryResult, setQueryResult] = useState<string | null>(null);
    const [clickedIri, setClickedIri] = useState<string | null>(null);

    const fetchData = async (searchTerm: string,
        currentPage: number,
        itemsPerPage: number,
        sorts: { key: string; direction: SortDirection }[],
        selectedCheckboxes: { [key: string]: boolean },
        format: string = '') => {
        setIsLoading(true); // Set loading to true
        setMessage('');
        setError(null);
        try {
            const urlParams = new URLSearchParams({
                search_term: searchTerm,
                page: currentPage.toString(),
                items_per_page: itemsPerPage.toString(),
            });

            // Add sorts as query params
            for (const { key, direction } of sorts) {
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
                throw new Error(`Failed to fetch models: ${response.statusText}`);
            }

            if (format === '' || format === 'json') {
                const fetchedDatasets = await response.json();
                setCurrentPage(currentPage);
                setTotalPages(fetchedDatasets["total_pages"]);
                setDatasets(fetchedDatasets["data"]);
                if (fetchedDatasets["data"].length == 0) {
                    setMessage("No datasets found.");
                } else {
                    setMessage('');
                }
            } else {
                await downloadFromResponse(response, 'find_datasets.csv');
            }
        } catch (error) {
            console.error('Error fetching models:', error);
            setError((error as Error).message);
        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
    }

    const handleSearch = async (searchTerm: string) => {
        setSearchTerm(searchTerm);
        await fetchData(searchTerm, 1, itemsPerPage, currentSorts, selectedCheckboxes);
    };

    const handleDownload = async () => {
        await fetchData(searchTerm, 1, itemsPerPage, currentSorts, selectedCheckboxes, 'csv');
    };

    const handlePageChange = async (page: number = 1, itemsPerPage: number = 10) => {
        setCurrentPage(page);
        setItemsPerPage(itemsPerPage);
        await fetchData(searchTerm, page, itemsPerPage, currentSorts, selectedCheckboxes);
    };

    const handleSort = async (sorts: { key: string; direction: SortDirection }[]) => {
        setCurrentSorts(sorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, sorts, selectedCheckboxes);
    }

    const handleRemoveSort = async (key: string) => {
        const newSorts = currentSorts.filter(sort => sort.key !== key);
        setCurrentSorts(newSorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, newSorts, selectedCheckboxes); // Update data with new sorts
    };

    const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, checked } = e.target;
        setSelectedCheckboxes(prev => ({
            ...prev,
            [name]: checked
        }));
    };

    const handleAnalyzeModelOutput = () => {
        navigate('/datasets/analyze-model-output');
    };

    const handlePlotPerformance = () => {
        let url = '/datasets/plot-performance'
        if (searchTerm) {
            url += '?search-term=' + searchTerm
        }
        navigate(url);
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
                    style={{ color: 'blue', textDecoration: 'underline' }}
                >
                    {value}
                </a>
            );
        }
        if (header === "Dataset Characteristics" && Array.isArray(value)) {
            return (
                <div>
                    {value.map((iri: string, index: number) => (
                        <div key={index}>
                            <a
                                href="#"
                                onClick={(e) => {
                                    e.preventDefault();
                                    handleIriClick(iri);
                                }}
                                style={{ color: 'blue', textDecoration: 'underline', marginRight: '8px' }}
                            >
                                {iri}
                            </a>
                        </div>
                    ))}
                </div>
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
            <LoadingBar isLoading={isLoading} />
            <h1>Find Datasets</h1>
            <div>
                <Search onSearch={handleSearch} placeholder={'Model Name/Model Type'} />
                <FindDatasetsFilter
                    selectedFilters={selectedCheckboxes}
                    onFilterChange={handleCheckboxChange} />
            </div>
            <div>
                <div style={{ margin: '8px 0' }}>
                    <button onClick={handleAnalyzeModelOutput}>Analyze Model Output</button>
                    <button style={{ marginLeft: '4px' }} onClick={handlePlotPerformance}>Plot Performance</button>
                </div>
                {datasets.length > 0 &&
                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <button onClick={handleDownload}
                            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span style={{ marginRight: '4px' }}>Download Results</span>
                            <DownloadIcon width={14} height={14} />
                        </button>
                    </div>
                }
                <Table data={datasets}
                    headers={sortHeaders}
                    mapItemToRow={mapItemToRow}
                    currentSorts={currentSorts}
                    onSort={handleSort}
                    onRemoveSort={handleRemoveSort}
                    message={message} />
                <Pagination
                    currentPage={currentPage}
                    totalPages={totalPages}
                    onPageChange={handlePageChange}
                />
            </div>
            {isPopupOpen && (
                <Modal onClose={closePopup}>
                    <h2 style={{ wordBreak: 'break-all', whiteSpace: 'normal' }}>
                        {clickedIri}
                    </h2>
                    <h3>
                        Details:
                    </h3>
                    <pre style={{ whiteSpace: 'pre-wrap' }}>{iriQueryResult}</pre>
                </Modal>
            )}

            {error && <ErrorMessage message={error} />}
        </div>
    );
};

export default FindDatasets;
