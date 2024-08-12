import React, {useState} from 'react';
import './styles/search.css';

interface SearchProps {
    onSearch: (searchTerm: string) => void;
    placeholder?: string; // Optional placeholder prop
}

const Search: React.FC<SearchProps> = ({onSearch, placeholder}) => {
    const [searchTerm, setSearchTerm] = useState('');

    const SearchIcon = () => {
        return (
            <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#5f6368">
                <path
                    d="M784-120 532-372q-30 24-69 38t-83 14q-109 0-184.5-75.5T120-580q0-109 75.5-184.5T380-840q109 0 184.5 75.5T640-580q0 44-14 83t-38 69l252 252-56 56ZM380-400q75 0 127.5-52.5T560-580q0-75-52.5-127.5T380-760q-75 0-127.5 52.5T200-580q0 75 52.5 127.5T380-400Z"/>
            </svg>
        );
    };

    const ClearIcon = () => {
        return (
            <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#5f6368">
                <path
                    d="m256-200-56-56 224-224-224-224 56-56 224 224 224-224 56 56-224 224 224 224-56 56-224-224-224 224Z"/>
            </svg>
        );
    };

    const handleSearch = () => {
        onSearch(searchTerm);
    };

    const handleClear = () => {
        setSearchTerm('');
    };

    const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Enter') {
            handleSearch();
        }
    };

    return (
        <div className="search-container">
            <input
                type="text"
                placeholder={placeholder || 'Search...'}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyDown={handleKeyDown}
                className="search-input"
            />
            {searchTerm && (
                <button onClick={handleClear} className="clear-button">
                    <ClearIcon/>
                </button>
            )}
            <button onClick={handleSearch}
                    className="search-button">
                <SearchIcon/>
            </button>
        </div>
    );
};

export default Search;
