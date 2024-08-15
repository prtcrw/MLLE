import React, {useState} from 'react';
import './styles/table.css';

interface TableProps {
    data: any[]; // Assuming any data type for now
    headers: string[];
    message?: string;
    sorts?: { [key: string]: 'asc' | 'desc' | null }; // Sorting definition object
    onSort?: (sorts: { [key: string]: 'asc' | 'desc' | null }) => void; // Sort event handler
}

const Table: React.FC<TableProps> = ({data, headers, message, sorts, onSort}) => {
    const [currentSorts, setCurrentSorts] = useState<TableProps['sorts']>(sorts || {});

    const ArrowUpIcon = () => {
        return (
            <svg xmlns="http://www.w3.org/2000/svg" height="12px" viewBox="0 -960 960 960" width="12px" fill="#5f6368">
                <path d="M440-160v-487L216-423l-56-57 320-320 320 320-56 57-224-224v487h-80Z"/>
            </svg>
        );
    };

    const ArrowDownIcon = () => {
        return (
            <svg xmlns="http://www.w3.org/2000/svg" height="12px" viewBox="0 -960 960 960" width="12px" fill="#5f6368">
                <path d="M440-800v487L216-537l-56 57 320 320 320-320-56-57-224 224v-487h-80Z"/>
            </svg>
        );
    };

    const handleSort = (column: string) => {
        const newSorts = {...currentSorts};
        const direction = sortDirection(column);
        newSorts[column] = direction === 'asc' ? 'desc' : (direction === 'desc' ? null : 'asc');

        setCurrentSorts(newSorts);

        if (onSort) {
            onSort(newSorts); // Pass the entire newSorts object
        }
    };

    const isSortedBy = (column: string) => currentSorts?.[column] !== undefined;
    const sortDirection = (column: string) => currentSorts?.[column];

    return (
        <div style={{'--column-count': headers.length} as React.CSSProperties}>
            {data.length > 0 ? (
                <table>
                    <thead>
                    <tr>
                        {headers.map((header, index) => (
                            <th
                                key={index}
                                onClick={() => isSortedBy(header) && handleSort(header)}
                            >
                                <div>
                                    <span className="name">{header}</span>
                                    <div className="sort-icon">
                                    {sortDirection(header) ? (sortDirection(header) == 'asc' ? <ArrowUpIcon/> :
                                        <ArrowDownIcon/>) : ''}
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
                                <td key={i}>{row[key]}</td>
                            ))}
                        </tr>
                    ))}
                    </tbody>
                </table>
            ) : (
                <p>{message || ''}</p>
            )}
        </div>
    );
};

export default Table;
