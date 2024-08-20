import React, {useState} from 'react';
import {Link, useNavigate} from 'react-router-dom';
import {buildV1Url, downloadFromResponse} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import ErrorMessage from '../../components/ErrorMessage.tsx';
import Search from '../../components/Search.tsx';
import Table from '../../components/Table.tsx';
import Pagination from '../../components/Pagination.tsx';
import ToggleSwitch from '../../components/ToggleSwitch.tsx';
import {DownloadIcon} from '../../components/Icons.tsx';

interface PipelineData {
    pipelineName: string;
    pipelineType: string;
    pipelineStructure: string;
    pipelineDataInput: string;
    pipelineAssociatedModel: string;
}

const FindPipelines: React.FC = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const [toggleConstraint, setToggleConstraint] = useState<boolean>(false);
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
                            sorts: { key: string; direction: 'asc' | 'desc' | null }[],
                            toggleConstraint: boolean,
                            format: string = '',) => {
                            setIsLoading(true); // Set loading to true
        try {
            const urlParams = new URLSearchParams({
                search_term: searchTerm,
                page: currentPage.toString(),
                items_per_page: itemsPerPage.toString(),
                toggle_constraint: toggleConstraint.toString(),
            });

            // Add sorts as query params
            for (const { key, direction } of sorts) {
                urlParams.append('sort', `${key},${direction}`);
            }

            if (format !== '') {
                urlParams.append('format', format);
            }

            const response = await fetch(buildV1Url(`pipelines/?${urlParams.toString()}`));
            if (!response.ok) {
                throw new Error(`Failed to fetch models: ${response.statusText}`);
            }

            if (format === '' || format === 'json') {
                const fetchedPipelines = await response.json();
                setCurrentPage(currentPage);
                setTotalPages(fetchedPipelines["total_pages"]);
                setPipelines(fetchedPipelines["data"]);
                if (fetchedPipelines["data"].length == 0) {
                    setMessage("No pipelines found.");
                } else {
                    setMessage('');
                }
            } else {
                await downloadFromResponse(response, 'find_pipelines.csv');
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
        await fetchData(searchTerm, 1, itemsPerPage, currentSorts, toggleConstraint);
    };

    const handleDownload = async () => {
        await fetchData(searchTerm, 1, itemsPerPage, currentSorts, toggleConstraint, 'csv');
    };

    const handlePageChange = async (page: number = 1, itemsPerPage: number = 10) => {
        setCurrentPage(page);
        setItemsPerPage(itemsPerPage);
        await fetchData(searchTerm, page, itemsPerPage, currentSorts, toggleConstraint);
    };

    const handleSort = async (sorts: { key: string; direction: 'asc' | 'desc' | null }[]) => {
        setCurrentSorts(sorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, sorts, toggleConstraint);
    }

    const handleRemoveSort = async (key: string) => {
        const newSorts = currentSorts.filter(sort => sort.key !== key);
        setCurrentSorts(newSorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, newSorts, toggleConstraint); // Update data with new sorts
    };

    const handleToggleConstraint = () => {
        setToggleConstraint(!toggleConstraint); // Toggle between Model and Dataset
    };

    const handleComparePipelines = () => {
        navigate('/pipelines/compare-pipelines');
    };

    const handleViewPipeline = () => {
        navigate('/pipelines/edit-pipeline');
    };

    return (
        <div>
            <LoadingBar isLoading={isLoading} />
            <h1>Find Pipelines</h1>

            <div style={{ margin: '8px 0' }}>
                <Search onSearch={handleSearch} placeholder={'Pipelines Constraint'} />
                <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span className="toggle-label">Model Constraint</span>
                    <ToggleSwitch isChecked={toggleConstraint} onToggle={handleToggleConstraint} />
                    <span className="toggle-label">Dataset Constraint</span>
                </div>
            </div>
            <div>
                <div style={{ margin: '8px 0' }}>
                    <button onClick={handleComparePipelines}>Compare Pipelines</button>
                    <button style={{ marginLeft: '4px' }} onClick={handleViewPipeline}>View Pipeline</button>
                </div>
                {pipelines.length > 0 &&
                    <div style={{display: 'flex', justifyContent: 'flex-end'}}>
                        <button onClick={handleDownload}
                                style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
                            <span style={{marginRight: '4px'}}>Download Results</span>
                            <DownloadIcon width={14} height={14}/>
                        </button>
                    </div>
                }
                <Table data={pipelines}
                       headers={headers}
                       mapItemToRow={(header, value) => {
                           if (header === "Pipeline Name") {
                               return <Link to={`/pipelines/edit-pipeline?pipeline-name=${value}`}>{value}</Link>;
                           } else {
                               return (value);
                           }
                       }}
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
            {error && <ErrorMessage message={error} />}
        </div>
    );
};

export default FindPipelines;
