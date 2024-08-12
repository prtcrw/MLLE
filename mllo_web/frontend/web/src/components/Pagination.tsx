import React, {useState} from 'react';

interface PaginationProps {
    currentPage: number;
    totalPages: number;
    onPageChange: (page: number, itemsPerPage: number) => void;
}


const Pagination: React.FC<PaginationProps> = ({currentPage, totalPages, onPageChange}) => {
    const itemsPerPageOptions = [10, 25, 50]; // Options for items per page

    const [itemsPerPage, setItemsPerPage] = useState(itemsPerPageOptions[0]);

    const handleItemsPerPageChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
        const value = parseInt(event.target.value, 10);
        setItemsPerPage(value);
        onPageChange(1, value); // Reset page to 1 when items per page changes
    };

    return (
        <div style={{display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <button
                disabled={currentPage <= 1}
                onClick={() => onPageChange(currentPage - 1, itemsPerPage)}
            >
                Previous
            </button>
            <span>Page {currentPage} of {totalPages}</span>
            <button
                disabled={currentPage === totalPages}
                onClick={() => onPageChange(currentPage + 1, itemsPerPage)}
            >
                Next
            </button>
            <select value={itemsPerPage} onChange={handleItemsPerPageChange}>
                {itemsPerPageOptions.map((option) => (
                    <option key={option} value={option}>
                        {option} per page
                    </option>
                ))}
            </select>
        </div>
    );
};

export default Pagination;
