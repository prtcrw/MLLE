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
    const [searchTerm, setSearchTerm] = useState('');
    const [pipelines, setPipelines] = useState<PipelineData[]>([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [itemsPerPage, setItemsPerPage] = useState(10);
    const sorts = [
        {key: "Pipeline Name", direction: null},
        {key: "Pipeline Type", direction: null},
        {key: "Pipeline Structure", direction: null},
        {key: "Pipeline Data Input", direction: null},
        {key: "Pipeline Associated Model", direction: null},
    ];
    const headers = sorts.map(sort => sort.key);
    const [currentSorts, setCurrentSorts] = useState<{ key: string; direction: 'asc' | 'desc' | null }[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate(); // Access useNavigate hook


    const fetchData = async (searchTerm: string,
                             currentPage: number,
                             itemsPerPage: number,
                             sorts: { key: string; direction: 'asc' | 'desc' | null }[]) => {
        setIsLoading(true); // Set loading to true
        try {
            const urlParams = new URLSearchParams({
                search_term: searchTerm,
                page: currentPage.toString(),
                items_per_page: itemsPerPage.toString(),
            });

            // Add sorts as query params
            for (const {key, direction} of sorts) {
                urlParams.append('sort', `${key},${direction}`);
            }

            const response = await fetch(buildV1Url(`pipelines/?${urlParams.toString()}`));
            if (!response.ok) {
                throw new Error(`Failed to fetch models: ${response.statusText}`);
            }
            const fetchedPipelines = await response.json();
            setCurrentPage(currentPage);
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
        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
    }

    const handleSearch = async (searchTerm: string) => {
        setSearchTerm(searchTerm);
        await fetchData(searchTerm, 1, itemsPerPage, currentSorts);
    };

    const handlePageChange = async (page: number = 1, itemsPerPage: number = 10) => {
        setCurrentPage(page);
        setItemsPerPage(itemsPerPage);
        await fetchData(searchTerm, page, itemsPerPage, currentSorts);
    };

    const handleSort = async (sorts: { key: string; direction: 'asc' | 'desc' | null }[]) => {
        setCurrentSorts(sorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, sorts);
    }

    const handleRemoveSort = async (key: string) => {
        const newSorts = currentSorts.filter(sort => sort.key !== key);
        setCurrentSorts(newSorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, newSorts); // Update data with new sorts
    };

    const handleComparePipelines = () => {
        navigate('/pipelines/compare-pipelines');
    };

    const handleViewPipeline = () => {
        navigate('/pipelines/edit-pipeline');
    };

    return (
        <div>
            <LoadingBar isLoading={isLoading}/>
            <h1>Find Pipelines</h1>
            <div>
                <Search onSearch={handleSearch} placeholder={'Model Name'}/>
            </div>
            <div>
                <div style={{margin: '8px 0'}}>
                    <button onClick={handleComparePipelines}>Compare Pipelines</button>
                    <button style={{marginLeft: '4px'}} onClick={handleViewPipeline}>View Pipeline</button>
                </div>
                <Table data={pipelines}
                       headers={headers}
                       sorts={sorts}
                       currentSorts={currentSorts}
                       onSort={handleSort}
                       onRemoveSort={handleRemoveSort}
                       message={message}/>
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
