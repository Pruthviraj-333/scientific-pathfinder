import { useEffect, useState } from 'react';
import { CheckCircle, Loader, Circle } from 'lucide-react';
import config from '../config';

const STEPS = [
  { id: 'librarian', label: 'Librarian', desc: 'Searching papers' },
  { id: 'cartographer', label: 'Cartographer', desc: 'Building graph' },
  { id: 'scientist', label: 'Scientist', desc: 'Analyzing gaps' },
  { id: 'complete', label: 'Complete', desc: 'Done!' },
];

export default function ProgressTracker({ session, onComplete }: any) {
  const [currentStep, setCurrentStep] = useState('librarian');
  const [messages, setMessages] = useState<string[]>([]);

  useEffect(() => {
    const ws = new WebSocket(config.ws(`/ws/${session.session_id}`));

    ws.onopen = () => {
      console.log('WebSocket connected');
      setMessages(prev => [...prev, 'Connected to server']);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket message:', data);

      if (data.type === 'progress') {
        setCurrentStep(data.step);
        setMessages(prev => [...prev, `${data.step}: ${data.message}`]);
      } else if (data.type === 'status') {
        setMessages(prev => [...prev, `${data.agent}: ${data.message}`]);
      } else if (data.type === 'complete') {
        setCurrentStep('complete'); // Set to complete
        session.result = data.data;
        setMessages(prev => [...prev, '✅ Research complete!']);
        onComplete();
      } else if (data.type === 'error') {
        setMessages(prev => [...prev, `❌ Error: ${data.message}`]);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setMessages(prev => [...prev, '❌ WebSocket connection error']);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    return () => ws.close();
  }, [session]);

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-blue-500/20 p-8">
      <h2 className="text-2xl font-bold text-white mb-6">
        ⚡ Research in Progress
      </h2>

      {/* Progress Steps */}
      <div className="flex justify-between mb-8">
        {STEPS.map((step, idx) => {
          const currentStepIndex = STEPS.findIndex((s) => s.id === currentStep);
          const isActive = step.id === currentStep && currentStep !== 'complete';
          const isComplete = currentStepIndex > idx || currentStep === 'complete';

          return (
            <div key={step.id} className="flex-1 relative">
              <div className="flex flex-col items-center">
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center border-2 ${
                    isComplete
                      ? 'bg-green-500 border-green-500'
                      : isActive
                      ? 'bg-blue-500 border-blue-500 animate-pulse'
                      : 'bg-slate-700 border-slate-600'
                  }`}
                >
                  {isComplete ? (
                    <CheckCircle className="w-6 h-6 text-white" />
                  ) : isActive ? (
                    <Loader className="w-6 h-6 text-white animate-spin" />
                  ) : (
                    <Circle className="w-6 h-6 text-slate-400" />
                  )}
                </div>
                <p className="mt-2 text-sm font-medium text-white">{step.label}</p>
                <p className="text-xs text-slate-400">{step.desc}</p>
              </div>
              {idx < STEPS.length - 1 && (
                <div
                  className={`absolute top-6 left-[60%] w-[80%] h-0.5 ${
                    isComplete ? 'bg-green-500' : 'bg-slate-600'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Activity Log */}
      <div className="bg-slate-900/50 rounded-lg p-4 max-h-60 overflow-y-auto">
        <h3 className="text-sm font-medium text-blue-200 mb-2">Activity Log</h3>
        <div className="space-y-1">
          {messages.map((msg, idx) => (
            <p key={idx} className="text-xs text-slate-300 font-mono">
              {msg}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}