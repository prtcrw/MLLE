import React from 'react';

interface FilterOption {
    label: string;
    value: string;
}

const FindModelsFilter: React.FC<{
    selectedFilters: string[];
    onFilterChange: (e: React.ChangeEvent<HTMLInputElement>) => void
}> = ({
          selectedFilters,
          onFilterChange,
      }) => {
    const filterOptions: FilterOption[] = [
        {label: 'Test Data', value: 'Test Data'},
        {label: 'Validation Data', value: 'Validation Data'},
        {label: 'Training Data', value: 'Training Data'},
        {label: 'Production Data', value: 'Production Data'},
    ];

    return (
        <div className="advanced-filters">
            {filterOptions.map((option) => (
                <label key={option.value}>
                    <input
                        type="checkbox"
                        value={option.value}
                        checked={selectedFilters.includes(option.value)}
                        onChange={(e) => onFilterChange(e)}
                    />
                    {option.label}
                </label>
            ))}
        </div>
    );
};

export default FindModelsFilter;
