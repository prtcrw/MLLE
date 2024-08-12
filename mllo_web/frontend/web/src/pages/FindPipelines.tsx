import React, { useState } from 'react';

interface PipelineData {
    pipelineName: string;
    pipelineType: string;
    pipelineStructure: string;
    pipelineDataInput: string;
    pipelineAssociatedModel: string;
}

const FindPipelines: React.FC = () => {
    const [modelName, setModelName] = useState('');
    const [pipelines, setPipelines] = useState<PipelineData[]>([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const resultsPerPage = 10;

    const handleSearch = async () => {
        const response = await fetch('http://localhost:5252/api/v1/pipelines/');
        const fetchedPipelines = await response.json();
        setPipelines(fetchedPipelines);
        setTotalPages(Math.ceil(fetchedPipelines.length / resultsPerPage));
    };

    const handlePageChange = (page: number) => {
        setCurrentPage(page);
        // Implement pagination logic here
    };

    const renderTable = () => {
        const startIndex = (currentPage - 1) * resultsPerPage;
        const endIndex = startIndex + resultsPerPage;
        const paginatedPipelines = pipelines.slice(startIndex, endIndex);

        return (
            <table>
                <thead>
                <tr>
                    <th>Pipeline Name</th>
                    <th>Pipeline Type</th>
                    <th>Pipeline Structure</th>
                    <th>Pipeline Data Input</th>
                    <th>Pipeline Associated Model</th>
                </tr>
                </thead>
                <tbody>
                {paginatedPipelines.map((pipeline, index) => (
                    <tr key={index}>
                        <td>{pipeline.pipelineName}</td>
                        <td>{pipeline.pipelineType}</td>
                        <td>{pipeline.pipelineStructure}</td>
                        <td>{pipeline.pipelineDataInput}</td>
                        <td>{pipeline.pipelineAssociatedModel}</td>
                    </tr>
                ))}
                </tbody>
            </table>
        );
    };

    return (
        <div>
            <h1>Find Pipelines</h1>
            <div>
                <input
                    type="text"
                    placeholder="Model Name"
                    value={modelName}
                    onChange={(e) => setModelName(e.target.value)}
                />
                <button onClick={handleSearch}>Search</button>
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

export default FindPipelines;
