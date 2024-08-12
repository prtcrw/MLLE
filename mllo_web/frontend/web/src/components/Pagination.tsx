import React, {useState} from 'react';
import './styles/pagination.css';

interface PaginationProps {
    currentPage: number;
    totalPages: number;
    onPageChange: (page: number, itemsPerPage: number) => void;
}

const Pagination: React.FC<PaginationProps> = ({
                                                   currentPage,
                                                   totalPages,
                                                   onPageChange,
                                               }) => {
    const itemsPerPageOptions = [10, 25, 50]; // Options for items per page

    const [itemsPerPage, setItemsPerPage] = useState(itemsPerPageOptions[0]);

    const handleItemsPerPageChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
        const value = parseInt(event.target.value, 10);
        setItemsPerPage(value);
        onPageChange(1, value); // Reset page to 1 when items per page changes
    };

    // Generate an array of page numbers
    const pageNumbers = Array.from({length: totalPages}, (_, i) => i + 1);

    const handlePageChange = (page: number) => {
        onPageChange(page, itemsPerPage);
    };

    return totalPages > 0 ? (
        <div className="pagination-container">
            <button disabled={currentPage <= 1} onClick={() => onPageChange(currentPage - 1, itemsPerPage)}>
                Previous
            </button>
            <ul className="pagination">
                {pageNumbers.map((page) => (
                    <li key={page} className={page === currentPage ? 'active' : ''}>
                        <button type="button" onClick={() => handlePageChange(page)}>
                            {page}
                        </button>
                    </li>
                ))}
            </ul>
            <button disabled={currentPage === totalPages} onClick={() => onPageChange(currentPage + 1, itemsPerPage)}>
                Next
            </button>
            <div className="items-per-page">
                <select value={itemsPerPage} onChange={handleItemsPerPageChange}>
                    {itemsPerPageOptions.map((option) => (
                        <option key={option} value={option}>
                            {option} per page
                        </option>
                    ))}
                </select>
            </div>
        </div>
    ) : null;
};

export default Pagination;
