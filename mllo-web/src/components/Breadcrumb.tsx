import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './styles/breadcrumb.css';

const Breadcrumb: React.FC = () => {
    const location = useLocation();
    const pathnames = location.pathname.split('/').filter((x) => x);

    // Utility function to capitalize the first letter of each word
    const capitalize = (str: string) => {
        return str.replace(/(^|\s)\S/g, (letter) => letter.toUpperCase());
    };

    return (
        <nav aria-label="breadcrumb">
            <ol className="breadcrumb">
                <li className="breadcrumb-item">
                    <Link to="/">Home</Link>
                </li>
                {pathnames.map((name, index) => {
                    const routeTo = `/${pathnames.slice(0, index + 1).join('/')}`;
                    const isLast = index === pathnames.length - 1;
                    const capitalizedName = capitalize(name.replace(/-/g, ' '));
                    return isLast ? (
                        <li key={name} className="breadcrumb-item active" aria-current="page">
                            {capitalizedName}
                        </li>
                    ) : (
                        <li key={name} className="breadcrumb-item">
                            <Link to={routeTo}>{capitalizedName}</Link>
                        </li>
                    );
                })}
            </ol>
        </nav>
    );
};

export default Breadcrumb;
