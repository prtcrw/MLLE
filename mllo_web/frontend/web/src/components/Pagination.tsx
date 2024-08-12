import React, { useState } from 'react';
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

    // Generate an array of page numbers with logic for showing only MAX_VISIBLE_PAGES
    const pageNumbers = [];
    const MAX_VISIBLE_PAGES = 10;
    const halfWindow = Math.floor(MAX_VISIBLE_PAGES / 2);

    if (totalPages <= MAX_VISIBLE_PAGES) {
        // Show all pages if less than or equal to MAX_VISIBLE_PAGES
        for (let i = 1; i <= totalPages; i++) {
            pageNumbers.push(i);
        }
    } else {
        // Show centered window of pages with active page in the middle
        const startPage = Math.max(Math.min(currentPage - halfWindow, totalPages - MAX_VISIBLE_PAGES + 1), 1);
        const endPage = Math.min(startPage + MAX_VISIBLE_PAGES - 1, totalPages);

        for (let i = startPage; i <= endPage; i++) {
            pageNumbers.push(i);
        }
    }

    const handlePageChange = (page: number) => {
        onPageChange(page, itemsPerPage);
    };

    return totalPages > 0 ? (
        <div className="pagination-container">
            {totalPages > MAX_VISIBLE_PAGES && (
                <button style={{ marginRight: '4px' }} disabled={currentPage === 1} onClick={() => onPageChange(1, itemsPerPage)}>
                    First
                </button>
            )}
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
            {totalPages > MAX_VISIBLE_PAGES && (
                <button style={{ marginLeft: '4px' }} disabled={currentPage === totalPages} onClick={() => onPageChange(totalPages, itemsPerPage)}>
                    Last
                </button>
            )}
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
