import React, {useState} from 'react';
import { Link } from 'react-router-dom';

const Menu: React.FC = () => {
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    const handleClickOutside = () => {
        if (isMenuOpen) {
            setIsMenuOpen(false);
        }
    };

    return (
        <div>
            {!isMenuOpen && (
                <button onClick={toggleMenu} className="menu-icon">
                    ☰
                </button>
            )}
            {isMenuOpen && (
                <>
                    <div className="menu-overlay" onClick={handleClickOutside}></div>
                    <div className="menu">
                        <div className="menu-header">
                            <h2 className="menu-title">MLLO</h2>
                            <button onClick={toggleMenu} className="close-button">
                                ✕
                            </button>
                        </div>
                        <li>
                            Analyzer
                            <ul className="submenu">
                                <li><Link to="/find-models" onClick={toggleMenu}>Find Models</Link></li>
                                <li><Link to="/find-pipelines" onClick={toggleMenu}>Find Pipelines</Link></li>
                                <li><Link to="/find-datasets" onClick={toggleMenu}>Find Datasets</Link></li>
                                <li><Link to="/plot-performance" onClick={toggleMenu}>Plot Performance</Link></li>
                                <li><Link to="/analyze-deployed-models" onClick={toggleMenu}>Analyze Deployed Models</Link></li>
                                <li><Link to="/compare-pipelines" onClick={toggleMenu}>Compare Pipelines</Link></li>
                            </ul>
                        </li>
                    </div>
                </>
            )}
        </div>
    );
};

export default Menu;
