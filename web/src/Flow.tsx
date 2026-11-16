import { memo, useMemo, useState } from 'react';
import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Node,
  type NodeProps,
} from '@xyflow/react';
import {
  ArrowDown,
  Check,
  Circle,
  ScanText,
  Languages,
  ArrowLeftRight,
  Tags,
  ShieldCheck,
  UserCheck,
  FileOutput,
} from 'lucide-react';
import '@xyflow/react/dist/style.css';
import type { Definition, Run, RunEvent } from './types';

const icons = {
  intake: ScanText,
  extract: Languages,
  fx: ArrowLeftRight,
  classify: Tags,
  validate: ShieldCheck,
  review: UserCheck,
  finalize: FileOutput,
};
type StepData = {
  label: string;
  subtitle: string;
  status: string;
  duration?: number;
  stepId: string;
};
type StepNode = Node<StepData, 'step'>;

const WorkflowNode = memo(function WorkflowNode({ data, selected }: NodeProps<StepNode>) {
  const Icon = icons[data.stepId as keyof typeof icons] || Circle;
  return (
    <div className={`flow-node ${data.status} ${selected ? 'selected' : ''}`}>
      <Handle type="target" position={Position.Left} />
      <div className="flow-node-top">
        <span className="node-icon">
          <Icon size={18} />
        </span>
        <span className={`node-state ${data.status}`}>
          {data.status === 'completed' ? <Check size={12} /> : <Circle size={9} />}
          {data.status}
        </span>
      </div>
      <strong>{data.label}</strong>
      <small>{data.subtitle}</small>
      <span className="node-duration">
        {data.duration != null ? `${data.duration} ms` : 'Waiting for execution'}
      </span>
      <Handle type="source" position={Position.Right} />
    </div>
  );
});
const nodeTypes = { step: WorkflowNode };

export default function Flow({
  definition,
  events,
  run,
}: {
  definition: Definition;
  events: RunEvent[];
  run?: Run;
}) {
  const [chosen, setChosen] = useState('extract');
  const latest = useMemo(() => new Map(events.map((event) => [event.node, event])), [events]);
  const nodes: StepNode[] = definition.nodes.map((step, index) => ({
    id: step.id,
    type: 'step',
    selected: chosen === step.id,
    position: { x: index < 4 ? index * 255 : (index - 4) * 255, y: index < 4 ? 0 : 220 },
    data: {
      label: step.label,
      subtitle: step.subtitle,
      stepId: step.id,
      status: latest.get(step.id)?.status || 'pending',
      duration: latest.get(step.id)?.payload.duration_ms,
    },
  }));
  const edges = definition.edges.map((edge) => ({
    ...edge,
    id: `${edge.source}-${edge.target}`,
    type: 'smoothstep',
    animated: latest.get(edge.target)?.status === 'running',
    style: {
      stroke: latest.get(edge.source)?.status === 'completed' ? '#8ca8d1' : '#d1dbe8',
      strokeWidth: 1.7,
    },
  }));
  const step = definition.nodes.find((node) => node.id === chosen);
  const event = latest.get(chosen);
  const completed = definition.nodes.filter(
    (node) => latest.get(node.id)?.status === 'completed',
  ).length;
  return (
    <div className="workflow-page">
      <div className="workflow-summary">
        <div>
          <span className="tiny-label">Code-defined pipeline</span>
          <h2>Every step, accounted for.</h2>
          <p>
            This canvas comes from the running LangGraph definition. Select a step to inspect its
            persisted output.
          </p>
        </div>
        <span className="workflow-count">
          {completed}
          <span> / 7 steps complete</span>
        </span>
      </div>
      <div className="flow-canvas" aria-label="Document processing workflow">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={(_, node) => setChosen(node.id)}
          nodesDraggable={false}
          nodesConnectable={false}
          edgesReconnectable={false}
          deleteKeyCode={null}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          minZoom={0.35}
          maxZoom={1.5}
          proOptions={{ hideAttribution: false }}
        >
          <Background gap={20} color="#d5deea" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div className="step-inspector">
        <div className="inspector-heading">
          <div>
            <span className="tiny-label">Step inspector</span>
            <h3>{step?.label}</h3>
          </div>
          <span className={`badge ${event?.status === 'completed' ? 'approved' : 'review'}`}>
            {event?.status || 'Not run'}
          </span>
        </div>
        <p>{step?.description}</p>
        <div className="inspector-tabs">
          <span>Output</span>
          <span>
            {event?.payload.duration_ms != null
              ? `${event.payload.duration_ms} ms measured`
              : 'No measured duration'}
          </span>
        </div>
        <pre className="json-output">
          {event?.payload.output
            ? JSON.stringify(event.payload.output, null, 2)
            : event?.payload.error ||
              (chosen === 'review'
                ? 'The workflow pauses here until a reviewer approves the record.'
                : 'Run a document to inspect this step’s output.')}
        </pre>
        <div className="small-note">
          <ArrowDown size={14} />
          {run?.mode === 'demo'
            ? 'Demo uses prepared external responses; calculations, validation, persistence, and review are real.'
            : 'Inputs and outputs stay in your local data directory.'}
        </div>
      </div>
    </div>
  );
}
