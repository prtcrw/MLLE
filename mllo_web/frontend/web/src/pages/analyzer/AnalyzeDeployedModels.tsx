import React, {useState} from 'react';
import {buildV1Url, downloadFromResponse} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import ErrorMessage from '../../components/ErrorMessage.tsx';
import Search from '../../components/Search.tsx';
import Table, {SortDirection} from '../../components/Table.tsx';
import Pagination from '../../components/Pagination.tsx';
import {DownloadIcon} from '../../components/Icons.tsx';
import {lowercaseToPascalCase, pascalCaseToWords} from '../../components/FormatUtilities.tsx';
import Modal from '../../components/Modal.tsx';

interface DeployedModelData {
    modelName: string;
    modelDeployedOnSystem: string;
    lastModelUpdate: string;
    modelExecutionTimestamp: string;
    modelInput: string;
    modelOutput: string;
    modelOutputUtilization: string;
    modelPerformanceMetric: string;
    modelPerformanceValue: string;
}

interface IRIQueryData {
    dataPropertyValuePairs: string;
    annotationPropertyValuePairs: string;
    types: string;
}

const AnalyzeDeployedModels: React.FC = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const [models, setModels] = useState<DeployedModelData[]>([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [itemsPerPage, setItemsPerPage] = useState(10);
    const sortHeaders = [
        "Model Name",
        "Model Deployed on System",
        "Last Model Update",
        "Model Execution Timestamp",
        "Model Input",
        "Model Output",
        "Model Output Utilization",
        "Model Performance Metric",
        "Model Performance Value",
    ];
    const [currentSorts, setCurrentSorts] = useState<{ key: string; direction: SortDirection }[]>([
        {key: "Model Name", direction: "asc"}
    ]);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [isPopupOpen, setIsPopupOpen] = useState(false);
    const [iriQueryResult, setQueryResult] = useState<IRIQueryData[] | null>(null);
    const [clickedIri, setClickedIri] = useState<string | null>(null);

    const fetchData = async (
        searchTerm: string,
        currentPage: number,
        itemsPerPage: number,
        sorts: { key: string; direction: SortDirection }[],
        format: string = ''
    ) => {
        setIsLoading(true);
        setMessage('');
        setError(null);
        try {
            const urlParams = new URLSearchParams({
                search_term: searchTerm,
                page: currentPage.toString(),
                items_per_page: itemsPerPage.toString(),
            });

            // Add sorts as query params
            for (const {key, direction} of sorts) {
                urlParams.append('sort', `${key},${direction}`);
            }

            if (format !== '') {
                urlParams.append('format', format);
            }

            const response = await fetch(buildV1Url(`models/deployed?${urlParams.toString()}`));
            if (!response.ok) {
                throw new Error(`Failed to fetch models: ${response.statusText}`);
            }

            if (format === '' || format === 'json') {
                const fetchedModels = await response.json();
                setCurrentPage(currentPage);
                setTotalPages(fetchedModels["total_pages"]);
                setModels(fetchedModels["data"]);
                if (fetchedModels["data"].length === 0) {
                    setMessage("No models found.");
                } else {
                    setMessage('');
                }
            } else {
                await downloadFromResponse(response, 'deployed_models.csv');
            }
        } catch (error) {
            console.error('Error fetching models:', error);
            setError((error as Error).message);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSearch = async (searchTerm: string) => {
        setSearchTerm(searchTerm);
        await fetchData(searchTerm, 1, itemsPerPage, currentSorts);
    };

    const handleDownload = async () => {
        await fetchData(searchTerm, 1, itemsPerPage, currentSorts, 'csv');
    };

    const handlePageChange = async (page: number = 1, itemsPerPage: number = 10) => {
        setCurrentPage(page);
        setItemsPerPage(itemsPerPage);
        await fetchData(searchTerm, page, itemsPerPage, currentSorts);
    };

    const handleSort = async (sorts: { key: string; direction: SortDirection }[]) => {
        setCurrentSorts(sorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, sorts);
    };

    const handleRemoveSort = async (key: string) => {
        const newSorts = currentSorts.filter(sort => sort.key !== key);
        setCurrentSorts(newSorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, newSorts); // Update data with new sorts
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

    const mapItemToRow = (_header: string, value: any) => {
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
        else if (typeof value === 'string') {
            if (/^[A-Z][a-z0-9]+([A-Z][a-z0-9]*)*$/.test(value)) {
                value = pascalCaseToWords(value);
            } else if (/^[a-z ]+$/.test(value)) {
                value = lowercaseToPascalCase(value);
            }
            return (
                <span>{value}</span>
            );
        }
        else {
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
            <h1>Analyze Deployed Models</h1>
            <div style={{margin: '8px 0'}}>
                <Search onSearch={handleSearch} placeholder={'Value'}/>
            </div>
            <div>
                {models.length > 0 &&
                    <div style={{display: 'flex', justifyContent: 'flex-end'}}>
                        <button onClick={handleDownload}
                                style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
                            <span style={{marginRight: '4px'}}>Download Results</span>
                            <DownloadIcon width={14} height={14}/>
                        </button>
                    </div>
                }
                <Table data={models}
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

export default AnalyzeDeployedModels;
