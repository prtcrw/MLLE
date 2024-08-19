import React from "react";

const ArrowUpIcon: React.FC<{ width?: number, height?: number }> = ({width, height}) => {
    width = width || 24;
    height = height || 24;
    return (
        <svg xmlns="http://www.w3.org/2000/svg" height={`${height}px`} viewBox="0 -960 960 960" width={`${width}px`}
             fill="#5f6368">
            <path d="M440-160v-487L216-423l-56-57 320-320 320 320-56 57-224-224v487h-80Z"/>
        </svg>
    );
};

const ArrowDownIcon: React.FC<{ width?: number, height?: number }> = ({width, height}) => {
    width = width || 24;
    height = height || 24;
    return (
        <svg xmlns="http://www.w3.org/2000/svg" height={`${height}px`} viewBox="0 -960 960 960" width={`${width}px`}
             fill="#5f6368">
            <path d="M440-800v487L216-537l-56 57 320 320 320-320-56-57-224 224v-487h-80Z"/>
        </svg>
    );
};

const DownloadIcon: React.FC<{ width?: number, height?: number }> = ({width, height}) => {
    width = width || 24;
    height = height || 24;
    return (
        <svg xmlns="http://www.w3.org/2000/svg" height={`${height}px`} viewBox="0 -960 960 960" width={`${width}px`}
             fill="#5f6368">
            <path
                d="M480-320 280-520l56-58 104 104v-326h80v326l104-104 56 58-200 200ZM240-160q-33 0-56.5-23.5T160-240v-120h80v120h480v-120h80v120q0 33-23.5 56.5T720-160H240Z"/>
        </svg>
    );
};

export {ArrowUpIcon, ArrowDownIcon, DownloadIcon};