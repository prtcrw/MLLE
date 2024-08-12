import React, {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import Table from '../../components/Table.tsx';
import Pagination from '../../components/Pagination.tsx';

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

    const handleSearch = async () => {
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
        const response = await fetch(`http://localhost:5252/api/v1/datasets/?page=${page}&items_per_page=${itemsPerPage}`);
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
                <input
                    type="text"
                    placeholder="Model Name/Model Type"
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                />
                <button onClick={handleSearch}>Search</button>
                <br/>
                <label>
                    <input
                        type="checkbox"
                        value="Test Data"
                        checked={selectedCheckboxes.includes('Test Data')}
                        onChange={handleCheckboxChange}
                    />
                    Test Data
                </label>
                <label>
                    <input
                        type="checkbox"
                        value="Validation Data"
                        checked={selectedCheckboxes.includes('Validation Data')}
                        onChange={handleCheckboxChange}
                    />
                    Validation Data
                </label>
                <label>
                    <input
                        type="checkbox"
                        value="Training Data"
                        checked={selectedCheckboxes.includes('Training Data')}
                        onChange={handleCheckboxChange}
                    />
                    Training Data
                </label>
                <label>
                    <input
                        type="checkbox"
                        value="Production Data"
                        checked={selectedCheckboxes.includes('Production Data')}
                        onChange={handleCheckboxChange}
                    />
                    Production Data
                </label>
            </div>
            <div>
                <div style={{ margin: '4px 0' }}>
                    <button onClick={handleAnalyzeModelOutput}>Analyze Model Output</button>
                    <button style={{ marginLeft: '4px' }} onClick={handlePlotPerformance}>Plot Performance</button>
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
