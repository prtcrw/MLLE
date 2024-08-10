import React from 'react';
import { Link } from 'react-router-dom';

interface SubmenuProps {
    items: { label: string; path: string }[];
    onItemClick: (event: React.MouseEvent) => void;
}

const Submenu: React.FC<SubmenuProps> = ({ items, onItemClick }) => {
    return (
        <ul className="submenu">
            {items.map((item) => (
                <li key={item.label} onClick={onItemClick}>
                    <Link to={item.path}>{item.label}</Link>
                </li>
            ))}
        </ul>
    );
};

export default Submenu;
