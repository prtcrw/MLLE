import React, {useState} from 'react';
import {buildV1Url, downloadFromResponse} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import ErrorMessage from '../../components/ErrorMessage.tsx';
import Search from '../../components/Search.tsx';
import Table, {SortDirection} from '../../components/Table.tsx';
import Pagination from '../../components/Pagination.tsx';
import {DownloadIcon} from '../../components/Icons.tsx';

interface DeployedModelData {
    modelName: string;
    modelDeployedOnSystem: string;
    lastModelUpdate: string;
    modelExecutionTimestamp: string;
    modelInputData: string;
    modelOutputData: string;
    modelOutputUtilization: string;
    modelPerformanceMetric: string;
    modelPerformanceValue: string;
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
        "Model Input Data",
        "Model Output Data",
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

    const mapItemToRow = (_header: string, value: any) => {
        return value;
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
            {error && <ErrorMessage message={error}/>}
        </div>
    );
};

export default AnalyzeDeployedModels;
