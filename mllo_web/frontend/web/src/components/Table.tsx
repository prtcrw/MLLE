import React, {ReactNode} from 'react';
import {ArrowDownIcon, ArrowUpIcon} from './Icons.tsx';
import './styles/table.css';

export type SortDirection = 'asc' | 'desc' | null;

interface TableProps {
    data: any[]; // Assuming any data type for now
    headers: string[];
    mapItemToRow?: (header: string, value: any) => ReactNode;
    currentSorts: { key: string; direction: SortDirection }[];
    onSort: (sorts: { key: string; direction: SortDirection }[]) => void;
    onRemoveSort: (key: string) => void;
    message?: string;
}

const Table: React.FC<TableProps> = ({
                                         data, headers, mapItemToRow,
                                         currentSorts,
                                         onSort, onRemoveSort,
                                         message
                                     }) => {
    const handleSort = (column: string) => {
        if (headers.findIndex(header => header === column) === -1) {
            return;
        }

        const newSorts = [...currentSorts || []];
        const existingSortIndex = newSorts.findIndex(sort => sort.key === column);

        if (existingSortIndex !== -1) {
            const newDirection = newSorts[existingSortIndex].direction === 'asc' ? 'desc' : null;
            if (newDirection === null) {
                // Remove the sort if the new direction is null
                newSorts.splice(existingSortIndex, 1);
            } else {
                newSorts[existingSortIndex].direction = newDirection;
            }
        } else {
            newSorts.push({key: column, direction: 'asc'});
        }

        if (onSort) {
            onSort(newSorts); // Pass the entire newSorts list
        }
    };

    const isSortedBy = (column: string) => {
        return headers.find(header => header === column) !== undefined;
    }

    const sortDirection = (column: string) => {
        const existingSort = currentSorts?.find(sort => sort.key === column);
        return existingSort?.direction;
    };

    return data.length > 0 ? (
        <div style={{'--column-count': headers.length} as React.CSSProperties}>
            <div className="sort-container">
                {currentSorts.filter(sort => sort.direction !== null).map(sort => (
                    <div key={sort.key} className="sort-item">
                        <span>{sort.key}</span>
                        <span className="sort-direction">{sort.direction === 'asc' ?
                            <ArrowUpIcon width={12} height={12}/> : sort.direction === 'desc' ?
                                <ArrowDownIcon width={12} height={12}/> : 'Unsorted'}</span>
                        <button className="remove-button" onClick={() => onRemoveSort(sort.key)}>✕</button>
                    </div>
                ))}
            </div>
            <table>
                <thead>
                <tr>
                    {headers.map((header, index) => (
                        <th key={index}
                            onClick={() => isSortedBy(header) && handleSort(header)}>
                            <div>
                                <span className="name">{header}</span>
                                <div className="sort-icon">
                                    {sortDirection(header) ? (sortDirection(header) == 'asc' ?
                                        <ArrowUpIcon width={12} height={12}/> :
                                        <ArrowDownIcon width={12} height={12}/>) : ''}
                                </div>
                            </div>
                        </th>
                    ))}
                </tr>
                </thead>
                <tbody>
                {data.map((row, index) => (
                    <tr key={index}>
                        {Object.keys(row).map((key, i) => (
                            <td key={i}>
                                {(mapItemToRow !== undefined) ? mapItemToRow(headers[i], row[key]) : row[key]}
                            </td>
                        ))}
                    </tr>
                ))}
                </tbody>
            </table>
        </div>
    ) : (<p>{message || ''}</p>)
};

export default Table;
