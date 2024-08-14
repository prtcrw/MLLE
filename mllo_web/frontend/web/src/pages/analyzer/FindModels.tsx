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
    const [searchFilter, setSearchFilter] = useState('');
    const [selectedCheckboxes, setSelectedCheckboxes] = useState<string[]>([]);
    const [models, setModels] = useState<ModelData[]>([]);
    const [currentPage, setCurrentPage] = useState(0);
    const [totalPages, setTotalPages] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate(); // Access useNavigate hook


    const handleSearch = async (searchTerm: string) => {
        setIsLoading(true); // Set loading to true
        try {
            setSearchFilter(searchTerm); // Update searchFilter state
            await handlePageChange(1);
        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
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
        try {
            const response = await fetch(buildV1Url(`models/?searchFilter=${searchFilter}&page=${page}&items_per_page=${itemsPerPage}`));
            if (!response.ok) {
                throw new Error(`Failed to fetch models: ${response.statusText}`);
            }
            const fetchedModels = await response.json();
            setCurrentPage(page);
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
        }
    };

    const handleAnalyzeDeployedModel = () => {
        navigate('/models/analyze-deployed-model');
    };

    return (
        <div>
            {isLoading && <LoadingBar isLoading={isLoading}/>}
            <h1>Find Models</h1>
            <div>
                <Search onSearch={handleSearch} placeholder={'Dataset Name'}/>
                <FindModelsFilter
                    selectedFilters={selectedCheckboxes}
                    onFilterChange={handleCheckboxChange}/>
            </div>
            <div style={{margin: '8px 0'}}>
                <div>
                    <button onClick={handleAnalyzeDeployedModel}>Analyze Deployed Model</button>
                </div>
                <Table data={models} headers={[
                    "Model Name",
                    "Model Type",
                    "Model Performance Metric",
                    "Model Performance Value",
                    "Model Objective",
                    "Data Preprocessing",
                    "ML Input Timestamp",
                    "Dataset Used For",
                ]} message={message}/>
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
