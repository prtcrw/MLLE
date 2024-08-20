import React from 'react';
import {useSearchParams} from "react-router-dom";

const PipelineEditor: React.FC = () => {
    const [searchParams] = useSearchParams();
    const pipelineName = searchParams.get('pipeline-name');

    return (
        <div>
            <h1>PipelineEditor</h1>
            {pipelineName ? (
                <p>This is the PipelineEditor page for {pipelineName}.</p>
            ) : (
                <p>This is the PipelineEditor page.</p>
            )}
        </div>
    );
};

export default PipelineEditor;
