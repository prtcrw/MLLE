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
        await fetchData(searchTerm, 1, itemsPerPage, sorts);
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
            <div style={{margin: '8px 0'}}>
                <div>
                    <button onClick={handleAnalyzeModelOutput}>Analyze Model Output</button>
                    <button style={{marginLeft: '4px'}} onClick={handlePlotPerformance}>Plot Performance</button>
                </div>
                <Table data={datasets} headers={[
                    "Dataset Name",
                    "Dataset Used As",
                    "ML Input Timestamp",
                    "Dataset Shape",
                    "Dataset Characteristics",
                    "Dataset Source",
                    "Model Type",
                    "Model Output",
                    "Model Output Utilization",
                    "Model Performance Metric",
                    "Model Performance Value",
                ]} message={message} sorts={{
                    "Dataset Name": null,
                    "Dataset Used As": null,
                    "ML Input Timestamp": null,
                    "Dataset Shape": null,
                    "Dataset Characteristics": null,
                    "Dataset Source": null,
                    "Model Type": null,
                    "Model Output": null,
                    "Model Output Utilization": null,
                    "Model Performance Metric": null,
                    "Model Performance Value": null,
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

export default FindDatasets;
