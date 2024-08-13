import React, {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {buildV1Url} from '../../services/api';
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
    const [datasetName, setDatasetName] = useState('');
    const [selectedCheckboxes, setSelectedCheckboxes] = useState<string[]>([]);
    const [models, setModels] = useState<ModelData[]>([]);
    const [currentPage, setCurrentPage] = useState(0);
    const [totalPages, setTotalPages] = useState(0);
    const navigate = useNavigate(); // Access useNavigate hook


    const handleSearch = async (searchTerm: string) => {
        setDatasetName(searchTerm); // Update datasetName state
        await handlePageChange(1);
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
        const response = await fetch(buildV1Url(`models/?page=${page}&items_per_page=${itemsPerPage}`));
        const fetchedModels = await response.json();
        setCurrentPage(page);
        setTotalPages(fetchedModels["total_pages"]);
        setModels(fetchedModels["data"]);
    };

    const handleAnalyzeDeployedModel = () => {
        navigate('/models/analyze-deployed-model');
    };

    return (
        <div>
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
                ]}/>
                <Pagination
                    currentPage={currentPage}
                    totalPages={totalPages}
                    onPageChange={handlePageChange}
                />
            </div>
        </div>
    );
};

export default FindModels;
