import React, {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {buildV1Url} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import ErrorMessage from '../../components/ErrorMessage.tsx';
import Search from '../../components/Search.tsx';
import Table from '../../components/Table.tsx';
import Pagination from '../../components/Pagination.tsx';

interface PipelineData {
    pipelineName: string;
    pipelineType: string;
    pipelineStructure: string;
    pipelineDataInput: string;
    pipelineAssociatedModel: string;
}

const FindPipelines: React.FC = () => {
    const [searchFilter, setSearchFilter] = useState('');
    const [pipelines, setPipelines] = useState<PipelineData[]>([]);
    const [currentPage, setCurrentPage] = useState(0);
    const [totalPages, setTotalPages] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate(); // Access useNavigate hook


    const handleSearch = async (searchTerm: string) => {
        setIsLoading(true); // Set loading to true
        try {
            setSearchFilter(searchTerm); // Update datasetName state
            await handlePageChange(1);
        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
    };

    const handlePageChange = async (page: number = 1, itemsPerPage: number = 10) => {
        try {
            const response = await fetch(buildV1Url(`pipelines/?searchFilter=${searchFilter}&page=${page}&items_per_page=${itemsPerPage}`));
            if (!response.ok) {
                throw new Error(`Failed to fetch models: ${response.statusText}`);
            }
            const fetchedPipelines = await response.json();
            setCurrentPage(page);
            setTotalPages(fetchedPipelines["total_pages"]);
            setPipelines(fetchedPipelines["data"]);
            if (fetchedPipelines["data"].length == 0) {
                setMessage("No pipelines found.");
            } else {
                setMessage('');
            }
        } catch (error) {
            console.error('Error fetching models:', error);
            setError((error as Error).message);
        }
    };

    const handleComparePipelines = () => {
        navigate('/pipelines/compare-pipelines');
    };

    const handleViewPipeline = () => {
        navigate('/pipelines/edit-pipeline');
    };

    return (
        <div>
            {isLoading && <LoadingBar isLoading={isLoading}/>}
            <h1>Find Pipelines</h1>
            <div>
                <Search onSearch={handleSearch} placeholder={'Model Name'}/>
            </div>
            <div style={{margin: '8px 0'}}>
                <div>
                    <button onClick={handleComparePipelines}>Compare Pipelines</button>
                    <button style={{marginLeft: '4px'}} onClick={handleViewPipeline}>View Pipeline</button>
                </div>

                <Table data={pipelines} headers={[
                    "Pipeline Name",
                    "Pipeline Type",
                    "Pipeline Structure",
                    "Pipeline Data Input",
                    "Pipeline Associated Model",
                ]} message={message}/>
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

export default FindPipelines;
