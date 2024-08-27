import React from 'react';
import {Link} from 'react-router-dom';

interface SubmenuProps {
    items: {
        label: string;
        path: string;
        children?: SubmenuProps['items'];
    }[];
    onItemClick: (event: React.MouseEvent) => void;
}

const Submenu: React.FC<SubmenuProps> = ({items, onItemClick}) => {
    return (
        <ul className="submenu">
            {items.map((item) => (
                <li key={item.label}>
                    <Link to={item.path} onClick={onItemClick}>
                        {item.label}
                    </Link>
                    {item.children && (
                        <Submenu items={item.children} onItemClick={onItemClick}/> // Recursively render sub-submenu
                    )}
                </li>
            ))}
        </ul>
    );
};

export default Submenu;
