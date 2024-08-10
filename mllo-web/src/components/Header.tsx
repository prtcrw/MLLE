import React from 'react';
import Breadcrumb from './Breadcrumb.tsx';
import './styles/header.css';

const Header: React.FC<{ isMenuOpen: boolean; toggleMenu: () => void }> = ({isMenuOpen, toggleMenu}) => {
    return (
        <div className="header">
            { // Conditionally render menu icon based on isMenuOpen
                !isMenuOpen && (
                    <button onClick={toggleMenu} className="menu-icon">
                        ☰
                    </button>
                )
            }
            <Breadcrumb/>
        </div>
    );
};

export default Header;