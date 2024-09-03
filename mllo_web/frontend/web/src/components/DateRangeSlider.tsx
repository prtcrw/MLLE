import React, { useState, useEffect } from 'react';
import Slider from '@mui/material/Slider';

interface DateRangeSliderProps {
    dates: (Date | null)[];
    onChange: (dateRange: [Date | null, Date | null]) => void;
    includeBlank: boolean;
    setIncludeBlank: (value: boolean) => void;
    value: [Date | null, Date | null];
}

const DateRangeSlider: React.FC<DateRangeSliderProps> = ({
    dates,
    onChange,
    includeBlank,
    setIncludeBlank,
    value,
}) => {
    const [minDate, setMinDate] = useState<number | null>(null);
    const [maxDate, setMaxDate] = useState<number | null>(null);

    useEffect(() => {
        const validDates = dates.filter((date): date is Date => date !== null);
        if (validDates.length > 0) {
            const minTimestamp = Math.min(...validDates.map(d => d.getTime()));
            const maxTimestamp = Math.max(...validDates.map(d => d.getTime()));
            setMinDate(minTimestamp);
            setMaxDate(maxTimestamp);
        } else {
            setMinDate(null);
            setMaxDate(null);
        }
    }, [dates]);

    const handleSliderChange = (event: Event, newValue: number | number[]) => {
        const [start, end] = newValue as number[];
        onChange([new Date(start), new Date(end)]);
    };

    const formatDate = (value: number) => {
        const date = new Date(value);
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    };

    if (minDate === null || maxDate === null) {
        return (
            <div style={{ marginTop: '16px' }}>
                <div>No valid date</div>
                <div style={{ marginTop: '8px' }}>
                    <label>
                        <input
                            type="checkbox"
                            checked={includeBlank}
                            onChange={(e) => setIncludeBlank(e.target.checked)}
                        />
                        Include blank dates
                    </label>
                </div>
            </div>
        );
    }

    // Compare only the date part, ignoring time
    if (minDate === maxDate) {
        return (
            <div style={{ marginTop: '16px' }}>
                <div>Available date: {formatDate(minDate)}</div>
                <div style={{ marginTop: '8px' }}>
                    <label>
                        <input
                            type="checkbox"
                            checked={includeBlank}
                            onChange={(e) => setIncludeBlank(e.target.checked)}
                        />
                        Include blank dates
                    </label>
                </div>
            </div>
        );
    }

    const sliderValue: [number, number] = [
        value[0] ? value[0].getTime() : minDate,
        value[1] ? value[1].getTime() : maxDate
    ];

    return (
        <div style={{ width: '100%', maxWidth: '200px', padding: '16px 0' }}>
            <Slider
                value={sliderValue}
                onChange={handleSliderChange}
                valueLabelDisplay="auto"
                min={minDate}
                max={maxDate}
                valueLabelFormat={formatDate}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px' }}>
                <span>{formatDate(sliderValue[0])}</span>
                <span>{formatDate(sliderValue[1])}</span>
            </div>
            <div style={{ marginTop: '8px' }}>
                <label>
                    <input
                        type="checkbox"
                        checked={includeBlank}
                        onChange={(e) => setIncludeBlank(e.target.checked)}
                    />
                    Include blank dates
                </label>
            </div>
        </div>
    );
};

export default DateRangeSlider;
