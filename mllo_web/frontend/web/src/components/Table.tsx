import React from 'react';

interface TableProps {
  data: any[]; // Assuming any data type for now
  headers: string[];
}

const Table: React.FC<TableProps> = ({ data, headers }) => {
  return (
    <table>
      <thead>
        <tr>
          {headers.map((header, index) => (
            <th key={index}>{header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, index) => (
          <tr key={index}>
            {Object.keys(row).map((key, i) => (
              <td key={i}>{row[key]}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default Table;
