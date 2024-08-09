import React, {useState} from 'react';
import {Link} from 'react-router-dom';

const Menu: React.FC = () => {
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    const handleMenuClick = (event: React.MouseEvent) => {
        event.stopPropagation(); // Stop click events from closing the menu
    };

    return (
        <div className="menu-container">
            <button onClick={toggleMenu} className={`menu-icon ${isMenuOpen ? 'hidden' : ''}`}>
                ☰
            </button>
            <div
                className={`menu-content ${isMenuOpen ? 'open' : ''}`}
                onClick={handleMenuClick} // Prevent menu content clicks from closing the menu
            >
                <div className="menu-header">
                    <h2 className="menu-title">MLLO</h2>
                    <button onClick={toggleMenu} className="close-button">
                        ✕
                    </button>
                </div>
                <ul>
                    <li>
                        <Link to="/">Analyzer</Link>
                        <ul className="submenu">
                            <li><Link to="/find-models">Find Models</Link></li>
                            <li><Link to="/find-pipelines">Find Pipelines</Link></li>
                            <li><Link to="/find-datasets">Find Datasets</Link></li>
                            <li><Link to="/plot-performance">Plot Performance</Link></li>
                            <li><Link to="/analyze-deployed-models">Analyze Deployed Models</Link></li>
                            <li><Link to="/compare-pipelines">Compare Pipelines</Link></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    );
};

export default Menu;
