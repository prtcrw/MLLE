import React from 'react';

interface FilterOption {
    label: string;
    value: string;
}

const FindDatasetsFilter: React.FC<{
    selectedFilters: { [key: string]: boolean };
    onFilterChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}> = ({
          selectedFilters,
          onFilterChange,
      }) => {
    const filterOptions: FilterOption[] = [
        {label: 'Test Data', value: 'test_data'},
        {label: 'Validation Data', value: 'validation_data'},
        {label: 'Training Data', value: 'training_data'},
        {label: 'Production Data', value: 'production_data'}
    ];

    return (
        <div className="advanced-filters">
            {filterOptions.map((option) => (
                <label key={option.value}>
                    <input
                        type="checkbox"
                        name={option.value}
                        checked={selectedFilters[option.value] || false}
                        onChange={onFilterChange}
                    />
                    <span>{option.label}</span>
                </label>
            ))}
        </div>
    );
};

export default FindDatasetsFilter;
