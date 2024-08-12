import React, {useState} from 'react';
import Table from '../components/Table';
import Pagination from '../components/Pagination';

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
        const response = await fetch(`http://localhost:5252/api/v1/models/?page=${page}&items_per_page=${itemsPerPage}`);
        const fetchedModels = await response.json();
        setCurrentPage(page);
        setTotalPages(fetchedModels["total_pages"]);
        setModels(fetchedModels["data"]);
    };

    return (
        <div>
            <h1>Find Models</h1>
            <div>
                <input
                    type="text"
                    placeholder="Dataset Name"
                    value={datasetName}
                    onChange={(e) => setDatasetName(e.target.value)}
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
