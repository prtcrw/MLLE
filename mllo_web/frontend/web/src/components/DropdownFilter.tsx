import React, { useState, useEffect, useRef } from 'react';

interface DropdownFilterProps {
    endpoint: string;  // API endpoint to fetch the options
    selectedValues: string[];  // Selected values in the dropdown
    onChange: (selected: string[]) => void;  // Callback function to pass selected values to the parent component
    label: string;  // Label for the dropdown
}

const DropdownFilter: React.FC<DropdownFilterProps> = ({ endpoint, selectedValues, onChange, label }) => {
    const [options, setOptions] = useState<string[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [isOpen, setIsOpen] = useState(false); // State to manage dropdown open/close
    const dropdownRef = useRef<HTMLDivElement>(null); // Ref to manage click outside

    useEffect(() => {
        // Fetch options from the given endpoint
        const fetchOptions = async () => {
            try {
                const response = await fetch(endpoint);
                if (!response.ok) {
                    throw new Error(`Failed to fetch options: ${response.statusText}`);
                }
                const data = await response.json();
                setOptions(data);
            } catch (error) {
                console.error('Error fetching options:', error);
                setError((error as Error).message);
            }
        };

        fetchOptions();
    }, [endpoint]);

    useEffect(() => {
        // Handle click outside dropdown
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    const handleCheckboxChange = (option: string) => {
        let newSelectedValues = [...selectedValues];
        if (newSelectedValues.includes(option)) {
            newSelectedValues = newSelectedValues.filter(value => value !== option);
        } else {
            newSelectedValues.push(option);
        }
        onChange(newSelectedValues);
    };

    const toggleDropdown = () => {
        setIsOpen(!isOpen);
    };

    const getSelectedSummary = () => {
        if (selectedValues.length === 0) {
            return `Select ${label}`;
        } else if (selectedValues.length === 1) {
            return selectedValues[0];
        } else {
            return `${selectedValues.length} items selected`;
        }
    };

    return (
        <div ref={dropdownRef} style={{ margin: '8px 0', position: 'relative' }}>
            <div 
                style={{ 
                    border: '1px solid #ccc', 
                    padding: '8px', 
                    cursor: 'pointer', 
                    backgroundColor: '#f9f9f9',
                    borderRadius: '8px', 
                    width: '250px', // Fixed width for the bar
                    boxSizing: 'border-box',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                }} 
                onClick={toggleDropdown}
                title={selectedValues.join(', ')} // Tooltip to show full selected items
            >
                {getSelectedSummary()}
            </div>
            {isOpen && (
                <div 
                    style={{ 
                        position: 'absolute', 
                        zIndex: 1, 
                        border: '1px solid #ccc', 
                        backgroundColor: '#fff', 
                        maxHeight: '200px',
                        overflowY: 'auto',
                        width: '100%', 
                        borderRadius: '8px',
                        boxShadow: '0px 4px 8px rgba(0, 0, 0, 0.1)'
                    }}
                >
                    {options.map((option) => (
                        <div key={option} style={{ padding: '8px', display: 'flex', alignItems: 'center' }}>
                            <input
                                type="checkbox"
                                checked={selectedValues.includes(option)}
                                onChange={() => handleCheckboxChange(option)}
                                style={{ marginRight: '8px' }}
                                id={`checkbox-${option}`}
                            />
                            <label 
                                htmlFor={`checkbox-${option}`}
                                style={{ cursor: 'pointer' }}
                            >
                                {option}
                            </label>
                        </div>
                    ))}
                    {error && <p style={{ color: 'red' }}>{error}</p>}
                </div>
            )}
        </div>
    );
};

export default DropdownFilter;
