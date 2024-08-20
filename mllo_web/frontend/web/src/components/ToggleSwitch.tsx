import React from 'react';
import './styles/toggleswitch.css'; 

interface ToggleSwitchProps {
    isChecked: boolean;
    onToggle: () => void;
}

const ToggleSwitch: React.FC<ToggleSwitchProps> = ({ isChecked, onToggle }) => {
    return (
        <label className="toggle-switch">
            <input
                type="checkbox"
                checked={isChecked}
                onChange={onToggle}
            />
            <span className="slider"></span>
        </label>
    );
};

export default ToggleSwitch;
