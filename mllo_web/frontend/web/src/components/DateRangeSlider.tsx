import React, { useState, useEffect } from 'react';
import Slider from '@mui/material/Slider';

interface DateRangeSliderProps {
    endpoint: string; // API endpoint to fetch the dates
    onChange: (range: [Date, Date], includeBlank: boolean) => void; // Callback function to pass selected date range and blank date inclusion to the parent component
}

const DateRangeSlider: React.FC<DateRangeSliderProps> = ({ endpoint, onChange }) => {
    const [minDate, setMinDate] = useState<Date | null>(null);
    const [maxDate, setMaxDate] = useState<Date | null>(null);
    const [availableDates, setAvailableDates] = useState<Date[]>([]);
    const [value, setValue] = useState<number[]>([]);
    const [includeBlankDate, setIncludeBlankDate] = useState<boolean>(false);

    useEffect(() => {
        // Fetch available dates from the API
        const fetchData = async () => {
            try {
                const response = await fetch(endpoint);
                const data = await response.json();

                const minDate = new Date(data.min_date);
                const maxDate = new Date(data.max_date);
                const availableDates = data.available_dates.map((date: string) => new Date(date));

                setMinDate(minDate);
                setMaxDate(maxDate);
                setAvailableDates(availableDates);
                setValue([0, availableDates.length - 1]); // Initialize slider with the first and last index
            } catch (error) {
                console.error('Error fetching dates:', error);
            }
        };

        fetchData();
    }, [endpoint]);

    const handleChange = (event: React.ChangeEvent<unknown>, newValue: number | number[]) => {
        setValue(newValue as number[]);
        onChange([availableDates[(newValue as number[])[0]], availableDates[(newValue as number[])[1]]], includeBlankDate);
    };

    const handleIncludeBlankDateChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setIncludeBlankDate(event.target.checked);
        onChange([availableDates[value[0]], availableDates[value[1]]], event.target.checked);
    };

    const valueLabelFormat = (index: number) => {
        const date = availableDates[index];
        return `${date.getDate().toString().padStart(2, '0')}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getFullYear()}`;
    };

    if (minDate && maxDate && minDate.getTime() === maxDate.getTime()) {
        // If minDate and maxDate are the same, show a static label
        return (
            <div>
                <p>Available Date: {valueLabelFormat(0)}</p>
                <div style={{ marginTop: '8px' }}>
                    <input
                        type="checkbox"
                        id="include-blank-date"
                        checked={includeBlankDate}
                        onChange={handleIncludeBlankDateChange}
                    />
                    <label htmlFor="include-blank-date" style={{ marginLeft: '8px' }}>Include Blank Dates</label>
                </div>
            </div>
        );
    }

    return (
        <div style={{ marginTop: '16px' }}>
            {minDate && maxDate && (
                <div style={{ display: 'flex', alignItems: 'center' }}>
                    <p>Selected range: {valueLabelFormat(value[0])} - {valueLabelFormat(value[1])}</p>
                    <div style={{ width: '30%', marginRight: '16px', marginLeft: '16px' }}>
                        <Slider
                            value={value}
                            min={0}
                            max={availableDates.length - 1}
                            marks={availableDates.map((_, index) => ({ value: index, label: '' }))}
                            step={1}
                            onChange={handleChange}
                            valueLabelDisplay="auto"
                            valueLabelFormat={valueLabelFormat}
                            disableSwap
                        />
                    </div>
                    <div>
                        <input
                            type="checkbox"
                            id="include-blank-date"
                            checked={includeBlankDate}
                            onChange={handleIncludeBlankDateChange}
                        />
                        <label htmlFor="include-blank-date" style={{ marginLeft: '8px' }}>Include Blank Dates</label>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DateRangeSlider;
