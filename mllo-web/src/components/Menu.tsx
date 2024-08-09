import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const Menu: React.FC = () => {
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    const handleClickOutside = (event: MouseEvent) => {
        const target = event.target as HTMLElement;
        if (isMenuOpen && !target.closest('.menu-container')) {
            setIsMenuOpen(false);
        }
    };

    useEffect(() => {
        document.addEventListener('click', handleClickOutside);
        return () => {
            document.removeEventListener('click', handleClickOutside);
        };
    }, [isMenuOpen]);

    return (
        <div className="menu-container">
            <button onClick={toggleMenu} className={`menu-icon ${isMenuOpen ? 'hidden' : ''}`}>
                ☰
            </button>
            <div className={`menu-content ${isMenuOpen ? 'open' : ''}`}>
                <div className="menu-header">
                    <h2 className="menu-title">MLLO</h2>
                    <button onClick={toggleMenu} className="close-button">
                        ✕
                    </button>
                </div>
                <ul>
                    <li>
                        <Link to="/analyzer" onClick={toggleMenu}>Analyzer</Link>
                        <ul className="submenu">
                            <li><Link to="/find-models" onClick={toggleMenu}>Find Models</Link></li>
                            <li><Link to="/find-pipelines" onClick={toggleMenu}>Find Pipelines</Link></li>
                            <li><Link to="/find-datasets" onClick={toggleMenu}>Find Datasets</Link></li>
                            <li><Link to="/plot-performance" onClick={toggleMenu}>Plot Performance</Link></li>
                            <li><Link to="/analyze-deployed-models" onClick={toggleMenu}>Analyze Deployed Models</Link></li>
                            <li><Link to="/compare-pipelines" onClick={toggleMenu}>Compare Pipelines</Link></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    );
};

export default Menu;
