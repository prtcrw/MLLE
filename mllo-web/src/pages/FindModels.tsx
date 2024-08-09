import React, { useState } from 'react';

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
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const resultsPerPage = 10;

    const handleSearch = () => {
        // Implement the search logic here
        // Example: Fetch or filter data based on datasetName and selectedCheckboxes
        // Simulate data fetching
        const fetchedModels = [
            // Example data, replace with actual data fetching logic
            {
                modelName: 'Model A',
                modelType: 'Type 1',
                modelPerformanceMetric: 'Accuracy',
                modelPerformanceValue: 95,
                modelObjective: 'Classification',
                dataPreprocessing: 'Normalization',
                mlInputTimestamp: '2024-08-08T12:00:00Z',
                datasetUsedFor: 'Training Data',
            },
            // Add more models as needed
        ];
        setModels(fetchedModels);
        setTotalPages(Math.ceil(fetchedModels.length / resultsPerPage));
    };

    const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { value, checked } = e.target;
        setSelectedCheckboxes(prev =>
            checked
                ? [...prev, value]
                : prev.filter(item => item !== value)
        );
    };

    const handlePageChange = (page: number) => {
        setCurrentPage(page);
        // Implement pagination logic here
    };

    const renderTable = () => {
        const startIndex = (currentPage - 1) * resultsPerPage;
        const endIndex = startIndex + resultsPerPage;
        const paginatedModels = models.slice(startIndex, endIndex);

        return (
            <table>
                <thead>
                <tr>
                    <th>Model Name</th>
                    <th>Model Type</th>
                    <th>Model Performance Metric</th>
                    <th>Model Performance Value</th>
                    <th>Model Objective</th>
                    <th>Data Preprocessing</th>
                    <th>ML Input Timestamp</th>
                    <th>Dataset Used For</th>
                </tr>
                </thead>
                <tbody>
                {paginatedModels.map((model, index) => (
                    <tr key={index}>
                        <td>{model.modelName}</td>
                        <td>{model.modelType}</td>
                        <td>{model.modelPerformanceMetric}</td>
                        <td>{model.modelPerformanceValue}</td>
                        <td>{model.modelObjective}</td>
                        <td>{model.dataPreprocessing}</td>
                        <td>{model.mlInputTimestamp}</td>
                        <td>{model.datasetUsedFor}</td>
                    </tr>
                ))}
                </tbody>
            </table>
        );
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
                <br />
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
                {renderTable()}
                <div>
                    <button
                        disabled={currentPage === 1}
                        onClick={() => handlePageChange(currentPage - 1)}
                    >
                        Previous
                    </button>
                    <span>Page {currentPage} of {totalPages}</span>
                    <button
                        disabled={currentPage === totalPages}
                        onClick={() => handlePageChange(currentPage + 1)}
                    >
                        Next
                    </button>
                </div>
            </div>
        </div>
    );
};

export default FindModels;
