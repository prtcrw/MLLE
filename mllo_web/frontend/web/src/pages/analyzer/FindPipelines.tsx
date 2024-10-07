import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { buildV1Url, downloadFromResponse } from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import ErrorMessage from '../../components/ErrorMessage.tsx';
import Search from '../../components/Search.tsx';
import Table, { SortDirection } from '../../components/Table.tsx';
import Pagination from '../../components/Pagination.tsx';
import ToggleSwitch from '../../components/ToggleSwitch.tsx';
import DropdownFilter from '../../components/DropdownFilter.tsx';
import { DownloadIcon } from '../../components/Icons.tsx';
import { pascalCaseToWords, lowercaseToPascalCase } from '../../components/FormatUtilities';

interface PipelineData {
    pipelineName: string;
    pipelineType: string;
    pipelineComponents: string[];
    pipelineDataInput: string;
    pipelineDataOutput: string;
    pipelineAssociatedModel: string;
}

const FindPipelines: React.FC = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const [toggleConstraint, setToggleConstraint] = useState<boolean>(false);
    const [pipelines, setPipelines] = useState<PipelineData[]>([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [itemsPerPage, setItemsPerPage] = useState(10);
    const [pipelineTypes, setPipelineTypes] = useState<string[]>([]);
    const sortHeaders = [
        "Pipeline Name",
        "Pipeline Type",
        "Pipeline Components",
        "Pipeline Data Input",
        "Pipeline Data Output",
        "Pipeline Associated Model",
    ];
    const [currentSorts, setCurrentSorts] = useState<{ key: string; direction: SortDirection }[]>([
        { key: "Pipeline Name", direction: 'asc' }
    ]);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate();
    const location = useLocation(); // Use useLocation to access the current URL

    useEffect(() => {
        const urlParams = new URLSearchParams(location.search);
        const searchTermFromUrl = urlParams.get('search_term');
        const toggleConstraintFromUrl = urlParams.get('toggle_constraint');

        // Only update the state if the 'search_term' exists in the URL
        if (searchTermFromUrl) {
            setSearchTerm(searchTermFromUrl);
            if (toggleConstraintFromUrl) {
                setToggleConstraint(toggleConstraintFromUrl === 'true');
            }

            // Fetch data with the extracted search term and toggle constraint
            fetchData(searchTermFromUrl, currentPage, itemsPerPage, currentSorts, toggleConstraintFromUrl === 'true');
        }
    }, [location.search]); // Depend on location.search to run when the URL changes

    const fetchData = async (
        searchTerm: string,
        currentPage: number,
        itemsPerPage: number,
        sorts: { key: string; direction: SortDirection }[],
        toggleConstraint: boolean,
        format: string = ''
    ) => {
        setIsLoading(true);
        setMessage('');
        setError(null);
        try {
            const urlParams = new URLSearchParams({
                search_term: searchTerm,
                page: currentPage.toString(),
                items_per_page: itemsPerPage.toString(),
                toggle_constraint: toggleConstraint.toString(),
            });

            // Add selected pipeline types to the query parameters if any are selected
            if (pipelineTypes.length > 0) {
                pipelineTypes.forEach((type) => {
                    urlParams.append('pipeline_types', type);
                });
            }

            for (const { key, direction } of sorts) {
                urlParams.append('sort', `${key},${direction}`);
            }

            if (format !== '') {
                urlParams.append('format', format);
            }

            const response = await fetch(buildV1Url(`pipelines/?${urlParams.toString()}`));
            if (!response.ok) {
                throw new Error(`Failed to fetch pipelines: ${response.statusText}`);
            }

            if (format === '' || format === 'json') {
                const fetchedPipelines = await response.json();
                setCurrentPage(currentPage);
                setTotalPages(fetchedPipelines["total_pages"]);
                setPipelines(fetchedPipelines["data"]);
                if (fetchedPipelines["data"].length === 0) {
                    setMessage("No pipelines found.");
                } else {
                    setMessage('');
                }
            } else {
                await downloadFromResponse(response, 'find_pipelines.csv');
            }
        } catch (error) {
            console.error('Error fetching pipelines:', error);
            setError((error as Error).message);
        } finally {
            setIsLoading(false);
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

    const handleSort = async (sorts: { key: string; direction: SortDirection }[]) => {
        setCurrentSorts(sorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, sorts, toggleConstraint);
    }

    const handleRemoveSort = async (key: string) => {
        const newSorts = currentSorts.filter(sort => sort.key !== key);
        setCurrentSorts(newSorts);
        await fetchData(searchTerm, currentPage, itemsPerPage, newSorts, toggleConstraint);
    };

    const handleToggleConstraint = () => {
        setToggleConstraint(!toggleConstraint);
    };

    const handleComparePipelines = () => {
        navigate('/pipelines/compare-pipelines');
    };

    const handleViewPipeline = () => {
        navigate('/pipelines/edit-pipeline');
    };

    const mapItemToRow = (header: string, value: any) => {
        if (header === "Pipeline Name") {
            return <Link to={`/pipelines/edit-pipeline?pipeline-name=${value}`}>{pascalCaseToWords(value)}</Link>;
        } else if (header === "Pipeline Components") {
            return (value && Array.isArray(value))
                ? value.map(component => lowercaseToPascalCase(component)).join('; ')
                : '';
        }
        if (typeof value === 'string') {
            if (/^[A-Z][a-z0-9]+([A-Z][a-z0-9]*)*$/.test(value)) {
                value = pascalCaseToWords(value);
            } else if (/^[a-z ]+$/.test(value)) {
                value = lowercaseToPascalCase(value);
            }
            return <span>{value}</span>;
        }
    };

    // Placeholder logic based on the presence of searchTerm in the URL
    const placeholder = searchTerm
        ? `${pascalCaseToWords(searchTerm)}`
        : !toggleConstraint
            ? 'Model Constraint'
            : 'Dataset Constraint';

    return (
        <div>
            <LoadingBar isLoading={isLoading} />
            <h1>Find Pipelines</h1>

            <div style={{ margin: '8px 0' }}>
                <Search 
                    onSearch={handleSearch}
                    placeholder={placeholder} 
                />
                <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span className="toggle-label">Model Constraint</span>
                    <ToggleSwitch isChecked={toggleConstraint} onToggle={handleToggleConstraint} />
                    <span className="toggle-label">Dataset Constraint</span>
                    <div style={{ marginLeft: '16px' }}>
                        <DropdownFilter
                            endpoint={buildV1Url('pipelines/types')}
                            selectedValues={pipelineTypes}
                            onChange={setPipelineTypes}
                            label="Pipeline Types"
                        />
                    </div>
                </div>
            </div>
            <div>
                <div style={{ margin: '8px 0' }}>
                    <button onClick={handleComparePipelines}>Compare Pipelines</button>
                    <button style={{ marginLeft: '4px' }} onClick={handleViewPipeline}>View Pipeline</button>
                </div>
                {pipelines.length > 0 &&
                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <button onClick={handleDownload}
                            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span style={{ marginRight: '4px' }}>Download Results</span>
                            <DownloadIcon width={14} height={14} />
                        </button>
                    </div>
                }
                <Table data={pipelines}
                    headers={sortHeaders}
                    mapItemToRow={mapItemToRow}
                    currentSorts={currentSorts}
                    onSort={handleSort}
                    onRemoveSort={handleRemoveSort}
                    message={message} />
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
