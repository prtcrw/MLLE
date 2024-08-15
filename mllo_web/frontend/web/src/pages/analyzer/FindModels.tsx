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
    const [sorts, setSorts] = useState<{ [key: string]: 'asc' | 'desc' | null }>({});
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate(); // Access useNavigate hook


    const fetchData = async (searchTerm: string,
                             currentPage: number,
                             itemsPerPage: number,
                             sorts: { [key: string]: 'asc' | 'desc' | null }) => {
        setIsLoading(true); // Set loading to true
        try {
            const urlParams = new URLSearchParams({
                search_term: searchTerm,
                page: currentPage.toString(),
                items_per_page: itemsPerPage.toString(),
            });

            // Add sorts as query params
            for (const [key, value] of Object.entries(sorts)) {
                if (value) {
                    urlParams.append('sort', `${key},${value}`);
                }
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

    const handleSort = async (sorts: { [key: string]: 'asc' | 'desc' | null }) => {
        setSorts(sorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, sorts);
    }

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
                ]} message={message} sorts={{
                    "Model Name": null,
                    "Model Type": null,
                    "Model Performance Metric": null,
                    "Model Performance Value": null,
                    "Model Objective": null,
                    "Data Preprocessing": null,
                    "ML Input Timestamp": null,
                    "Dataset Used For": null,
                }} onSort={handleSort}/>
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
