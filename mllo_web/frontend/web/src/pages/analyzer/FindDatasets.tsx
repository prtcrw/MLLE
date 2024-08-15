import React, {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {buildV1Url} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import ErrorMessage from '../../components/ErrorMessage.tsx';
import Search from '../../components/Search.tsx';
import Table from '../../components/Table.tsx';
import Pagination from '../../components/Pagination.tsx';
import FindDatasetsFilter from './FindDatasetsFilter.tsx';

interface DatasetData {
    datasetName: string;
    datasetUsedAs: string;
    mlInputTimestamp: string;
    datasetShape: string;
    datasetCharacteristics: string;
    datasetSource: string;
    modelType: string;
    modelOutput: string;
    modelOutputUtilization: string;
    modelPerformanceMetric: string;
    modelPerformanceValue: string;
}

const FindDatasets: React.FC = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCheckboxes, setSelectedCheckboxes] = useState<string[]>([]);
    const [datasets, setDatasets] = useState<DatasetData[]>([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [itemsPerPage, setItemsPerPage] = useState(10);
    const sorts = [
        {key: "Dataset Name", direction: null},
        {key: "Dataset Used As", direction: null},
        {key: "ML Input Timestamp", direction: null},
        {key: "Dataset Shape", direction: null},
        {key: "Dataset Characteristics", direction: null},
        {key: "Dataset Source", direction: null},
        {key: "Model Type", direction: null},
        {key: "Model Output", direction: null},
        {key: "Model Output Utilization", direction: null},
        {key: "Model Performance Metric", direction: null},
        {key: "Model Performance Value", direction: null},
    ];
    const headers = sorts.map(sort => sort.key);
    const [currentSorts, setCurrentSorts] = useState<{ key: string; direction: 'asc' | 'desc' | null }[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate(); // Access useNavigate hook


    const fetchData = async (searchTerm: string,
                             currentPage: number,
                             itemsPerPage: number,
                             sorts: { key: string; direction: 'asc' | 'desc' | null }[]) => {
        setIsLoading(true); // Set loading to true
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

            const response = await fetch(buildV1Url(`datasets/?${urlParams.toString()}`));
            if (!response.ok) {
                throw new Error(`Failed to fetch models: ${response.statusText}`);
            }
            const fetchedDatasets = await response.json();
            setCurrentPage(currentPage);
            setTotalPages(fetchedDatasets["total_pages"]);
            setDatasets(fetchedDatasets["data"]);
            if (fetchedDatasets["data"].length == 0) {
                setMessage("No datasets found.");
            } else {
                setMessage('');
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
        await fetchData(searchTerm, 1, itemsPerPage, currentSorts);
    };

    const handlePageChange = async (page: number = 1, itemsPerPage: number = 10) => {
        setCurrentPage(page);
        setItemsPerPage(itemsPerPage);
        await fetchData(searchTerm, page, itemsPerPage, currentSorts);
    };

    const handleSort = async (sorts: { key: string; direction: 'asc' | 'desc' | null }[]) => {
        setCurrentSorts(sorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, sorts);
    }

    const handleRemoveSort = async (key: string) => {
        const newSorts = currentSorts.filter(sort => sort.key !== key);
        setCurrentSorts(newSorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, newSorts); // Update data with new sorts
    };

    const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const {value, checked} = e.target;
        setSelectedCheckboxes(prev =>
            checked
                ? [...prev, value]
                : prev.filter(item => item !== value)
        );
    };

    const handleAnalyzeModelOutput = () => {
        navigate('/datasets/analyze-model-output');
    };

    const handlePlotPerformance = () => {
        navigate('/datasets/plot-performance');
    };

    return (
        <div>
            <LoadingBar isLoading={isLoading}/>
            <h1>Find Datasets</h1>
            <div>
                <Search onSearch={handleSearch} placeholder={'Model Name/Model Type'}/>
                <FindDatasetsFilter
                    selectedFilters={selectedCheckboxes}
                    onFilterChange={handleCheckboxChange}/>
            </div>
            <div>
                <div style={{margin: '8px 0'}}>
                    <button onClick={handleAnalyzeModelOutput}>Analyze Model Output</button>
                    <button style={{marginLeft: '4px'}} onClick={handlePlotPerformance}>Plot Performance</button>
                </div>
                <Table data={datasets}
                       headers={headers}
                       sorts={sorts}
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

export default FindDatasets;
