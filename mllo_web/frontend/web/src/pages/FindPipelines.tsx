import React, {useState} from 'react';
import Table from '../components/Table';
import Pagination from '../components/Pagination';

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
    const [currentPage, setCurrentPage] = useState(0);
    const [totalPages, setTotalPages] = useState(0);

    const handleSearch = async () => {
        await handlePageChange(1);
    };

    const handlePageChange = async (page: number = 1, itemsPerPage: number = 10) => {
        const response = await fetch(`http://localhost:5252/api/v1/pipelines/?page=${page}&items_per_page=${itemsPerPage}`);
        const fetchedPipelines = await response.json();
        setCurrentPage(page);
        setTotalPages(fetchedPipelines["total_pages"]);
        setPipelines(fetchedPipelines["data"]);
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
                <Table data={pipelines} headers={[
                    "Pipeline Name",
                    "Pipeline Type",
                    "Pipeline Structure",
                    "Pipeline Data Input",
                    "Pipeline Associated Model",
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

export default FindPipelines;
