import React, {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {buildV1Url} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import ErrorMessage from '../../components/ErrorMessage.tsx';
import Search from '../../components/Search.tsx';
import Table from '../../components/Table.tsx';
import Pagination from '../../components/Pagination.tsx';
import FindModelsFilter from './FindModelsFilter.tsx';

interface ModelData {
    modelName: string;
    modelType: string;
    modelPerformanceMetric: string;
    modelPerformanceValue: number;
    modelObjective: string;
    dataPreprocessing: string;
    mlInputTimestamp: string;
    datasetUsedFor: string;
}


const FindModels: React.FC = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCheckboxes, setSelectedCheckboxes] = useState<string[]>([]);
    const [models, setModels] = useState<ModelData[]>([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [itemsPerPage, setItemsPerPage] = useState(10);
    const sorts = [
        {key: "Model Name", direction: null},
        {key: "Model Type", direction: null},
        {key: "Model Performance Metric", direction: null},
        {key: "Model Performance Value", direction: null},
        {key: "Model Objective", direction: null},
        {key: "Data Preprocessing", direction: null},
        {key: "ML Input Timestamp", direction: null},
        {key: "Dataset Used For", direction: null},
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

            const response = await fetch(buildV1Url(`models/?${urlParams.toString()}`));
            if (!response.ok) {
                throw new Error(`Failed to fetch models: ${response.statusText}`);
            }
            const fetchedModels = await response.json();
            setCurrentPage(currentPage);
            setTotalPages(fetchedModels["total_pages"]);
            setModels(fetchedModels["data"]);
            if (fetchedModels["data"].length == 0) {
                setMessage("No models found.");
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
        await fetchData(searchTerm, 1, itemsPerPage, sorts);
    };

    const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const {value, checked} = e.target;
        setSelectedCheckboxes(prev =>
            checked
                ? [...prev, value]
                : prev.filter(item => item !== value)
        );
    };

    const handlePageChange = async (page: number = 1, itemsPerPage: number = 10) => {
        setCurrentPage(page);
        setItemsPerPage(itemsPerPage);
        await fetchData(searchTerm, page, itemsPerPage, sorts);
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

    const handleAnalyzeDeployedModel = () => {
        navigate('/models/analyze-deployed-model');
    };

    return (
        <div>
            <LoadingBar isLoading={isLoading}/>
            <h1>Find Models</h1>
            <div>
                <Search onSearch={handleSearch} placeholder={'Dataset Name'}/>
                <FindModelsFilter
                    selectedFilters={selectedCheckboxes}
                    onFilterChange={handleCheckboxChange}/>
            </div>
            <div>
                <div style={{margin: '8px 0'}}>
                    <button onClick={handleAnalyzeDeployedModel}>Analyze Deployed Model</button>
                </div>
                <Table data={models}
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

export default FindModels;
