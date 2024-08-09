import React, { useState } from 'react';

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
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const resultsPerPage = 10;

    const handleSearch = () => {
        // Implement the search logic here
        // Example: Fetch or filter data based on searchFilter and selectedCheckboxes
        // Simulate data fetching
        const fetchedDatasets = [
            {
                datasetName: 'Dataset A',
                datasetUsedFor: 'Training Data',
                mlInputTimestamp: '2024-08-08T12:00:00Z',
                datasetSize: '500MB',
                datasetCharacteristics: 'High Quality',
                datasetSource: 'Source A',
                modelOutput: 'Output A',
                outputUtilization: 'Model Training',
            },
            // Add more datasets as needed
        ];
        setDatasets(fetchedDatasets);
        setTotalPages(Math.ceil(fetchedDatasets.length / resultsPerPage));
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
        const paginatedDatasets = datasets.slice(startIndex, endIndex);

        return (
            <table>
                <thead>
                <tr>
                    <th>Dataset Name</th>
                    <th>Dataset Used For</th>
                    <th>ML Input Timestamp</th>
                    <th>Dataset Size</th>
                    <th>Dataset Characteristics</th>
                    <th>Dataset Source</th>
                    <th>Model Output</th>
                    <th>Output Utilization</th>
                </tr>
                </thead>
                <tbody>
                {paginatedDatasets.map((dataset, index) => (
                    <tr key={index}>
                        <td>{dataset.datasetName}</td>
                        <td>{dataset.datasetUsedFor}</td>
                        <td>{dataset.mlInputTimestamp}</td>
                        <td>{dataset.datasetSize}</td>
                        <td>{dataset.datasetCharacteristics}</td>
                        <td>{dataset.datasetSource}</td>
                        <td>{dataset.modelOutput}</td>
                        <td>{dataset.outputUtilization}</td>
                    </tr>
                ))}
                </tbody>
            </table>
        );
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

export default FindDatasets;
