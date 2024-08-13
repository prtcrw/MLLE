import React, {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {buildV1Url} from '../../services/api';
import Search from '../../components/Search.tsx';
import Table from '../../components/Table.tsx';
import Pagination from '../../components/Pagination.tsx';
import FindDatasetsFilter from './FindDatasetsFilter.tsx';

interface DatasetData {
    datasetName: string;
    datasetUsedFor: string;
    mlInputTimestamp: string;
    datasetSize: string;
    datasetCharacteristics: string;
    datasetSource: string;
    modelOutput: string;
    outputUtilization: string;
}

const FindDatasets: React.FC = () => {
    const [searchFilter, setSearchFilter] = useState('');
    const [selectedCheckboxes, setSelectedCheckboxes] = useState<string[]>([]);
    const [datasets, setDatasets] = useState<DatasetData[]>([]);
    const [currentPage, setCurrentPage] = useState(0);
    const [totalPages, setTotalPages] = useState(0);
    const navigate = useNavigate(); // Access useNavigate hook


    const handleSearch = async (searchTerm: string) => {
        setSearchFilter(searchTerm); // Update datasetName state
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
        const response = await fetch(buildV1Url(`datasets/?searchFilter=${searchFilter}&page=${page}&items_per_page=${itemsPerPage}`));
        const fetchedDatasets = await response.json();
        setCurrentPage(page);
        setTotalPages(fetchedDatasets["total_pages"]);
        setDatasets(fetchedDatasets["data"]);
    };

    const handleAnalyzeModelOutput = () => {
        navigate('/datasets/analyze-model-output');
    };

    const handlePlotPerformance = () => {
        navigate('/datasets/plot-performance');
    };

    return (
        <div>
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
                    "Dataset Used For",
                    "ML Input Timestamp",
                    "Dataset Size",
                    "Dataset Characteristics",
                    "Dataset Source",
                    "Model Output",
                    "Output Utilization",
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

export default FindDatasets;
